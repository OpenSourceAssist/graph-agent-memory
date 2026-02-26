"""Type conversions between Neo4j Agent Memory and Google ADK types.

Provides utilities for converting between the internal neo4j-agent-memory
types and Google ADK types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j_agent_memory.memory.long_term import Entity, Preference
    from neo4j_agent_memory.memory.short_term import Message


@dataclass
class MemoryEntry:
    """Represents a memory entry in ADK format.

    This is a standalone dataclass that mirrors the ADK MemoryEntry structure
    for compatibility when google-adk is not installed.
    """

    id: str
    content: str
    memory_type: str  # "message", "entity", "preference", "trace"
    timestamp: datetime | None = None
    metadata: dict[str, Any] | None = None
    score: float | None = None  # Similarity score for search results


@dataclass
class SessionMessage:
    """Represents a message in a session."""

    role: str
    content: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] | None = None


def message_to_memory_entry(msg: Message) -> MemoryEntry:
    """Convert a neo4j-agent-memory Message to a MemoryEntry.

    Args:
        msg: The Message object to convert.

    Returns:
        MemoryEntry with message data.
    """
    role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)

    return MemoryEntry(
        id=str(msg.id),
        content=msg.content,
        memory_type="message",
        timestamp=msg.created_at if hasattr(msg, "created_at") else None,
        metadata={
            "role": role,
            "session_id": msg.session_id if hasattr(msg, "session_id") else None,
            **(msg.metadata or {}),
        },
        score=msg.metadata.get("similarity") if msg.metadata else None,
    )


def entity_to_memory_entry(entity: Entity) -> MemoryEntry:
    """Convert a neo4j-agent-memory Entity to a MemoryEntry.

    Args:
        entity: The Entity object to convert.

    Returns:
        MemoryEntry with entity data.
    """
    entity_type = entity.type.value if hasattr(entity.type, "value") else str(entity.type)

    content = entity.display_name
    if entity.description:
        content = f"{entity.display_name}: {entity.description}"

    return MemoryEntry(
        id=str(entity.id),
        content=content,
        memory_type="entity",
        timestamp=entity.created_at if hasattr(entity, "created_at") else None,
        metadata={
            "name": entity.display_name,
            "type": entity_type,
            "description": entity.description,
            "aliases": entity.aliases if hasattr(entity, "aliases") else [],
        },
    )


def preference_to_memory_entry(pref: Preference) -> MemoryEntry:
    """Convert a neo4j-agent-memory Preference to a MemoryEntry.

    Args:
        pref: The Preference object to convert.

    Returns:
        MemoryEntry with preference data.
    """
    content = f"[{pref.category}] {pref.preference}"
    if pref.context:
        content += f" (context: {pref.context})"

    return MemoryEntry(
        id=str(pref.id),
        content=content,
        memory_type="preference",
        timestamp=pref.created_at if hasattr(pref, "created_at") else None,
        metadata={
            "category": pref.category,
            "preference": pref.preference,
            "context": pref.context,
        },
    )


def session_message_from_dict(data: dict[str, Any]) -> SessionMessage:
    """Create a SessionMessage from a dictionary.

    Args:
        data: Dictionary with message data.

    Returns:
        SessionMessage instance.
    """
    return SessionMessage(
        role=data.get("role", "user"),
        content=data.get("content", ""),
        timestamp=data.get("timestamp"),
        metadata=data.get("metadata"),
    )


def memory_entry_to_dict(entry: MemoryEntry) -> dict[str, Any]:
    """Convert a MemoryEntry to a dictionary.

    Args:
        entry: The MemoryEntry to convert.

    Returns:
        Dictionary representation.
    """
    return {
        "id": entry.id,
        "content": entry.content,
        "memory_type": entry.memory_type,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "metadata": entry.metadata,
        "score": entry.score,
    }
