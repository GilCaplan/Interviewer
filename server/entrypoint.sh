#!/bin/bash
#
# Docker Entrypoint Script for Interview Platform with LLM Support
# Handles model initialization and graceful startup
#

set -e

echo "🚀 Starting Interview Platform with LLM Support"
echo "========================================================"

# Function to check if model is downloaded
check_model_downloaded() {
    local model_path="${LOCAL_MODEL_PATH:-./models/llama-1b-instruct}"
    if [[ -f "$model_path/config.json" && -f "$model_path/tokenizer.json" ]]; then
        return 0  # Model exists
    else
        return 1  # Model missing
    fi
}

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
    
    # Check Local Model
    if [[ "$USE_LOCAL_MODEL" == "true" ]]; then
        if check_model_downloaded; then
            echo "✅ Local LLM: Model downloaded and ready"
        else
            echo "⚠️ Local LLM: Model not downloaded (will download on first use)"
        fi
    else
        echo "❌ Local LLM: Disabled (USE_LOCAL_MODEL=false)"
    fi
    
    echo "🔄 Fallback: Mock responses always available"
    echo ""
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

# Function to pre-warm local LLM (optional)
prewarm_local_llm() {
    if [[ "$USE_LOCAL_MODEL" == "true" && "$PREWARM_LOCAL_MODEL" == "true" ]]; then
        echo "🔥 Pre-warming local LLM model..."
        python -c "
from app.local_llm_service import local_llm_service
try:
    if local_llm_service.initialize_model():
        print('✅ Local LLM pre-warmed successfully')
    else:
        print('⚠️ Local LLM pre-warm failed - will initialize on first use')
except Exception as e:
    print(f'⚠️ Local LLM pre-warm error: {e}')
" || echo "⚠️ Pre-warm failed - continuing anyway"
    fi
}

# Main startup sequence
main() {
    echo "🔧 Environment: ${FLASK_ENV:-development}"
    echo "🌐 Server will start on port ${SERVER_PORT:-5000}"
    echo ""
    
    # Display LLM configuration
    display_llm_status
    
    # Wait for dependencies
    wait_for_dependencies
    
    # Pre-warm model if requested
    prewarm_local_llm
    
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