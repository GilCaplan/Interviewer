from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import json
import subprocess
import tempfile
import os
from .auth import token_required
from .config import Config

coding_challenges = Blueprint('coding_challenges', __name__)

# Connect to MongoDB
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
challenges_collection = db.coding_challenges
submissions_collection = db.coding_submissions


# Get all coding challenges
@coding_challenges.route('/api/coding-challenges', methods=['GET'])
@token_required
def get_all_challenges(user):
    try:
        # Get all challenges
        all_challenges = list(challenges_collection.find())

        # Get user's submissions to check completion status
        user_submissions = list(submissions_collection.find({
            "user_id": user["user_id"],
            "status": "success"
        }))

        # Create a set of challenge IDs that the user has completed
        completed_challenges = set(submission["challenge_id"] for submission in user_submissions)

        # Format challenges for response
        formatted_challenges = []
        for challenge in all_challenges:
            challenge["_id"] = str(challenge["_id"])
            challenge["id"] = challenge["_id"]  # For frontend compatibility

            # Check if user has completed this challenge
            challenge["completion"] = str(challenge["_id"]) in completed_challenges

            formatted_challenges.append(challenge)

        return jsonify({
            "success": True,
            "challenges": formatted_challenges
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching challenges: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to retrieve challenges"
        }), 500


# Get a specific coding challenge
@coding_challenges.route('/api/coding-challenges/<challenge_id>', methods=['GET'])
@token_required
def get_challenge(user, challenge_id):
    try:
        # Find the challenge
        challenge = challenges_collection.find_one({"_id": ObjectId(challenge_id)})

        if not challenge:
            return jsonify({
                "success": False,
                "message": "Challenge not found"
            }), 404

        # Check if user has completed this challenge
        completion = submissions_collection.find_one({
            "user_id": user["user_id"],
            "challenge_id": challenge_id,
            "status": "success"
        })

        # Format challenge for response
        challenge["_id"] = str(challenge["_id"])
        challenge["id"] = challenge["_id"]  # For frontend compatibility
        challenge["completion"] = completion is not None

        return jsonify({
            "success": True,
            "challenge": challenge
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching challenge: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to retrieve challenge"
        }), 500


# Create a new coding challenge
@coding_challenges.route('/api/coding-challenges', methods=['POST'])
@token_required
def create_challenge(user):
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['title', 'description', 'difficulty', 'starterCode']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False,
                    "message": f"Field {field} is required"
                }), 400

        # Create new challenge document
        new_challenge = {
            "title": data["title"],
            "description": data["description"],
            "difficulty": data["difficulty"],
            "starterCode": data["starterCode"],
            "tags": data.get("tags", []),
            "examples": data.get("examples", []),
            "constraints": data.get("constraints", []),
            "testCases": data.get("testCases", []),
            "author_id": user["user_id"],
            "author": user["username"],
            "created_at": datetime.datetime.utcnow(),
            "last_updated": datetime.datetime.utcnow()
        }

        # Insert challenge into database
        result = challenges_collection.insert_one(new_challenge)

        # Format the new challenge for response
        new_challenge["_id"] = str(result.inserted_id)
        new_challenge["id"] = new_challenge["_id"]  # For frontend compatibility

        return jsonify({
            "success": True,
            "message": "Challenge created successfully",
            "challenge": new_challenge
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error creating challenge: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to create challenge"
        }), 500


# Run code for a challenge
@coding_challenges.route('/api/run-code', methods=['POST'])
@token_required
def run_code(user):
    try:
        data = request.get_json()

        # Validate required fields
        if not data or not data.get('code') or not data.get('challengeId'):
            return jsonify({
                "success": False,
                "message": "Code and challenge ID are required"
            }), 400

        challenge_id = data["challengeId"]
        code = data["code"]
        language = data.get("language", "python")

        # Get the challenge to retrieve test cases
        challenge = challenges_collection.find_one({"_id": ObjectId(challenge_id)})

        if not challenge:
            return jsonify({
                "success": False,
                "message": "Challenge not found"
            }), 404

        # Run the code with test cases
        test_results = run_tests(code, challenge["testCases"], language)

        # Check if all tests passed
        all_passed = all(test["passed"] for test in test_results)

        # If all tests passed, record the successful submission
        if all_passed:
            submission = {
                "user_id": user["user_id"],
                "challenge_id": challenge_id,
                "code": code,
                "language": language,
                "status": "success",
                "submitted_at": datetime.datetime.utcnow()
            }
            submissions_collection.insert_one(submission)

        return jsonify({
            "success": True,
            "output": "Code execution completed",
            "testResults": test_results,
            "allPassed": all_passed
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error running code: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Failed to run code: {str(e)}"
        }), 500


# Helper function to run tests
def run_tests(code, test_cases, language):
    results = []

    if language == "python":
        for idx, test_case in enumerate(test_cases):
            test_result = {
                "id": idx,
                "name": f"Test Case {idx + 1}",
                "input": test_case.get("input", ""),
                "expected": test_case.get("expectedOutput", ""),
                "actual": "",
                "passed": False
            }

            try:
                # Create a temporary file with the user's code and test
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
                    function_name = test_case.get("functionName", "solution")

                    # Write the user's code
                    f.write(code.encode())

                    # Add test runner code
                    test_code = f"\n\n# Test runner\nif __name__ == '__main__':\n"
                    test_code += f"    try:\n"
                    test_code += f"        result = {function_name}({test_case['input']})\n"
                    test_code += f"        print(repr(result))\n"
                    test_code += f"    except Exception as e:\n"
                    test_code += f"        print(f'Error: {{str(e)}}')\n"

                    f.write(test_code.encode())
                    temp_filename = f.name

                # Run the code in a subprocess
                process = subprocess.Popen(
                    ['python3', temp_filename],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(timeout=5)

                # Get the result
                if process.returncode == 0:
                    actual_output = stdout.decode().strip()
                    if actual_output.startswith("Error:"):
                        test_result["actual"] = actual_output
                        test_result["passed"] = False
                    else:
                        test_result["actual"] = actual_output

                        # Compare with expected output (with flexible comparison for different string formats)
                        expected = test_case["expectedOutput"].strip()
                        # Try to normalize both outputs for comparison
                        try:
                            expected_eval = eval(expected)
                            actual_eval = eval(actual_output)
                            test_result["passed"] = expected_eval == actual_eval
                        except:
                            # Fall back to string comparison
                            test_result["passed"] = expected == actual_output
                else:
                    test_result["actual"] = f"Error: {stderr.decode()}"
                    test_result["passed"] = False

                # Clean up temp file
                os.unlink(temp_filename)

            except subprocess.TimeoutExpired:
                test_result["actual"] = "Error: Execution timed out"
                test_result["passed"] = False
            except Exception as e:
                test_result["actual"] = f"Error: {str(e)}"
                test_result["passed"] = False

            results.append(test_result)

    return results