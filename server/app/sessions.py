from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import secrets
import string
import uuid
from enum import Enum
from .auth import token_required, get_current_user
from .config import Config

sessions_bp = Blueprint('sessions', __name__)

# Connect to MongoDB
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
template_sessions_collection = db.template_sessions
templates_collection = db.templates
session_participants_collection = db.session_participants
session_messages_collection = db.session_messages
question_queue_collection = db.question_queue


class SessionStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CLOSED = "closed"


class QuestionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ParticipantRole(Enum):
    HOST = "host"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


def generate_session_code():
    """Generate a unique 6-character session code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def generate_session_password():
    """Generate a random session password"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))


# Create a new template building session
@sessions_bp.route('/api/sessions/create', methods=['POST'])
@token_required
def create_session(user):
    try:
        data = request.get_json() or {}

        # Generate unique session code
        session_code = generate_session_code()
        while template_sessions_collection.find_one({"session_code": session_code}):
            session_code = generate_session_code()

        # Generate password if not provided
        password = data.get('password') or generate_session_password()

        session_data = {
            "session_id": str(uuid.uuid4()),
            "session_code": session_code,
            "password": password,
            "host_user_id": user["user_id"],
            "host_username": user["username"],
            "title": data.get('title', f"Template Session {session_code}"),
            "description": data.get('description', ''),
            "max_participants": data.get('max_participants', 10),
            "max_questions": data.get('max_questions', 20),
            "template_config": {
                "subject": data.get('subject', ''),
                "sub_subject": data.get('sub_subject', ''),
                "difficulty": data.get('difficulty', 'NORMAL'),
                "question_types": data.get('question_types', ['open_ended']),
                "allow_hints": data.get('allow_hints', True)
            },
            "status": SessionStatus.ACTIVE.value,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
            "settings": {
                "llm_enabled": data.get('llm_enabled', True),
                "auto_approve_llm": data.get('auto_approve_llm', False),
                "participant_suggestions": data.get('participant_suggestions', True),
                "require_approval": data.get('require_approval', True)
            }
        }

        result = template_sessions_collection.insert_one(session_data)
        session_data["_id"] = str(result.inserted_id)

        # Add host as first participant
        participant_data = {
            "session_id": session_data["session_id"],
            "user_id": user["user_id"],
            "username": user["username"],
            "role": ParticipantRole.HOST.value,
            "joined_at": datetime.datetime.utcnow(),
            "is_active": True
        }
        session_participants_collection.insert_one(participant_data)

        return jsonify({
            "success": True,
            "session": {
                "session_id": session_data["session_id"],
                "session_code": session_code,
                "password": password,
                "title": session_data["title"],
                "description": session_data["description"],
                "max_participants": session_data["max_participants"],
                "max_questions": session_data["max_questions"],
                "template_config": session_data["template_config"],
                "settings": session_data["settings"],
                "created_at": session_data["created_at"].isoformat()
            }
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating session: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to create session"
        }), 500


# Join an existing session
@sessions_bp.route('/api/sessions/join', methods=['POST'])
@token_required
def join_session(user):
    try:
        data = request.get_json()
        session_code = data.get('session_code')
        password = data.get('password')

        if not session_code or not password:
            return jsonify({
                "success": False,
                "message": "Session code and password are required"
            }), 400

        # Find session
        session = template_sessions_collection.find_one({
            "session_code": session_code,
            "password": password,
            "status": SessionStatus.ACTIVE.value
        })

        if not session:
            return jsonify({
                "success": False,
                "message": "Invalid session code, password, or session is not active"
            }), 404

        # Check if user is already in session
        existing_participant = session_participants_collection.find_one({
            "session_id": session["session_id"],
            "user_id": user["user_id"]
        })

        if existing_participant:
            # Reactivate if they were inactive
            session_participants_collection.update_one(
                {"_id": existing_participant["_id"]},
                {"$set": {"is_active": True, "rejoined_at": datetime.datetime.utcnow()}}
            )
        else:
            # Check participant limit
            active_participants = session_participants_collection.count_documents({
                "session_id": session["session_id"],
                "is_active": True
            })

            if active_participants >= session["max_participants"]:
                return jsonify({
                    "success": False,
                    "message": "Session is full"
                }), 400

            # Add new participant
            participant_data = {
                "session_id": session["session_id"],
                "user_id": user["user_id"],
                "username": user["username"],
                "role": ParticipantRole.CONTRIBUTOR.value,
                "joined_at": datetime.datetime.utcnow(),
                "is_active": True
            }
            session_participants_collection.insert_one(participant_data)

        return jsonify({
            "success": True,
            "session": {
                "session_id": session["session_id"],
                "session_code": session["session_code"],
                "title": session["title"],
                "description": session["description"],
                "template_config": session["template_config"],
                "settings": session["settings"],
                "is_host": session["host_user_id"] == user["user_id"]
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error joining session: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to join session"
        }), 500


# Get session details and participants
@sessions_bp.route('/api/sessions/<session_id>', methods=['GET'])
@token_required
def get_session(user, session_id):
    try:
        # Verify user is participant
        participant = session_participants_collection.find_one({
            "session_id": session_id,
            "user_id": user["user_id"],
            "is_active": True
        })

        if not participant:
            return jsonify({
                "success": False,
                "message": "Not authorized to view this session"
            }), 403

        session = template_sessions_collection.find_one({"session_id": session_id})
        if not session:
            return jsonify({
                "success": False,
                "message": "Session not found"
            }), 404

        # Get all active participants
        participants = list(session_participants_collection.find({
            "session_id": session_id,
            "is_active": True
        }, {"_id": 0, "password": 0}))

        # Get current template progress
        approved_questions = list(question_queue_collection.find({
            "session_id": session_id,
            "status": QuestionStatus.APPROVED.value
        }, {"_id": 0}))

        pending_questions = list(question_queue_collection.find({
            "session_id": session_id,
            "status": QuestionStatus.PENDING.value
        }, {"_id": 0}))

        session["_id"] = str(session["_id"])

        return jsonify({
            "success": True,
            "session": session,
            "participants": participants,
            "template_progress": {
                "approved_questions": approved_questions,
                "pending_questions": pending_questions,
                "total_approved": len(approved_questions),
                "total_pending": len(pending_questions),
                "max_questions": session["max_questions"]
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting session: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to get session details"
        }), 500


# Submit a question to the queue
@sessions_bp.route('/api/sessions/<session_id>/questions', methods=['POST'])
@token_required
def submit_question(user, session_id):
    try:
        data = request.get_json()

        # Verify user is participant
        participant = session_participants_collection.find_one({
            "session_id": session_id,
            "user_id": user["user_id"],
            "is_active": True
        })

        if not participant:
            return jsonify({
                "success": False,
                "message": "Not authorized to submit questions to this session"
            }), 403

        session = template_sessions_collection.find_one({"session_id": session_id})
        if not session or session["status"] != SessionStatus.ACTIVE.value:
            return jsonify({
                "success": False,
                "message": "Session not found or not active"
            }), 404

        # Check if we've reached max questions
        approved_count = question_queue_collection.count_documents({
            "session_id": session_id,
            "status": QuestionStatus.APPROVED.value
        })

        if approved_count >= session["max_questions"]:
            return jsonify({
                "success": False,
                "message": "Template has reached maximum number of questions"
            }), 400

        question_data = {
            "question_id": str(uuid.uuid4()),
            "session_id": session_id,
            "submitted_by": user["user_id"],
            "submitted_by_username": user["username"],
            "question_text": data.get('question_text', ''),
            "answer": data.get('answer', ''),
            "question_type": data.get('question_type', 'open_ended'),
            "difficulty": data.get('difficulty', session["template_config"]["difficulty"]),
            "hints": data.get('hints', []),
            "multiple_choice_options": data.get('multiple_choice_options', []),
            "correct_answer": data.get('correct_answer', ''),
            "source": data.get('source', 'user'),  # user or llm
            "status": QuestionStatus.PENDING.value,
            "submitted_at": datetime.datetime.utcnow(),
            "metadata": data.get('metadata', {})
        }

        result = question_queue_collection.insert_one(question_data)
        question_data["_id"] = str(result.inserted_id)

        return jsonify({
            "success": True,
            "question": question_data
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error submitting question: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to submit question"
        }), 500


# Approve or reject a question (host only)
@sessions_bp.route('/api/sessions/<session_id>/questions/<question_id>/review', methods=['POST'])
@token_required
def review_question(user, session_id, question_id):
    try:
        data = request.get_json()
        action = data.get('action')  # approve or reject

        if action not in ['approve', 'reject']:
            return jsonify({
                "success": False,
                "message": "Action must be 'approve' or 'reject'"
            }), 400

        # Verify user is host
        session = template_sessions_collection.find_one({
            "session_id": session_id,
            "host_user_id": user["user_id"]
        })

        if not session:
            return jsonify({
                "success": False,
                "message": "Not authorized to review questions in this session"
            }), 403

        # Find the question
        question = question_queue_collection.find_one({
            "question_id": question_id,
            "session_id": session_id
        })

        if not question:
            return jsonify({
                "success": False,
                "message": "Question not found"
            }), 404

        # Update question status
        new_status = QuestionStatus.APPROVED.value if action == 'approve' else QuestionStatus.REJECTED.value

        question_queue_collection.update_one(
            {"question_id": question_id},
            {
                "$set": {
                    "status": new_status,
                    "reviewed_at": datetime.datetime.utcnow(),
                    "reviewed_by": user["user_id"],
                    "review_comments": data.get('comments', '')
                }
            }
        )

        return jsonify({
            "success": True,
            "message": f"Question {action}d successfully"
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error reviewing question: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to review question"
        }), 500


# Finalize template (creates final template document)
@sessions_bp.route('/api/sessions/<session_id>/finalize', methods=['POST'])
@token_required
def finalize_template(user, session_id):
    try:
        # Verify user is host
        session = template_sessions_collection.find_one({
            "session_id": session_id,
            "host_user_id": user["user_id"]
        })

        if not session:
            return jsonify({
                "success": False,
                "message": "Not authorized to finalize this session"
            }), 403

        # Get all approved questions
        approved_questions = list(question_queue_collection.find({
            "session_id": session_id,
            "status": QuestionStatus.APPROVED.value
        }, {"_id": 0, "session_id": 0, "status": 0}))

        if not approved_questions:
            return jsonify({
                "success": False,
                "message": "No approved questions to create template"
            }), 400

        # Create final template
        template_data = {
            "template_id": str(uuid.uuid4()),
            "title": session["title"],
            "description": session["description"],
            "created_by": user["user_id"],
            "created_by_username": user["username"],
            "source_session_id": session_id,
            "config": session["template_config"],
            "questions": approved_questions,
            "metadata": {
                "total_questions": len(approved_questions),
                "collaborators": list(session_participants_collection.find({
                    "session_id": session_id
                }, {"username": 1, "role": 1, "_id": 0})),
                "creation_method": "collaborative_session"
            },
            "is_public": False,  # Can be made public later
            "created_at": datetime.datetime.utcnow(),
            "tags": []
        }

        result = templates_collection.insert_one(template_data)
        template_data["_id"] = str(result.inserted_id)

        # Mark session as completed
        template_sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "status": SessionStatus.COMPLETED.value,
                    "completed_at": datetime.datetime.utcnow(),
                    "final_template_id": template_data["template_id"]
                }
            }
        )

        return jsonify({
            "success": True,
            "template": template_data
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error finalizing template: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to finalize template"
        }), 500


# Get user's sessions
@sessions_bp.route('/api/sessions/my-sessions', methods=['GET'])
@token_required
def get_user_sessions(user):
    try:
        # Get sessions where user is a participant
        user_sessions = list(session_participants_collection.find({
            "user_id": user["user_id"],
            "is_active": True
        }, {"session_id": 1, "_id": 0}))

        session_ids = [s["session_id"] for s in user_sessions]

        sessions = list(template_sessions_collection.find({
            "session_id": {"$in": session_ids}
        }, {"password": 0}))

        # Convert ObjectId to string
        for session in sessions:
            session["_id"] = str(session["_id"])
            session["is_host"] = session["host_user_id"] == user["user_id"]

        return jsonify({
            "success": True,
            "sessions": sessions
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting user sessions: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to get user sessions"
        }), 500