"""
Password hashing utilities
Shared between auth.py and sessions.py to avoid circular imports
Uses PBKDF2 for secure password hashing (built into Python, no external dependencies)
"""
import hashlib
import secrets
import os


def hash_session_password(password):
    """
    Hash a session password using PBKDF2-SHA256 (secure for passwords)
    PBKDF2 is designed to be slow and computationally expensive to prevent brute force attacks
    """
    if not password:
        return ""
    
    # Generate a random salt (32 bytes = 256 bits)
    salt = os.urandom(32)
    
    # Hash password with PBKDF2-SHA256 
    # 100,000 iterations makes it computationally expensive for attackers
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',                    # Hash algorithm
        password.encode('utf-8'),    # Password bytes
        salt,                        # Salt bytes  
        100000                       # 100,000 iterations (NIST recommended minimum)
    )
    
    # Return salt + hash in base64 format for storage
    import base64
    salt_b64 = base64.b64encode(salt).decode('ascii')
    hash_b64 = base64.b64encode(password_hash).decode('ascii')
    
    return f"{salt_b64}${hash_b64}"


def verify_session_password(password, stored_hash):
    """
    Verify a session password against stored PBKDF2 hash
    Uses constant-time comparison to prevent timing attacks
    """
    if not password or not stored_hash:
        return False
    
    # Split salt and hash
    try:
        salt_b64, expected_hash_b64 = stored_hash.split('$', 1)
    except ValueError:
        return False
    
    try:
        # Decode salt and hash from base64
        import base64
        salt = base64.b64decode(salt_b64.encode('ascii'))
        expected_hash = base64.b64decode(expected_hash_b64.encode('ascii'))
    except Exception:
        return False
    
    # Hash the provided password with the same salt and parameters
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'), 
        salt,
        100000  # Same iteration count
    )
    
    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(password_hash, expected_hash)