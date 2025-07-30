from flask import Blueprint, jsonify
from pymongo import MongoClient
from .config import Config
import os

main = Blueprint('main', __name__)


@main.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Interview Assistant API is running"})


@main.route('/api/info', methods=['GET'])
def info():
    # Detect testing mode from multiple indicators
    testing_mode = (
        os.getenv('TESTING', '').lower() == 'true' or
        os.getenv('TEST_MODE', '').lower() == '1' or
        os.getenv('FLASK_ENV', '') == 'testing' or
        # Check if we're using test database
        'test' in os.getenv('MONGO_URI', '').lower() or
        # Check if server is running on test port  
        os.getenv('SERVER_PORT') == '5001'
    )
    
    return jsonify({
        "name": "Interview Process Assistant",
        "version": "0.1.0",
        "testing_mode": testing_mode,
        "features": [
            "Practice programming problems",
            "Logical puzzles/riddles", 
            "Interview questions",
            "Behavioral questions",
            "And more coming soon!"
        ]
    })


# Template routes moved to templates.py module
