import uuid

from bson import ObjectId
from flask import Blueprint, jsonify
from .server_utils import get_templates_collection, get_sessions_collection
from .sessions import start_session_from_template

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


@main.route('/templates', methods=['GET'])
def get_all_templates():
	templates_collection = get_templates_collection()

	try:
		# Fetch all templates from the database
		templates = list(templates_collection.find())
		for t in templates:
			t["_id"] = str(t["_id"])

		return jsonify({"templates": templates}), 200
	except Exception as e:
		return jsonify({"error": str(e)}), 500


@main.route('/templates/<template_id>', methods=['GET'])
def get_template_by_id(template_id):
	from bson import ObjectId
	template = get_templates_collection().find_one({"_id": ObjectId(template_id)})
	if not template:
		return jsonify({"error": "Template not found"}), 404

	# Convert ObjectId to string
	template["_id"] = str(template["_id"])
	return jsonify({"template": template}), 200


@main.route('/sessions/<session_id>', methods=['GET'])
def get_session_by_id(session_id):
	sessions_collection = get_sessions_collection()
	session = sessions_collection.find_one({"_id": ObjectId(session_id)})
	if not session:
		return jsonify({"error": "Session not found"}), 404

	# Convert ObjectId to string
	session["_id"] = str(session["_id"])
	return jsonify({"session": session}), 200
