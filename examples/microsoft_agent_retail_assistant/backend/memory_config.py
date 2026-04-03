"""Memory configuration for the retail assistant."""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.config.settings import ExtractionConfig
from neo4j_agent_memory.integrations.microsoft_agent import (
    GDSAlgorithm,
    GDSConfig,
    Neo4jContextProvider,
    Neo4jMicrosoftMemory,
)
from neo4j_agent_memory.memory.long_term import DeduplicationConfig

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Neo4j connection
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")

    # OpenAI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Azure OpenAI (alternative)
    azure_openai_api_key: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_deduplication_config() -> DeduplicationConfig:
    """Create DeduplicationConfig for product entity deduplication.

    This ensures that product entities with similar names (e.g.,
    "Nike Air Max" vs "Nike Air Max 90") are properly deduplicated
    in the knowledge graph.
    """
    return DeduplicationConfig(
        enabled=True,
        auto_merge_threshold=0.95,
        flag_threshold=0.85,
        use_fuzzy_matching=True,
        fuzzy_threshold=0.9,
        max_candidates=10,
        match_same_type_only=True,
    )


def get_extraction_config() -> ExtractionConfig:
    """Create ExtractionConfig for retail entity extraction.

    Configures the extraction pipeline to identify product names,
    brands, categories, and other retail-relevant entities from
    customer conversations.
    """
    return ExtractionConfig(
        enable_spacy=True,
        enable_gliner=True,
        enable_llm_fallback=False,
    )


def get_memory_settings() -> MemorySettings:
    """Create MemorySettings from environment."""
    return MemorySettings(
        neo4j={
            "uri": settings.neo4j_uri,
            "user": settings.neo4j_user,
            "password": SecretStr(settings.neo4j_password),
        },
        embedding={
            "provider": "openai",
            "model": "text-embedding-3-small",
            "api_key": SecretStr(settings.openai_api_key) if settings.openai_api_key else None,
        },
        extraction=get_extraction_config(),
    )


def get_gds_config() -> GDSConfig:
    """Create GDS configuration for retail recommendations."""
    return GDSConfig(
        enabled=True,
        use_pagerank_for_ranking=True,
        pagerank_weight=0.3,
        use_community_grouping=True,
        expose_as_tools=[
            GDSAlgorithm.SHORTEST_PATH,
            GDSAlgorithm.NODE_SIMILARITY,
            GDSAlgorithm.PAGERANK,
        ],
        fallback_to_basic=True,
        warn_on_fallback=True,
    )


async def create_memory(session_id: str, user_id: str | None = None) -> Neo4jMicrosoftMemory:
    """
    Create a memory instance for a session.

    Args:
        session_id: Session identifier.
        user_id: Optional user identifier.

    Returns:
        Configured Neo4jMicrosoftMemory instance.
    """
    memory_settings = get_memory_settings()
    gds_config = get_gds_config()

    # Create memory client (in real app, manage connection lifecycle)
    client = MemoryClient(memory_settings)
    await client.connect()

    return Neo4jMicrosoftMemory(
        memory_client=client,
        session_id=session_id,
        user_id=user_id,
        include_short_term=True,
        include_long_term=True,
        include_reasoning=True,
        max_context_items=15,
        max_recent_messages=10,
        extract_entities=True,
        extract_entities_async=True,
        gds_config=gds_config,
    )


# Context provider factory for agent
def create_context_provider(
    memory_client: MemoryClient,
    session_id: str,
    user_id: str | None = None,
) -> Neo4jContextProvider:
    """
    Create a context provider for the agent.

    Args:
        memory_client: Connected MemoryClient.
        session_id: Session identifier.
        user_id: Optional user identifier.

    Returns:
        Configured Neo4jContextProvider.
    """
    return Neo4jContextProvider(
        memory_client=memory_client,
        session_id=session_id,
        user_id=user_id,
        include_short_term=True,
        include_long_term=True,
        include_reasoning=True,
        max_context_items=15,
        max_recent_messages=10,
        extract_entities=True,
        extract_entities_async=True,
        gds_config=get_gds_config(),
    )
