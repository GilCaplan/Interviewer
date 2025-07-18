from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import json
from .auth import token_required
from .config import Config

questions = Blueprint('questions', __name__, url_prefix='/questions')

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
			"created_at": datetime.datetime.utcnow(),
			"last_updated": datetime.datetime.utcnow()
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
			"last_updated": datetime.datetime.utcnow()
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
# This is a stub that will be expanded later
@questions.route('/api/llm-questions', methods=['POST'])
@token_required
def generate_questions(user):
	try:
		data = request.get_json()

		if not data or not data.get('prompt'):
			return jsonify({
				"success": False,
				"message": "Prompt is required"
			}), 400

		# Placeholder for LLM integration
		# This will be replaced with actual LLM API calls later
		topic = data.get('prompt', '').lower()

		# Sample mock questions based on topic
		questions = []

		if 'javascript' in topic or 'js' in topic:
			questions = [
				"What's the difference between let, const and var?",
				"Explain closures in JavaScript.",
				"How does prototypal inheritance work?",
				"What is event delegation?",
				"Explain async/await and how it differs from promises."
			]
		elif 'react' in topic:
			questions = [
				"What are React hooks?",
				"Explain the component lifecycle.",
				"What is the virtual DOM?",
				"How does state differ from props?",
				"What is JSX?"
			]
		elif 'system design' in topic or 'architecture' in topic:
			questions = [
				"How would you design a URL shortening service?",
				"Design a distributed cache system.",
				"How would you approach designing Twitter's backend?",
				"Explain how you would design a notification system.",
				"Design a scalable photo-sharing application."
			]
		else:
			# Generic questions based on the provided topic
			questions = [
				f"Explain the key principles of {topic}.",
				f"What are the best practices when working with {topic}?",
				f"Describe your experience with {topic}.",
				f"How would you implement {topic} in a large-scale application?",
				f"What tools or frameworks do you prefer when working with {topic} and why?"
			]

		return jsonify({
			"success": True,
			"questions": questions
		}), 200
	except Exception as e:
		current_app.logger.error(f"Error generating questions: {str(e)}")
		return jsonify({
			"success": False,
			"message": "Failed to generate questions"
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
