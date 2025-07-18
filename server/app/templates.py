from bson.objectid import ObjectId
from flask import Blueprint, jsonify

from server.app.auth import token_required
from .server_utils import get_templates_collection

templates = Blueprint('templates', __name__)


# @templates.route('/templates', methods=['GET'])
# # @token_required
# def get_all_templates():
#     try:
#         # Fetch all templates from the database
#         templates_collection = list(get_templates_collection().find())
#         for t in templates_collection:
#             t["_id"] = str(t["_id"])
#         return jsonify({"templates": templates_collection}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#
#
# @templates.route('/templates/<template_id>', methods=['GET'])
# # @token_required
# def get_template_by_id(template_id):
#     template = get_templates_collection().find_one({"_id": ObjectId(template_id)})
#     if not template:
#         return jsonify({"error": "Template not found"}), 404
#
#     # Convert ObjectId to string
#     template["_id"] = str(template["_id"])
#     return jsonify({"template": template}), 200
