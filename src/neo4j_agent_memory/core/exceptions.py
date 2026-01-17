"""Custom exceptions for neo4j-agent-memory."""


class MemoryError(Exception):
    """Base exception for all memory-related errors."""

    pass


class ConnectionError(MemoryError):
    """Raised when there's a problem connecting to Neo4j."""

    pass


class SchemaError(MemoryError):
    """Raised when there's a problem with the database schema."""

    pass


class ExtractionError(MemoryError):
    """Raised when entity extraction fails."""

    pass


class ResolutionError(MemoryError):
    """Raised when entity resolution fails."""

    pass


class EmbeddingError(MemoryError):
    """Raised when embedding generation fails."""

    pass


class ConfigurationError(MemoryError):
    """Raised when there's a configuration problem."""

    pass


class NotConnectedError(MemoryError):
    """Raised when attempting operations without an active connection."""

    pass
