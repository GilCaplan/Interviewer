from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
import secrets
import uuid
from functools import wraps
from pymongo import MongoClient
from .config import Config

auth = Blueprint('auth', __name__)

# Connect to MongoDB
client = MongoClient(Config.MONGO_URI)
db = client.get_default_database()
users_collection = db.users
sessions_collection = db.sessions


# Helper function to get the current user from JWT token
def get_current_user(request):
    token = None

    # Get token from header
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

    # Get token from cookies
    if not token and 'session_token' in request.cookies:
        token = request.cookies['session_token']

    if not token:
        return None

    try:
        # Verify the token
        payload = jwt.decode(
            token,
            current_app.config.get('SECRET_KEY'),
            algorithms=['HS256']
        )

        # Check if session exists and is valid
        session = sessions_collection.find_one({'session_id': payload['session_id']})

        if not session or session.get('is_revoked', False):
            return None

        user = users_collection.find_one({'username': payload['username']})
        return user
    except:
        return None


# Decorator for routes that require authentication
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user(request)

        if not user:
            return jsonify({'message': 'Authentication required'}), 401

        return f(user, *args, **kwargs)

    return decorated


# Login route
@auth.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('username'):
        return jsonify({'message': 'Username is required'}), 400

    username = data.get('username').strip()

    # Validate username
    if not username or len(username) < 3 or len(username) > 30:
        return jsonify({'message': 'Username must be between 3 and 30 characters'}), 400

    # Check if username contains only alphanumeric characters and underscores
    if not all(c.isalnum() or c == '_' for c in username):
        return jsonify({'message': 'Username can only contain letters, numbers, and underscores'}), 400

    # Find or create user
    user = users_collection.find_one({'username': username})

    if not user:
        # Create a new user
        user = {
            'username': username,
            'created_at': datetime.datetime.utcnow(),
            'user_id': str(uuid.uuid4()),
            'is_guest': username.startswith('Guest_')
        }
        users_collection.insert_one(user)

    # Create a new session
    session_id = str(uuid.uuid4())
    session = {
        'session_id': session_id,
        'username': username,
        'created_at': datetime.datetime.utcnow(),
        'expires_at': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'is_revoked': False
    }
    sessions_collection.insert_one(session)

    # Generate a JWT token
    token = jwt.encode(
        {
            'username': username,
            'session_id': session_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        },
        current_app.config.get('SECRET_KEY'),
        algorithm='HS256'
    )

    # Create response
    response = jsonify({
        'message': 'Login successful',
        'username': username,
        'token': token
    })

    # Set secure cookie
    response.set_cookie(
        'session_token',
        token,
        httponly=True,
        secure=not current_app.config.get('DEBUG', False),  # Secure in production
        samesite='Lax',
        max_age=60 * 60 * 24 * 7  # 7 days
    )

    return response, 200


# Logout route
@auth.route('/api/auth/logout', methods=['POST'])
@token_required
def logout(user):
    token = None

    # Get token from header
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

    # Get token from cookies
    if not token and 'session_token' in request.cookies:
        token = request.cookies['session_token']

    if token:
        try:
            # Decode the token to get the session ID
            payload = jwt.decode(
                token,
                current_app.config.get('SECRET_KEY'),
                algorithms=['HS256']
            )

            # Revoke the session
            sessions_collection.update_one(
                {'session_id': payload['session_id']},
                {'$set': {'is_revoked': True}}
            )

        except:
            pass  # If token is invalid, just continue

    # Create response
    response = jsonify({'message': 'Logout successful'})

    # Clear the cookie
    response.delete_cookie('session_token')

    return response, 200


# Verify token route
@auth.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token(user):
    return jsonify({
        'message': 'Token is valid',
        'username': user['username']
    }), 200


# Get current user route
@auth.route('/api/auth/user', methods=['GET'])
@token_required
def get_user(user):
    return jsonify({
        'username': user['username'],
        'user_id': user['user_id'],
        'is_guest': user.get('is_guest', False)
    }), 200