FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

# Clean install with specific versions
RUN pip install --no-cache-dir -r requirements.txt
RUN npm install @monaco-editor/react

COPY . .

# Add curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

EXPOSE 5000

# Use a direct python command to avoid Flask CLI issues
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]