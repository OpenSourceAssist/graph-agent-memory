"""Pydantic AI integration for neo4j-agent-memory."""

try:
    from neo4j_agent_memory.integrations.pydantic_ai.memory import (
        MemoryDependency,
        create_memory_tools,
        record_agent_trace,
    )

    __all__ = [
        "MemoryDependency",
        "create_memory_tools",
        "record_agent_trace",
    ]
except ImportError:
    __all__ = []
