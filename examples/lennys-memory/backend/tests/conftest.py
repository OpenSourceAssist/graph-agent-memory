"""Shared test fixtures for Lenny's Memory backend tests."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def neo4j_available() -> bool:
    """Check if Neo4j environment variables are configured."""
    return all(
        [
            os.environ.get("NEO4J_URI"),
            os.environ.get("NEO4J_USERNAME"),
            os.environ.get("NEO4J_PASSWORD"),
        ]
    )


@pytest.fixture
def mock_message():
    """Create a mock message with podcast metadata."""

    def _create_message(
        content: str = "Test content",
        speaker: str = "Test Speaker",
        episode_guest: str = "Test Guest",
        timestamp: str = "00:00:00",
        similarity: float = 0.85,
        source: str = "lenny_podcast",
    ):
        msg = MagicMock()
        msg.content = content
        msg.metadata = {
            "speaker": speaker,
            "episode_guest": episode_guest,
            "timestamp": timestamp,
            "source": source,
            "similarity": similarity,
        }
        return msg

    return _create_message


@pytest.fixture
def mock_memory_client():
    """Create a mock memory client for unit tests."""
    client = MagicMock()
    client.short_term.search_messages = AsyncMock(return_value=[])
    client.short_term.add_message = AsyncMock()
    client.short_term.get_conversation = AsyncMock(return_value=None)
    client.long_term.search_entities = AsyncMock(return_value=[])
    client.long_term.get_entity_by_name = AsyncMock(return_value=None)
    client._client.execute_read = AsyncMock(return_value=[])
    client._client.execute_write = AsyncMock(return_value=[])
    client.get_stats = AsyncMock(return_value={"conversations": 0, "messages": 0, "entities": 0})
    client.get_locations = AsyncMock(return_value=[])
    client.reasoning.get_similar_traces = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_agent_context(mock_memory_client):
    """Create a mock agent RunContext."""
    ctx = MagicMock()
    ctx.deps.client = mock_memory_client
    return ctx


class MockEmbedder:
    """Mock embedder that generates deterministic embeddings for testing."""

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate a deterministic embedding based on text hash."""
        import hashlib

        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Create a reproducible embedding from the hash
        embedding = []
        for i in range(self.dimensions):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] - 128) / 128.0)
        return embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return [await self.embed(text) for text in texts]


@pytest_asyncio.fixture
async def memory_client():
    """Create a real memory client for integration tests.

    Requires NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD environment variables
    and a running Neo4j instance.
    """
    if not neo4j_available():
        pytest.skip("Neo4j not available - set NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD")

    from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
    from neo4j_agent_memory.core.exceptions import ConnectionError

    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.environ["NEO4J_URI"],
            username=os.environ["NEO4J_USERNAME"],
            password=os.environ["NEO4J_PASSWORD"],
        ),
    )

    client = MemoryClient(settings, embedder=MockEmbedder())
    try:
        await client.__aenter__()
    except ConnectionError:
        pytest.skip("Neo4j not reachable - is the database running?")

    yield client

    # Cleanup test data - delete test-specific nodes only
    await client._client.execute_write(
        """
        MATCH (c:Conversation)
        WHERE c.session_id STARTS WITH 'test-'
        OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
        DETACH DELETE c, m
        """
    )
    await client.__aexit__(None, None, None)
