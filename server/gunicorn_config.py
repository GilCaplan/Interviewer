"""
Production-grade Gunicorn configuration for high concurrency
Optimized for 1000+ concurrent users with stability focus
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5001"
backlog = 2048

# Worker processes - optimized for high concurrency
workers = min(multiprocessing.cpu_count() * 2, 8)  # Balanced approach
worker_class = "eventlet"  # Support for WebSockets and async operations
worker_connections = 1000
max_requests = 2000  # Restart workers after handling this many requests
max_requests_jitter = 100  # Add randomness to avoid thundering herd
preload_app = True  # Load application code before forker workers

# Timeouts - adjusted for high load
timeout = 30
keepalive = 2
graceful_timeout = 30

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr  
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Performance tuning
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance
tmp_upload_dir = "/tmp"

# Security
limit_request_line = 8192
limit_request_fields = 200
limit_request_field_size = 16384

# Process naming
proc_name = "interview_platform"

def pre_fork(server, worker):
    """Called before worker processes are forked"""
    server.log.info("Worker about to be forked")

def worker_int(worker):
    """Called when worker receives INT or QUIT signal"""
    worker.log.info("Worker received INT or QUIT signal")

def on_exit(server):
    """Called when gunicorn is shutting down"""
    server.log.info("Gunicorn shutting down")