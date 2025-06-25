# server/app/simple_sessions.py
from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit, join_room, leave_room
from pymongo import MongoClient
import datetime
import secrets
import string
import uuid
import random
from .auth import token_required
from .config import Config

sessions = Blueprint('sessions', __name__)

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
sessions_collection = db.sessions
messages_collection = db.session_messages
questions_collection = db.session_questions

# Mock LLM responses for different subjects
MOCK_LLM_RESPONSES = {
    "python": [
        "What is the difference between a list and a tuple in Python?",
        "Explain the concept of list comprehensions with an example.",
        "How do you handle exceptions in Python?",
        "What are decorators and how do you use them?",
        "Explain the difference between __str__ and __repr__ methods."
    ],
    "javascript": [
        "What is the difference between let, const, and var?",
        "Explain event bubbling and event capturing.",
        "What are promises and how do they work?",
        "What is the difference between == and === in JavaScript?",
        "Explain the concept of closures with an example."
    ],
    "algorithms": [
        "Implement a binary search algorithm.",
        "Explain the time complexity of quicksort.",
        "What is the difference between BFS and DFS?",
        "How would you detect a cycle in a linked list?",
        "Implement a function to reverse a binary tree."
    ],
    "system_design": [
        "How would you design a URL shortener like bit.ly?",
        "Explain how you would design a chat application.",
        "How would you scale a web application to handle millions of users?",
        "Design a caching system for a web application.",
        "How would you design a file storage system like Dropbox?"
    ]
}


def generate_session_code():
    """Generate a 6-character session code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def mock_llm_generate_question(subject="general", context=""):
    """Mock LLM API that generates questions based on subject"""
    subject_lower = subject.lower()

    # Find matching subject
    questions = MOCK_LLM_RESPONSES.get(subject_lower, MOCK_LLM_RESPONSES["python"])

    # Add some randomness and context awareness
    base_question = random.choice(questions)

    if context:
        # Simple context awareness
        if "beginner" in context.lower():
            base_question = "Beginner level: " + base_question
        elif "advanced" in context.lower():
            base_question = "Advanced: " + base_question

    return {
        "question": base_question,
        "difficulty": random.choice(["easy", "medium", "hard"]),
        "type": "multiple_choice" if random.choice([True, False]) else "open_ended",
        "hints": [
            "Think about the core concepts",
            "Consider edge cases",
            "Try to provide examples"
        ],
        "generated_by": "mock_llm",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


# Create a new session
@sessions.route('/api/sessions/create', methods=['POST'])
@token_required
def create_session(user):
    try:
        data = request.get_json() or {}

        # Generate unique session code
        session_code = generate_session_code()
        while sessions_collection.find_one({"session_code": session_code}):
            session_code = generate_session_code()

        session_data = {
            "session_id": str(uuid.uuid4()),
            "session_code": session_code,
            "title": data.get('title', f"Question Session {session_code}"),
            "subject": data.get('subject', 'general'),
            "description": data.get('description', ''),
            "host_id": user["user_id"],
            "host_username": user["username"],
            "participants": [user["username"]],
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
            "status": "active",
            "settings": {
                "max_participants": data.get('max_participants', 10),
                "allow_llm": data.get('allow_llm', True),
                "allow_user_questions": data.get('allow_user_questions', True),
                "auto_approve_questions": data.get('auto_approve_questions', False)
            }
        }

        result = sessions_collection.insert_one(session_data)

        # Remove MongoDB ObjectId for response
        session_data.pop('_id', None)

        return jsonify({
            "message": "Session created successfully",
            "session": session_data
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating session: {str(e)}")
        return jsonify({"error": "Failed to create session"}), 500


# Join a session
@sessions.route('/api/sessions/join/<session_code>', methods=['POST'])
@token_required
def join_session(user, session_code):
    try:
        session = sessions_collection.find_one({"session_code": session_code.upper()})

        if not session:
            return jsonify({"error": "Session not found"}), 404

        if session["status"] != "active":
            return jsonify({"error": "Session is not active"}), 400

        # Check if user is already in session
        if user["username"] not in session["participants"]:
            # Check participant limit
            if len(session["participants"]) >= session["settings"]["max_participants"]:
                return jsonify({"error": "Session is full"}), 400

            # Add user to session
            sessions_collection.update_one(
                {"session_code": session_code.upper()},
                {
                    "$push": {"participants": user["username"]},
                    "$set": {"updated_at": datetime.datetime.utcnow()}
                }
            )

        # Get updated session
        updated_session = sessions_collection.find_one({"session_code": session_code.upper()})
        updated_session.pop('_id', None)

        return jsonify({
            "message": "Joined session successfully",
            "session": updated_session
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error joining session: {str(e)}")
        return jsonify({"error": "Failed to join session"}), 500


# Become host (take over hosting)
@sessions.route('/api/sessions/<session_id>/become-host', methods=['POST'])
@token_required
def become_host(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})

        if not session:
            return jsonify({"error": "Session not found"}), 404

        if user["username"] not in session["participants"]:
            return jsonify({"error": "You must be a participant to become host"}), 400

        # Update host
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "host_id": user["user_id"],
                    "host_username": user["username"],
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )

        # Broadcast host change to all participants
        emit('host_changed', {
            'new_host': user["username"],
            'timestamp': datetime.datetime.utcnow().isoformat()
        }, room=session_id, namespace='/')

        return jsonify({"message": f"{user['username']} is now the host"}), 200

    except Exception as e:
        current_app.logger.error(f"Error changing host: {str(e)}")
        return jsonify({"error": "Failed to change host"}), 500


# Get LLM generated question
@sessions.route('/api/sessions/<session_id>/llm-question', methods=['POST'])
@token_required
def get_llm_question(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})

        if not session:
            return jsonify({"error": "Session not found"}), 404

        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403

        if not session["settings"]["allow_llm"]:
            return jsonify({"error": "LLM questions are disabled for this session"}), 400

        data = request.get_json() or {}
        subject = data.get('subject', session.get('subject', 'general'))
        context = data.get('context', '')

        # Generate question using mock LLM
        llm_response = mock_llm_generate_question(subject, context)

        # Save question to database
        question_data = {
            "question_id": str(uuid.uuid4()),
            "session_id": session_id,
            "question_text": llm_response["question"],
            "difficulty": llm_response["difficulty"],
            "type": llm_response["type"],
            "hints": llm_response["hints"],
            "source": "llm",
            "created_by": "mock_llm",
            "created_at": datetime.datetime.utcnow(),
            "status": "pending",  # Host needs to approve
            "subject": subject
        }

        questions_collection.insert_one(question_data)
        question_data.pop('_id', None)

        return jsonify({
            "message": "LLM question generated",
            "question": question_data
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error generating LLM question: {str(e)}")
        return jsonify({"error": "Failed to generate question"}), 500


# User submits their own question
@sessions.route('/api/sessions/<session_id>/add-question', methods=['POST'])
@token_required
def add_user_question(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})

        if not session:
            return jsonify({"error": "Session not found"}), 404

        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403

        if not session["settings"]["allow_user_questions"]:
            return jsonify({"error": "User questions are disabled for this session"}), 400

        data = request.get_json() or {}

        if not data.get('question_text'):
            return jsonify({"error": "Question text is required"}), 400

        question_data = {
            "question_id": str(uuid.uuid4()),
            "session_id": session_id,
            "question_text": data["question_text"],
            "difficulty": data.get('difficulty', 'medium'),
            "type": data.get('type', 'open_ended'),
            "hints": data.get('hints', []),
            "source": "user",
            "created_by": user["username"],
            "created_at": datetime.datetime.utcnow(),
            "status": "approved" if session["settings"]["auto_approve_questions"] else "pending",
            "subject": data.get('subject', session.get('subject', 'general'))
        }

        questions_collection.insert_one(question_data)
        question_data.pop('_id', None)

        return jsonify({
            "message": "Question added successfully",
            "question": question_data
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error adding user question: {str(e)}")
        return jsonify({"error": "Failed to add question"}), 500


# Send chat message
@sessions.route('/api/sessions/<session_id>/chat', methods=['POST'])
@token_required
def send_chat_message(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})

        if not session:
            return jsonify({"error": "Session not found"}), 404

        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403

        data = request.get_json() or {}
        message_text = data.get('message', '').strip()

        if not message_text:
            return jsonify({"error": "Message cannot be empty"}), 400

        message_data = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "username": user["username"],
            "message": message_text,
            "timestamp": datetime.datetime.utcnow(),
            "type": data.get('type', 'chat')  # chat, question_suggestion, etc.
        }

        messages_collection.insert_one(message_data)
        message_data.pop('_id', None)

        # Broadcast message to all session participants
        emit('new_message', message_data, room=session_id, namespace='/')

        return jsonify({
            "message": "Message sent",
            "chat_message": message_data
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error sending message: {str(e)}")
        return jsonify({"error": "Failed to send message"}), 500


# Get session data (questions, messages, etc.)
@sessions.route('/api/sessions/<session_id>', methods=['GET'])
@token_required
def get_session_data(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})

        if not session:
            return jsonify({"error": "Session not found"}), 404

        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403

        # Get questions
        questions = list(questions_collection.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("created_at", 1))

        # Get recent messages
        messages = list(messages_collection.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50))
        messages.reverse()  # Show chronologically

        session.pop('_id', None)

        return jsonify({
            "session": session,
            "questions": questions,
            "messages": messages
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting session data: {str(e)}")
        return jsonify({"error": "Failed to get session data"}), 500


# Approve/reject questions (host only)
@sessions.route('/api/sessions/<session_id>/questions/<question_id>/approve', methods=['POST'])
@token_required
def approve_question(user, session_id, question_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})

        if not session:
            return jsonify({"error": "Session not found"}), 404

        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can approve questions"}), 403

        data = request.get_json() or {}
        action = data.get('action', 'approve')  # approve or reject

        if action not in ['approve', 'reject']:
            return jsonify({"error": "Invalid action"}), 400

        # Update question status
        result = questions_collection.update_one(
            {"question_id": question_id, "session_id": session_id},
            {"$set": {"status": "approved" if action == "approve" else "rejected"}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Question not found"}), 404

        return jsonify({"message": f"Question {action}d successfully"}), 200

    except Exception as e:
        current_app.logger.error(f"Error approving question: {str(e)}")
        return jsonify({"error": "Failed to approve question"}), 500


# List all active sessions
@sessions.route('/api/sessions/list', methods=['GET'])
@token_required
def list_sessions(user):
    try:
        # Get sessions where user is a participant
        user_sessions = list(sessions_collection.find(
            {"participants": user["username"], "status": "active"},
            {
                "_id": 0,
                "session_id": 1,
                "session_code": 1,
                "title": 1,
                "subject": 1,
                "host_username": 1,
                "participants": 1,
                "created_at": 1
            }
        ).sort("created_at", -1))

        return jsonify({"sessions": user_sessions}), 200

    except Exception as e:
        current_app.logger.error(f"Error listing sessions: {str(e)}")
        return jsonify({"error": "Failed to list sessions"}), 500