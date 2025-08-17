from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from datetime import datetime
from pymongo import MongoClient
from .config import Config
from .auth import token_required  # Assuming you have a token_required decorator

interviews_bp = Blueprint('interviews_bp', __name__)

# MongoDB connection, consistent with other blueprints
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()

# Helper to get the collection
def get_interview_sessions_collection():
    return db.interview_sessions


def get_templates_collection():
    return db.templates


@interviews_bp.route('/api/interviews/start', methods=['POST'])
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


@interviews_bp.route('/api/interviews/<session_id>', methods=['GET'])
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


@interviews_bp.route('/api/interviews/<session_id>/answer', methods=['POST'])
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


@interviews_bp.route('/api/interviews/<session_id>/finish', methods=['POST'])
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