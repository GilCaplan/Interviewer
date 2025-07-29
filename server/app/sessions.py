# server/app/sessions.py
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
from .templates import QUESTION_TYPES, validate_question_data
from .llm_service import LLMService

sessions_bp = Blueprint('sessions', __name__)

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
sessions_collection = db.simple_sessions  # Fixed collection name
messages_collection = db.session_messages
questions_collection = db.session_questions
users_collection = db.users

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


def mock_llm_generate_question(subject="general", context="", question_type="open_ended", question_number=1):
    """Enhanced mock LLM API that generates structured questions based on type and context"""
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
        if "question " + str(question_number) in context.lower():
            base_question = f"Question {question_number}: " + base_question

    # Generate type-specific content
    question_data = {
        "question_text": base_question,
        "difficulty": random.choice(["easy", "medium", "hard"]),
        "type": question_type,
        "hints": [
            "Think about the core concepts",
            "Consider edge cases",
            "Try to provide examples"
        ],
        "generated_by": "mock_llm",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    # Add type-specific fields
    if question_type == "multiple_choice":
        # Generate sample options based on subject
        if subject_lower == "python":
            question_data["options"] = ["True", "False", "It depends", "None of the above"]
            question_data["correct_answer"] = "True"
        else:
            question_data["options"] = ["Option A", "Option B", "Option C", "Option D"]
            question_data["correct_answer"] = "Option A"
        question_data["explanation"] = "This is the correct answer because..."
    
    elif question_type == "true_false":
        question_data["correct_answer"] = random.choice([True, False])
        question_data["explanation"] = "This statement is correct/incorrect because..."
    
    elif question_type == "coding":
        question_data["language"] = subject_lower if subject_lower in ["python", "javascript", "java"] else "python"
        question_data["starter_code"] = "# Write your solution here\ndef solution():\n    pass"
        question_data["solution"] = "# Sample solution\ndef solution():\n    return 'implemented'"
    
    elif question_type == "short_answer":
        question_data["expected_keywords"] = ["key", "concept", "important"]
        question_data["max_words"] = 50
    
    return question_data


# Create a new session
@sessions_bp.route('/api/sessions/create', methods=['POST'])
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
            "template_mode": data.get('template_mode', False),  # NEW: Flag for template building
            "settings": {
                "max_participants": data.get('max_participants', 10),
                "max_questions": data.get('max_questions', 20),  # NEW: Question limit for template
                "allow_llm": data.get('allow_llm', True),
                "allow_user_questions": data.get('allow_user_questions', True),
                "auto_approve_questions": data.get('auto_approve_questions', False),
                "question_numbering": data.get('question_numbering', True)  # NEW: Sequential numbering
            },
            "template_data": {  # NEW: Template building data
                "current_question_number": 0,
                "questions_queue": [],  # Questions being built
                "ready_questions": []   # Finalized questions
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
@sessions_bp.route('/api/sessions/join/<session_code>', methods=['POST'])
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
@sessions_bp.route('/api/sessions/<session_id>/become-host', methods=['POST'])
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
@sessions_bp.route('/api/sessions/<session_id>/llm-question', methods=['POST'])
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
@sessions_bp.route('/api/sessions/<session_id>/add-question', methods=['POST'])
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
@sessions_bp.route('/api/sessions/<session_id>/chat', methods=['POST'])
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
@sessions_bp.route('/api/sessions/<session_id>', methods=['GET'])
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
@sessions_bp.route('/api/sessions/<session_id>/questions/<question_id>/approve', methods=['POST'])
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
@sessions_bp.route('/api/sessions/list', methods=['GET'])
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


# NEW ENDPOINTS FOR STRUCTURED TEMPLATE BUILDING

# Start building a specific question number
@sessions_bp.route('/api/sessions/<session_id>/questions/<int:question_number>/start', methods=['POST'])
@token_required
def start_question_building(user, session_id, question_number):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        data = request.get_json() or {}
        question_type = data.get('type', 'open_ended')
        
        if question_type not in QUESTION_TYPES:
            return jsonify({"error": f"Invalid question type: {question_type}"}), 400
        
        # Check if question number is valid
        max_questions = session["settings"]["max_questions"]
        if question_number < 1 or question_number > max_questions:
            return jsonify({"error": f"Question number must be between 1 and {max_questions}"}), 400
        
        # Check if question with this number already exists
        questions_queue = session.get("template_data", {}).get("questions_queue", [])
        ready_questions = session.get("template_data", {}).get("ready_questions", [])
        
        for q in questions_queue + ready_questions:
            if q.get("question_number") == question_number:
                return jsonify({"error": f"Question {question_number} already exists"}), 400
        
        # Initialize question structure
        question_structure = {
            "question_number": question_number,
            "type": question_type,
            "status": "building",  # building, ready, finalized
            "created_by": user["username"],
            "created_at": datetime.datetime.utcnow(),
            "question_id": str(uuid.uuid4()),
            "collaboration_notes": [],
            "llm_suggestions": [],
            "user_content": {}
        }
        
        # Add type-specific template fields
        type_config = QUESTION_TYPES[question_type]
        for field in type_config['required_fields'] + type_config['optional_fields']:
            question_structure["user_content"][field] = ""
        
        # Update session with new question
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"template_data.questions_queue": question_structure},
                "$set": {
                    "template_data.current_question_number": question_number,
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
        
        # Broadcast to all participants
        emit('question_building_started', {
            'question_number': question_number,
            'question_type': question_type,
            'started_by': user["username"],
            'question_structure': question_structure
        }, room=session_id, namespace='/')
        
        return jsonify({
            "message": f"Started building question {question_number}",
            "question": question_structure
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error starting question building: {str(e)}")
        return jsonify({"error": "Failed to start question building"}), 500


# Update question content (collaborative editing)
@sessions_bp.route('/api/sessions/<session_id>/questions/<question_id>/update', methods=['PUT'])
@token_required
def update_question_content(user, session_id, question_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        data = request.get_json() or {}
        field_name = data.get('field')
        field_value = data.get('value')
        
        if not field_name:
            return jsonify({"error": "Field name is required"}), 400
        
        # Find the question in the queue
        questions_queue = session.get("template_data", {}).get("questions_queue", [])
        question_index = None
        
        for i, q in enumerate(questions_queue):
            if q["question_id"] == question_id:
                question_index = i
                break
        
        if question_index is None:
            return jsonify({"error": "Question not found in building queue"}), 404
        
        current_question = questions_queue[question_index]
        
        # Validate field for question type
        type_config = QUESTION_TYPES[current_question["type"]]
        allowed_fields = type_config['required_fields'] + type_config['optional_fields']
        
        if field_name not in allowed_fields:
            return jsonify({"error": f"Field '{field_name}' not allowed for question type '{current_question['type']}'"}), 400
        
        # Update the field
        update_path = f"template_data.questions_queue.{question_index}.user_content.{field_name}"
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    update_path: field_value,
                    f"template_data.questions_queue.{question_index}.updated_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
        
        # Broadcast update to all participants
        emit('question_content_updated', {
            'question_id': question_id,
            'question_number': current_question["question_number"],
            'field': field_name,
            'value': field_value,
            'updated_by': user["username"]
        }, room=session_id, namespace='/')
        
        return jsonify({
            "message": "Question content updated",
            "field": field_name,
            "value": field_value
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating question content: {str(e)}")
        return jsonify({"error": "Failed to update question content"}), 500


# Generate LLM suggestion for specific question field
@sessions_bp.route('/api/sessions/<session_id>/questions/<question_id>/llm-suggest', methods=['POST'])
@token_required
def generate_llm_suggestion(user, session_id, question_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        if not session["settings"]["allow_llm"]:
            return jsonify({"error": "LLM suggestions are disabled for this session"}), 400
        
        data = request.get_json() or {}
        field_name = data.get('field', 'question_text')
        context = data.get('context', '')
        
        # Find the question
        questions_queue = session.get("template_data", {}).get("questions_queue", [])
        current_question = None
        
        for q in questions_queue:
            if q["question_id"] == question_id:
                current_question = q
                break
        
        if not current_question:
            return jsonify({"error": "Question not found"}), 404
        
        # Generate LLM suggestion
        subject = session.get('subject', 'general')
        question_type = current_question["type"]
        question_number = current_question["question_number"]
        
        # Build context with existing question content
        existing_content = current_question.get("user_content", {})
        full_context = f"{context}. Question {question_number}. Existing content: {existing_content}"
        
        llm_response = LLMService.generate_question(
            subject=subject,
            context=full_context,
            question_type=question_type,
            question_number=question_number
        )
        
        # Extract the requested field from LLM response
        suggested_value = llm_response.get(field_name, f"LLM suggestion for {field_name}")
        
        suggestion_data = {
            "suggestion_id": str(uuid.uuid4()),
            "field": field_name,
            "suggested_value": suggested_value,
            "full_llm_response": llm_response,
            "context_used": full_context,
            "generated_at": datetime.datetime.utcnow(),
            "requested_by": user["username"]
        }
        
        # Save suggestion to question
        sessions_collection.update_one(
            {"session_id": session_id, "template_data.questions_queue.question_id": question_id},
            {
                "$push": {"template_data.questions_queue.$.llm_suggestions": suggestion_data},
                "$set": {"updated_at": datetime.datetime.utcnow()}
            }
        )
        
        # Broadcast to participants
        emit('llm_suggestion_generated', {
            'question_id': question_id,
            'question_number': current_question["question_number"],
            'suggestion': suggestion_data,
            'requested_by': user["username"]
        }, room=session_id, namespace='/')
        
        return jsonify({
            "message": "LLM suggestion generated",
            "suggestion": suggestion_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error generating LLM suggestion: {str(e)}")
        return jsonify({"error": "Failed to generate LLM suggestion"}), 500


# Add collaboration note to question
@sessions_bp.route('/api/sessions/<session_id>/questions/<question_id>/note', methods=['POST'])
@token_required
def add_collaboration_note(user, session_id, question_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        data = request.get_json() or {}
        note_text = data.get('note', '').strip()
        
        if not note_text:
            return jsonify({"error": "Note text is required"}), 400
        
        note_data = {
            "note_id": str(uuid.uuid4()),
            "note": note_text,
            "author": user["username"],
            "timestamp": datetime.datetime.utcnow(),
            "field_reference": data.get('field_reference')  # Optional: which field this note refers to
        }
        
        # Add note to question
        sessions_collection.update_one(
            {"session_id": session_id, "template_data.questions_queue.question_id": question_id},
            {
                "$push": {"template_data.questions_queue.$.collaboration_notes": note_data},
                "$set": {"updated_at": datetime.datetime.utcnow()}
            }
        )
        
        # Broadcast to participants
        emit('collaboration_note_added', {
            'question_id': question_id,
            'note': note_data
        }, room=session_id, namespace='/')
        
        return jsonify({
            "message": "Collaboration note added",
            "note": note_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error adding collaboration note: {str(e)}")
        return jsonify({"error": "Failed to add collaboration note"}), 500


# Finalize question (move from queue to ready questions)
@sessions_bp.route('/api/sessions/<session_id>/questions/<question_id>/finalize', methods=['POST'])
@token_required
def finalize_question(user, session_id, question_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can finalize questions
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can finalize questions"}), 403
        
        # Find and remove question from queue
        questions_queue = session.get("template_data", {}).get("questions_queue", [])
        question_to_finalize = None
        updated_queue = []
        
        for q in questions_queue:
            if q["question_id"] == question_id:
                question_to_finalize = q
            else:
                updated_queue.append(q)
        
        if not question_to_finalize:
            return jsonify({"error": "Question not found in building queue"}), 404
        
        # Validate question completeness
        question_type = question_to_finalize["type"]
        user_content = question_to_finalize.get("user_content", {})
        
        is_valid, validation_message = validate_question_data(question_type, user_content)
        if not is_valid:
            return jsonify({"error": f"Question validation failed: {validation_message}"}), 400
        
        # Prepare finalized question
        finalized_question = {
            "question_id": question_to_finalize["question_id"],
            "question_number": question_to_finalize["question_number"],
            "type": question_type,
            "status": "finalized",
            "created_by": question_to_finalize["created_by"],
            "finalized_by": user["username"],
            "created_at": question_to_finalize["created_at"],
            "finalized_at": datetime.datetime.utcnow(),
            **user_content  # Include all the question content
        }
        
        # Update session: remove from queue, add to ready questions
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "template_data.questions_queue": updated_queue,
                    "updated_at": datetime.datetime.utcnow()
                },
                "$push": {"template_data.ready_questions": finalized_question}
            }
        )
        
        # Broadcast to participants
        emit('question_finalized', {
            'question': finalized_question,
            'finalized_by': user["username"]
        }, room=session_id, namespace='/')
        
        return jsonify({
            "message": f"Question {question_to_finalize['question_number']} finalized successfully",
            "question": finalized_question
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error finalizing question: {str(e)}")
        return jsonify({"error": "Failed to finalize question"}), 500


# Convert session to template
@sessions_bp.route('/api/sessions/<session_id>/convert-to-template', methods=['POST'])
@token_required
def convert_session_to_template(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can convert to template
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can convert session to template"}), 403
        
        data = request.get_json() or {}
        
        # Get finalized questions
        ready_questions = session.get("template_data", {}).get("ready_questions", [])
        
        if not ready_questions:
            return jsonify({"error": "No finalized questions to convert"}), 400
        
        # Import templates collection
        from .templates import templates_collection
        
        # Create template data
        template_data = {
            "template_id": str(uuid.uuid4()),
            "template_name": data.get('template_name', session.get('title', 'Converted Template')),
            "description": data.get('description', f"Converted from session {session['session_code']}"),
            "subject": session.get('subject', 'general'),
            "sub_subject": data.get('sub_subject', ''),
            "difficulty": data.get('difficulty', 'medium'),
            "created_by": user["username"],
            "created_by_id": user["user_id"],
            "is_public": data.get('is_public', False),
            "tags": data.get('tags', []),
            "metadata": {
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
                "version": 1,
                "question_count": len(ready_questions),
                "estimated_time": len(ready_questions) * 3,  # 3 minutes per question estimate
                "converted_from_session": session_id
            },
            "settings": {
                "max_questions": len(ready_questions),
                "allow_shuffle": data.get('allow_shuffle', True),
                "show_hints": data.get('show_hints', True),
                "time_limit": data.get('time_limit', len(ready_questions) * 3)
            },
            "questions": ready_questions
        }
        
        # Save template
        result = templates_collection.insert_one(template_data)
        template_data.pop('_id', None)
        
        # Update session to mark as converted
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "converted_to_template": template_data["template_id"],
                    "conversion_date": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
        
        return jsonify({
            "message": "Session converted to template successfully",
            "template": template_data
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error converting session to template: {str(e)}")
        return jsonify({"error": "Failed to convert session to template"}), 500


# Update session mode/visibility settings
@sessions_bp.route('/api/sessions/<session_id>/settings', methods=['PUT'])
@token_required
def update_session_settings(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can update settings
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can update session settings"}), 403
        
        data = request.get_json() or {}
        
        # Updatable settings
        update_fields = {}
        if 'viewing_mode' in data:  # edit, view_only, suggestions_only
            update_fields['settings.viewing_mode'] = data['viewing_mode']
        if 'allow_llm' in data:
            update_fields['settings.allow_llm'] = data['allow_llm']
        if 'allow_user_questions' in data:
            update_fields['settings.allow_user_questions'] = data['allow_user_questions']
        if 'max_participants' in data:
            update_fields['settings.max_participants'] = data['max_participants']
        
        if update_fields:
            update_fields['updated_at'] = datetime.datetime.utcnow()
            
            sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": update_fields}
            )
            
            # Broadcast settings update to all participants
            emit('session_settings_updated', {
                'session_id': session_id,
                'settings': data,
                'updated_by': user["username"]
            }, room=session_id, namespace='/')
        
        return jsonify({"message": "Session settings updated successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating session settings: {str(e)}")
        return jsonify({"error": "Failed to update session settings"}), 500


# Get session participants details
@sessions_bp.route('/api/sessions/<session_id>/participants', methods=['GET'])
@token_required
def get_session_participants(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        # Get participant details from users collection
        participant_usernames = session.get("participants", [])
        participant_details = []
        
        for username in participant_usernames:
            user_info = users_collection.find_one({"username": username}, {"_id": 0, "username": 1, "user_id": 1, "is_guest": 1, "created_at": 1})
            if user_info:
                user_info['is_host'] = username == session["host_username"]
                user_info['online'] = True  # TODO: Implement real online status
                participant_details.append(user_info)
        
        return jsonify({
            "participants": participant_details,
            "total_count": len(participant_details),
            "host": session["host_username"]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting session participants: {str(e)}")
        return jsonify({"error": "Failed to get session participants"}), 500


# General LLM chat endpoint for session
@sessions_bp.route('/api/sessions/<session_id>/llm-chat', methods=['POST'])
@token_required
def llm_chat(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        if not session["settings"]["allow_llm"]:
            return jsonify({"error": "LLM chat is disabled for this session"}), 400
        
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Build context from session
        context = f"Session: {session.get('title', 'Untitled')}, Subject: {session.get('subject', 'general')}"
        
        # Get LLM response
        llm_response = LLMService.generate_chat_response(message, context)
        
        # Store the chat message
        chat_data = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_message": message,
            "llm_response": llm_response["response"],
            "username": user["username"],
            "timestamp": datetime.datetime.utcnow(),
            "generated_by": llm_response["generated_by"]
        }
        
        # Store in messages collection or session data
        messages_collection.insert_one(chat_data)
        
        # Broadcast to all participants
        emit('llm_chat_response', {
            'message_id': chat_data["message_id"],
            'user_message': message,
            'llm_response': llm_response["response"],
            'username': user["username"],
            'timestamp': chat_data["timestamp"].isoformat()
        }, room=session_id, namespace='/')
        
        return jsonify({
            "message": "LLM chat response generated",
            "response": llm_response["response"],
            "message_id": chat_data["message_id"]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error with LLM chat: {str(e)}")
        return jsonify({"error": "Failed to process LLM chat"}), 500


# Get session chat history
@sessions_bp.route('/api/sessions/<session_id>/chat-history', methods=['GET'])
@token_required
def get_chat_history(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        # Get chat messages for this session
        chat_messages = list(messages_collection.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", 1).limit(100))  # Last 100 messages
        
        return jsonify({
            "messages": chat_messages,
            "total_count": len(chat_messages)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({"error": "Failed to get chat history"}), 500