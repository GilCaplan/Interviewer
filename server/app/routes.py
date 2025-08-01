from flask import Blueprint, jsonify
from pymongo import MongoClient
from .config import Config
from .availability import availability_manager
from .security import security_manager
from .async_handler import task_manager
from .llm_service import LLMService
import os

main = Blueprint('main', __name__)


@main.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check with system status"""
    try:
        # Check database connectivity
        client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db_status = True
    except:
        db_status = False
    
    # Get system status
    system_status = availability_manager.get_system_status()
    system_status['database_connection'] = db_status
    
    overall_health = db_status and system_status['overall_health']
    
    return jsonify({
        "status": "ok" if overall_health else "degraded",
        "message": "Interview Assistant API is running",
        "system_status": system_status,
        "timestamp": availability_manager.last_health_check.isoformat()
    }), 200 if overall_health else 503


@main.route('/api/info', methods=['GET'])
def info():
    # Detect testing mode from multiple indicators
    testing_mode = (
        os.getenv('TESTING', '').lower() == 'true' or
        os.getenv('TEST_MODE', '').lower() == '1' or
        os.getenv('FLASK_ENV', '') == 'testing' or
        # Check if we're using test database
        'test' in os.getenv('MONGO_URI', '').lower() or
        # Check if server is running on test port  
        os.getenv('SERVER_PORT') == '5001'
    )
    
    return jsonify({
        "name": "Interview Process Assistant",
        "version": "0.1.0",
        "testing_mode": testing_mode,
        "features": [
            "Practice programming problems",
            "Logical puzzles/riddles", 
            "Interview questions",
            "Behavioral questions",
            "And more coming soon!"
        ],
        "system_metrics": {
            "async_tasks": task_manager.get_system_metrics(),
            "security_status": security_manager.get_security_report()
        }
    })


# System monitoring and security endpoints
@main.route('/api/system/status', methods=['GET'])
def system_status():
    """Comprehensive system status for monitoring"""
    return jsonify({
        "availability": availability_manager.get_system_status(),
        "security": security_manager.get_security_report(),
        "performance": task_manager.get_system_metrics(),
        "timestamp": availability_manager.last_health_check.isoformat()
    })

@main.route('/api/system/security-report', methods=['GET'])
def security_report():
    """Detailed security status report"""
    return jsonify(security_manager.get_security_report())

@main.route('/api/llm/status', methods=['GET'])
def llm_status():
    """Get detailed LLM service status"""
    try:
        status_info = LLMService.get_llm_status()
        
        return jsonify({
            "status": "available" if LLMService.is_available() else "unavailable",
            "services": status_info,
            "message": "LLM service status retrieved successfully",
            "timestamp": availability_manager.last_health_check.isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error retrieving LLM status: {str(e)}",
            "timestamp": availability_manager.last_health_check.isoformat()
        }), 500

# Template routes moved to templates.py module
