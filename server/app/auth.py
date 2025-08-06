from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
import secrets
import uuid
from functools import wraps
from .config import Config
from .database import users_collection, sessions_collection
from .high_scale_optimizer import extreme_scale_protection
from .ultra_scale_config import ultra_scale_protection

auth = Blueprint('auth', __name__)


# Get the current user from JWT token
def get_current_user(request):
    token = None

    # Try header first, then cookies
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            pass
    
    if not token:
        token = request.cookies.get('session_token')

    if not token or not isinstance(token, str) or len(token) < 10:
        return None

    try:
        # Decode and validate token
        payload = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=['HS256'])
        
        username = payload.get('username')
        session_id = payload.get('session_id')
        if not username or not session_id:
            return None

        # Check if session is still valid
        session = sessions_collection.find_one({'session_id': session_id})
        if not session or session.get('is_revoked', False):
            return None

        # Check expiration
        if session.get('expires_at') and session['expires_at'] < datetime.datetime.utcnow():
            return None

        return users_collection.find_one({'username': username})
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
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


# Verify JWT token (for testing)
def verify_token(token):
    """Verify a JWT token and return payload or None"""
    if not token or not isinstance(token, str) or len(token) < 10:
        return None
    
    try:
        payload = jwt.decode(token, current_app.config.get('SECRET_KEY', 'default_secret'), algorithms=['HS256'])
        
        # Check if expired
        if 'exp' in payload:
            exp_time = datetime.datetime.fromtimestamp(payload['exp'])
            if exp_time < datetime.datetime.utcnow():
                return None
        
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


# Registration route
@auth.route('/api/auth/register', methods=['POST'])
@rate_limit('auth', 5, 900, per_user=False)  # 5 attempts per 15 minutes per client
def register():
    try:
        # Basic validation
        if not request.is_json:
            return jsonify({'message': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Request body is required'}), 400
            
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username:
            return jsonify({'message': 'Username is required'}), 400
        if not email:
            return jsonify({'message': 'Email is required'}), 400
        if not password:
            return jsonify({'message': 'Password is required'}), 400
            
        # Validate username
        if len(username) < 3 or len(username) > 30:
            return jsonify({'message': 'Username must be between 3 and 30 characters'}), 400
        if not all(c.isalnum() or c == '_' for c in username):
            return jsonify({'message': 'Username can only contain letters, numbers, and underscores'}), 400
            
        # Validate email (basic)
        if '@' not in email or '.' not in email.split('@')[1]:
            return jsonify({'message': 'Invalid email format'}), 400
            
        # Validate password
        if len(password) < 6:
            return jsonify({'message': 'Password must be at least 6 characters'}), 400
        
        # Check if user already exists
        existing_user = users_collection.find_one({
            '$or': [{'username': username}, {'email': email}]
        })
        if existing_user:
            return jsonify({'message': 'Username or email already exists'}), 409
        
        # Create user
        user = {
            'username': username,
            'email': email,
            'password': password,  # In production, hash this
            'created_at': datetime.datetime.utcnow(),
            'user_id': str(uuid.uuid4()),
            'is_guest': False
        }
        users_collection.insert_one(user)
        
        # Create session
        session_id = str(uuid.uuid4())
        session = {
            'session_id': session_id,
            'username': username,
            'created_at': datetime.datetime.utcnow(),
            'expires_at': datetime.datetime.utcnow() + datetime.timedelta(days=7),
            'is_revoked': False
        }
        sessions_collection.insert_one(session)

        # Generate JWT token
        token = jwt.encode({
            'username': username,
            'session_id': session_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config.get('SECRET_KEY'), algorithm='HS256')

        # Return response
        response = jsonify({
            'message': 'Registration successful',
            'username': username,
            'token': token,
            'user': {'username': username, 'user_id': user['user_id']}
        })

        response.set_cookie('session_token', token, httponly=True,
                          secure=not current_app.config.get('DEBUG', False),
                          samesite='Lax', max_age=60 * 60 * 24 * 7)

        return response, 201

    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'message': 'Registration failed'}), 500


# Login route with rate limiting
@auth.route('/api/auth/login', methods=['POST'])
@ultra_scale_protection  # Ultra-scale optimization for 1500+ users
def login():
    try:
        # Basic validation
        if not request.is_json:
            return jsonify({'message': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data or not data.get('username'):
            return jsonify({'message': 'Username is required'}), 400
            
        username = data.get('username')
        if not isinstance(username, str):
            return jsonify({'message': 'Username must be a string'}), 400
            
        # Clean username
        import html
        username = html.escape(username.strip())
        
        # Check for bad characters
        if '\x00' in username or any(ord(c) < 32 and c not in '\t\n\r' for c in username):
            return jsonify({'message': 'Invalid characters in username'}), 400
            
    except Exception:
        return jsonify({'message': 'Invalid request format'}), 400

    # Validate username
    if not username or len(username) < 3 or len(username) > 30:
        return jsonify({'message': 'Username must be between 3 and 30 characters'}), 400

    # Check if username contains only alphanumeric characters and underscores
    if not all(c.isalnum() or c == '_' for c in username):
        return jsonify({'message': 'Username can only contain letters, numbers, and underscores'}), 400

    try:
        # Find or create user
        user = users_collection.find_one({'username': username})
        if not user:
            user = {
                'username': username,
                'created_at': datetime.datetime.utcnow(),
                'user_id': str(uuid.uuid4()),
                'is_guest': username.startswith('Guest_')
            }
            users_collection.insert_one(user)

        # Create session
        session_id = str(uuid.uuid4())
        session = {
            'session_id': session_id,
            'username': username,
            'created_at': datetime.datetime.utcnow(),
            'expires_at': datetime.datetime.utcnow() + datetime.timedelta(days=7),
            'is_revoked': False
        }
        sessions_collection.insert_one(session)

        # Generate JWT token
        token = jwt.encode({
            'username': username,
            'session_id': session_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config.get('SECRET_KEY'), algorithm='HS256')

        # Return response with secure cookie
        response = jsonify({
            'message': 'Login successful',
            'username': username,
            'token': token,
            'user': {'username': username, 'user_id': user['user_id']}
        })

        response.set_cookie('session_token', token, httponly=True,
                          secure=not current_app.config.get('DEBUG', False),
                          samesite='Lax', max_age=60 * 60 * 24 * 7)

        return response, 200

    except Exception as e:
        # Log the error for debugging but don't expose internal details
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'Authentication failed'}), 500


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