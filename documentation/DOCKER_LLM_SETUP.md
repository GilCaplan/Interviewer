# Docker Setup with Local LLM Support

This guide explains how to run the Interview Platform with local Llama 3.2 1B model support using Docker.

## 🎯 Overview

The Docker LLM setup provides three LLM fallback layers:
1. **Gemini API** (if API key provided) - Production quality
2. **Local Llama 3.2 1B** (downloaded automatically) - Good quality, no API costs  
3. **Mock responses** (always available) - Basic fallback

## 🚀 Quick Start

### Option 1: One-Command Setup
```bash
# Download and run the automated setup script
./build-and-run-llm.sh
```

### Option 2: Manual Docker Compose
```bash
# Copy environment template
cp .env.docker.llm .env

# Build and start services
docker-compose -f docker-compose.llm.yml up --build -d

# Check status
docker-compose -f docker-compose.llm.yml ps
```

## 📋 Build Options

### Runtime Download (Default - Recommended)
- **Fastest build time** (~5 minutes)
- Model downloads on first LLM request (~5-10 minutes)
- Best for development and testing

```bash
./build-and-run-llm.sh --runtime-download
```

### Build-Time Download
- **Slower build time** (~15-20 minutes) 
- **Fastest startup** - model ready immediately
- Best for production deployments

```bash
./build-and-run-llm.sh --build-download
```

### No Local Model
- **Smallest image size**
- Uses only Gemini API or mock responses
- Best for resource-constrained environments

```bash
./build-and-run-llm.sh --no-local-model
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# LLM Configuration
GEMINI_API_KEY=                          # Optional: Google Gemini API key
HUGGINGFACE_TOKEN=                       # Optional: For private model access
USE_LOCAL_MODEL=true                     # Enable/disable local model
DOWNLOAD_MODEL_AT_BUILD=false            # Download during build vs runtime
PREWARM_LOCAL_MODEL=false               # Pre-load model on startup

# Performance Tuning
LLM_REQUESTS_PER_MINUTE=15              # Rate limiting
LLM_REQUESTS_PER_DAY=1500               # Daily quota
```

### HuggingFace Token Setup

1. Create account at https://huggingface.co
2. Go to Settings → Access Tokens
3. Create a new token with "Read" permissions
4. Add to `.env`: `HUGGINGFACE_TOKEN=your_token_here`

**Note**: Token is optional - models download without it, but having one ensures faster downloads and access to gated models.

## 💾 System Requirements

### Minimum Requirements
- **RAM**: 4GB available
- **Disk**: 3GB free space
- **CPU**: 2+ cores
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### Recommended Requirements  
- **RAM**: 8GB+ (for smooth multi-user operation)
- **Disk**: 5GB+ free space
- **CPU**: 4+ cores
- **SSD**: For faster model loading

### GPU Support (Optional)
```bash
# Install nvidia-docker2
# Update docker-compose.llm.yml to use GPU-enabled base image
# Set USE_GPU=true in .env
```

## 🐳 Docker Architecture

### Services Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │    Database     │
│   (React)       │    │  (Flask + LLM)  │    │   (MongoDB)     │
│   Port: 3000    │◄───┤   Port: 5000    │◄───┤   Port: 27017   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Volume Mounts
- `llm_models:/app/models` - Persistent model storage
- `llm_cache:/app/.cache` - HuggingFace cache
- `mongodb_data_llm:/data/db` - Database persistence

### Resource Limits
```yaml
# Backend container limits
Memory: 4GB limit, 2GB reservation
CPU: 2.0 cores limit, 1.0 core reservation
```

## 🔧 Development Workflow

### Local Development with Docker
```bash
# Start with auto-rebuild on code changes
docker-compose -f docker-compose.llm.yml up --build

# View logs in real-time
docker-compose -f docker-compose.llm.yml logs -f backend

# Execute commands in running container
docker-compose -f docker-compose.llm.yml exec backend bash
```

### Testing LLM Integration
```bash
# Check LLM service status
curl http://localhost:5000/api/llm/status

# Test question generation
curl -X POST http://localhost:5000/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{"subject": "python", "type": "open_ended"}'
```

## 🎛️ Performance Optimization

### Memory Optimization
- **4-bit quantization**: Reduces model memory by ~75%
- **CPU inference**: Works on any system, no GPU required
- **Model caching**: Downloads once, reuses across restarts

### Startup Optimization  
```bash
# Pre-warm model (slower startup, faster first request)
./build-and-run-llm.sh --prewarm

# Build-time download (slower build, faster startup)  
./build-and-run-llm.sh --build-download
```

### Production Settings
```bash
# .env for production
FLASK_ENV=production
PREWARM_LOCAL_MODEL=true
DOWNLOAD_MODEL_AT_BUILD=true
USE_LOCAL_MODEL=true
GEMINI_API_KEY=your_production_key
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Out of Memory During Build
```bash
# Increase Docker memory limit to 6GB+
# Or use runtime download instead
./build-and-run-llm.sh --runtime-download
```

#### 2. Model Download Fails
```bash
# Check HuggingFace token
echo $HUGGINGFACE_TOKEN

# Manual download test
docker-compose -f docker-compose.llm.yml exec backend python download_model.py
```

#### 3. Slow Performance
```bash
# Check available resources
docker stats

# Enable pre-warming
PREWARM_LOCAL_MODEL=true docker-compose -f docker-compose.llm.yml up -d
```

#### 4. Container Crashes
```bash
# Check logs for memory issues
docker-compose -f docker-compose.llm.yml logs backend

# Increase memory limits in docker-compose.llm.yml
```

### Health Checks
```bash
# Overall system health
curl http://localhost:5000/api/health

# LLM-specific status  
curl http://localhost:5000/api/llm/status

# Database connection
curl http://localhost:5000/api/db/health
```

### Log Analysis
```bash
# View all services
docker-compose -f docker-compose.llm.yml logs

# Backend only
docker-compose -f docker-compose.llm.yml logs backend

# Follow logs in real-time
docker-compose -f docker-compose.llm.yml logs -f --tail=100
```

## 🔐 Security Considerations

### Production Deployment
- Change default `SECRET_KEY`
- Use environment-specific `.env` files
- Enable HTTPS with SSL certificates
- Restrict network access to necessary ports
- Regular security updates for base images

### API Key Security
```bash
# Use Docker secrets for sensitive data
echo "your_api_key" | docker secret create gemini_api_key -
```

## 📊 Monitoring

### Built-in Metrics
- Model load status and memory usage
- Request rate limiting status  
- Database connection health
- Container resource utilization

### External Monitoring
```bash
# Add Prometheus metrics endpoint
# Configure Grafana dashboards
# Set up alerting for resource limits
```

## 🔄 Updates and Maintenance

### Updating the Model
```bash
# Remove old model and restart
docker-compose -f docker-compose.llm.yml down
docker volume rm project_interviewer_llm_models
docker-compose -f docker-compose.llm.yml up --build -d
```

### Updating the Application
```bash
# Pull latest code and rebuild
git pull
docker-compose -f docker-compose.llm.yml up --build -d
```

### Backup and Restore
```bash
# Backup database and models
docker run --rm -v project_interviewer_mongodb_data_llm:/data -v $(pwd):/backup alpine tar czf /backup/mongodb_backup.tar.gz /data
docker run --rm -v project_interviewer_llm_models:/data -v $(pwd):/backup alpine tar czf /backup/models_backup.tar.gz /data
```

## 📈 Scaling

### Horizontal Scaling
- Deploy multiple backend replicas
- Use load balancer (nginx/traefik)
- Shared model volume across replicas
- Database clustering for high availability

### Vertical Scaling
- Increase container memory limits
- Use GPU-enabled instances
- Optimize model quantization settings
- Enable model parallelism for larger models