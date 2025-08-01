import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from .config import Config
from .routes import main
from .auth import auth
from .questions import questions
from .sessions import sessions_bp
from .templates import templates_bp
from .coding_challenges import coding_challenges
from .websocket_handlers import init_simple_websockets  # Only import the function
from .async_handler import init_async_manager, shutdown_async_manager
from .interviews import interviews_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize the app with the config
    config_class.init_app(app)

    # Create SocketIO instance here
    socketio = SocketIO()

    # Initialize SocketIO with the app
    socketio.init_app(app,
                      cors_allowed_origins="*",
                      async_mode='threading',
                      logger=True,
                      engineio_logger=True)

    # Initialize websocket handlers with the socketio instance
    init_simple_websockets(socketio)

    # Enable CORS with more specific configuration
    # CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(questions)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(coding_challenges)
    app.register_blueprint(interviews_bp)

    # Global error handlers for graceful error handling
    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Bad request", "message": "Invalid request format"}, 400
    
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found", "message": "Requested resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error", "message": "An unexpected error occurred"}, 500
    
    from werkzeug.exceptions import BadRequest
    from flask import request
    import json
    
    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        return {"error": "Bad request", "message": "Invalid JSON or request format"}, 400
    
    @app.before_request
    def validate_json():
        """Validate JSON for POST/PUT requests"""
        if request.method in ['POST', 'PUT'] and request.content_type and 'application/json' in request.content_type:
            try:
                if request.data:  # Only validate if there's actually data
                    request.get_json(force=True)
            except:
                return {"error": "Invalid JSON", "message": "Request body contains malformed JSON"}, 400

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    # Initialize async task manager
    init_async_manager()

    # Register shutdown handler
    @app.teardown_appcontext
    def shutdown_async_on_teardown(exception):
        shutdown_async_manager()

    return app, socketio


app, socketio_instance = create_app()

if __name__ == '__main__':
    # Use environment variable SERVER_PORT if available, else default to 5000
    port = int(os.environ.get('SERVER_PORT', 5000))
    socketio_instance.run(app, host='0.0.0.0', port=port, debug=True)