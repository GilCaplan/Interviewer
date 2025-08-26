# Comprehensive security and access control module
import hashlib
import secrets
import jwt
import re
import time
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from .config import Config

class SecurityManager:
    """Handles all security-related operations"""
    
    def __init__(self):
        self.failed_attempts = {}  # Track failed login attempts
        self.suspicious_activities = {}  # Track suspicious activities
        self.blocked_ips = set()  # Temporarily blocked IPs
        self.security_events = []  # Security event log
    
    def validate_input_security(self, input_data, input_type='general'):
        """Comprehensive input validation and sanitization"""
        if not isinstance(input_data, str):
            return str(input_data) if input_data is not None else ""
        
        # Remove null bytes and control characters
        cleaned = ''.join(c for c in input_data if ord(c) >= 32 or c in '\t\n\r')
        
        # Check for various injection patterns
        dangerous_patterns = {
            'sql_injection': [
                r';\s*(drop|delete|truncate|alter)\s+',
                r'union\s+select',
                r'exec\s*\(',
                r'xp_cmdshell',
                r'sp_executesql'
            ],
            'nosql_injection': [
                r'\$where',
                r'\$regex',
                r'\$ne',
                r'\$gt',
                r'\$lt'
            ],
            'xss': [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'vbscript:',
                r'on\w+\s*=',
                r'<iframe',
                r'<object',
                r'<embed'
            ],
            'path_traversal': [
                r'\.\./+',
                r'%2e%2e/',
                r'\\.\\.\\',
                r'~/',
                r'/etc/',
                r'/proc/'
            ],
            'command_injection': [
                r';\s*(cat|ls|pwd|whoami|id|uname)',
                r'\|\s*(cat|ls|pwd|whoami|id|uname)',
                r'`[^`]*`',
                r'\$\([^)]*\)'
            ]
        }
        
        # Check for dangerous patterns
        threat_level = 0
        detected_threats = []
        
        for threat_type, patterns in dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL):
                    threat_level += 1
                    detected_threats.append(threat_type)
                    break
        
        # Log security events
        if threat_level > 0:
            self.log_security_event('input_validation_threat', {
                'input_type': input_type,
                'threat_level': threat_level,
                'detected_threats': detected_threats,
                'input_sample': cleaned[:100] + '...' if len(cleaned) > 100 else cleaned,
                'client_ip': request.remote_addr if hasattr(request, 'remote_addr') else 'unknown'
            })
        
        # Apply sanitization based on input type
        if input_type == 'username':
            # Only allow alphanumeric and underscore
            cleaned = re.sub(r'[^a-zA-Z0-9_]', '', cleaned)
            if len(cleaned) > 30:
                cleaned = cleaned[:30]
        
        elif input_type == 'password':
            # Less restrictive for passwords but check for obvious attacks
            if threat_level > 2:
                raise ValueError("Password contains potentially malicious content")
        
        elif input_type == 'session_code':
            # Only allow alphanumeric, convert to uppercase
            cleaned = re.sub(r'[^A-Z0-9]', '', cleaned.upper())
            if len(cleaned) != 6:
                raise ValueError("Invalid session code format")
        
        else:
            # General sanitization
            import html
            cleaned = html.escape(cleaned, quote=True)
            # Remove remaining dangerous patterns
            for patterns in dangerous_patterns.values():
                for pattern in patterns:
                    cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        return cleaned
    
    def check_rate_limit_security(self, client_ip, endpoint):
        """Security-focused rate limiting"""
        now = time.time()
        key = f"{client_ip}:{endpoint}"
        
        if key not in self.failed_attempts:
            self.failed_attempts[key] = []
        
        # Clean old attempts (older than 1 hour)
        self.failed_attempts[key] = [
            attempt for attempt in self.failed_attempts[key] 
            if now - attempt < 3600
        ]
        
        # Check if too many attempts
        recent_attempts = len([
            attempt for attempt in self.failed_attempts[key]
            if now - attempt < 900  # 15 minutes
        ])
        
        if recent_attempts > 20:  # More than 20 attempts in 15 minutes
            self.blocked_ips.add(client_ip)
            self.log_security_event('rate_limit_exceeded', {
                'client_ip': client_ip,
                'endpoint': endpoint,
                'attempts': recent_attempts
            })
            return False
        
        return True
    
    def validate_jwt_security(self, token):
        """Enhanced JWT validation with security checks"""
        try:
            # Decode without verification first to check structure
            unverified = jwt.decode(token, options={"verify_signature": False})
            
            # Check for suspicious claims
            if 'admin' in unverified or 'root' in unverified:
                self.log_security_event('suspicious_jwt_claims', {
                    'token_claims': list(unverified.keys()),
                    'client_ip': request.remote_addr if hasattr(request, 'remote_addr') else 'unknown'
                })
            
            # Now verify the token properly
            payload = jwt.decode(
                token,
                current_app.config.get('SECRET_KEY'),
                algorithms=['HS256']
            )
            
            # Check token age
            if 'exp' in payload:
                exp_time = datetime.fromtimestamp(payload['exp'])
                if exp_time < datetime.utcnow():
                    raise jwt.ExpiredSignatureError("Token has expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as e:
            # Log invalid token attempts
            self.log_security_event('invalid_token_attempt', {
                'error': str(e),
                'client_ip': request.remote_addr if hasattr(request, 'remote_addr') else 'unknown'
            })
            raise
    
    def check_session_security(self, session_data, user_context):
        """Validate session security"""
        security_issues = []
        
        # Check for session hijacking indicators
        if 'created_at' in session_data:
            created_time = session_data['created_at']
            if isinstance(created_time, str):
                created_time = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            
            # Sessions older than 24 hours should be refreshed
            if datetime.utcnow() - created_time > timedelta(hours=24):
                security_issues.append('session_too_old')
        
        # Check for suspicious session modifications
        if 'host_id' in session_data and user_context.get('user_id') != session_data['host_id']:
            # Non-host trying to perform host actions
            if request.method in ['DELETE', 'PUT'] and 'finalize' in request.path:
                security_issues.append('unauthorized_host_action')
        
        # Log security issues
        if security_issues:
            self.log_security_event('session_security_issues', {
                'issues': security_issues,
                'session_id': session_data.get('session_id', 'unknown'),
                'user_id': user_context.get('user_id', 'unknown'),
                'client_ip': request.remote_addr if hasattr(request, 'remote_addr') else 'unknown'
            })
        
        return len(security_issues) == 0, security_issues
    
    def log_security_event(self, event_type, details):
        """Log security events for monitoring"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'severity': self._calculate_severity(event_type)
        }
        
        self.security_events.append(event)
        
        # Keep only recent events (last 1000)
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Log to application logger for persistence
        if hasattr(current_app, 'logger'):
            current_app.logger.warning(f"Security Event - {event_type}: {json.dumps(details)}")
    
    def _calculate_severity(self, event_type):
        """Calculate severity level for security events"""
        high_severity = ['rate_limit_exceeded', 'suspicious_jwt_claims', 'unauthorized_host_action']
        medium_severity = ['input_validation_threat', 'invalid_token_attempt', 'session_security_issues']
        
        if event_type in high_severity:
            return 'high'
        elif event_type in medium_severity:
            return 'medium'
        else:
            return 'low'
    
    def get_security_report(self):
        """Generate security status report"""
        now = datetime.utcnow()
        recent_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event['timestamp']) > now - timedelta(hours=24)
        ]
        
        threat_summary = {}
        for event in recent_events:
            event_type = event['event_type']
            threat_summary[event_type] = threat_summary.get(event_type, 0) + 1
        
        return {
            'total_events_24h': len(recent_events),
            'threat_summary': threat_summary,
            'blocked_ips': len(self.blocked_ips),
            'security_status': 'healthy' if len(recent_events) < 10 else 'alert',
            'high_severity_events': len([e for e in recent_events if e['severity'] == 'high'])
        }
    
    def is_ip_blocked(self, ip_address):
        """Check if IP is temporarily blocked"""
        return ip_address in self.blocked_ips
    
    def unblock_ip(self, ip_address):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)

# Global security manager instance
security_manager = SecurityManager()

def security_required(check_type='general'):
    """Decorator for endpoints requiring security validation"""
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr or 'unknown'
            
            # Check if IP is blocked
            if security_manager.is_ip_blocked(client_ip):
                return jsonify({
                    'error': 'Access temporarily blocked',
                    'message': 'Your IP has been temporarily blocked due to suspicious activity'
                }), 403
            
            # Check rate limiting
            if not security_manager.check_rate_limit_security(client_ip, request.endpoint):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.'
                }), 429
            
            # Validate request data if present
            if request.is_json and request.get_json():
                try:
                    data = request.get_json()
                    for key, value in data.items():
                        if isinstance(value, str):
                            security_manager.validate_input_security(value, key)
                except ValueError as e:
                    return jsonify({
                        'error': 'Invalid input',
                        'message': str(e)
                    }), 400
            
            return func(*args, **kwargs)
        
        return decorated_function
    return decorator

def sanitize_text_input(text, max_length=1000):
    """
    Sanitize and validate text input with length limits
    
    Args:
        text (str): Input text to sanitize
        max_length (int): Maximum allowed length
    
    Returns:
        str: Sanitized text
    
    Raises:
        ValueError: If input is invalid or too long
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    
    # Check length limit
    if len(text) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")
    
    # Use existing security validation
    return security_manager.validate_input_security(text, 'general')