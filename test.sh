#!/bin/bash
set -e

echo "🧪 Interview Assistant Test Runner"
echo "=================================="

# Default values
TEST_TYPE="fast"
DOCKER_COMPOSE_FILE="docker-compose.test.yml"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            TEST_TYPE="full"
            shift
            ;;
        --fast)
            TEST_TYPE="fast"
            shift
            ;;
        --basic)
            TEST_TYPE="basic"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--fast|--full|--basic] [--help]"
            echo ""
            echo "Options:"
            echo "  --fast    Run fast test suite (default)"
            echo "  --full    Run complete test suite (takes 10+ minutes)"
            echo "  --basic   Run only basic functionality tests"
            echo "  --help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run fast tests"
            echo "  $0 --full            # Run all tests"
            echo "  $0 --basic           # Run only basic tests"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose could not be found. Please install Docker Desktop."
    exit 1
fi

# Check if .env file exists
if [[ ! -f .env ]]; then
    echo "⚠️  No .env file found. Creating from example..."
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo "✅ Created .env file from example. Please edit it with your settings."
    else
        echo "❌ .env.example file not found. Please create a .env file manually."
        exit 1
    fi
fi

# Start test environment
echo "🚀 Starting test environment..."
docker-compose -f $DOCKER_COMPOSE_FILE up --build -d server db

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run tests based on type
echo "🧪 Running $TEST_TYPE tests..."
case $TEST_TYPE in
    "fast")
        docker-compose -f $DOCKER_COMPOSE_FILE run --rm tests python run_all_tests.py --fast --exclude scaling --exclude extreme
        ;;
    "full")
        docker-compose -f $DOCKER_COMPOSE_FILE run --rm tests python run_all_tests.py
        ;;
    "basic")
        docker-compose -f $DOCKER_COMPOSE_FILE run --rm tests python individual_tests/test_basic_functionality.py
        ;;
esac

TEST_EXIT_CODE=$?

# Cleanup
echo "🧹 Cleaning up test environment..."
docker-compose -f $DOCKER_COMPOSE_FILE down

# Report results
if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    echo "✅ All tests passed!"
    echo "🎉 Your Interview Assistant is working perfectly!"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
    echo "💡 Check the output above for details or run with --basic first"
    exit $TEST_EXIT_CODE
fi