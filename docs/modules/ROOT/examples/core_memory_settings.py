"""Shared settings for the three local Bolt memory tutorials."""

from neo4j_agent_memory import MemorySettings


def settings():
    return MemorySettings(
        backend="bolt",
        neo4j={"uri": "bolt://localhost:7687", "password": "docs-local-password"},
        embedding="openai/text-embedding-3-small",
        llm=None,
        extraction={"extractor_type": "none"},
        resolution={"strategy": "none"},
        geocoding={"enabled": False},
        enrichment={"enabled": False},
    )
