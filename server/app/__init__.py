import os
import time
import redis
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .config import Config
from .routes import main
from .auth import auth
from .questions import questions
from .sessions import sessions_bp
from .templates import templates_bp
from .websocket_handlers import init_simple_websockets  # Only import the function
from .async_handler import init_async_manager, shutdown_async_manager
from .interviews import interviews_bp
from .crash_prevention import CrashPrevention


# Production optimization imports removed for Docker-only setup

def create_app(config_class=Config):
	app = Flask(__name__)
	app.config.from_object(config_class)

	# Docker-based configuration (production scaling removed)

	# Initialize the app with the config
	config_class.init_app(app)

	# Configure session storage (fallback to filesystem if Redis unavailable)
	try:
		# Try Redis first for production scalability
		redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
		redis_client.ping()  # Test connection
		app.config['SESSION_TYPE'] = 'redis'
		app.config['SESSION_REDIS'] = redis_client
		limiter_storage = "redis://localhost:6379"
		app.logger.info("✅ Using Redis for sessions and rate limiting")
	except (redis.RedisError, redis.ConnectionError, Exception) as e:
		# Fallback to memory/filesystem for development
		app.config['SESSION_TYPE'] = 'filesystem'
		limiter_storage = "memory://"
		app.logger.warning(f"⚠️ Redis unavailable ({str(e)}), using filesystem/memory storage")

	app.config['SESSION_PERMANENT'] = False
	app.config['SESSION_USE_SIGNER'] = True
	app.config['SESSION_KEY_PREFIX'] = 'interview_platform:'
	app.config['SESSION_COOKIE_HTTPONLY'] = True
	app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

	# Session management handled by JWT tokens

	# Initialize rate limiter for API protection
	# Use much higher limits in testing mode
	testing_mode = (
			os.getenv('TESTING', '').lower() == 'true' or
			os.getenv('TEST_MODE', '').lower() == '1' or
			os.getenv('FLASK_ENV', '') == 'testing'
	)

	if testing_mode:
		default_limits = ["500000 per hour", "50000 per minute"]  # Very high limits for testing
	else:
		default_limits = ["1000 per hour", "100 per minute"]

	limiter = Limiter(
		key_func=get_remote_address,
		default_limits=default_limits,
		storage_uri=limiter_storage
	)
	limiter.init_app(app)

	# Create SocketIO instance with optimized settings for 1000+ users
	socketio = SocketIO()

	# Initialize SocketIO for ultra-scale (1500+ users)
	socketio.init_app(app,
	                  cors_allowed_origins="*",
	                  async_mode='threading',  # Threading for Python 3.13 compatibility
	                  logger=False,  # Disable for performance
	                  engineio_logger=False,  # Disable for performance
	                  max_http_buffer_size=4000000,  # 4MB buffer for ultra-high load
	                  ping_timeout=60,  # Increased for ultra-scale stability
	                  ping_interval=30,  # Longer intervals under high load
	                  max_decode_packets=200,  # Higher batch size for efficiency
	                  allow_upgrades=True,
	                  transports=['websocket', 'polling'])

	# Store socketio instance on app for access
	app.socketio = socketio

	# Initialize websocket handlers with the socketio instance
	init_simple_websockets(socketio)

	# Enable CORS with more specific configuration
	# CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
	CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

	# Apply rate limiting to auth endpoints
	# limiter.limit("10 per minute")(auth)
	# limiter.limit("50 per minute")(sessions_bp)

	# Register blueprints
	app.register_blueprint(main)
	app.register_blueprint(auth)
	app.register_blueprint(questions)
	app.register_blueprint(sessions_bp)
	app.register_blueprint(templates_bp)
	app.register_blueprint(interviews_bp)

	# Enhanced error handlers for graceful error handling and security
	@app.errorhandler(400)
	def bad_request(error):
		return {"error": "Bad request", "message": "Invalid request format"}, 400

	@app.errorhandler(404)
	def not_found(error):
		return {"error": "Not found", "message": "Requested resource not found"}, 404

	@app.errorhandler(413)
	def request_entity_too_large(error):
		return {"error": "Request too large", "message": "Request payload exceeds maximum size limit"}, 413

	@app.errorhandler(500)
	def internal_error(error):
		return {"error": "Internal server error", "message": "An unexpected error occurred"}, 500

	# Global exception handler to prevent any crashes
	@app.errorhandler(Exception)
	def handle_all_exceptions(error):
		"""Catch all unhandled exceptions to prevent server crashes"""
		import traceback
		import logging

		# Log the full traceback for debugging
		logging.error(f"Unhandled exception: {error}")
		logging.error(f"Traceback: {traceback.format_exc()}")

		# Always return a graceful error response, never crash
		return {
			"error": "Internal server error",
			"message": "An unexpected error occurred but the server remains stable"
		}, 500

	from werkzeug.exceptions import BadRequest
	from flask import request
	import json

	@app.errorhandler(BadRequest)
	def handle_bad_request(error):
		return {"error": "Bad request", "message": "Invalid JSON or request format"}, 400

	@app.before_request
	def validate_json():
		"""Validate JSON for POST/PUT requests with size and security checks"""
		if request.method in ['POST', 'PUT'] and request.content_type and 'application/json' in request.content_type:
			try:
				if request.data:  # Only validate if there's actually data
					# Check content length first
					if request.content_length and request.content_length > app.config.get('JSON_MAX_SIZE',
					                                                                      5 * 1024 * 1024):
						return {"error": "Request too large", "message": "JSON payload exceeds maximum size"}, 413

					json_data = request.get_json(force=True)

					# Additional security: check for deeply nested objects
					if isinstance(json_data, dict):
						def check_depth(obj, depth=0):
							if depth > 20:  # Prevent deeply nested JSON attacks
								return False
							if isinstance(obj, dict):
								return all(check_depth(v, depth + 1) for v in obj.values())
							elif isinstance(obj, list):
								return all(check_depth(item, depth + 1) for item in obj)
							return True

						if not check_depth(json_data):
							return {"error": "Invalid JSON", "message": "JSON structure too deeply nested"}, 400

			except UnicodeDecodeError:
				return {"error": "Invalid encoding", "message": "Request contains invalid character encoding"}, 400
			except Exception:
				return {"error": "Invalid JSON", "message": "Request body contains malformed JSON"}, 400

	@app.after_request
	def after_request(response):
		response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
		response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
		return response

	# Initialize async task manager
	init_async_manager()

	# Enhanced request monitoring and performance optimization
	@app.before_request
	def optimize_request_handling():
		CrashPrevention.monitor_resources()
		# Clean cache periodically
		# Production optimization calls removed for Docker-only setup

	# Add health check endpoint for load balancers
	@app.route('/api/health')
	def health_check():
		return {'status': 'healthy', 'timestamp': int(time.time())}, 200

	# Add server stats endpoint with high-scale metrics
	@app.route('/api/stats')
	# @limiter.limit("5 per minute")
	def server_stats():
		import threading
		import os
		try:
			# Try to get system stats without psutil
			import resource
			memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024  # Convert to MB
			cpu_usage = 0.0  # Placeholder
		except ImportError:
			memory_usage = 0.0
			cpu_usage = 0.0

		# High-scale statistics removed for Docker-only setup
		high_scale_stats = {}

		return {
			'memory_usage': memory_usage,
			'cpu_usage': cpu_usage,
			'active_threads': threading.active_count(),
			'connections': getattr(socketio.server, 'manager', {}).get('connection_count', 0),
			'high_scale_metrics': high_scale_stats,
			'pid': os.getpid()
		}

	# Register shutdown handler
	@app.teardown_appcontext
	def shutdown_async_on_teardown(exception):
		shutdown_async_manager()

	# Store limiter instance for use in other modules
	app.limiter = limiter

	return app


# Create default app instance for Flask CLI compatibility
app = create_app()
# SocketIO is attached to the app instance as app.socketio

if __name__ == '__main__':
	# Use environment variable SERVER_PORT if available, else default to 5000
	port = int(os.environ.get('SERVER_PORT') or 5000)
	app.socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
