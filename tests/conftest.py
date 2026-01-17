"""Pytest fixtures for neo4j-agent-memory tests."""

import asyncio
import hashlib
import os
import subprocess
import time
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from pydantic import SecretStr

from neo4j_agent_memory import MemorySettings, Neo4jConfig
from neo4j_agent_memory.embeddings.base import BaseEmbedder
from neo4j_agent_memory.extraction.base import (
    EntityExtractor,
    ExtractedEntity,
    ExtractedPreference,
    ExtractedRelation,
    ExtractionResult,
)
from neo4j_agent_memory.resolution.base import EntityResolver, ResolvedEntity

# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test requiring Neo4j")
    config.addinivalue_line("markers", "docker: mark test as requiring Docker")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Auto-skip integration tests if Neo4j is not available."""
    # Check if we should run integration tests
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes")

    if not run_integration:
        skip_integration = pytest.mark.skip(reason="Set RUN_INTEGRATION_TESTS=1 to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Mock Components for Unit Tests
# =============================================================================


class MockEmbedder(BaseEmbedder):
    """Mock embedder for unit tests that generates deterministic embeddings."""

    def __init__(self, dimensions: int = 1536):
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic fake embedding based on text hash."""
        h = hashlib.sha256(text.encode()).hexdigest()
        # Create reproducible embedding from hash
        embedding = []
        for i in range(0, min(len(h), self._dimensions * 2), 2):
            if len(embedding) >= self._dimensions:
                break
            embedding.append(float(int(h[i : i + 2], 16)) / 255.0)
        # Pad if needed
        while len(embedding) < self._dimensions:
            embedding.append(0.0)
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(t) for t in texts]


class MockExtractor(EntityExtractor):
    """Mock entity extractor for unit tests with simple rule-based extraction."""

    async def extract(
        self,
        text: str,
        *,
        entity_types: list[str] | None = None,
        extract_relations: bool = True,
        extract_preferences: bool = True,
    ) -> ExtractionResult:
        """Simple rule-based extraction for testing."""
        entities = []
        relations = []
        preferences = []

        # Simple name detection
        words = text.split()
        for i, word in enumerate(words):
            # Detect potential names (capitalized words)
            if word and word[0].isupper() and len(word) > 1:
                # Skip common words
                if word.lower() not in [
                    "i",
                    "the",
                    "a",
                    "an",
                    "is",
                    "are",
                    "was",
                    "were",
                    "hi",
                    "hello",
                ]:
                    entities.append(
                        ExtractedEntity(
                            name=word,
                            type="PERSON"
                            if word not in ["Acme", "Google", "Apple"]
                            else "ORGANIZATION",
                            confidence=0.8,
                        )
                    )

        # Detect preferences
        if extract_preferences:
            preference_patterns = [
                ("love", "like"),
                ("prefer", "preference"),
                ("enjoy", "like"),
                ("hate", "dislike"),
                ("favorite", "like"),
            ]
            text_lower = text.lower()
            for pattern, category in preference_patterns:
                if pattern in text_lower:
                    # Find the thing being preferred
                    idx = text_lower.find(pattern)
                    after = text[idx:].split(maxsplit=2)
                    if len(after) > 1:
                        preferences.append(
                            ExtractedPreference(
                                category=category,
                                preference=text,
                                confidence=0.7,
                            )
                        )
                    break

        return ExtractionResult(
            entities=entities,
            relations=relations,
            preferences=preferences,
            source_text=text,
        )


class MockResolver(EntityResolver):
    """Mock entity resolver for unit tests."""

    async def resolve(
        self,
        entity_name: str,
        entity_type: str,
        *,
        existing_entities: list[str] | None = None,
    ) -> ResolvedEntity:
        """Simple exact match resolution."""
        normalized = entity_name.lower().strip()

        if existing_entities:
            for existing in existing_entities:
                if existing.lower().strip() == normalized:
                    return ResolvedEntity(
                        original_name=entity_name,
                        canonical_name=existing,
                        entity_type=entity_type,
                        confidence=1.0,
                        match_type="exact",
                    )

        return ResolvedEntity(
            original_name=entity_name,
            canonical_name=entity_name,
            entity_type=entity_type,
            confidence=1.0,
            match_type="none",
        )

    async def resolve_batch(
        self,
        entities: list[tuple[str, str]],
    ) -> list[ResolvedEntity]:
        """Resolve multiple entities."""
        return [await self.resolve(name, etype) for name, etype in entities]

    async def find_matches(
        self,
        entity_name: str,
        entity_type: str,
        candidates: list[str],
    ) -> list:
        """Find matches from candidates."""
        return []


@pytest.fixture
def mock_embedder():
    """Provide a mock embedder for unit tests."""
    return MockEmbedder()


@pytest.fixture
def mock_extractor():
    """Provide a mock entity extractor for unit tests."""
    return MockExtractor()


@pytest.fixture
def mock_resolver():
    """Provide a mock entity resolver for unit tests."""
    return MockResolver()


# =============================================================================
# Neo4j Docker Management
# =============================================================================


def is_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_neo4j_container_running() -> bool:
    """Check if the Neo4j test container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=neo4j-agent-memory-test", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "neo4j-agent-memory-test" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_neo4j_container() -> bool:
    """Start the Neo4j test container using docker-compose."""
    try:
        # Get the directory containing docker-compose.test.yml
        compose_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "docker-compose.test.yml"
        )

        if not os.path.exists(compose_file):
            return False

        result = subprocess.run(
            ["docker", "compose", "-f", compose_file, "up", "-d", "--wait"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def stop_neo4j_container():
    """Stop the Neo4j test container."""
    try:
        compose_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "docker-compose.test.yml"
        )

        if os.path.exists(compose_file):
            subprocess.run(
                ["docker", "compose", "-f", compose_file, "down", "-v"],
                capture_output=True,
                timeout=60,
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def wait_for_neo4j(uri: str, username: str, password: str, timeout: int = 60) -> bool:
    """Wait for Neo4j to be ready to accept connections."""
    from neo4j import GraphDatabase
    from neo4j.exceptions import AuthError, ServiceUnavailable

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            driver.verify_connectivity()
            driver.close()
            return True
        except (ServiceUnavailable, AuthError, Exception):
            time.sleep(1)
    return False


# =============================================================================
# Integration Test Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def neo4j_connection_info():
    """Get Neo4j connection info, starting container if needed."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "test-password")

    return {
        "uri": uri,
        "username": username,
        "password": password,
    }


@pytest.fixture(scope="session")
def ensure_neo4j_running(neo4j_connection_info):
    """
    Ensure Neo4j is running for integration tests.

    This fixture will:
    1. Check if Neo4j is already available
    2. If not, try to start the Docker container
    3. Wait for Neo4j to be ready
    """
    uri = neo4j_connection_info["uri"]
    username = neo4j_connection_info["username"]
    password = neo4j_connection_info["password"]

    # First, check if Neo4j is already available
    if wait_for_neo4j(uri, username, password, timeout=5):
        yield neo4j_connection_info
        return

    # Try to start Docker container
    if is_docker_available():
        if not is_neo4j_container_running():
            if not start_neo4j_container():
                pytest.skip("Could not start Neo4j Docker container")

        # Wait for Neo4j to be ready
        if not wait_for_neo4j(uri, username, password, timeout=60):
            pytest.skip("Neo4j not ready after timeout")
    else:
        pytest.skip("Docker not available and Neo4j not running")

    yield neo4j_connection_info


@pytest.fixture
def memory_settings(ensure_neo4j_running):
    """Test settings with default configuration."""
    return MemorySettings(
        neo4j=Neo4jConfig(
            uri=ensure_neo4j_running["uri"],
            username=ensure_neo4j_running["username"],
            password=SecretStr(ensure_neo4j_running["password"]),
        )
    )


@pytest.fixture
def session_id():
    """Generate unique session ID for test isolation."""
    return f"test-{uuid4()}"


@pytest.fixture
async def neo4j_client(memory_settings) -> AsyncGenerator:
    """
    Real Neo4j client for integration tests.

    Requires Neo4j to be running.
    """
    from neo4j_agent_memory.graph.client import Neo4jClient
    from neo4j_agent_memory.graph.schema import SchemaManager

    client = Neo4jClient(memory_settings.neo4j)

    try:
        await client.connect()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")

    # Set up schema
    schema_manager = SchemaManager(client)
    await schema_manager.setup_all()

    yield client

    # Cleanup test data
    try:
        await client.execute_write("MATCH (n) WHERE n.id STARTS WITH 'test-' DETACH DELETE n")
    except Exception:
        pass

    await client.close()


@pytest.fixture
async def memory_client(
    memory_settings, mock_embedder, mock_extractor, mock_resolver
) -> AsyncGenerator:
    """
    Full MemoryClient for integration tests with mock components.

    Uses mock embedder/extractor/resolver to avoid external API calls.
    Requires Neo4j to be running.
    """
    from neo4j_agent_memory import MemoryClient

    client = MemoryClient(
        memory_settings,
        embedder=mock_embedder,
        extractor=mock_extractor,
        resolver=mock_resolver,
    )

    try:
        await client.connect()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")

    yield client

    # Cleanup test data - delete all test entities
    try:
        await client._client.execute_write("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    await client.close()


@pytest.fixture
async def clean_memory_client(
    memory_settings, mock_embedder, mock_extractor, mock_resolver
) -> AsyncGenerator:
    """
    MemoryClient with clean database state for isolation.

    Cleans up ALL test data before and after each test.
    """
    from neo4j_agent_memory import MemoryClient

    client = MemoryClient(
        memory_settings,
        embedder=mock_embedder,
        extractor=mock_extractor,
        resolver=mock_resolver,
    )

    try:
        await client.connect()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")

    # Clean before test - delete all nodes
    try:
        await client._client.execute_write("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    yield client

    # Clean after test - delete all nodes
    try:
        await client._client.execute_write("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    await client.close()
