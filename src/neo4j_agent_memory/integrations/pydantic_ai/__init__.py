"""Pydantic AI integration for neo4j-agent-memory."""

try:
    from neo4j_agent_memory.integrations.pydantic_ai.memory import (
        MemoryDependency,
        create_memory_tools,
    )

    __all__ = [
        "MemoryDependency",
        "create_memory_tools",
    ]
except ImportError:
    __all__ = []
