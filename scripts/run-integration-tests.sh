#!/bin/bash
# Script to run integration tests with Neo4j Docker container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Neo4j Agent Memory Integration Tests ==="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo "Error: docker compose is not available"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping Neo4j container..."
    docker compose -f docker-compose.test.yml down -v 2>/dev/null || true
}

# Parse arguments
KEEP_RUNNING=false
VERBOSE=false
TEST_PATTERN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep|-k)
            KEEP_RUNNING=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --pattern|-p)
            TEST_PATTERN="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --keep, -k      Keep Neo4j container running after tests"
            echo "  --verbose, -v   Run tests with verbose output"
            echo "  --pattern, -p   Only run tests matching pattern"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set up cleanup trap (unless --keep is specified)
if [ "$KEEP_RUNNING" = false ]; then
    trap cleanup EXIT
fi

# Start Neo4j
echo "Starting Neo4j container..."
docker compose -f docker-compose.test.yml up -d

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        # Try a Cypher query to ensure it's fully ready
        if docker exec neo4j-agent-memory-test cypher-shell -u neo4j -p test-password "RETURN 1" > /dev/null 2>&1; then
            echo "Neo4j is ready!"
            break
        fi
    fi
    echo "  Waiting... (attempt $i/60)"
    sleep 2
done

# Check if Neo4j is actually ready
if ! curl -s http://localhost:7474 > /dev/null 2>&1; then
    echo "Error: Neo4j failed to start within timeout"
    exit 1
fi

echo ""
echo "Running integration tests..."
echo ""

# Build pytest command
PYTEST_CMD="uv run pytest tests/integration"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ -n "$TEST_PATTERN" ]; then
    PYTEST_CMD="$PYTEST_CMD -k '$TEST_PATTERN'"
fi

PYTEST_CMD="$PYTEST_CMD --tb=short"

# Run tests
export RUN_INTEGRATION_TESTS=1
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=test-password

eval $PYTEST_CMD

echo ""
echo "=== Integration tests completed ==="

if [ "$KEEP_RUNNING" = true ]; then
    echo ""
    echo "Neo4j container is still running."
    echo "To stop it: docker compose -f docker-compose.test.yml down -v"
fi
