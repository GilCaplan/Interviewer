#!/bin/bash
#
# Install SocketIO dependencies for WebSocket collaboration tests
# This ensures python-socketio is available in Docker environment
#

echo "🔌 Installing SocketIO dependencies..."

# Install python-socketio with client support
pip install "python-socketio[client]>=5.13.0" --quiet --no-cache-dir

# Verify installation
python -c "import socketio; print('✅ SocketIO installed successfully')" 2>/dev/null || {
    echo "❌ Failed to install SocketIO"
    exit 1
}

echo "🎉 SocketIO dependencies ready for WebSocket collaboration"