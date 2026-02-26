"""Google Agent Development Kit (ADK) integration for neo4j-agent-memory.

Provides Neo4j-backed memory services for Google ADK agents.

Example:
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

    settings = MemorySettings(...)
    async with MemoryClient(settings) as client:
        memory_service = Neo4jMemoryService(client)
        # Use with Google ADK agent
"""

__all__ = [
    "Neo4jMemoryService",
]


def __getattr__(name: str):
    if name == "Neo4jMemoryService":
        from neo4j_agent_memory.integrations.google_adk.memory_service import (
            Neo4jMemoryService,
        )

        return Neo4jMemoryService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
