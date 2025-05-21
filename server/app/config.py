import os
import logging
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/interview-assistant'

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