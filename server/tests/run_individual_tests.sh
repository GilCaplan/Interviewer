#!/bin/bash

# Run all individual test files in the individual_tests directory
# Usage: ./run_individual_tests.sh [options]
# Options:
#   --fast: Run with shorter timeouts
#   --parallel: Run tests in parallel (experimental)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDIVIDUAL_TESTS_DIR="$SCRIPT_DIR/individual_tests"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"

# Use project virtual environment if available
if [ -f "$VENV_PATH/bin/python" ]; then
    PYTHON_CMD="$VENV_PATH/bin/python"
    echo "🐍 Using project virtual environment: $VENV_PATH"
elif [ -f "$VENV_PATH/Scripts/python.exe" ]; then
    # Windows support
    PYTHON_CMD="$VENV_PATH/Scripts/python.exe"
    echo "🐍 Using project virtual environment: $VENV_PATH (Windows)"
else
    PYTHON_CMD="python"
    echo "⚠️ Warning: No virtual environment found, using system Python"
fi

# Default settings
TIMEOUT=60
PARALLEL=false
FAST_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            FAST_MODE=true
            TIMEOUT=15
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --fast      Run with shorter timeouts (15s instead of 60s)"
            echo "  --parallel  Run tests in parallel (experimental)"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set environment variables for testing
export TESTING=true
export TEST_MODE=1
export FLASK_ENV=testing

echo "🧪 Running All Individual Tests"
echo "==============================="
echo "Directory: $INDIVIDUAL_TESTS_DIR"
echo "Timeout: ${TIMEOUT}s"
echo "Parallel: $PARALLEL"
echo "Fast Mode: $FAST_MODE"
echo ""

# Find all Python test files - handle paths with spaces properly
TEST_FILES=()
# Use temporary file approach for better compatibility
temp_file=$(mktemp)
find "$INDIVIDUAL_TESTS_DIR" -name "test_*.py" -type f | sort > "$temp_file"

while IFS= read -r file; do
    if [ -n "$file" ]; then
        TEST_FILES+=("$file")
    fi
done < "$temp_file"

rm -f "$temp_file"

if [ ${#TEST_FILES[@]} -eq 0 ]; then
    echo "❌ No test files found in $INDIVIDUAL_TESTS_DIR"
    exit 1
fi

echo "Found ${#TEST_FILES[@]} test files:"
for file in "${TEST_FILES[@]}"; do
    echo "  - $(basename "$file")"
done
echo ""

# Function to run a single test
run_test() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .py)
    
    echo "🔍 Running $test_name..."
    
    if timeout "$TIMEOUT" "$PYTHON_CMD" "$test_file" 2>&1; then
        echo "✅ $test_name: PASSED"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "⏱️ $test_name: TIMEOUT (${TIMEOUT}s)"
        else
            echo "❌ $test_name: FAILED"
        fi
        return 1
    fi
}

# Change to the project root directory
cd "/Users/USER/Desktop/University/Semester 6/FullStack/Project_Interviewer"

PASSED=0
FAILED=0
TIMED_OUT=0

if [ "$PARALLEL" = true ]; then
    echo "⚡ Running tests in parallel..."
    
    # Run tests in parallel using background processes
    declare -a PIDS=()
    declare -a TEST_NAMES=()
    
    for test_file in "${TEST_FILES[@]}"; do
        test_name=$(basename "$test_file" .py)
        TEST_NAMES+=("$test_name")
        
        (
            if timeout "$TIMEOUT" "$PYTHON_CMD" "$test_file" >/dev/null 2>&1; then
                echo "✅ $test_name: PASSED"
                exit 0
            else
                exit_code=$?
                if [ $exit_code -eq 124 ]; then
                    echo "⏱️ $test_name: TIMEOUT (${TIMEOUT}s)"
                    exit 124
                else
                    echo "❌ $test_name: FAILED"
                    exit 1
                fi
            fi
        ) &
        
        PIDS+=($!)
    done
    
    # Wait for all background processes
    for i in "${!PIDS[@]}"; do
        wait ${PIDS[$i]}
        exit_code=$?
        
        case $exit_code in
            0)
                ((PASSED++))
                ;;
            124)
                ((TIMED_OUT++))
                ;;
            *)
                ((FAILED++))
                ;;
        esac
    done
    
else
    echo "🔄 Running tests sequentially..."
    
    for test_file in "${TEST_FILES[@]}"; do
        if run_test "$test_file"; then
            ((PASSED++))
        else
            exit_code=$?
            if [ $exit_code -eq 124 ]; then
                ((TIMED_OUT++))
            else
                ((FAILED++))
            fi
        fi
        echo ""
    done
fi

echo ""
echo "📊 RESULTS SUMMARY"
echo "=================="
echo "Total tests: ${#TEST_FILES[@]}"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo "⏱️ Timed out: $TIMED_OUT"

if [ $FAILED -eq 0 ] && [ $TIMED_OUT -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed!"
    exit 0
else
    echo ""
    echo "💥 Some tests failed or timed out"
    exit 1
fi