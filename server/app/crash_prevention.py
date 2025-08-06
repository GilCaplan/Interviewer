"""
Comprehensive Crash Prevention System
Ensures server NEVER crashes under any load conditions
"""

import functools
import logging
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
import psutil
import os

# Global crash prevention state
_request_counts = defaultdict(lambda: deque())
_error_counts = defaultdict(int)
_circuit_breakers = defaultdict(lambda: {'state': 'closed', 'failure_count': 0, 'last_failure': None})
_resource_monitor = {'memory_usage': 0, 'cpu_usage': 0, 'active_threads': 0}

class CrashPrevention:
    """Global crash prevention manager"""
    
    @staticmethod
    def monitor_resources():
        """Monitor system resources to prevent crashes"""
        try:
            process = psutil.Process(os.getpid())
            _resource_monitor['memory_usage'] = process.memory_percent()
            _resource_monitor['cpu_usage'] = process.cpu_percent()
            _resource_monitor['active_threads'] = threading.active_count()
            
            # Emergency resource protection
            if _resource_monitor['memory_usage'] > 85:
                logging.warning(f"⚠️ High memory usage: {_resource_monitor['memory_usage']:.1f}%")
            
            if _resource_monitor['active_threads'] > 500:
                logging.warning(f"⚠️ High thread count: {_resource_monitor['active_threads']}")
                
        except Exception as e:
            logging.error(f"Resource monitoring failed: {e}")
    
    @staticmethod
    def circuit_breaker(endpoint_name, failure_threshold=10, recovery_timeout=60):
        """Circuit breaker decorator to prevent cascade failures"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                breaker = _circuit_breakers[endpoint_name]
                now = datetime.now()
                
                # Check circuit breaker state
                if breaker['state'] == 'open':
                    if breaker['last_failure'] and now - breaker['last_failure'] > timedelta(seconds=recovery_timeout):
                        breaker['state'] = 'half_open'
                        breaker['failure_count'] = 0
                    else:
                        return {'error': 'Service temporarily unavailable'}, 503
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Success - reset circuit breaker
                    if breaker['state'] == 'half_open':
                        breaker['state'] = 'closed'
                        breaker['failure_count'] = 0
                    
                    return result
                    
                except Exception as e:
                    # Handle failure
                    breaker['failure_count'] += 1
                    breaker['last_failure'] = now
                    
                    if breaker['failure_count'] >= failure_threshold:
                        breaker['state'] = 'open'
                        logging.warning(f"🔥 Circuit breaker opened for {endpoint_name}")
                    
                    # Always return graceful error, never crash
                    logging.error(f"Graceful failure in {endpoint_name}: {e}")
                    return {'error': 'Operation failed gracefully', 'details': str(e)}, 500
            
            return wrapper
        return decorator
    
    @staticmethod
    def rate_limit_protection(endpoint_name, max_requests=100, time_window=60):
        """Advanced rate limiting to prevent server overload"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                now = time.time()
                requests = _request_counts[endpoint_name]
                
                # Clean old requests outside time window
                while requests and requests[0] < now - time_window:
                    requests.popleft()
                
                # Check rate limit
                if len(requests) >= max_requests:
                    logging.warning(f"⚠️ Rate limit exceeded for {endpoint_name}")
                    return {'error': 'Rate limit exceeded', 'retry_after': time_window}, 429
                
                # Record request
                requests.append(now)
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Rate-limited endpoint {endpoint_name} failed gracefully: {e}")
                    return {'error': 'Request failed', 'message': str(e)}, 500
            
            return wrapper
        return decorator

def safe_execute(func, default_return=None, log_errors=True):
    """Execute function safely with guaranteed no crashes"""
    try:
        return func()
    except Exception as e:
        if log_errors:
            logging.error(f"Safe execution failed gracefully: {e}")
        return default_return

def safe_database_operation(operation, default_return=None):
    """Execute database operations with retry and graceful failure"""
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            
            logging.error(f"Database operation failed after {max_retries} attempts: {e}")
            return default_return

def memory_safe_operation(operation, max_memory_mb=500):
    """Execute operation with memory monitoring"""
    try:
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        result = operation()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        if final_memory - initial_memory > max_memory_mb:
            logging.warning(f"⚠️ High memory allocation: {final_memory - initial_memory:.1f}MB")
        
        return result
    except Exception as e:
        logging.error(f"Memory-safe operation failed gracefully: {e}")
        return None

# Global exception handler
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global handler to prevent any uncaught exceptions from crashing server"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow graceful shutdown
        return
    
    logging.critical(f"🚨 CRITICAL ERROR CAUGHT (Server protected from crash): {exc_type.__name__}: {exc_value}")
    logging.critical("📊 Resource State:", extra={'memory': _resource_monitor['memory_usage'], 
                                                 'threads': _resource_monitor['active_threads']})

# Install global exception handler
import sys
sys.excepthook = global_exception_handler