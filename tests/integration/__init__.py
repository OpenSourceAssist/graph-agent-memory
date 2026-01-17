"""Integration tests for neo4j-agent-memory.

These tests require a running Neo4j instance. By default, they are skipped
unless the RUN_INTEGRATION_TESTS environment variable is set.

To run integration tests locally:

1. Start Neo4j using Docker:
   docker compose -f docker-compose.test.yml up -d

2. Run tests with the environment variable:
   RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration -v

3. Stop Neo4j when done:
   docker compose -f docker-compose.test.yml down -v
"""
