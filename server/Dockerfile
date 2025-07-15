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

# Use app/__init__.py which reads SERVER_PORT from environment
CMD ["python", "app/__init__.py"]