import os
import logging
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
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