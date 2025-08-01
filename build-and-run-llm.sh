#!/bin/bash
#
# Build and Run Script for Interview Platform with Local LLM
# Provides different build options for various use cases
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOWNLOAD_AT_BUILD=false
PREWARM_MODEL=false
BUILD_TYPE="runtime-download"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "🤖 Interview Platform with Local LLM - Build Script"
    echo "=================================================="
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Build Types:"
    echo "  --build-download    Download model during build (slower build, faster startup)"
    echo "  --runtime-download  Download model at runtime (faster build, slower first startup) [DEFAULT]"
    echo "  --no-local-model    Disable local model entirely (smallest image)"
    echo ""
    echo "Options:"
    echo "  --prewarm          Pre-warm model on startup (requires more memory)"
    echo "  --gpu             Enable GPU support (requires nvidia-docker)"
    echo "  --help            Show this help message"
    echo ""
    echo "Environment:"
    echo "  Set HUGGINGFACE_TOKEN in .env for private model access"
    echo ""
    echo "Examples:"
    echo "  $0                           # Quick build, model downloads on first use"
    echo "  $0 --build-download          # Download model during build"
    echo "  $0 --prewarm                 # Pre-warm model on startup"
    echo "  $0 --no-local-model          # Use only Gemini API or mocks"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-download)
            DOWNLOAD_AT_BUILD=true
            BUILD_TYPE="build-download"
            shift
            ;;
        --runtime-download)
            DOWNLOAD_AT_BUILD=false
            BUILD_TYPE="runtime-download"
            shift
            ;;
        --no-local-model)
            BUILD_TYPE="no-local"
            shift
            ;;
        --prewarm)
            PREWARM_MODEL=true
            shift
            ;;
        --gpu)
            USE_GPU=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check available disk space (need ~2GB for model)
    if [[ "$BUILD_TYPE" == "build-download" ]]; then
        AVAILABLE=$(df . | awk 'NR==2 {print $4}')
        if [[ $AVAILABLE -lt 2097152 ]]; then  # 2GB in KB
            print_warning "Low disk space detected. Model download requires ~2GB"
        fi
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Create .env from template if it doesn't exist
    if [[ ! -f .env ]]; then
        if [[ -f .env.docker.llm ]]; then
            cp .env.docker.llm .env
            print_status "Created .env from template"
        else
            print_warning ".env file not found, using defaults"
        fi
    fi
    
    # Set build-specific environment variables
    export DOWNLOAD_MODEL_AT_BUILD=$DOWNLOAD_AT_BUILD
    export PREWARM_LOCAL_MODEL=$PREWARM_MODEL
    
    if [[ "$BUILD_TYPE" == "no-local" ]]; then
        export USE_LOCAL_MODEL=false
    else
        export USE_LOCAL_MODEL=true
    fi
    
    print_success "Environment configured for: $BUILD_TYPE"
}

# Function to build the application
build_application() {
    print_status "Building Interview Platform with LLM support..."
    print_status "Build type: $BUILD_TYPE"
    
    if [[ "$DOWNLOAD_AT_BUILD" == "true" ]]; then
        print_warning "Model will be downloaded during build (this may take 10-15 minutes)"
        print_status "Build will be slower but startup will be faster"
    else
        print_status "Model will be downloaded on first startup"
    fi
    
    # Build with docker-compose
    docker-compose -f docker-compose.llm.yml build --no-cache
    
    print_success "Build completed successfully"
}

# Function to start the application
start_application() {
    print_status "Starting Interview Platform..."
    
    # Start services
    docker-compose -f docker-compose.llm.yml up -d
    
    print_status "Services are starting up..."
    print_status "Backend: http://localhost:5000"
    print_status "Frontend: http://localhost:3000"
    
    if [[ "$BUILD_TYPE" != "no-local" && "$DOWNLOAD_AT_BUILD" == "false" ]]; then
        print_warning "Local model will download on first LLM request (may take 5-10 minutes)"
    fi
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    if docker-compose -f docker-compose.llm.yml ps | grep -q "Up (healthy)"; then
        print_success "🎉 Interview Platform is running!"
        print_success "   Frontend: http://localhost:3000"
        print_success "   Backend API: http://localhost:5000"
        print_success "   Health Check: http://localhost:5000/api/health"
    else
        print_warning "Services are starting... Check logs with: docker-compose -f docker-compose.llm.yml logs"
    fi
}

# Function to show system requirements
show_requirements() {
    echo ""
    print_status "💾 System Requirements:"
    echo "   • RAM: 4GB minimum, 8GB recommended"
    echo "   • Disk: 3GB free space (2GB for model + 1GB for containers)"
    echo "   • CPU: 2+ cores recommended"
    echo ""
    
    if [[ "$BUILD_TYPE" != "no-local" ]]; then
        print_status "🧠 LLM Configuration:"
        echo "   • Model: Llama 3.2 1B Instruct (~1GB)"
        echo "   • Device: CPU inference (GPU support available)"
        echo "   • Memory usage: ~2GB during inference"
        echo ""
    fi
    
    print_status "⚡ Performance Tips:"
    echo "   • Use --prewarm for faster first requests"
    echo "   • Use --build-download for faster startup"
    echo "   • Set GEMINI_API_KEY for production use"
    echo "   • Consider GPU setup for heavy usage"
}

# Main execution
main() {
    echo "🤖 Interview Platform with Local LLM"
    echo "===================================="
    echo ""
    
    show_requirements
    check_prerequisites
    setup_environment
    build_application
    start_application
    
    echo ""
    print_success "🚀 Setup complete! Your AI-powered interview platform is ready."
    echo ""
    print_status "Next steps:"
    echo "   1. Visit http://localhost:3000 to use the platform"
    echo "   2. Check logs: docker-compose -f docker-compose.llm.yml logs -f"
    echo "   3. Stop services: docker-compose -f docker-compose.llm.yml down"
    echo ""
    
    if [[ "$BUILD_TYPE" != "no-local" ]]; then
        print_status "🧠 LLM Features Available:"
        echo "   • Question generation with local AI"
        echo "   • Smart suggestions and improvements"
        echo "   • No API costs for local inference"
        echo "   • Works offline after model download"
    fi
}

# Run main function
main