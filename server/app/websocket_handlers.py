from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, disconnect
from flask import request
from pymongo import MongoClient
import datetime
import json
import uuid
from .auth import get_current_user
from .config import Config

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
template_sessions_collection = db.template_sessions
session_participants_collection = db.session_participants
session_messages_collection = db.session_messages
question_queue_collection = db.question_queue

# Store active connections
active_connections = {}


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client {request.sid} connected")
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client {request.sid} disconnected")

    # Remove from active connections
    if request.sid in active_connections:
        session_id = active_connections[request.sid].get('session_id')
        if session_id:
            leave_room(session_id)
            # Notify other participants
            emit('participant_left', {
                'username': active_connections[request.sid].get('username'),
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, room=session_id)
        del active_connections[request.sid]


@socketio.on('join_session')
def handle_join_session(data):
    """Handle user joining a session room"""
    try:
        # Get user from token
        user = get_current_user(request)
        if not user:
            emit('error', {'message': 'Authentication required'})
            return

        session_id = data.get('session_id')
        if not session_id:
            emit('error', {'message': 'Session ID required'})
            return

        # Verify user is participant
        participant = session_participants_collection.find_one({
            "session_id": session_id,
            "user_id": user["user_id"],
            "is_active": True
        })

        if not participant:
            emit('error', {'message': 'Not authorized to join this session'})
            return

        # Join the room
        join_room(session_id)

        # Store connection info
        active_connections[request.sid] = {
            'user_id': user["user_id"],
            'username': user["username"],
            'session_id': session_id,
            'role': participant['role']
        }

        # Notify other participants
        emit('participant_joined', {
            'username': user["username"],
            'role': participant['role'],
            'timestamp': datetime.datetime.utcnow().isoformat()
        }, room=session_id, include_self=False)

        emit('session_joined', {
            'message': 'Successfully joined session'
        })

    except Exception as e:
        print(f"Error joining session: {str(e)}")
        emit('error', {'message': 'Failed to join session'})


@socketio.on('send_message')
def handle_send_message(data):
    """Handle chat messages in session"""
    try:
        if request.sid not in active_connections:
            emit('error', {'message': 'Not connected to any session'})
            return

        connection_info = active_connections[request.sid]
        session_id = connection_info['session_id']
        user_id = connection_info['user_id']
        username = connection_info['username']

        message_text = data.get('message', '').strip()
        if not message_text:
            emit('error', {'message': 'Message cannot be empty'})
            return

        # Store message in database
        message_data = {
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
            "message": message_text,
            "message_type": "chat",
            "timestamp": datetime.datetime.utcnow()
        }

        session_messages_collection.insert_one(message_data)

        # Broadcast to all session participants
        emit('new_message', {
            'username': username,
            'message': message_text,
            'message_type': 'chat',
            'timestamp': message_data['timestamp'].isoformat()
        }, room=session_id)

    except Exception as e:
        print(f"Error sending message: {str(e)}")
        emit('error', {'message': 'Failed to send message'})


@socketio.on('request_llm_questions')
def handle_llm_request(data):
    """Handle LLM question generation requests"""
    try:
        if request.sid not in active_connections:
            emit('error', {'message': 'Not connected to any session'})
            return

        connection_info = active_connections[request.sid]
        session_id = connection_info['session_id']
        username = connection_info['username']

        # Get session details
        session = template_sessions_collection.find_one({"session_id": session_id})
        if not session or not session.get('settings', {}).get('llm_enabled', False):
            emit('error', {'message': 'LLM is not enabled for this session'})
            return

        prompt = data.get('prompt', '').strip()
        num_questions = min(data.get('num_questions', 3), 10)  # Max 10 at once

        if not prompt:
            emit('error', {'message': 'Prompt is required for LLM generation'})
            return

        # Notify participants that LLM is generating
        emit('llm_generating', {
            'username': username,
            'prompt': prompt,
            'num_questions': num_questions,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }, room=session_id)

        # For now, return mock questions (you'll replace this with real LLM later)
        mock_questions = [
            {
                "question_text": f"What are the key concepts of {prompt}?",
                "question_type": "open_ended",
                "difficulty": "NORMAL",
                "answer": f"This question tests understanding of {prompt}",
                "hints": ["Think about fundamentals", "Consider practical applications"]
            },
            {
                "question_text": f"How would you implement {prompt} in a real project?",
                "question_type": "open_ended",
                "difficulty": "MODERATE",
                "answer": f"Implementation details for {prompt}",
                "hints": ["Consider scalability", "Think about best practices"]
            }
        ]

        # Add generated questions to queue
        for question in mock_questions[:num_questions]:
            question_data = {
                "question_id": str(uuid.uuid4()),
                "session_id": session_id,
                "submitted_by": "llm_system",
                "submitted_by_username": "AI Assistant",
                "question_text": question.get("question_text", ""),
                "answer": question.get("answer", ""),
                "question_type": question.get("question_type", "open_ended"),
                "difficulty": question.get("difficulty", "NORMAL"),
                "hints": question.get("hints", []),
                "multiple_choice_options": question.get("multiple_choice_options", []),
                "correct_answer": question.get("correct_answer", ""),
                "source": "llm",
                "status": "pending",
                "submitted_at": datetime.datetime.utcnow(),
                "metadata": {"llm_prompt": prompt}
            }

            question_queue_collection.insert_one(question_data)

        # Notify all session participants
        emit('llm_questions_generated', {
            'questions': mock_questions[:num_questions],
            'num_generated': len(mock_questions[:num_questions]),
            'timestamp': datetime.datetime.utcnow().isoformat()
        }, room=session_id)

    except Exception as e:
        print(f"Error requesting LLM questions: {str(e)}")
        emit('error', {'message': 'Failed to request LLM questions'})


