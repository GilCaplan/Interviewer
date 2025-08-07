import os
import logging
import secrets
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/interview-assistant'
    
    # LLM Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    USE_MOCK_LLM = os.environ.get('USE_MOCK_LLM', 'false').lower() == 'true'
    
    # Local LLM Configuration
    HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN')
    USE_LOCAL_MODEL = os.environ.get('USE_LOCAL_MODEL', 'true').lower() == 'true'
    LOCAL_MODEL_NAME = os.environ.get('LOCAL_MODEL_NAME', 'meta-llama/Llama-3.2-1B-Instruct')
    LOCAL_MODEL_PATH = os.environ.get('LOCAL_MODEL_PATH', './models/llama-1b-instruct')
    PREWARM_LOCAL_MODEL = os.environ.get('PREWARM_LOCAL_MODEL', 'false').lower() == 'true'
    
    # Rate Limiting
    LLM_REQUESTS_PER_MINUTE = int(os.environ.get('LLM_REQUESTS_PER_MINUTE', '15'))
    LLM_REQUESTS_PER_DAY = int(os.environ.get('LLM_REQUESTS_PER_DAY', '1500'))

    # High-Performance Scaling Configuration
    MAX_CONCURRENT_CONNECTIONS = int(os.environ.get('MAX_CONCURRENT_CONNECTIONS', '2000'))
    DATABASE_POOL_SIZE = int(os.environ.get('DATABASE_POOL_SIZE', '200'))  # Match ultra_scale_config
    MAX_OVERFLOW = int(os.environ.get('MAX_OVERFLOW', '200'))
    POOL_TIMEOUT = int(os.environ.get('POOL_TIMEOUT', '30'))
    POOL_RECYCLE = int(os.environ.get('POOL_RECYCLE', '3600'))
    
    # Thread Pool Configuration
    MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '500'))
    THREAD_POOL_SIZE = int(os.environ.get('THREAD_POOL_SIZE', '1000'))
    
    # Request Timeout Configuration
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '120'))
    SOCKET_TIMEOUT = int(os.environ.get('SOCKET_TIMEOUT', '60'))

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or logging.INFO

    @staticmethod
    def init_app(app):
        # Configure logging
        handler = logging.StreamHandler()
        handler.setLevel(Config.LOG_LEVEL)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.setLevel(Config.LOG_LEVEL)