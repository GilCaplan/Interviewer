from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient
from .config import Config
from .auth import token_required  # Assuming you have a token_required decorator

interviews_bp = Blueprint('interviews_bp', __name__)

# MongoDB connection, consistent with other blueprints
client = MongoClient(Config.get_mongo_uri())
db = client.get_default_database()

# Helper to get the collection
def get_interview_sessions_collection():
    return db.interview_sessions


def get_templates_collection():
    return db.templates


@interviews_bp.route('/api/interview/start', methods=['POST'])
@token_required
def start_interview_session(current_user):
    """
    Starts a new mock interview session from a template.
    Expects { "template_id": "..." } in the request body.
    """
    data = request.get_json()
    if not data or 'template_id' not in data:
        return jsonify({"error": "Template ID is required"}), 400

    template_id_str = data['template_id']

    # Find the template using the public-facing UUID string
    template = get_templates_collection().find_one({"template_id": template_id_str})
    if not template:
        return jsonify({"error": "Template not found"}), 404

    # Defend against starting an interview with an empty template
    if not template.get("questions"):
        return jsonify({"error": "Cannot start an interview with a template that has no questions"}), 400

    # Get the internal MongoDB _id for referencing
    template_oid = template['_id']

    # Create a new interview session document
    session_doc = {
        "user_id": current_user["user_id"],
        "template_id": template_oid,
        "template_name": template.get("template_name"),
        "status": "in_progress",  # e.g., in_progress, completed
        "started_at": datetime.utcnow(),
        "ended_at": None,
        "current_question_index": 0,
        "questions": template.get("questions", []),
        "answers": []  # Will store user answers
    }

    result = get_interview_sessions_collection().insert_one(session_doc)
    session_id = str(result.inserted_id)

    return jsonify({
        "message": "Interview session started successfully",
        "interview_session_id": session_id
    }), 201


@interviews_bp.route('/api/interview/<session_id>', methods=['GET'])
@token_required
def get_interview_session(current_user, session_id):
    """
    Retrieves the state of a specific interview session.
    """
    try:
        session_oid = ObjectId(session_id)
    except Exception:
        return jsonify({"error": "Invalid session ID format"}), 400

    session = get_interview_sessions_collection().find_one({"_id": session_oid})

    if not session:
        return jsonify({"error": "Interview session not found"}), 404

    # Ensure the user owns this session
    if session.get("user_id") != current_user["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403

    # Convert ObjectIds to strings for JSON serialization
    session['_id'] = str(session['_id'])
    session['template_id'] = str(session['template_id'])

    return jsonify({"session": session}), 200


@interviews_bp.route('/api/interview/<session_id>/answer', methods=['POST'])
@token_required
def submit_answer(current_user, session_id):
    """
    Submits an answer for the current question and moves to the next.
    Expects { "answer": "..." } in the request body.
    """
    data = request.get_json()
    if not data or 'answer' not in data:
        return jsonify({"error": "Answer is required"}), 400

    try:
        session_oid = ObjectId(session_id)
    except Exception:
        return jsonify({"error": "Invalid session ID format"}), 400

    session = get_interview_sessions_collection().find_one({"_id": session_oid})

    if not session:
        return jsonify({"error": "Interview session not found"}), 404

    if session.get("user_id") != current_user["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403

    if session.get("status") != "in_progress":
        return jsonify({"error": "Interview is not in progress"}), 400

    current_index = session.get("current_question_index", 0)
    total_questions = len(session.get("questions", []))

    if current_index >= total_questions:
        return jsonify({"error": "No more questions in this interview"}), 400

    # Get the current question to check the answer
    current_question = session["questions"][current_index]
    correct_answer = current_question.get("correct_answer")
    user_answer = data["answer"]

    # Determine if the answer is correct (case-insensitive for strings)
    is_correct = False
    if correct_answer is not None:
        if isinstance(correct_answer, str):
            is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        elif isinstance(correct_answer, bool):
            is_correct = user_answer.lower() == str(correct_answer).lower()
        else:
            # Handles other potential types like numbers
            is_correct = user_answer == correct_answer

    # Store the answer
    answer_doc = {
        "question_index": current_index,
        "question_text": current_question.get("question_text"),
        "answer": user_answer,
        "submitted_at": datetime.utcnow(),
        "is_correct": is_correct,
        "correct_answer": correct_answer  # Store for review
    }

    # Move to the next question
    next_index = current_index + 1

    get_interview_sessions_collection().update_one(
        {"_id": session_oid},
        {
            "$push": {"answers": answer_doc},
            "$set": {"current_question_index": next_index}
        }
    )

    return jsonify({
        "message": "Answer submitted successfully",
        "next_question_index": next_index
    }), 200


@interviews_bp.route('/api/interview/<session_id>/finish', methods=['POST'])
@token_required
def finish_interview(current_user, session_id):
    """
    Marks the interview session as completed.
    """
    try:
        session_oid = ObjectId(session_id)
    except Exception:
        return jsonify({"error": "Invalid session ID format"}), 400

    update_result = get_interview_sessions_collection().update_one(
        {"_id": session_oid, "user_id": current_user["user_id"]},
        {
            "$set": {
                "status": "completed",
                "ended_at": datetime.utcnow()
            }
        }
    )

    if update_result.matched_count == 0:
        return jsonify({"error": "Interview session not found or unauthorized"}), 404

    return jsonify({"message": "Interview finished successfully"}), 200


@interviews_bp.route('/api/interview/questions/save', methods=['POST'])
@token_required
def save_interview_question(current_user):
    """
    Saves a custom question created during interview preparation.
    Expects: {
        "question_text": "...",
        "question_type": "open_ended|multiple_choice|true_false|coding",
        "options": [...], // for multiple choice
        "correct_answer": "...", // optional
        "hints": "...", // optional
        "category": "...", // optional
        "difficulty": "easy|medium|hard", // optional
        "metadata": {...} // optional additional data
    }
    """
    try:
        data = request.get_json()
        if not data or not data.get('question_text'):
            return jsonify({"error": "Question text is required"}), 400

        # Clean and validate the question data
        question_data = {
            "user_id": current_user["user_id"],
            "question_text": data.get('question_text', '').strip(),
            "question_type": data.get('question_type', 'open_ended'),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "source": "interview_creation",
            "is_ai_generated": data.get('is_ai_generated', False)
        }

        # Add optional fields if provided
        if data.get('options') and data.get('question_type') == 'multiple_choice':
            question_data['options'] = data['options']
        
        if data.get('correct_answer'):
            question_data['correct_answer'] = data['correct_answer']
        
        if data.get('hints'):
            question_data['hints'] = data['hints']
        
        if data.get('category'):
            question_data['category'] = data['category']
        
        if data.get('difficulty'):
            question_data['difficulty'] = data['difficulty']
        
        if data.get('metadata'):
            question_data['metadata'] = data['metadata']

        # Insert into questions collection
        result = db.questions.insert_one(question_data)
        question_data['_id'] = str(result.inserted_id)

        current_app.logger.info(f"Question saved by user {current_user['user_id']}: {question_data['question_text'][:50]}...")

        return jsonify({
            "message": "Question saved successfully",
            "question_id": str(result.inserted_id),
            "question": question_data
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error saving interview question: {str(e)}")
        return jsonify({"error": "Failed to save question"}), 500


@interviews_bp.route('/api/interview/questions/my', methods=['GET'])
@token_required
def get_my_interview_questions(current_user):
    """
    Retrieves all questions saved by the current user during interview preparation.
    Supports filtering by category, difficulty, and question type.
    """
    try:
        # Get query parameters for filtering
        category = request.args.get('category')
        difficulty = request.args.get('difficulty') 
        question_type = request.args.get('question_type')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 questions
        skip = int(request.args.get('skip', 0))

        # Build filter query
        filter_query = {"user_id": current_user["user_id"]}
        
        if category:
            filter_query["category"] = category
        if difficulty:
            filter_query["difficulty"] = difficulty
        if question_type:
            filter_query["question_type"] = question_type

        # Get questions with pagination
        cursor = db.questions.find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
        questions = []
        
        for question in cursor:
            question['_id'] = str(question['_id'])
            questions.append(question)

        # Get total count for pagination
        total_count = db.questions.count_documents(filter_query)

        return jsonify({
            "questions": questions,
            "total_count": total_count,
            "page_info": {
                "limit": limit,
                "skip": skip,
                "has_more": skip + len(questions) < total_count
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving user questions: {str(e)}")
        return jsonify({"error": "Failed to retrieve questions"}), 500


@interviews_bp.route('/api/interview/questions/<question_id>', methods=['PUT'])
@token_required  
def update_interview_question(current_user, question_id):
    """
    Updates a saved interview question.
    Only the question owner can update their questions.
    """
    try:
        question_oid = ObjectId(question_id)
    except Exception:
        return jsonify({"error": "Invalid question ID format"}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided"}), 400

        # Verify question ownership
        existing_question = db.questions.find_one({"_id": question_oid, "user_id": current_user["user_id"]})
        if not existing_question:
            return jsonify({"error": "Question not found or unauthorized"}), 404

        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}
        
        # Only update fields that are provided
        allowed_fields = ['question_text', 'question_type', 'options', 'correct_answer', 'hints', 'category', 'difficulty', 'metadata']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400

        # Update the question
        result = db.questions.update_one(
            {"_id": question_oid},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Question not found"}), 404

        # Return updated question
        updated_question = db.questions.find_one({"_id": question_oid})
        updated_question['_id'] = str(updated_question['_id'])

        current_app.logger.info(f"Question updated by user {current_user['user_id']}: {question_id}")

        return jsonify({
            "message": "Question updated successfully",
            "question": updated_question
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error updating interview question: {str(e)}")
        return jsonify({"error": "Failed to update question"}), 500


@interviews_bp.route('/api/interview/questions/<question_id>', methods=['DELETE'])
@token_required
def delete_interview_question(current_user, question_id):
    """
    Deletes a saved interview question.
    Only the question owner can delete their questions.
    """
    try:
        question_oid = ObjectId(question_id)
    except Exception:
        return jsonify({"error": "Invalid question ID format"}), 400

    try:
        # Delete the question (only if owned by current user)
        result = db.questions.delete_one({"_id": question_oid, "user_id": current_user["user_id"]})

        if result.deleted_count == 0:
            return jsonify({"error": "Question not found or unauthorized"}), 404

        current_app.logger.info(f"Question deleted by user {current_user['user_id']}: {question_id}")

        return jsonify({"message": "Question deleted successfully"}), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting interview question: {str(e)}")
        return jsonify({"error": "Failed to delete question"}), 500