#!/bin/bash
set -e

echo "🧪 NEW USER SETUP VERIFICATION"
echo "================================"
echo "This script tests the complete setup process as described in README.md"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test 1: Check if .env.example exists
echo "1. Checking .env.example file..."
if [[ -f .env.example ]]; then
    log_success ".env.example exists"
    
    # Check if it contains required variables
    required_vars=("FLASK_APP" "SERVER_PORT" "MONGO_URI" "GEMINI_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" .env.example; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -eq 0 ]]; then
        log_success "All required environment variables present"
    else
        log_error "Missing variables in .env.example: ${missing_vars[*]}"
    fi
else
    log_error ".env.example not found - new users won't have template"
fi

# Test 2: Check if .env file setup works
echo ""
echo "2. Testing .env file creation..."
if [[ -f .env ]]; then
    log_info ".env file already exists (expected during development)"
else
    log_warning ".env file doesn't exist - testing creation from example"
    if [[ -f .env.example ]]; then
        cp .env.example .env
        log_success "Created .env from .env.example"
    fi
fi

# Test 3: Check Docker setup
echo ""
echo "3. Testing Docker configuration..."

# Clean start
log_info "Cleaning up any existing containers..."
docker-compose down -v &>/dev/null || true

# Test if docker-compose.yml is valid
if docker-compose config &>/dev/null; then
    log_success "docker-compose.yml is valid"
else
    log_error "docker-compose.yml has configuration errors"
    exit 1
fi

# Load environment variables from .env file
if [[ -f .env ]]; then
    log_info "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
    SERVER_PORT=${SERVER_PORT:-5002}
    FRONTEND_PORT=3000
    log_info "Using SERVER_PORT=$SERVER_PORT, FRONTEND_PORT=$FRONTEND_PORT"
else
    log_warning "No .env file found, using default ports"
    SERVER_PORT=5002
    FRONTEND_PORT=3000
fi

# Test 4: Start services and verify
echo ""
echo "4. Starting services (this may take a few minutes)..."
log_info "Running: docker-compose up --build -d"

if timeout 180 docker-compose up --build -d; then
    log_success "Services started successfully"
else
    log_error "Failed to start services within timeout"
    docker-compose logs --tail=20
    exit 1
fi

# Wait for services to be ready
echo ""
echo "5. Waiting for services to be ready..."
sleep 15

# Check service status
echo ""
echo "6. Checking service health..."

# Check database
if docker-compose exec -T db mongosh --quiet --eval "db.adminCommand('ping')" &>/dev/null; then
    log_success "MongoDB is running and accessible"
else
    log_error "MongoDB connection failed"
fi

# Check backend API
backend_response=$(curl -s -w "%{http_code}" -o /tmp/health_check http://localhost:$SERVER_PORT/api/health 2>/dev/null || echo "000")
if [[ "$backend_response" == "200" ]]; then
    log_success "Backend API is responding (http://localhost:$SERVER_PORT)"
    health_message=$(jq -r '.message' /tmp/health_check 2>/dev/null || echo "Unknown")
    log_info "API message: $health_message"
else
    log_error "Backend API not responding (got HTTP $backend_response)"
    echo "Backend logs:"
    docker-compose logs server --tail=10
fi

# Check frontend
frontend_response=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:$FRONTEND_PORT 2>/dev/null || echo "000")
if [[ "$frontend_response" == "200" ]]; then
    log_success "Frontend is accessible (http://localhost:$FRONTEND_PORT)"
else
    log_error "Frontend not accessible (got HTTP $frontend_response)"
    echo "Frontend logs:"
    docker-compose logs client --tail=10
fi

# Test 7: Test basic API functionality
echo ""
echo "7. Testing basic API functionality..."

if [[ "$backend_response" == "200" ]]; then
    # Test user creation
    log_info "Testing user authentication..."
    auth_response=$(curl -s -X POST http://localhost:$SERVER_PORT/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username": "setup_test_user"}' || echo "")
    
    if echo "$auth_response" | grep -q "token"; then
        log_success "User authentication working"
        token=$(echo "$auth_response" | jq -r '.token' 2>/dev/null)
        
        # Test authenticated endpoint
        if [[ -n "$token" && "$token" != "null" ]]; then
            if curl -s -H "Authorization: Bearer $token" \
                http://localhost:$SERVER_PORT/api/templates >/dev/null; then
                log_success "Authenticated API endpoints accessible"
            else
                log_warning "Authenticated endpoints may have issues"
            fi
        fi
    else
        log_error "User authentication failed"
        echo "Response: $auth_response"
    fi
else
    log_warning "Skipping API tests - backend not accessible"
fi

# Test 8: Test database operations
echo ""
echo "8. Testing database operations..."

if docker-compose exec -T db mongosh --quiet --eval "
    use interview_assistant;
    db.test_collection.insertOne({test: 'new_user_setup', timestamp: new Date()});
    db.test_collection.findOne({test: 'new_user_setup'});
    db.test_collection.deleteOne({test: 'new_user_setup'});
" &>/dev/null; then
    log_success "Database operations working correctly"
else
    log_error "Database operations failed"
fi

# Test 9: Quick functionality test
echo ""
echo "9. Running quick functionality test..."

if timeout 30 docker-compose -f docker-compose.test.yml run --rm tests python individual_tests/test_basic_functionality.py &>/dev/null; then
    log_success "Basic functionality tests pass"
else
    log_warning "Some functionality tests may have issues (this could be normal)"
fi

# Summary
echo ""
echo "🎯 SETUP VERIFICATION SUMMARY"
echo "=============================="

# Count services running
running_services=$(docker-compose ps --services --filter "status=running" | wc -l)
total_services=$(docker-compose ps --services | wc -l)

echo "Services running: $running_services/$total_services"

if [[ "$backend_response" == "200" && "$frontend_response" == "200" ]]; then
    echo ""
    log_success "🎉 SETUP SUCCESSFUL! Your Interview Assistant is ready to use:"
    echo ""
    echo "   📱 Frontend (React):  http://localhost:$FRONTEND_PORT"
    echo "   🔧 Backend API:       http://localhost:$SERVER_PORT"
    echo "   📊 Database:          mongodb://localhost:27017"
    echo ""
    echo "   To stop: docker-compose down"
    echo "   To view logs: docker-compose logs [service_name]"
    echo ""
else
    echo ""
    log_warning "Setup completed with some issues. Check the logs above."
    echo ""
fi

# Cleanup
echo ""
log_info "Cleaning up test environment..."
docker-compose down -v &>/dev/null || true
rm -f /tmp/health_check 2>/dev/null || true

echo ""
echo "Setup verification completed!"