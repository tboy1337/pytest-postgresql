#!/usr/bin/env bash
#
# Run pytest-postgresql tests in Docker container with PostgreSQL binaries.
#
# This script builds and runs the Docker test environment that includes
# PostgreSQL 17 binaries (pg_ctl, initdb, postgres) to run all tests
# including those that require pg_ctl, regardless of the host OS.
#
# Usage:
#   ./run-docker-tests.sh                    # Run all tests with coverage
#   ./run-docker-tests.sh tests/test_executor.py  # Run specific test file
#   ./run-docker-tests.sh --build-only       # Only build the Docker image
#   ./run-docker-tests.sh --no-build         # Skip building, use existing image
#   ./run-docker-tests.sh --no-coverage      # Run without coverage
#   ./run-docker-tests.sh --quiet            # Less verbose output

set -e

# Default options
COVERAGE=true
VERBOSE=true
TEST_PATH="tests/"
BUILD_ONLY=false
NO_BUILD=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --quiet)
            VERBOSE=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [TEST_PATH]"
            echo ""
            echo "Options:"
            echo "  --build-only     Only build the Docker image"
            echo "  --no-build       Skip building, use existing image"
            echo "  --no-coverage    Run without coverage reporting"
            echo "  --quiet          Less verbose output"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                              # Run all tests"
            echo "  $0 tests/test_executor.py       # Run specific file"
            echo "  $0 --build-only                 # Build only"
            exit 0
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "${CYAN}=====================================${NC}"
echo -e "${CYAN}pytest-postgresql Docker Test Runner${NC}"
echo -e "${CYAN}=====================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed or not in PATH${NC}"
    echo -e "${CYAN}Please install Docker from https://www.docker.com/get-started${NC}"
    exit 1
fi

DOCKER_VERSION=$(docker --version)
echo -e "${GREEN}Docker found: $DOCKER_VERSION${NC}"

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo -e "${RED}ERROR: Docker daemon is not running${NC}"
    echo -e "${CYAN}Please start Docker${NC}"
    exit 1
fi

echo -e "${GREEN}Docker daemon is running${NC}"
echo ""

# Build Docker image if needed
if [ "$NO_BUILD" = false ]; then
    echo -e "${CYAN}Building Docker test image...${NC}"
    docker-compose -f docker-compose.tests.yml build test-runner
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Docker build failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Docker image built successfully${NC}"
    echo ""
fi

if [ "$BUILD_ONLY" = true ]; then
    echo -e "${GREEN}Build complete. Use --no-build flag to skip building next time.${NC}"
    exit 0
fi

# Prepare pytest command
PYTEST_CMD="pytest $TEST_PATH"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=pytest_postgresql --cov-report=term --cov-report=html --cov-report=json --cov-branch"
fi

PYTEST_CMD="$PYTEST_CMD --tb=short"

echo -e "${CYAN}Running tests in Docker container...${NC}"
echo -e "${GRAY}Command: $PYTEST_CMD${NC}"
echo ""

# Run tests
docker-compose -f docker-compose.tests.yml run --rm test-runner bash -c "$PYTEST_CMD"

EXIT_CODE=$?

echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${GREEN}=====================================${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${CYAN}Coverage reports generated:${NC}"
        echo -e "${GRAY}  - Terminal output (see above)${NC}"
        echo -e "${GRAY}  - HTML: htmlcov/index.html${NC}"
        echo -e "${GRAY}  - JSON: coverage.json${NC}"
        
        if [ -f "check_coverage.py" ]; then
            echo ""
            echo -e "${CYAN}Running coverage analysis...${NC}"
            python check_coverage.py
        fi
    fi
else
    echo -e "${RED}=====================================${NC}"
    echo -e "${RED}Tests failed with exit code: $EXIT_CODE${NC}"
    echo -e "${RED}=====================================${NC}"
fi

echo ""
echo -e "${CYAN}Cleaning up...${NC}"
docker-compose -f docker-compose.tests.yml down

exit $EXIT_CODE
