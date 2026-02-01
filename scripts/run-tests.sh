#!/bin/bash
# Test runner script for BookingOpt

set -e

echo "=================================================="
echo "BookingOpt Test Runner"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Parse arguments
RUN_INTEGRATION=false
RUN_LINT=false
RUN_TYPE_CHECK=false
RUN_UNIT=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --lint)
            RUN_LINT=true
            shift
            ;;
        --type-check)
            RUN_TYPE_CHECK=true
            shift
            ;;
        --all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_LINT=true
            RUN_TYPE_CHECK=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--unit] [--integration] [--lint] [--type-check] [--all]"
            exit 1
            ;;
    esac
done

# Check if running in project root
if [ ! -f "pytest.ini" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Install dependencies
print_step "Installing test dependencies..."
pip install -q -r app/tests/requirements.txt

# Linting
if [ "$RUN_LINT" = true ]; then
    print_step "Running linting checks..."

    echo "  → Running ruff..."
    ruff check app/ || print_warn "Ruff found issues"

    echo "  → Running black (format check)..."
    black --check app/ || print_warn "Black found formatting issues"
fi

# Type checking
if [ "$RUN_TYPE_CHECK" = true ]; then
    print_step "Running type checks..."
    mypy app/api app/worker || print_warn "MyPy found type issues"
fi

# Unit tests
if [ "$RUN_UNIT" = true ]; then
    print_step "Running unit tests..."
    pytest app/tests/test_api.py -v --tb=short
fi

# Integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    print_step "Running integration tests..."

    # Check if Docker Compose services are running
    if ! curl -s http://localhost/health > /dev/null 2>&1; then
        print_warn "Docker Compose services not running. Starting them..."

        cd hotel-optimizer-infra
        docker compose up -d

        # Wait for services to be ready
        echo "  → Waiting for services to start..."
        sleep 30

        # Check health
        for i in {1..10}; do
            if curl -s http://localhost/health > /dev/null 2>&1; then
                echo "  → Services are healthy!"
                break
            fi
            echo "  → Waiting... ($i/10)"
            sleep 5
        done

        cd ..
    fi

    # Run integration tests
    pytest app/tests/test_integration.py -v -m integration --tb=short
fi

echo ""
print_step "✅ Tests completed!"
