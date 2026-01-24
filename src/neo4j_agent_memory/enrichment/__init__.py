"""Entity enrichment from external knowledge sources.

Provides background enrichment of entities with data from:
- Wikimedia/Wikipedia: Summaries, descriptions, Wikidata IDs
- Diffbot: Structured knowledge graph data

Enrichment runs asynchronously and does not block entity extraction.

Example:
    from neo4j_agent_memory.enrichment import (
        WikimediaProvider,
        DiffbotProvider,
        create_enrichment_service,
    )

    # Using Wikimedia directly (free, no API key)
    provider = WikimediaProvider()
    result = await provider.enrich("Albert Einstein", "PERSON")
    print(result.description)
    print(result.wikipedia_url)

    # Using Diffbot (requires API key)
    provider = DiffbotProvider(api_key="your-key")
    result = await provider.enrich("Apple Inc", "ORGANIZATION")
    print(result.metadata.get("industries"))

    # Using factory with configuration
    from neo4j_agent_memory.config.settings import EnrichmentConfig

    config = EnrichmentConfig(enabled=True, providers=["wikimedia"])
    service = create_enrichment_service(config)
"""

from neo4j_agent_memory.enrichment.background import BackgroundEnrichmentService
from neo4j_agent_memory.enrichment.base import (
    EnrichmentProvider,
    EnrichmentResult,
    EnrichmentStatus,
    EnrichmentTask,
    NoOpEnrichmentProvider,
)
from neo4j_agent_memory.enrichment.factory import (
    CachedEnrichmentProvider,
    CompositeEnrichmentProvider,
    create_diffbot_provider,
    create_enrichment_provider,
    create_enrichment_service,
    create_wikimedia_provider,
)

__all__ = [
    # Base types
    "EnrichmentProvider",
    "EnrichmentResult",
    "EnrichmentStatus",
    "EnrichmentTask",
    "NoOpEnrichmentProvider",
    # Factory functions
    "create_enrichment_provider",
    "create_enrichment_service",
    "create_wikimedia_provider",
    "create_diffbot_provider",
    # Wrapper classes
    "CachedEnrichmentProvider",
    "CompositeEnrichmentProvider",
    # Background service
    "BackgroundEnrichmentService",
    # Providers (lazy loaded)
    "WikimediaProvider",
    "DiffbotProvider",
]


# Lazy imports for provider classes to avoid loading httpx unless needed
def __getattr__(name: str) -> type:
    if name == "WikimediaProvider":
        from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider

        return WikimediaProvider
    elif name == "DiffbotProvider":
        from neo4j_agent_memory.enrichment.diffbot import DiffbotProvider

        return DiffbotProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
