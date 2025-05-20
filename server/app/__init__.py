from flask import Flask
from flask_cors import CORS
from config import Config
from routes import main


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS
    CORS(app)

    # Register blueprints
    app.register_blueprint(main)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)