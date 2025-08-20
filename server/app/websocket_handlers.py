from flask import current_app, request
from flask_socketio import join_room, leave_room

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