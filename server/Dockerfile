FROM python:3.11-slim

WORKDIR /app

# Add curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Clean install with specific versions
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 flaskuser && chown -R flaskuser:flaskuser /app

# Expose default port (actual port controlled by environment)
EXPOSE 5001

USER flaskuser

CMD ["python", "-c", "from app import app, socketio_instance; import os; socketio_instance.run(app, host='0.0.0.0', port=int(os.environ.get('SERVER_PORT', 5001)), debug=True, allow_unsafe_werkzeug=True)"]