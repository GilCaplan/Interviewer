from flask import current_app, request
from flask_socketio import join_room, leave_room, emit
import datetime

from .database import sessions_collection
from .utils import clean_user_input, clean_session_for_response


def init_simple_websockets(socketio):
    """Initializes basic WebSocket event handlers."""

    @socketio.on('connect')
    def handle_connect():
        current_app.logger.info(f"Client connected: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        current_app.logger.info(f"Client disconnected: {request.sid}")

    @socketio.on('join_session')
    def handle_join_session(session_id):
        if session_id:
            join_room(session_id)
            current_app.logger.info(f"Client {request.sid} joined room: {session_id}")

    @socketio.on('leave_session')
    def handle_leave_session(session_id):
        if session_id:
            leave_room(session_id)
            current_app.logger.info(f"Client {request.sid} left room: {session_id}")

    @socketio.on('update_session_metadata')
    def handle_update_session_metadata(data):
        """
        Handles real-time updates to the session's core metadata (title, description, etc.)
        """
        session_id = data.get('session_id')
        metadata = data.get('metadata')

        if not session_id or not metadata:
            return  # Or emit an error to the client

        # In a real application, you would get the user from the socket session
        # and verify they are the host of this session_id.
        # For now, we'll proceed with the update.

        session = sessions_collection.find_one({"session_id": session_id})
        if not session:
            return

        # Sanitize and prepare update fields
        update_fields = {
            'title': clean_user_input(metadata.get('template_name', session.get('title'))),
            'description': clean_user_input(metadata.get('description', session.get('description'))),
            'subject': clean_user_input(metadata.get('subject', session.get('subject'))),
            'difficulty': clean_user_input(metadata.get('difficulty', session.get('difficulty'))),
            'updated_at': datetime.datetime.utcnow()
        }

        sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": update_fields}
        )

        # Fetch the fully updated session and broadcast it to all clients
        updated_session = sessions_collection.find_one({"session_id": session_id})
        clean_session = clean_session_for_response(updated_session)
        emit('session_updated', clean_session, room=session_id)