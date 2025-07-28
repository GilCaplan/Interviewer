# server/app/templates.py
from flask import Blueprint, request, jsonify, current_app
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import uuid
from .auth import token_required
from .config import Config

templates_bp = Blueprint('templates', __name__)

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
templates_collection = db.templates
template_questions_collection = db.template_questions

# Question types and their schemas
QUESTION_TYPES = {
    'multiple_choice': {
        'required_fields': ['question_text', 'options', 'correct_answer'],
        'optional_fields': ['explanation', 'hints', 'time_limit'],
        'schema': {
            'question_text': str,
            'options': list,  # List of choice strings
            'correct_answer': str,  # Should match one of the options
            'explanation': str,
            'hints': list,
            'time_limit': int  # in seconds
        }
    },
    'open_ended': {
        'required_fields': ['question_text'],
        'optional_fields': ['sample_answer', 'grading_criteria', 'hints', 'time_limit'],
        'schema': {
            'question_text': str,
            'sample_answer': str,
            'grading_criteria': list,  # List of criteria strings
            'hints': list,
            'time_limit': int
        }
    },
    'true_false': {
        'required_fields': ['question_text', 'correct_answer'],
        'optional_fields': ['explanation', 'hints'],
        'schema': {
            'question_text': str,
            'correct_answer': bool,
            'explanation': str,
            'hints': list
        }
    },
    'coding': {
        'required_fields': ['question_text', 'language'],
        'optional_fields': ['starter_code', 'solution', 'test_cases', 'hints', 'time_limit'],
        'schema': {
            'question_text': str,
            'language': str,  # python, javascript, java, etc.
            'starter_code': str,
            'solution': str,
            'test_cases': list,  # List of test case objects
            'hints': list,
            'time_limit': int
        }
    },
    'short_answer': {
        'required_fields': ['question_text'],
        'optional_fields': ['expected_keywords', 'sample_answers', 'hints', 'max_words'],
        'schema': {
            'question_text': str,
            'expected_keywords': list,
            'sample_answers': list,
            'hints': list,
            'max_words': int
        }
    }
}

DIFFICULTY_LEVELS = ['easy', 'medium', 'hard']
SUBJECTS = [
    'algorithms', 'data_structures', 'system_design', 'python', 'javascript', 
    'java', 'react', 'databases', 'networking', 'behavioral', 'general'
]


def validate_question_data(question_type, question_data):
    """Validate question data against its type schema"""
    if question_type not in QUESTION_TYPES:
        return False, f"Invalid question type: {question_type}"
    
    type_config = QUESTION_TYPES[question_type]
    
    # Check required fields
    for field in type_config['required_fields']:
        if field not in question_data:
            return False, f"Missing required field: {field}"
    
    # Validate specific field types for multiple choice
    if question_type == 'multiple_choice':
        options = question_data.get('options', [])
        correct_answer = question_data.get('correct_answer')
        
        if len(options) < 2:
            return False, "Multiple choice questions must have at least 2 options"
        
        if correct_answer not in options:
            return False, "Correct answer must be one of the provided options"
    
    return True, "Valid"


# Create a new template
@templates_bp.route('/api/templates', methods=['POST'])
@token_required
def create_template(user):
    try:
        data = request.get_json() or {}
        
        template_data = {
            "template_id": str(uuid.uuid4()),
            "template_name": data.get('template_name', 'Untitled Template'),
            "description": data.get('description', ''),
            "subject": data.get('subject', 'general'),
            "sub_subject": data.get('sub_subject', ''),
            "difficulty": data.get('difficulty', 'medium'),
            "created_by": user["username"],
            "created_by_id": user["user_id"],
            "is_public": data.get('is_public', False),
            "tags": data.get('tags', []),
            "metadata": {
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
                "version": 1,
                "question_count": 0,
                "estimated_time": 0  # in minutes
            },
            "settings": {
                "max_questions": data.get('max_questions', 20),
                "allow_shuffle": data.get('allow_shuffle', True),
                "show_hints": data.get('show_hints', True),
                "time_limit": data.get('time_limit', 60)  # minutes
            },
            "questions": []
        }
        
        # Validate difficulty and subject
        if template_data['difficulty'] not in DIFFICULTY_LEVELS:
            return jsonify({"error": "Invalid difficulty level"}), 400
        
        if template_data['subject'] not in SUBJECTS:
            return jsonify({"error": "Invalid subject"}), 400
        
        result = templates_collection.insert_one(template_data)
        template_data.pop('_id', None)
        
        return jsonify({
            "message": "Template created successfully",
            "template": template_data
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating template: {str(e)}")
        return jsonify({"error": "Failed to create template"}), 500


# Get all templates (with filtering)
@templates_bp.route('/api/templates', methods=['GET'])
@token_required
def get_templates(user):
    try:
        # Query parameters for filtering
        subject = request.args.get('subject')
        difficulty = request.args.get('difficulty')
        is_public = request.args.get('is_public')
        created_by = request.args.get('created_by')
        
        # Build query
        query = {}
        
        if subject:
            query['subject'] = subject
        if difficulty:
            query['difficulty'] = difficulty
        if is_public is not None:
            query['is_public'] = is_public.lower() == 'true'
        if created_by:
            query['created_by'] = created_by
        else:
            # By default, show public templates + user's own templates
            query['$or'] = [
                {'is_public': True},
                {'created_by_id': user["user_id"]}
            ]
        
        templates = list(templates_collection.find(
            query,
            {'_id': 0}
        ).sort("metadata.created_at", -1))
        
        return jsonify({"templates": templates}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching templates: {str(e)}")
        return jsonify({"error": "Failed to fetch templates"}), 500


# Get specific template
@templates_bp.route('/api/templates/<template_id>', methods=['GET'])
@token_required
def get_template(user, template_id):
    try:
        template = templates_collection.find_one({"template_id": template_id}, {"_id": 0})
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        # Check access permissions
        if not template['is_public'] and template['created_by_id'] != user["user_id"]:
            return jsonify({"error": "Access denied"}), 403
        
        return jsonify({"template": template}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching template: {str(e)}")
        return jsonify({"error": "Failed to fetch template"}), 500


# Update template metadata
@templates_bp.route('/api/templates/<template_id>', methods=['PUT'])
@token_required
def update_template(user, template_id):
    try:
        template = templates_collection.find_one({"template_id": template_id})
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        if template['created_by_id'] != user["user_id"]:
            return jsonify({"error": "Only template owner can update"}), 403
        
        data = request.get_json() or {}
        
        # Update allowed fields
        update_fields = {}
        if 'template_name' in data:
            update_fields['template_name'] = data['template_name']
        if 'description' in data:
            update_fields['description'] = data['description']
        if 'subject' in data and data['subject'] in SUBJECTS:
            update_fields['subject'] = data['subject']
        if 'sub_subject' in data:
            update_fields['sub_subject'] = data['sub_subject']
        if 'difficulty' in data and data['difficulty'] in DIFFICULTY_LEVELS:
            update_fields['difficulty'] = data['difficulty']
        if 'is_public' in data:
            update_fields['is_public'] = data['is_public']
        if 'tags' in data:
            update_fields['tags'] = data['tags']
        if 'settings' in data:
            update_fields['settings'] = {**template['settings'], **data['settings']}
        
        update_fields['metadata.updated_at'] = datetime.datetime.utcnow()
        update_fields['metadata.version'] = template['metadata']['version'] + 1
        
        templates_collection.update_one(
            {"template_id": template_id},
            {"$set": update_fields}
        )
        
        updated_template = templates_collection.find_one({"template_id": template_id}, {"_id": 0})
        
        return jsonify({
            "message": "Template updated successfully",
            "template": updated_template
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating template: {str(e)}")
        return jsonify({"error": "Failed to update template"}), 500


# Add question to template
@templates_bp.route('/api/templates/<template_id>/questions', methods=['POST'])
@token_required
def add_question_to_template(user, template_id):
    try:
        template = templates_collection.find_one({"template_id": template_id})
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        if template['created_by_id'] != user["user_id"]:
            return jsonify({"error": "Only template owner can add questions"}), 403
        
        data = request.get_json() or {}
        question_type = data.get('type', 'open_ended')
        
        # Validate question type and data
        is_valid, validation_message = validate_question_data(question_type, data)
        if not is_valid:
            return jsonify({"error": validation_message}), 400
        
        # Check if template has reached max questions
        current_count = len(template.get('questions', []))
        max_questions = template['settings']['max_questions']
        
        if current_count >= max_questions:
            return jsonify({"error": f"Template has reached maximum questions limit ({max_questions})"}), 400
        
        question_data = {
            "question_id": str(uuid.uuid4()),
            "question_number": current_count + 1,
            "type": question_type,
            "question_text": data['question_text'],
            "difficulty": data.get('difficulty', template['difficulty']),
            "points": data.get('points', 1),
            "created_at": datetime.datetime.utcnow(),
            "created_by": user["username"],
            "source": data.get('source', 'user')  # user, llm, imported
        }
        
        # Add type-specific fields
        type_config = QUESTION_TYPES[question_type]
        for field in type_config['required_fields'] + type_config['optional_fields']:
            if field in data and field != 'question_text':  # Already added above
                question_data[field] = data[field]
        
        # Add question to template
        templates_collection.update_one(
            {"template_id": template_id},
            {
                "$push": {"questions": question_data},
                "$set": {
                    "metadata.updated_at": datetime.datetime.utcnow(),
                    "metadata.question_count": current_count + 1,
                    "metadata.version": template['metadata']['version'] + 1
                }
            }
        )
        
        return jsonify({
            "message": "Question added successfully",
            "question": question_data
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error adding question: {str(e)}")
        return jsonify({"error": "Failed to add question"}), 500


# Update question in template
@templates_bp.route('/api/templates/<template_id>/questions/<question_id>', methods=['PUT'])
@token_required
def update_question_in_template(user, template_id, question_id):
    try:
        template = templates_collection.find_one({"template_id": template_id})
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        if template['created_by_id'] != user["user_id"]:
            return jsonify({"error": "Only template owner can update questions"}), 403
        
        data = request.get_json() or {}
        
        # Find the question to update
        questions = template.get('questions', [])
        question_index = None
        for i, q in enumerate(questions):
            if q['question_id'] == question_id:
                question_index = i
                break
        
        if question_index is None:
            return jsonify({"error": "Question not found"}), 404
        
        current_question = questions[question_index]
        question_type = data.get('type', current_question['type'])
        
        # Validate question data
        is_valid, validation_message = validate_question_data(question_type, data)
        if not is_valid:
            return jsonify({"error": validation_message}), 400
        
        # Update question data
        updated_question = {**current_question}
        
        # Update allowed fields
        updatable_fields = ['question_text', 'type', 'difficulty', 'points'] + \
                          QUESTION_TYPES[question_type]['required_fields'] + \
                          QUESTION_TYPES[question_type]['optional_fields']
        
        for field in updatable_fields:
            if field in data:
                updated_question[field] = data[field]
        
        updated_question['updated_at'] = datetime.datetime.utcnow()
        
        # Update the question in the array
        update_path = f"questions.{question_index}"
        templates_collection.update_one(
            {"template_id": template_id},
            {
                "$set": {
                    update_path: updated_question,
                    "metadata.updated_at": datetime.datetime.utcnow(),
                    "metadata.version": template['metadata']['version'] + 1
                }
            }
        )
        
        return jsonify({
            "message": "Question updated successfully",
            "question": updated_question
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating question: {str(e)}")
        return jsonify({"error": "Failed to update question"}), 500


# Delete question from template
@templates_bp.route('/api/templates/<template_id>/questions/<question_id>', methods=['DELETE'])
@token_required
def delete_question_from_template(user, template_id, question_id):
    try:
        template = templates_collection.find_one({"template_id": template_id})
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        if template['created_by_id'] != user["user_id"]:
            return jsonify({"error": "Only template owner can delete questions"}), 403
        
        # Remove the question and renumber remaining questions
        questions = template.get('questions', [])
        updated_questions = []
        
        for i, q in enumerate(questions):
            if q['question_id'] != question_id:
                q['question_number'] = len(updated_questions) + 1
                updated_questions.append(q)
        
        if len(updated_questions) == len(questions):
            return jsonify({"error": "Question not found"}), 404
        
        templates_collection.update_one(
            {"template_id": template_id},
            {
                "$set": {
                    "questions": updated_questions,
                    "metadata.updated_at": datetime.datetime.utcnow(),
                    "metadata.question_count": len(updated_questions),
                    "metadata.version": template['metadata']['version'] + 1
                }
            }
        )
        
        return jsonify({"message": "Question deleted successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting question: {str(e)}")
        return jsonify({"error": "Failed to delete question"}), 500


# Get question types and their schemas
@templates_bp.route('/api/templates/question-types', methods=['GET'])
@token_required
def get_question_types(user):
    # Convert QUESTION_TYPES to JSON-serializable format
    serializable_question_types = {}
    for q_type, config in QUESTION_TYPES.items():
        serializable_question_types[q_type] = {
            'required_fields': config['required_fields'],
            'optional_fields': config['optional_fields'],
            'description': f"{q_type.replace('_', ' ').title()} question type"
        }
    
    return jsonify({
        "question_types": serializable_question_types,
        "difficulty_levels": DIFFICULTY_LEVELS,
        "subjects": SUBJECTS
    }), 200


# Delete template
@templates_bp.route('/api/templates/<template_id>', methods=['DELETE'])
@token_required
def delete_template(user, template_id):
    try:
        template = templates_collection.find_one({"template_id": template_id})
        
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        if template['created_by_id'] != user["user_id"]:
            return jsonify({"error": "Only template owner can delete template"}), 403
        
        templates_collection.delete_one({"template_id": template_id})
        
        return jsonify({"message": "Template deleted successfully"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting template: {str(e)}")
        return jsonify({"error": "Failed to delete template"}), 500