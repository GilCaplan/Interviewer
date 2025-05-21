import os
from flask import Flask
from flask_cors import CORS
from .config import Config
from .routes import main
from .auth import auth
from .questions import questions
from .coding_challenges import coding_challenges


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize the app with the config
    config_class.init_app(app)

    # Enable CORS with more specific configuration
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(questions)

    app.register_blueprint(coding_challenges)

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    return app


app = create_app()

if __name__ == '__main__':
    # Use environment variable SERVER_PORT if available, else default to 5000
    port = int(os.environ.get('SERVER_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)