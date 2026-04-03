"""Memory client factory and lifecycle management."""

import logging

from neo4j_agent_memory import (
    ExtractionConfig,
    MemoryClient,
    MemoryIntegration,
    MemorySettings,
    Neo4jConfig,
    SessionStrategy,
)
from neo4j_agent_memory.memory.long_term import DeduplicationConfig
from src.config import get_settings

logger = logging.getLogger(__name__)

_memory_client: MemoryClient | None = None
_memory_integration: MemoryIntegration | None = None
_memory_connected: bool = False


async def init_memory_client() -> MemoryClient | None:
    """Initialize the memory client singleton.

    Returns the client if connected successfully, None otherwise.
    The app can still run without memory features if Neo4j is unavailable.
    """
    global _memory_client, _memory_integration, _memory_connected

    if _memory_client is not None:
        return _memory_client

    settings = get_settings()

    memory_settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
        ),
        extraction=ExtractionConfig(
            enable_gliner=False,
            enable_spacy=False,
            enable_llm_fallback=False,
        ),
    )

    _memory_client = MemoryClient(memory_settings)

    try:
        await _memory_client.connect()
        _memory_connected = True
        logger.info("Successfully connected to Neo4j memory graph")

        # Initialize MemoryIntegration for high-level operations
        _memory_integration = MemoryIntegration(
            neo4j_uri=settings.neo4j_uri,
            neo4j_password=settings.neo4j_password.get_secret_value(),
            session_strategy=SessionStrategy.PER_CONVERSATION,
            auto_extract=True,
            auto_preferences=True,
        )
        await _memory_integration.connect()
        logger.info("MemoryIntegration initialized with auto-preferences enabled")

    except Exception as e:
        logger.warning(f"Failed to connect to Neo4j memory graph: {e}")
        logger.warning("Memory features will be disabled. Check your Neo4j configuration.")
        _memory_connected = False

    return _memory_client


def get_memory_client() -> MemoryClient | None:
    """Get the memory client singleton.

    Returns:
        The memory client if initialized and connected, None otherwise.
    """
    if not _memory_connected:
        return None
    return _memory_client


def get_memory_integration() -> MemoryIntegration | None:
    """Get the MemoryIntegration singleton for high-level operations.

    Returns:
        The MemoryIntegration if initialized and connected, None otherwise.
    """
    if not _memory_connected:
        return None
    return _memory_integration


def is_memory_connected() -> bool:
    """Check if memory client is connected."""
    return _memory_connected


async def close_memory_client() -> None:
    """Close the memory client connection."""
    global _memory_client, _memory_integration, _memory_connected

    if _memory_integration is not None:
        await _memory_integration.close()
    if _memory_client is not None and _memory_connected:
        await _memory_client.close()
    _memory_client = None
    _memory_integration = None
    _memory_connected = False
