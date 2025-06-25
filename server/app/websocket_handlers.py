# server/app/simple_websocket_handlers.py
from flask_socketio import emit, join_room, leave_room
from flask import request
from pymongo import MongoClient
import datetime
import uuid
from .auth import get_current_user
from .config import Config

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
sessions_collection = db.sessions
messages_collection = db.session_messages
questions_collection = db.session_questions

# Store active connections per session
session_connections = {}


def init_simple_websockets(socketio):
    """Initialize WebSocket handlers for simple sessions"""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"Client {request.sid} connected")
        emit('connected', {'message': 'Connected to server'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"Client {request.sid} disconnected")

        # Remove from all session rooms
        for session_id, connections in session_connections.items():
            if request.sid in connections:
                connections.remove(request.sid)
                # Notify others in the session
                emit('user_disconnected', {
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }, room=session_id)

    @socketio.on('join_session_room')
    def handle_join_session_room(data):
        """Handle user joining a session room for real-time updates"""
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

            # Verify user is a participant of this session
            session = sessions_collection.find_one({"session_id": session_id})
            if not session:
                emit('error', {'message': 'Session not found'})
                return

            if user["username"] not in session.get("participants", []):
                emit('error', {'message': 'Access denied - not a participant'})
                return

            # Join the session room
            join_room(session_id)

            # Track connection
            if session_id not in session_connections:
                session_connections[session_id] = []
            session_connections[session_id].append(request.sid)

            # Notify others that user joined
            emit('user_joined_room', {
                'username': user["username"],
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, room=session_id, include_self=False)

            emit('joined_session_room', {
                'session_id': session_id,
                'message': 'Successfully joined session room'
            })

        except Exception as e:
            print(f"Error joining session room: {str(e)}")
            emit('error', {'message': 'Failed to join session room'})

    @socketio.on('leave_session_room')
    def handle_leave_session_room(data):
        """Handle user leaving a session room"""
        try:
            user = get_current_user(request)
            if not user:
                return

            session_id = data.get('session_id')
            if session_id:
                leave_room(session_id)

                # Remove from tracking
                if session_id in session_connections:
                    if request.sid in session_connections[session_id]:
                        session_connections[session_id].remove(request.sid)

                # Notify others
                emit('user_left_room', {
                    'username': user["username"],
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }, room=session_id)

        except Exception as e:
            print(f"Error leaving session room: {str(e)}")

    @socketio.on('send_chat_message')
    def handle_chat_message(data):
        """Handle real-time chat messages"""
        try:
            user = get_current_user(request)
            if not user:
                emit('error', {'message': 'Authentication required'})
                return

            session_id = data.get('session_id')
            message_text = data.get('message', '').strip()

            if not session_id or not message_text:
                emit('error', {'message': 'Session ID and message are required'})
                return

            # Verify user is a participant
            session = sessions_collection.find_one({"session_id": session_id})
            if not session or user["username"] not in session.get("participants", []):
                emit('error', {'message': 'Access denied'})
                return

            # Create message
            message_data = {
                "message_id": str(uuid.uuid4()),
                "session_id": session_id,
                "username": user["username"],
                "message": message_text,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "type": data.get('type', 'chat')
            }

            # Save to database
            messages_collection.insert_one({
                **message_data,
                "timestamp": datetime.datetime.utcnow()  # Store as datetime in DB
            })

            # Broadcast to all users in the session
            emit('new_chat_message', message_data, room=session_id)

        except Exception as e:
            print(f"Error handling chat message: {str(e)}")
            emit('error', {'message': 'Failed to send message'})

    @socketio.on('suggest_question')
    def handle_question_suggestion(data):
        """Handle real-time question suggestions"""
        try:
            user = get_current_user(request)
            if not user:
                emit('error', {'message': 'Authentication required'})
                return

            session_id = data.get('session_id')
            question_text = data.get('question_text', '').strip()

            if not session_id or not question_text:
                emit('error', {'message': 'Session ID and question text are required'})
                return

            # Verify user is a participant
            session = sessions_collection.find_one({"session_id": session_id})
            if not session or user["username"] not in session.get("participants", []):
                emit('error', {'message': 'Access denied'})
                return

            # Create question suggestion
            suggestion_data = {
                "suggestion_id": str(uuid.uuid4()),
                "session_id": session_id,
                "username": user["username"],
                "question_text": question_text,
                "difficulty": data.get('difficulty', 'medium'),
                "type": data.get('type', 'open_ended'),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "status": "suggestion"
            }

            # Broadcast question suggestion to all users
            emit('new_question_suggestion', suggestion_data, room=session_id)

            # If it's the host, they can approve/reject
            if user["username"] == session.get("host_username"):
                emit('host_question_action', {
                    'suggestion_id': suggestion_data['suggestion_id'],
                    'can_approve': True
                }, room=request.sid)

        except Exception as e:
            print(f"Error handling question suggestion: {str(e)}")
            emit('error', {'message': 'Failed to suggest question'})

    @socketio.on('approve_question_suggestion')
    def handle_approve_question_suggestion(data):
        """Handle host approving/rejecting question suggestions"""
        try:
            user = get_current_user(request)
            if not user:
                emit('error', {'message': 'Authentication required'})
                return

            session_id = data.get('session_id')
            suggestion_id = data.get('suggestion_id')
            action = data.get('action', 'approve')  # approve or reject

            if not session_id or not suggestion_id:
                emit('error', {'message': 'Session ID and suggestion ID are required'})
                return

            # Verify user is the host
            session = sessions_collection.find_one({"session_id": session_id})
            if not session or user["username"] != session.get("host_username"):
                emit('error', {'message': 'Only the host can approve questions'})
                return

            # Broadcast the decision
            emit('question_suggestion_result', {
                'suggestion_id': suggestion_id,
                'action': action,
                'approved_by': user["username"],
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, room=session_id)

        except Exception as e:
            print(f"Error handling question approval: {str(e)}")
            emit('error', {'message': 'Failed to process approval'})

    @socketio.on('request_llm_question')
    def handle_llm_question_request(data):
        """Handle real-time LLM question generation requests"""
        try:
            user = get_current_user(request)
            if not user:
                emit('error', {'message': 'Authentication required'})
                return

            session_id = data.get('session_id')
            subject = data.get('subject', 'general')
            context = data.get('context', '')

            if not session_id:
                emit('error', {'message': 'Session ID required'})
                return

            # Verify user is a participant
            session = sessions_collection.find_one({"session_id": session_id})
            if not session or user["username"] not in session.get("participants", []):
                emit('error', {'message': 'Access denied'})
                return

            if not session["settings"].get("allow_llm", True):
                emit('error', {'message': 'LLM questions are disabled'})
                return

            # Notify all users that LLM is generating a question
            emit('llm_generating', {
                'username': user["username"],
                'subject': subject,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, room=session_id)

            # This would integrate with the mock LLM from the main sessions module
            # For now, just notify that a question was requested
            emit('llm_question_requested', {
                'username': user["username"],
                'subject': subject,
                'context': context,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, room=session_id)

        except Exception as e:
            print(f"Error handling LLM question request: {str(e)}")
            emit('error', {'message': 'Failed to request LLM question'})

    @socketio.on('typing_indicator')
    def handle_typing_indicator(data):
        """Handle typing indicators for chat"""
        try:
            user = get_current_user(request)
            if not user:
                return

            session_id = data.get('session_id')
            is_typing = data.get('is_typing', False)

            if session_id:
                emit('user_typing', {
                    'username': user["username"],
                    'is_typing': is_typing,
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }, room=session_id, include_self=False)

        except Exception as e:
            print(f"Error handling typing indicator: {str(e)}")

    @socketio.on('session_status_update')
    def handle_session_status_update(data):
        """Handle session status updates (host only)"""
        try:
            user = get_current_user(request)
            if not user:
                emit('error', {'message': 'Authentication required'})
                return

            session_id = data.get('session_id')
            status = data.get('status')

            if not session_id or not status:
                emit('error', {'message': 'Session ID and status required'})
                return

            # Verify user is the host
            session = sessions_collection.find_one({"session_id": session_id})
            if not session or user["username"] != session.get("host_username"):
                emit('error', {'message': 'Only the host can update session status'})
                return

            # Update session status in database
            sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"status": status, "updated_at": datetime.datetime.utcnow()}}
            )

            # Broadcast status update
            emit('session_status_changed', {
                'status': status,
                'updated_by': user["username"],
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, room=session_id)

        except Exception as e:
            print(f"Error handling status update: {str(e)}")
            emit('error', {'message': 'Failed to update session status'})

    return socketio