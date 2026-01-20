"""Agent dependencies extending MemoryDependency."""

from dataclasses import dataclass

from neo4j import AsyncDriver

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency


@dataclass
class AgentDeps(MemoryDependency):
    """Extended agent dependencies with news graph access.

    Inherits from MemoryDependency to get memory context capabilities
    and adds news graph database access.
    """

    news_driver: AsyncDriver | None = None
    news_database: str = "neo4j"
    memory_enabled: bool = True

    @classmethod
    def create(
        cls,
        memory: MemoryClient | None,
        session_id: str,
        news_driver: AsyncDriver | None = None,
        news_database: str = "neo4j",
        memory_enabled: bool = True,
    ) -> "AgentDeps":
        """Create agent dependencies with memory client and news driver."""
        return cls(
            client=memory,  # MemoryDependency uses 'client' field
            session_id=session_id,
            news_driver=news_driver,
            news_database=news_database,
            memory_enabled=memory_enabled,
        )
