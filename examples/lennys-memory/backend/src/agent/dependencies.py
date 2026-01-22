"""Agent dependencies extending MemoryDependency."""

from dataclasses import dataclass

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency


@dataclass
class AgentDeps(MemoryDependency):
    """Extended agent dependencies for podcast exploration.

    Inherits from MemoryDependency to get memory context capabilities.
    """

    memory_enabled: bool = True

    @classmethod
    def create(
        cls,
        memory: MemoryClient | None,
        session_id: str,
        memory_enabled: bool = True,
    ) -> "AgentDeps":
        """Create agent dependencies with memory client."""
        return cls(
            client=memory,  # MemoryDependency uses 'client' field
            session_id=session_id,
            memory_enabled=memory_enabled,
        )
