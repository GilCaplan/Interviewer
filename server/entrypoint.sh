#!/bin/bash
#
# Docker Entrypoint Script for Interview Platform with LLM Support
# Handles model initialization and graceful startup
#

set -e

echo "🚀 Starting Interview Platform with LLM Support"
echo "========================================================"


# Function to display LLM status
display_llm_status() {
    echo "🧠 LLM Service Status:"
    echo "--------------------"
    
    # Check Gemini
    if [[ -n "$GEMINI_API_KEY" ]]; then
        echo "✅ Gemini API: Available"
    else
        echo "❌ Gemini API: No API key provided"
    fi
    
    
    echo "🔄 Fallback: Mock responses always available"
    echo ""
}

# Function to install additional dependencies
install_dependencies() {
    echo "📦 Installing additional dependencies..."
    
    # Install SocketIO for WebSocket collaboration tests
    if [[ -f "./install_socketio.sh" ]]; then
        echo "🔌 Installing SocketIO dependencies..."
        bash ./install_socketio.sh
    fi
}

# Function to wait for dependencies
wait_for_dependencies() {
    echo "⏳ Checking dependencies..."
    
    # Wait for database if MONGO_URI is provided
    if [[ -n "$MONGO_URI" ]]; then
        echo "🔍 Waiting for MongoDB connection..."
        python -c "
import os
import time
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

mongo_uri = os.environ.get('MONGO_URI', 'mongodb://db:27017/interview-assistant')
max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        client.server_info()
        print('✅ MongoDB connection successful')
        break
    except ServerSelectionTimeoutError:
        attempt += 1
        print(f'⏳ MongoDB not ready, attempt {attempt}/{max_attempts}')
        time.sleep(2)
else:
    print('⚠️ MongoDB connection timeout - continuing anyway')
"
    fi
}


# Main startup sequence
main() {
    echo "🔧 Environment: ${FLASK_ENV:-development}"
    echo "🌐 Server will start on port ${SERVER_PORT:-5000}"
    echo ""
    
    # Display LLM configuration
    display_llm_status
    
    # Install additional dependencies
    install_dependencies
    
    # Wait for dependencies
    wait_for_dependencies
    
    echo "🎯 Starting Flask application..."
    echo "========================================================"
    
    # Execute the main command
    exec "$@"
}

# Handle signals gracefully
cleanup() {
    echo ""
    echo "🛑 Received shutdown signal"
    echo "🧹 Cleaning up..."
    # Add any cleanup logic here
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run main function
main "$@"