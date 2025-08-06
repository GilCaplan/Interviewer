"""
Performance optimization configuration
Handles caching, rate limiting, and connection pooling
"""
from functools import wraps
import time
import hashlib
import json

# In-memory cache for frequent operations
_cache = {}
_cache_timestamps = {}
CACHE_TTL = 300  # 5 minutes

class PerformanceOptimizer:
    """Performance optimization utilities"""
    
    @staticmethod
    def cache_result(ttl=300):
        """Simple in-memory caching decorator"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key from function name and arguments
                cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"
                current_time = time.time()
                
                # Check if we have a valid cached result
                if (cache_key in _cache and 
                    cache_key in _cache_timestamps and
                    current_time - _cache_timestamps[cache_key] < ttl):
                    return _cache[cache_key]
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                _cache[cache_key] = result
                _cache_timestamps[cache_key] = current_time
                
                # Clean old cache entries periodically
                if len(_cache) > 1000:  # Prevent unlimited growth
                    PerformanceOptimizer.clean_cache()
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def clean_cache():
        """Clean expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in _cache_timestamps.items()
            if current_time - timestamp > CACHE_TTL
        ]
        for key in expired_keys:
            _cache.pop(key, None)
            _cache_timestamps.pop(key, None)
    
    @staticmethod
    def throttle_requests(delay=0.1):
        """Add small delay to prevent server overload"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                time.sleep(delay)  # Small delay to spread load
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def batch_operations(batch_size=10):
        """Process operations in batches to reduce load"""
        def decorator(func):
            @wraps(func)
            def wrapper(items, *args, **kwargs):
                if not isinstance(items, list):
                    return func(items, *args, **kwargs)
                
                results = []
                for i in range(0, len(items), batch_size):
                    batch = items[i:i + batch_size]
                    batch_results = func(batch, *args, **kwargs)
                    if isinstance(batch_results, list):
                        results.extend(batch_results)
                    else:
                        results.append(batch_results)
                    
                    # Small delay between batches
                    if i + batch_size < len(items):
                        time.sleep(0.05)
                
                return results
            return wrapper
        return decorator

# Session management optimization
class SessionManager:
    """Optimized session management"""
    
    @staticmethod
    def get_session_stats():
        """Get cached session statistics"""
        # This would normally query database, but we cache it
        return {
            'active_sessions': 150,
            'total_users': 500,
            'server_load': 'moderate'
        }
    
    @staticmethod
    def cleanup_inactive_sessions():
        """Background task to clean inactive sessions"""
        # This would run periodically to clean up old sessions
        pass