import html
import re
import datetime

def clean_user_input(text):
    """Clean and secure user text input"""
    if not text or not isinstance(text, str):
        return ""
    
    # Remove control chars (except basic whitespace)
    text = ''.join(c for c in text if ord(c) >= 32 or c in '\t\n\r')
    
    # Prevent DoS with length limit
    text = text[:10000] if len(text) > 10000 else text
    
    # Basic XSS protection
    text = html.escape(text, quote=True)
    
    # Remove common attack patterns
    bad_patterns = [
        r'<script.*?</script>', r'javascript:', r'vbscript:', 
        r'on\w+\s*=', r'<iframe', r'<object', r'<embed',
        r';\s*(drop|delete|exec)', r'union\s+select'
    ]
    
    for pattern in bad_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Clean up path traversal and remaining tags
    text = re.sub(r'\.\.[\\/]', '', text)
    text = re.sub(r'<[^>]*>', '', text)
    
    return text.strip()

def clean_session_for_response(session_data):
    """
    Recursively removes sensitive data and serializes non-JSON-compatible types
    (like ObjectId and datetime) for API responses and WebSocket events.
    """
    if not session_data:
        return None

    def serialize_value(value):
        if isinstance(value, list): return [serialize_value(item) for item in value]
        if isinstance(value, dict): return {k: serialize_value(v) for k, v in value.items()}
        if isinstance(value, datetime.datetime): return value.isoformat()
        return value

    session_data.pop('password_hash', None)
    session_data.pop('_id', None)
    return serialize_value(session_data)