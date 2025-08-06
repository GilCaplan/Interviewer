"""
Ultra-High Scale Configuration for 1500+ Users
Extreme optimizations for maximum concurrency
"""
import os
import threading
import time
from functools import wraps

class UltraScaleConfig:
    """Configuration optimizations for 1500+ concurrent users"""
    
    @staticmethod
    def configure_system_limits():
        """Configure system for ultra-high concurrency"""
        try:
            import resource
            
            # Set maximum file descriptors
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            new_limit = min(hard, 16384)  # 16K file descriptors
            resource.setrlimit(resource.RLIMIT_NOFILE, (new_limit, hard))
            
            # Set stack size for threads
            threading.stack_size(128 * 1024)  # 128KB stack per thread
            
        except Exception as e:
            print(f"System limit configuration: {e}")
    
    @staticmethod
    def optimize_database_connections():
        """Optimize database for ultra-high load"""
        return {
            'maxPoolSize': 200,  # Increased pool size
            'minPoolSize': 50,   # Higher minimum
            'maxIdleTimeMS': 30000,  # 30 second idle timeout
            'serverSelectionTimeoutMS': 5000,  # 5 second selection timeout
            'connectTimeoutMS': 10000,  # 10 second connection timeout
            'socketTimeoutMS': 20000,   # 20 second socket timeout
        }
    
    @staticmethod
    def get_ultra_scale_flask_config():
        """Flask configuration for 1500+ users"""
        return {
            'MAX_CONTENT_LENGTH': 32 * 1024 * 1024,  # 32MB for ultra scale
            'JSON_MAX_SIZE': 10 * 1024 * 1024,       # 10MB JSON
            'SEND_FILE_MAX_AGE_DEFAULT': 300,        # 5 minute cache
            'PERMANENT_SESSION_LIFETIME': 1800,       # 30 minute sessions
            'SESSION_COOKIE_SECURE': False,           # For development
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
        }
    
    @staticmethod
    def ultra_scale_throttle(base_delay=0.02, max_delay=3.0):
        """Ultra-scale adaptive throttling decorator"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                import psutil
                
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent
                active_threads = threading.active_count()
                
                # Calculate dynamic delay based on multiple factors
                cpu_factor = cpu_percent / 100.0
                memory_factor = memory_percent / 100.0
                thread_factor = min(active_threads / 2000.0, 1.0)  # Expect up to 2000 threads
                
                # Weighted delay calculation
                load_factor = (cpu_factor * 0.4 + memory_factor * 0.4 + thread_factor * 0.2)
                
                if load_factor > 0.95:  # Extreme load
                    delay = max_delay
                elif load_factor > 0.85:  # Very high load
                    delay = max_delay * 0.7
                elif load_factor > 0.70:  # High load
                    delay = max_delay * 0.4
                elif load_factor > 0.50:  # Medium load
                    delay = base_delay * 2
                else:  # Normal load
                    delay = base_delay
                
                time.sleep(delay)
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Ultra-resilient error handling
                    return {"error": "Ultra-scale graceful failure", "message": str(e)}, 503
                    
            return wrapper
        return decorator

def configure_ultra_scale_environment():
    """Configure entire environment for 1500+ users"""
    config = UltraScaleConfig()
    
    # System configuration
    config.configure_system_limits()
    
    # Environment variables for ultra-scale
    os.environ['PYTHONHASHSEED'] = '0'
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Threading optimizations
    threading.stack_size(128 * 1024)  # Smaller stack size for more threads
    
    return config.get_ultra_scale_flask_config()

# Ultra-scale decorator for critical endpoints
ultra_scale_protection = UltraScaleConfig.ultra_scale_throttle()

# Database configuration for ultra-scale
ULTRA_SCALE_DB_CONFIG = UltraScaleConfig.optimize_database_connections()