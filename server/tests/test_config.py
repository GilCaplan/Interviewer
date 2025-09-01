#!/usr/bin/env python3
"""
Centralized Test Configuration
Single place to configure all test settings including server port
"""

import os

# Load .env file from project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(project_root, '.env')

# Try to load dotenv if available, otherwise parse manually
try:
    from dotenv import load_dotenv
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
except ImportError:
    # Manual .env parsing if dotenv not available
    if os.path.exists(dotenv_path):
        with open(dotenv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

# Server Configuration - Use SERVER_PORT from .env (should be 5002)
TEST_SERVER_PORT = os.getenv('TEST_SERVER_PORT') or os.getenv('SERVER_PORT', '5002')
TEST_SERVER_HOST = os.getenv('TEST_SERVER_HOST', 'localhost')
TEST_API_BASE_URL = f"http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}"

# Database Configuration
TEST_DATABASE_URI = os.getenv('TEST_DATABASE_URI', 'mongodb://localhost:27017/test_interview_platform')

# API Endpoints
API_URLS = [
    TEST_API_BASE_URL,
    f"http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}",
    f"http://server:{TEST_SERVER_PORT}",  # Docker service name
]

# Test Settings
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BATCH_SIZE = 50

# LLM Configuration for Testing
TEST_GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyDPcKzuRmfAsYnyYb44nEYuozs1plPjyQ8')

def get_primary_api_url():
    """Get the primary API URL for testing"""
    return TEST_API_BASE_URL

def get_all_api_urls():
    """Get all possible API URLs to try"""
    return API_URLS

def is_server_running():
    """Check if test server is running"""
    import requests
    try:
        response = requests.get(f"{TEST_API_BASE_URL}/api/health", timeout=5)
        # Accept both healthy (200) and degraded (503) status
        return response.status_code in [200, 503]
    except:
        return False

# Environment Variables for Tests
TEST_ENV_VARS = {
    'TESTING': 'true',
    'TEST_MODE': '1',
    'FLASK_ENV': 'testing',
    'SERVER_PORT': TEST_SERVER_PORT,
    'GEMINI_API_KEY': TEST_GEMINI_API_KEY,
}

def setup_test_environment():
    """Setup environment variables for testing"""
    for key, value in TEST_ENV_VARS.items():
        os.environ[key] = value