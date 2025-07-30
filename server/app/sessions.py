# server/app/sessions.py
from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit, join_room, leave_room
from pymongo import MongoClient
import datetime
import secrets
import string
import uuid
import random
import re
import html
import hashlib
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


def hash_session_password(password):
    """Hash a session password using SHA-256 with salt"""
    if not password:
        return None
    
    # Generate a random salt
    salt = secrets.token_hex(16)  # 32-character hex string
    
    # Create hash using SHA-256
    password_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    hash_obj = hashlib.sha256(password_bytes + salt_bytes)
    password_hash = hash_obj.hexdigest()
    
    # Store salt and hash together, separated by '$'
    return f"{salt}${password_hash}"


def verify_session_password(password, stored_hash):
    """Verify a session password against its hash"""
    if not password or not stored_hash:
        return False
    
    try:
        # Split stored hash into salt and hash
        if '$' not in stored_hash:
            return False
        
        salt, expected_hash = stored_hash.split('$', 1)
        
        # Hash the provided password with the stored salt
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        hash_obj = hashlib.sha256(password_bytes + salt_bytes)
        actual_hash = hash_obj.hexdigest()
        
        # Compare hashes using secure comparison
        return secrets.compare_digest(expected_hash, actual_hash)
    except (ValueError, TypeError, AttributeError):
        return False


def clean_session_for_response(session):
    """Remove sensitive data from session before sending to client"""
    if session:
        # Create a copy to avoid modifying original
        clean_session = dict(session)
        # Remove password hash from response
        clean_session.pop('password_hash', None)
        clean_session.pop('_id', None)
        return clean_session
    return session


def clean_user_input(text):
    """Clean and secure user text input"""
    if not text or not isinstance(text, str):
        return ""
    
    # Remove control chars (except basic whitespace)
    text = ''.join(c for c in text if ord(c) >= 32 or c in '\t\n\r')
    
    # Prevent DoS with length limit
    text = text[:10000] if len(text) > 10000 else text
    
    # Basic XSS protection
    text = html.escape(text, quote=True)
    
    # Remove common attack patterns
    bad_patterns = [
        r'<script.*?</script>', r'javascript:', r'vbscript:', 
        r'on\w+\s*=', r'<iframe', r'<object', r'<embed',
        r';\s*(drop|delete|exec)', r'union\s+select'
    ]
    
    for pattern in bad_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Clean up path traversal and remaining tags
    text = re.sub(r'\.\.[\\/]', '', text)
    text = re.sub(r'<[^>]*>', '', text)
    
    return text.strip()


def is_valid_session_code(session_code):
    """Check if session code is valid format"""
    return (session_code and isinstance(session_code, str) and 
            re.match(r'^[A-Z0-9]{6}$', session_code.upper()))


def is_valid_uuid(question_id):
    """Check if string is a valid UUID"""
    if not question_id or not isinstance(question_id, str):
        return False
    try:
        uuid.UUID(question_id)
        return True
    except ValueError:
        return False


def validate_session_data(data):
    """Validate and sanitize session creation data with enhanced security"""
    if not isinstance(data, dict):
        raise ValueError("Session data must be a dictionary")
    
    # Check for suspicious patterns
    data_str = str(data).lower()
    suspicious_patterns = [
        'drop table', 'delete from', 'union select', 'exec ', 'xp_cmdshell',
        'script>', '<img', 'javascript:', 'onerror=', 'onload=',
        '../', '..\\', '%2e%2e', 'etc/passwd', 'system32'
    ]
    
    for pattern in suspicious_patterns:
        if pattern in data_str:
            raise ValueError(f"Suspicious content detected: {pattern}")
    
    clean_data = {}
    
    # Title validation with enhanced security
    title = data.get('title', '')
    if not isinstance(title, str):
        title = str(title) if title is not None else ''
    title = title.strip()
    
    if len(title) > 1000:  # Reject extremely long titles
        raise ValueError("Title too long")
    
    if title:
        clean_data['title'] = clean_user_input(title)[:100]  # Max 100 chars
    else:
        clean_data['title'] = 'Untitled Session'
    
    # Subject validation with whitelist
    valid_subjects = ['general', 'python', 'javascript', 'algorithms', 'system_design', 'java', 'react', 'databases']
    subject = data.get('subject', 'general')
    if not isinstance(subject, str):
        subject = 'general'
    subject = subject.lower().strip()
    clean_data['subject'] = subject if subject in valid_subjects else 'general'
    
    # Description validation with enhanced sanitization
    description = data.get('description', '')
    if not isinstance(description, str):
        description = str(description) if description is not None else ''
    description = description.strip()
    
    if len(description) > 5000:  # Reject extremely long descriptions
        raise ValueError("Description too long")
        
    clean_data['description'] = clean_user_input(description)[:500]  # Max 500 chars
    
    # Settings validation with type safety
    settings = data.get('settings', {})
    if not isinstance(settings, dict):
        settings = {}
    
    # Helper functions for data conversion
    def get_int(value, default, min_val, max_val):
        try:
            num = int(value) if isinstance(value, (int, float, str)) and str(value).isdigit() else default
            return max(min_val, min(num, max_val))
        except:
            return default
    
    def get_bool(value, default):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value) if isinstance(value, (int, float)) else default
    
    # Set limits and features
    clean_data['max_participants'] = get_int(settings.get('max_participants', 10), 10, 1, 50)
    clean_data['max_questions'] = get_int(settings.get('max_questions', 20), 20, 1, 100)
    clean_data['allow_llm'] = get_bool(settings.get('allow_llm', True), True)
    clean_data['allow_user_questions'] = get_bool(settings.get('allow_user_questions', True), True)
    clean_data['auto_approve_questions'] = get_bool(settings.get('auto_approve_questions', False), False)
    clean_data['question_numbering'] = get_bool(settings.get('question_numbering', True), True)
    clean_data['template_mode'] = get_bool(data.get('template_mode', False), False)
    
    # Password validation (optional)
    password = data.get('password', '')
    if password:
        if not isinstance(password, str):
            raise ValueError("Password must be a string")
        password = password.strip()
        
        # Password security requirements
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters long")
        if len(password) > 50:
            raise ValueError("Password too long (max 50 characters)")
            
        # Check for suspicious patterns in password
        if any(pattern in password.lower() for pattern in ['script>', '<img', 'javascript:', 'drop table']):
            raise ValueError("Invalid characters in password")
            
        clean_data['password'] = password
    else:
        clean_data['password'] = None
    
    return clean_data


def validate_question_content(field_name, field_value, question_type):
    """Validate and sanitize question content"""
    if not isinstance(field_name, str) or not field_name.strip():
        return None, "Invalid field name"
    
    # Get allowed fields for this question type
    if question_type not in QUESTION_TYPES:
        return None, f"Invalid question type: {question_type}"
    
    type_config = QUESTION_TYPES[question_type]
    allowed_fields = type_config['required_fields'] + type_config['optional_fields']
    
    if field_name not in allowed_fields:
        return None, f"Field '{field_name}' not allowed for question type '{question_type}'"
    
    # Sanitize based on field type
    if field_name in ['question_text', 'explanation', 'sample_answer', 'starter_code', 'solution']:
        # Text fields
        if isinstance(field_value, str):
            sanitized_value = clean_user_input(field_value)
            if len(sanitized_value) > 5000:  # Max 5000 chars for text fields
                return None, "Text content too long (max 5000 characters)"
            return sanitized_value, None
        else:
            return "", None
    
    elif field_name in ['options', 'expected_keywords', 'grading_criteria']:
        # Array fields
        if isinstance(field_value, list):
            sanitized_array = []
            for item in field_value[:20]:  # Max 20 items
                if isinstance(item, str):
                    sanitized_item = clean_user_input(item)
                    if sanitized_item and len(sanitized_item) <= 200:  # Max 200 chars per item
                        sanitized_array.append(sanitized_item)
            return sanitized_array, None
        else:
            return [], None
    
    elif field_name == 'correct_answer':
        # Special handling for correct_answer based on question type
        if question_type == 'true_false':
            return bool(field_value), None
        elif question_type == 'multiple_choice' and isinstance(field_value, str):
            return clean_user_input(field_value)[:200], None
        else:
            return clean_user_input(str(field_value))[:200], None
    
    elif field_name in ['max_words', 'time_limit']:
        # Numeric fields
        try:
            num_value = int(field_value)
            return max(1, min(num_value, 10000)), None  # Between 1 and 10000
        except (ValueError, TypeError):
            return 1, None
    
    elif field_name == 'language':
        # Programming language field
        valid_languages = ['python', 'javascript', 'java', 'cpp', 'c', 'go', 'rust']
        lang = str(field_value).lower().strip()
        return lang if lang in valid_languages else 'python', None
    
    else:
        # Default string sanitization
        return clean_user_input(str(field_value))[:1000], None


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
        # Basic validation
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400
            
        # Clean and validate the input
        try:
            clean_data = validate_session_data(data)
        except (ValueError, TypeError) as e:
            current_app.logger.warning(f"Bad session data from {user.get('username', 'unknown')}: {str(e)}")
            return jsonify({"error": "Invalid session data"}), 400

        # Generate unique session code
        session_code = generate_session_code()
        while sessions_collection.find_one({"session_code": session_code}):
            session_code = generate_session_code()

        # Handle password protection
        password_hash = hash_session_password(clean_data['password']) if clean_data['password'] else None

        session_data = {
            "session_id": str(uuid.uuid4()),
            "session_code": session_code,
            "title": clean_data['title'],
            "subject": clean_data['subject'],
            "description": clean_data['description'],
            "host_id": user["user_id"],
            "host_username": user["username"],
            "participants": [user["username"]],
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
            "status": "active",
            "template_mode": clean_data['template_mode'],
            "settings": {
                "max_participants": clean_data['max_participants'],
                "max_questions": clean_data['max_questions'],
                "allow_llm": clean_data['allow_llm'],
                "allow_user_questions": clean_data['allow_user_questions'],
                "auto_approve_questions": clean_data['auto_approve_questions'],
                "question_numbering": clean_data['question_numbering']
            },
            "template_data": {
                "current_question_number": 0,
                "questions_queue": [],
                "ready_questions": []
            },
            "password_hash": password_hash,
            "is_password_protected": password_hash is not None
        }

        sessions_collection.insert_one(session_data)

        # Return clean session data (no password hash)
        return jsonify({
            "message": "Session created successfully",
            "session": clean_session_for_response(session_data)
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

        # Check password if session is password protected
        if session.get("is_password_protected", False):
            data = request.get_json() if request.is_json else {}
            provided_password = data.get('password', '').strip()
            
            if not provided_password:
                return jsonify({
                    "error": "Password required", 
                    "password_required": True
                }), 401
            
            stored_hash = session.get("password_hash")
            if not stored_hash or not verify_session_password(provided_password, stored_hash):
                return jsonify({
                    "error": "Invalid password",
                    "password_required": True
                }), 401

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
        clean_updated_session = clean_session_for_response(updated_session)

        return jsonify({
            "message": "Joined session successfully",
            "session": clean_updated_session
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

        # Clean session data for response (remove password hash)
        clean_session = clean_session_for_response(session)

        return jsonify({
            "session": clean_session,
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


# List all active sessions (both /api/sessions and /api/sessions/list for compatibility)
@sessions_bp.route('/api/sessions', methods=['GET'])
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
        # Validate inputs
        if not is_valid_uuid(question_id):
            return jsonify({"error": "Invalid question ID format"}), 400
        
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
            current_app.logger.error(f"Question {question_id} not found in queue. Available: {[q['question_id'] for q in questions_queue]}")
            return jsonify({"error": "Question not found in building queue"}), 404
        
        current_question = questions_queue[question_index]
        
        # Validate and sanitize the field content
        sanitized_value, error_msg = validate_question_content(field_name, field_value, current_question["type"])
        
        if error_msg:
            return jsonify({"error": error_msg}), 400
        
        # Update the field with sanitized value
        update_path = f"template_data.questions_queue.{question_index}.user_content.{field_name}"
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    update_path: sanitized_value,
                    f"template_data.questions_queue.{question_index}.updated_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
        
        current_app.logger.info(f"Updated question {question_id} field '{field_name}' with value: {sanitized_value}")
        
        # Broadcast update to all participants
        emit('question_content_updated', {
            'question_id': question_id,
            'question_number': current_question["question_number"],
            'field': field_name,
            'value': sanitized_value,
            'updated_by': user["username"]
        }, room=session_id, namespace='/')
        
        return jsonify({
            "message": "Question content updated",
            "field": field_name,
            "value": sanitized_value
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
        # Validate inputs
        if not is_valid_uuid(question_id):
            return jsonify({"error": "Invalid question ID format"}), 400
            
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can finalize questions
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can finalize questions"}), 403
        
        # Get fresh session data to ensure we have latest state
        fresh_session = sessions_collection.find_one({"session_id": session_id})
        if not fresh_session:
            return jsonify({"error": "Session not found"}), 404
            
        # Find and remove question from queue
        questions_queue = fresh_session.get("template_data", {}).get("questions_queue", [])
        ready_questions = fresh_session.get("template_data", {}).get("ready_questions", [])
        
        # Debug logging
        current_app.logger.info(f"Finalize attempt - Question ID: {question_id}")
        current_app.logger.info(f"Questions in queue: {[q.get('question_id') for q in questions_queue]}")
        current_app.logger.info(f"Questions already ready: {[q.get('question_id') for q in ready_questions]}")
        
        question_to_finalize = None
        updated_queue = []
        
        for q in questions_queue:
            if q.get("question_id") == question_id:
                question_to_finalize = q
                current_app.logger.info(f"Found question to finalize: Q{q.get('question_number')}")
            else:
                updated_queue.append(q)
        
        if not question_to_finalize:
            # Check if it's already finalized
            for q in ready_questions:
                if q.get("question_id") == question_id:
                    return jsonify({"error": "Question is already finalized"}), 400
            
            current_app.logger.error(f"Question {question_id} not found. Available IDs: {[q.get('question_id') for q in questions_queue]}")
            return jsonify({"error": f"Question not found in building queue. Available questions: {[q.get('question_id') for q in questions_queue]}"}), 404
        
        # Validate question completeness with basic checks
        question_type = question_to_finalize.get("type")
        user_content = question_to_finalize.get("user_content", {})
        
        # Basic validation - at least question_text should exist
        if not user_content.get("question_text", "").strip():
            return jsonify({"error": "Question text is required before finalizing"}), 400
        
        # Type-specific validation
        if question_type == "multiple_choice":
            options = user_content.get("options", [])
            correct_answer = user_content.get("correct_answer", "")
            if not options or len([opt for opt in options if opt.strip()]) < 2:
                return jsonify({"error": "Multiple choice questions need at least 2 options"}), 400
            if not correct_answer.strip():
                return jsonify({"error": "Multiple choice questions need a correct answer"}), 400
        elif question_type == "true_false":
            correct_answer = user_content.get("correct_answer")
            if correct_answer is None:
                return jsonify({"error": "True/false questions need a correct answer"}), 400
        
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
            "user_content": user_content  # Preserve structure
        }
        
        # Copy all user content fields to top level for easier access
        for field, value in user_content.items():
            if field not in finalized_question:
                finalized_question[field] = value
        
        current_app.logger.info(f"Finalizing question {question_id} with content: {user_content}")
        
        # Update session: remove from queue, add to ready questions
        update_result = sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "template_data.questions_queue": updated_queue,
                    "updated_at": datetime.datetime.utcnow()
                },
                "$push": {"template_data.ready_questions": finalized_question}
            }
        )
        
        if update_result.modified_count == 0:
            current_app.logger.error(f"Failed to update session during finalization")
            return jsonify({"error": "Failed to update session"}), 500
        
        current_app.logger.info(f"Successfully finalized question {question_id}")
        
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


# DEBUG: Get detailed session state  
@sessions_bp.route('/api/sessions/<session_id>/debug', methods=['GET'])
@token_required
def debug_session_state(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if user["username"] not in session["participants"]:
            return jsonify({"error": "Access denied"}), 403
        
        template_data = session.get("template_data", {})
        questions_queue = template_data.get("questions_queue", [])
        ready_questions = template_data.get("ready_questions", [])
        
        debug_info = {
            "session_id": session_id,
            "template_data": template_data,
            "questions_in_queue": len(questions_queue),
            "questions_ready": len(ready_questions),
            "queue_question_ids": [q.get("question_id") for q in questions_queue],
            "queue_question_numbers": [q.get("question_number") for q in questions_queue],
            "ready_question_ids": [q.get("question_id") for q in ready_questions],
            "ready_question_numbers": [q.get("question_number") for q in ready_questions],
            "queue_details": questions_queue,
            "ready_details": ready_questions
        }
        
        return jsonify({"debug": debug_info}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error debugging session: {str(e)}")
        return jsonify({"error": "Failed to debug session"}), 500


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


# DELETE SESSION AND CLEANUP ENDPOINTS

# Delete entire session (host only)
@sessions_bp.route('/api/sessions/<session_id>', methods=['DELETE'])
@token_required
def delete_session(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can delete session
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can delete the session"}), 403
        
        # Delete session and all related data
        sessions_collection.delete_one({"session_id": session_id})
        
        # Clean up related data
        messages_collection.delete_many({"session_id": session_id})
        questions_collection.delete_many({"session_id": session_id})
        
        current_app.logger.info(f"Session {session_id} deleted by host {user['username']}")
        
        return jsonify({"message": "Session deleted successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting session: {str(e)}")
        return jsonify({"error": "Failed to delete session"}), 500


# Remove question from session (host only)
@sessions_bp.route('/api/sessions/<session_id>/questions/<question_id>', methods=['DELETE'])
@token_required
def remove_question_from_session(user, session_id, question_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can remove questions
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can remove questions"}), 403
        
        template_data = session.get("template_data", {})
        questions_queue = template_data.get("questions_queue", [])
        ready_questions = template_data.get("ready_questions", [])
        
        # Remove from queue
        updated_queue = [q for q in questions_queue if q["question_id"] != question_id]
        
        # Remove from ready questions
        updated_ready = [q for q in ready_questions if q["question_id"] != question_id]
        
        # Check if question was found and removed
        if len(updated_queue) == len(questions_queue) and len(updated_ready) == len(ready_questions):
            return jsonify({"error": "Question not found"}), 404
        
        # Update session
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "template_data.questions_queue": updated_queue,
                    "template_data.ready_questions": updated_ready,
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
        
        # Also remove from questions collection if it exists there
        questions_collection.delete_one({"question_id": question_id})
        
        current_app.logger.info(f"Question {question_id} removed from session {session_id} by {user['username']}")
        
        # Broadcast removal to all participants
        emit('question_removed', {
            'question_id': question_id,
            'removed_by': user["username"],
            'session_id': session_id
        }, room=session_id, namespace='/')
        
        return jsonify({"message": "Question removed successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error removing question: {str(e)}")
        return jsonify({"error": "Failed to remove question"}), 500


# Clear all questions from session (host only)
@sessions_bp.route('/api/sessions/<session_id>/questions/clear', methods=['DELETE'])
@token_required
def clear_all_questions(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can clear questions
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can clear all questions"}), 403
        
        # Clear all questions from session template data
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "template_data.questions_queue": [],
                    "template_data.ready_questions": [],
                    "template_data.current_question_number": 0,
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
        
        # Also clear from questions collection
        questions_collection.delete_many({"session_id": session_id})
        
        current_app.logger.info(f"All questions cleared from session {session_id} by {user['username']}")
        
        # Broadcast clear to all participants
        emit('all_questions_cleared', {
            'cleared_by': user["username"],
            'session_id': session_id
        }, room=session_id, namespace='/')
        
        return jsonify({"message": "All questions cleared successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error clearing all questions: {str(e)}")
        return jsonify({"error": "Failed to clear all questions"}), 500


# Delete all user sessions (cleanup for fresh start)
@sessions_bp.route('/api/sessions/cleanup-user', methods=['DELETE']) 
@token_required
def cleanup_user_sessions(user):
    try:
        # Get all sessions where user is host or participant
        user_sessions = list(sessions_collection.find({
            "$or": [
                {"host_username": user["username"]},
                {"participants": user["username"]}
            ]
        }))
        
        session_ids = [s["session_id"] for s in user_sessions]
        
        # Delete all user's sessions
        sessions_collection.delete_many({
            "$or": [
                {"host_username": user["username"]},
                {"participants": user["username"]}
            ]
        })
        
        # Clean up related data
        if session_ids:
            messages_collection.delete_many({"session_id": {"$in": session_ids}})
            questions_collection.delete_many({"session_id": {"$in": session_ids}})
        
        current_app.logger.info(f"User {user['username']} cleaned up {len(user_sessions)} sessions")
        
        return jsonify({
            "message": f"Cleaned up {len(user_sessions)} sessions",
            "deleted_sessions": len(user_sessions)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error during user cleanup: {str(e)}")
        return jsonify({"error": "Failed to cleanup user sessions"}), 500


# Reset session to fresh state (clear all template data)
@sessions_bp.route('/api/sessions/<session_id>/reset', methods=['POST'])
@token_required
def reset_session(user, session_id):
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Only host can reset session
        if session["host_username"] != user["username"]:
            return jsonify({"error": "Only the host can reset the session"}), 403
        
        # Reset template data to fresh state
        fresh_template_data = {
            "current_question_number": 0,
            "questions_queue": [],
            "ready_questions": []
        }
        
        sessions_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "template_data": fresh_template_data,
                    "updated_at": datetime.datetime.utcnow()
                }
            }
        )
        
        # Clear related data
        messages_collection.delete_many({"session_id": session_id})
        questions_collection.delete_many({"session_id": session_id})
        
        current_app.logger.info(f"Session {session_id} reset to fresh state by {user['username']}")
        
        # Broadcast reset to all participants
        emit('session_reset', {
            'reset_by': user["username"],
            'session_id': session_id
        }, room=session_id, namespace='/')
        
        return jsonify({"message": "Session reset to fresh state successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error resetting session: {str(e)}")
        return jsonify({"error": "Failed to reset session"}), 500