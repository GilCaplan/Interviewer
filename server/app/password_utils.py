"""
Password hashing utilities
Shared between auth.py and sessions.py to avoid circular imports
"""
import hashlib
import secrets


def hash_session_password(password):
    """Hash a session password using SHA-256 with salt"""
    if not password:
        return ""
    
    # Generate a random salt
    salt = secrets.token_hex(16)
    salt_bytes = salt.encode('utf-8')
    
    # Hash password with salt
    password_bytes = password.encode('utf-8')
    
    hash_obj = hashlib.sha256(password_bytes + salt_bytes)
    password_hash = hash_obj.hexdigest()
    
    # Return salt$hash format for verification
    return f"{salt}${password_hash}"


def verify_session_password(password, stored_hash):
    """Verify a session password against stored hash"""
    if not password or not stored_hash:
        return False
    
    # Split salt and hash
    try:
        salt, expected_hash = stored_hash.split('$', 1)
    except ValueError:
        return False
    
    # Hash the provided password with the same salt
    salt_bytes = salt.encode('utf-8')
    password_bytes = password.encode('utf-8')
    
    hash_obj = hashlib.sha256(password_bytes + salt_bytes)
    actual_hash = hash_obj.hexdigest()
    
    # Compare hashes
    return actual_hash == expected_hash