"""AWS Bedrock AgentCore integration for neo4j-agent-memory.

This module provides a MemoryProvider implementation for AWS Bedrock AgentCore
that uses Neo4j Context Graphs as the backing store.

Example:
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

    async with MemoryClient(settings) as client:
        provider = Neo4jMemoryProvider(
            memory_client=client,
            namespace="my-app",
        )

        # Store memories
        await provider.store_memory(
            session_id="session-123",
            content="User prefers dark mode",
        )

        # Search memories
        results = await provider.search_memory(
            query="preferences",
            session_id="session-123",
        )
"""

from neo4j_agent_memory.integrations.agentcore.hybrid import (
    HybridMemoryProvider,
    RoutingStrategy,
)
from neo4j_agent_memory.integrations.agentcore.memory_provider import (
    Neo4jMemoryProvider,
)
from neo4j_agent_memory.integrations.agentcore.types import (
    Memory,
    MemorySearchResult,
    MemoryType,
    SessionContext,
)

__all__ = [
    "Neo4jMemoryProvider",
    "HybridMemoryProvider",
    "RoutingStrategy",
    "Memory",
    "MemorySearchResult",
    "MemoryType",
    "SessionContext",
]
