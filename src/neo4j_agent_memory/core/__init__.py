"""Core abstractions and base classes for neo4j-agent-memory."""

from neo4j_agent_memory.core.exceptions import (
    MemoryError,
    ConnectionError,
    SchemaError,
    ExtractionError,
    ResolutionError,
    EmbeddingError,
)
from neo4j_agent_memory.core.memory import (
    MemoryEntry,
    MemoryStore,
    BaseMemory,
)

__all__ = [
    # Exceptions
    "MemoryError",
    "ConnectionError",
    "SchemaError",
    "ExtractionError",
    "ResolutionError",
    "EmbeddingError",
    # Base classes
    "MemoryEntry",
    "MemoryStore",
    "BaseMemory",
]
