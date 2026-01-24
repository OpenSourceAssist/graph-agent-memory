"""Memory client factory and lifecycle management."""

import logging

from neo4j_agent_memory import EmbeddingConfig, MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.config.settings import EnrichmentConfig, EnrichmentProvider
from src.config import get_settings

logger = logging.getLogger(__name__)

_memory_client: MemoryClient | None = None
_memory_connected: bool = False


async def init_memory_client() -> MemoryClient | None:
    """Initialize the memory client singleton.

    Returns the client if connected successfully, None otherwise.
    The app can still run without memory features if Neo4j is unavailable.
    """
    global _memory_client, _memory_connected

    if _memory_client is not None:
        return _memory_client

    settings = get_settings()

    # Debug: verify API key is loaded
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    logger.info(
        f"OpenAI API key loaded: {bool(api_key)} (length: {len(api_key) if api_key else 0})"
    )

    # Configure enrichment providers
    providers = [EnrichmentProvider.WIKIMEDIA]  # Free, no API key needed
    diffbot_key = settings.diffbot_api_key.get_secret_value() if settings.diffbot_api_key else None
    if diffbot_key:
        providers.insert(0, EnrichmentProvider.DIFFBOT)  # Diffbot first if available
        logger.info("Diffbot enrichment enabled")

    enrichment_config = EnrichmentConfig(
        enabled=settings.enrichment_enabled,
        providers=providers,
        diffbot_api_key=settings.diffbot_api_key,
        background_enabled=True,  # Async processing
        cache_results=True,  # Cache to avoid repeated API calls
        entity_types=["PERSON", "ORGANIZATION", "LOCATION", "EVENT"],
        min_confidence=0.7,
    )

    if settings.enrichment_enabled:
        logger.info(f"Entity enrichment enabled with providers: {[p.value for p in providers]}")

    memory_settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
        ),
        embedding=EmbeddingConfig(
            api_key=settings.openai_api_key,
        ),
        enrichment=enrichment_config,
    )

    _memory_client = MemoryClient(memory_settings)

    try:
        await _memory_client.connect()
        _memory_connected = True
        logger.info("Successfully connected to Neo4j memory graph")
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


def is_memory_connected() -> bool:
    """Check if memory client is connected."""
    return _memory_connected


async def close_memory_client() -> None:
    """Close the memory client connection."""
    global _memory_client, _memory_connected

    if _memory_client is not None and _memory_connected:
        await _memory_client.close()
    _memory_client = None
    _memory_connected = False
