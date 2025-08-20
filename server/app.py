#!/usr/bin/env python3
"""
Simple entry point to run the Flask application
"""
import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

if __name__ == '__main__':
    try:
        app = create_app()
        port = int(os.environ.get('SERVER_PORT') or 5000)
        print(f"Starting server on port {port}...")
        app.socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)