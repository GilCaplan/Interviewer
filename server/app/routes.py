from flask import Blueprint, jsonify
from pymongo import MongoClient
from .config import Config

main = Blueprint('main', __name__)


@main.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Interview Assistant API is running"})


@main.route('/api/info', methods=['GET'])
def info():
    return jsonify({
        "name": "Interview Process Assistant",
        "version": "0.1.0",
        "features": [
            "Practice programming problems",
            "Logical puzzles/riddles",
            "Interview questions",
            "Behavioral questions",
            "And more coming soon!"
        ]
    })


# Template routes moved to templates.py module
