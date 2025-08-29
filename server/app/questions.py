from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import json
from .auth import token_required
from .config import Config
from .llm_service import LLMService
from .rate_limiter import rate_limit

questions = Blueprint('questions', __name__)

# Connect to MongoDB
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
# questions_collection = db.interview_questions
questions_collection = db['interview_questions']


# Get all questions for a user
@questions.route('/api/questions', methods=['GET'])
@token_required
def get_user_questions(user):
	try:
		# Get user's questions
		user_questions = list(questions_collection.find({"user_id": user["user_id"]}))

		# Convert ObjectId to string for JSON serialization
		for question in user_questions:
			question["_id"] = str(question["_id"])

		return jsonify({
			"success": True,
			"questions": user_questions
		}), 200
	except Exception as e:
		current_app.logger.error(f"Error fetching questions: {str(e)}")
		return jsonify({
			"success": False,
			"message": "Failed to retrieve questions"
		}), 500


# Add a new question
@questions.route('/api/questions', methods=['POST'])
@token_required
def add_question(user):
	try:
		data = request.get_json()

		if not data or not data.get('question'):
			return jsonify({
				"success": False,
				"message": "Question text is required"
			}), 400

		# Create new question document
		new_question = {
			"user_id": user["user_id"],
			"question": data.get('question'),
			"answer": data.get('answer', ''),
			"category": data.get('category', 'general'),
			"created_at": datetime.utcnow(),
			"last_updated": datetime.utcnow()
		}

		# Insert question into database
		result = questions_collection.insert_one(new_question)

		# Return success response with the ID
		return jsonify({
			"success": True,
			"message": "Question added successfully",
			"question_id": str(result.inserted_id)
		}), 201
	except Exception as e:
		current_app.logger.error(f"Error adding question: {str(e)}")
		return jsonify({
			"success": False,
			"message": "Failed to add question"
		}), 500


# Update an existing question
@questions.route('/api/questions/<question_id>', methods=['PUT'])
@token_required
def update_question(user, question_id):
	try:
		data = request.get_json()

		if not data:
			return jsonify({
				"success": False,
				"message": "No update data provided"
			}), 400

		# Find the question and check ownership
		question = questions_collection.find_one({
			"_id": ObjectId(question_id),
			"user_id": user["user_id"]
		})

		if not question:
			return jsonify({
				"success": False,
				"message": "Question not found or you don't have permission to update it"
			}), 404

		# Update the question
		updates = {
			"question": data.get('question', question["question"]),
			"answer": data.get('answer', question["answer"]),
			"category": data.get('category', question["category"]),
			"last_updated": datetime.utcnow()
		}

		questions_collection.update_one(
			{"_id": ObjectId(question_id)},
			{"$set": updates}
		)

		return jsonify({
			"success": True,
			"message": "Question updated successfully"
		}), 200
	except Exception as e:
		current_app.logger.error(f"Error updating question: {str(e)}")
		return jsonify({
			"success": False,
			"message": "Failed to update question"
		}), 500


# Delete a question
@questions.route('/api/questions/<question_id>', methods=['DELETE'])
@token_required
def delete_question(user, question_id):
	try:
		# Find the question and check ownership
		question = questions_collection.find_one({
			"_id": ObjectId(question_id),
			"user_id": user["user_id"]
		})

		if not question:
			return jsonify({
				"success": False,
				"message": "Question not found or you don't have permission to delete it"
			}), 404

		# Delete the question
		questions_collection.delete_one({"_id": ObjectId(question_id)})

		return jsonify({
			"success": True,
			"message": "Question deleted successfully"
		}), 200
	except Exception as e:
		current_app.logger.error(f"Error deleting question: {str(e)}")
		return jsonify({
			"success": False,
			"message": "Failed to delete question"
		}), 500


# LLM-generated questions endpoint
@questions.route('/api/llm-questions', methods=['POST'])
@rate_limit('llm', 30, 3600, per_user=True)  # 30 LLM requests per hour per user
@token_required
def generate_questions(user):
	"""Generate questions using Gemini API"""
	try:
		data = request.get_json()
		
		# Validate input
		if not data:
			return jsonify({
				"success": False,
				"message": "Request data is required"
			}), 400

		subject = data.get('subject', data.get('prompt', 'general'))
		question_type = data.get('question_type', 'open_ended')
		context = data.get('context', '')
		count = min(int(data.get('count', 1)), 5)  # Max 5 questions per request
		
		# Check if LLM service is available
		if not LLMService.is_available():
			llm_status = LLMService.get_llm_status()
			return jsonify({
				"success": False,
				"message": "LLM service unavailable. Please check your Gemini API key configuration.",
				"llm_status": llm_status,
				"fallback": True
			}), 503

		# Generate questions using Gemini API
		generated_questions = []
		
		for i in range(count):
			try:
				# Generate question using LLM service
				question_data = LLMService.generate_question(
					subject=subject,
					context=context + f" (Question {i+1} of {count})",
					question_type=question_type,
					question_number=i+1
				)
				
				# Extract the question text and metadata
				question_info = {
					"question_text": question_data.get("question_text", ""),
					"type": question_data.get("type", question_type),
					"difficulty": question_data.get("difficulty", "medium"),
					"subject": question_data.get("subject", subject),
					"generated_by": question_data.get("generated_by", "unknown"),
					"llm_source": question_data.get("llm_source", "unknown"),
					"timestamp": question_data.get("timestamp"),
					"question_number": i + 1
				}
				
				# Add type-specific fields
				if question_type == "multiple_choice":
					question_info.update({
						"options": question_data.get("options", []),
						"correct_answer": question_data.get("correct_answer", ""),
						"explanation": question_data.get("explanation", "")
					})
				elif question_type == "true_false":
					question_info.update({
						"correct_answer": question_data.get("correct_answer", True),
						"explanation": question_data.get("explanation", "")
					})
				elif question_type == "coding":
					question_info.update({
						"language": question_data.get("language", "python"),
						"starter_code": question_data.get("starter_code", ""),
						"solution": question_data.get("solution", ""),
						"test_cases": question_data.get("test_cases", [])
					})
				elif question_type == "short_answer":
					question_info.update({
						"expected_keywords": question_data.get("expected_keywords", []),
						"sample_answers": question_data.get("sample_answers", []),
						"max_words": question_data.get("max_words", 50)
					})
				else:  # open_ended
					question_info.update({
						"sample_answer": question_data.get("sample_answer", ""),
						"grading_criteria": question_data.get("grading_criteria", [])
					})
				
				# Add hints if available
				if question_data.get("hints"):
					question_info["hints"] = question_data["hints"]
				
				generated_questions.append(question_info)
				
			except Exception as question_error:
				current_app.logger.error(f"Error generating question {i+1}: {str(question_error)}")
				# Add a fallback question
				generated_questions.append({
					"question_text": f"Sample {subject} question {i+1}: Explain a key concept in {subject}.",
					"type": question_type,
					"difficulty": "medium",
					"subject": subject,
					"generated_by": "fallback",
					"llm_source": "mock",
					"question_number": i + 1,
					"error": "LLM generation failed, using fallback"
				})

		return jsonify({
			"success": True,
			"questions": generated_questions,
			"count": len(generated_questions),
			"llm_status": {
				"service": "gemini",
				"available": True,
				"generated_by": generated_questions[0].get("generated_by", "unknown") if generated_questions else "unknown"
			}
		}), 200
		
	except Exception as e:
		current_app.logger.error(f"Error in LLM questions endpoint: {str(e)}")
		return jsonify({
			"success": False,
			"message": "Failed to generate questions",
			"error": str(e)
		}), 500


@questions.route("/insert_dummy", methods=["GET"])
@token_required
def insert_dummy_template():
	try:
		# Connect to MongoDB
		client = MongoClient(Config.MONGO_URI)
		db = client.get_default_database()
		# questions_collection = db.interview_questions
		templates_collection = db['templates']

		dummy_template = {
			"template_name": "Dummy Template: Algorithms",
			"created_by": "admin@example.com",
			"public": True,
			"difficulty": "NORMAL",
			"subject": "Algorithms",
			"sub_subject": "Sorting",
			"questions": [
				{
					"question_text": "What is the time complexity of quicksort in the average case?",
					"type": "MCQ",
					"choices": ["O(n)", "O(n log n)", "O(n^2)", "O(log n)"],
					"correct_answer": "O(n log n)"
				},
				{
					"question_text": "Explain why merge sort is stable.",
					"type": "OPEN",
					"hints": ["Think about equal elements and their order"]
				}
			],
			"metadata": {
				"created_at": datetime.utcnow().isoformat(),
				"usage_count": 0
			}
		}

		result = templates_collection.insert_one(dummy_template)
		return jsonify({"message": "Dummy template inserted", "id": str(result.inserted_id)}), 200

	except Exception as e:
		current_app.logger.error(f"Failed to insert dummy template: {e}")
		return jsonify({"message": "Failed to insert dummy template message", "error": str(e)}), 500
