# Availability and redundancy management module
import time
import json
import logging
from datetime import datetime, timedelta
from flask import current_app
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from .config import Config

class AvailabilityManager:
    """Manages system availability and handles failures gracefully"""
    
    def __init__(self):
        self.service_status = {
            'database': True,
            'llm_service': True,
            'websocket': True,
            'session_storage': True
        }
        self.fallback_data = {}
        self.error_counts = {}
        self.last_health_check = datetime.utcnow()
        
    def check_database_health(self, db_client):
        """Check MongoDB database connectivity"""
        try:
            # Simple ping test
            db_client.admin.command('ping')
            self.service_status['database'] = True
            self.error_counts['database'] = 0
            return True
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            self.service_status['database'] = False
            self.error_counts['database'] = self.error_counts.get('database', 0) + 1
            current_app.logger.error(f"Database health check failed: {e}")
            return False
    
    def check_llm_service_health(self):
        """Check LLM service availability"""
        try:
            # We'll implement a simple check - if we've had recent successful LLM calls
            recent_failures = self.error_counts.get('llm_service', 0)
            if recent_failures > 5:  # More than 5 consecutive failures
                self.service_status['llm_service'] = False
                return False
            
            self.service_status['llm_service'] = True
            return True
        except Exception as e:
            self.service_status['llm_service'] = False
            self.error_counts['llm_service'] = self.error_counts.get('llm_service', 0) + 1
            current_app.logger.error(f"LLM service health check failed: {e}")
            return False
    
    def handle_database_failure(self, operation_type, data=None):
        """Handle database failure with fallback strategies"""
        current_app.logger.warning(f"Database failure during {operation_type}, implementing fallback")
        
        if operation_type == 'session_read':
            # Return cached session data if available
            return self.fallback_data.get('sessions', {})
        
        elif operation_type == 'session_write':
            # Cache session data in memory for later persistence
            if 'sessions' not in self.fallback_data:
                self.fallback_data['sessions'] = {}
            if data:
                session_id = data.get('session_id')
                if session_id:
                    self.fallback_data['sessions'][session_id] = data
            return True
        
        elif operation_type == 'user_read':
            # Allow continued operation with limited functionality
            return {'username': 'temp_user', 'user_id': 'temp_id', 'is_guest': True}
        
        return None
    
    def handle_llm_failure(self, request_type, context=None):
        """Handle LLM service failure with mock responses"""
        current_app.logger.warning(f"LLM service failure for {request_type}, using fallback")
        
        fallback_responses = {
            'question_suggestion': {
                'multiple_choice': "What is the most important concept in this topic?",
                'open_ended': "Explain your understanding of this concept.",
                'coding': "Write a function that solves this problem.",
                'true_false': "This statement is correct.",
                'short_answer': "Provide a brief explanation."
            },
            'general_chat': [
                "I'm currently experiencing connectivity issues. Please try again later.",
                "Service temporarily unavailable. Your session data is safe.",
                "I'll be back online shortly. Continue working on your questions."
            ]
        }
        
        if request_type in fallback_responses:
            if isinstance(fallback_responses[request_type], dict):
                question_type = context.get('question_type', 'open_ended') if context else 'open_ended'
                return fallback_responses[request_type].get(question_type, "Service temporarily unavailable.")
            else:
                import random
                return random.choice(fallback_responses[request_type])
        
        return "Service temporarily unavailable. Please try again later."
    
    def recover_from_failures(self, db_client):
        """Attempt to recover from service failures"""
        recovery_actions = []
        
        # Try to recover database connection
        if not self.service_status['database']:
            if self.check_database_health(db_client):
                recovery_actions.append("Database connection restored")
                
                # Persist any cached data
                if 'sessions' in self.fallback_data:
                    try:
                        sessions_collection = db_client.get_default_database().simple_sessions
                        for session_id, session_data in self.fallback_data['sessions'].items():
                            sessions_collection.update_one(
                                {'session_id': session_id},
                                {'$set': session_data},
                                upsert=True
                            )
                        recovery_actions.append("Cached session data persisted")
                        self.fallback_data['sessions'] = {}
                    except Exception as e:
                        current_app.logger.error(f"Failed to persist cached data: {e}")
        
        # Reset error counts on successful recovery
        if recovery_actions:
            self.error_counts = {}
            current_app.logger.info(f"Recovery actions completed: {recovery_actions}")
        
        return recovery_actions
    
    def get_system_status(self):
        """Get comprehensive system status"""
        overall_health = all(self.service_status.values())
        
        return {
            'overall_health': overall_health,
            'services': self.service_status.copy(),
            'error_counts': self.error_counts.copy(),
            'last_health_check': self.last_health_check.isoformat(),
            'fallback_active': len(self.fallback_data) > 0,
            'uptime_status': 'healthy' if overall_health else 'degraded'
        }
    
    def log_service_failure(self, service_name, error_message):
        """Log service failure for monitoring"""
        self.error_counts[service_name] = self.error_counts.get(service_name, 0) + 1
        current_app.logger.error(f"Service failure - {service_name}: {error_message}")
        
        # If too many errors, mark service as down
        if self.error_counts[service_name] > 3:
            self.service_status[service_name] = False
    
    def reset_service_status(self, service_name):
        """Reset service status after successful operation"""
        self.service_status[service_name] = True
        self.error_counts[service_name] = 0

# Global availability manager instance
availability_manager = AvailabilityManager()

def with_availability_handling(service_name, fallback_handler=None):
    """Decorator for functions that need availability handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                availability_manager.reset_service_status(service_name)
                return result
            except Exception as e:
                availability_manager.log_service_failure(service_name, str(e))
                
                if fallback_handler:
                    return fallback_handler(*args, **kwargs)
                
                # Default fallback behavior
                if service_name == 'database':
                    return availability_manager.handle_database_failure('unknown', kwargs.get('data'))
                elif service_name == 'llm_service':
                    return availability_manager.handle_llm_failure('unknown', kwargs)
                
                raise e
        
        return wrapper
    return decorator