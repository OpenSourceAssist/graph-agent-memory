"""Google ADK MemoryService implementation backed by Neo4j.

Provides a Neo4j-backed implementation of the Google ADK MemoryService
interface for persistent agent memory.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from neo4j_agent_memory.integrations.google_adk.types import (
    MemoryEntry,
    SessionMessage,
    entity_to_memory_entry,
    message_to_memory_entry,
    preference_to_memory_entry,
    session_message_from_dict,
)

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)


class Neo4jMemoryService:
    """Neo4j-backed memory service for Google ADK agents.

    Implements the ADK MemoryService interface to provide:
    - Session memory persistence
    - Semantic memory search
    - Entity/fact storage

    .. warning::
        Google ADK is in preview. The MemoryService interface may change
        before GA release.

    Example:
        from neo4j_agent_memory import MemoryClient, MemorySettings
        from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

        settings = MemorySettings(...)
        async with MemoryClient(settings) as client:
            memory_service = Neo4jMemoryService(
                memory_client=client,
                user_id="user-123",
            )

            # Store a session
            await memory_service.add_session_to_memory(session)

            # Search memories
            results = await memory_service.search_memories("project deadline")

    Attributes:
        user_id: Optional user identifier for personalization.
        include_entities: Whether to extract and search entities.
        include_preferences: Whether to extract and search preferences.
    """

    def __init__(
        self,
        memory_client: MemoryClient,
        *,
        user_id: str | None = None,
        include_entities: bool = True,
        include_preferences: bool = True,
        extract_on_store: bool = True,
    ):
        """Initialize the Neo4j memory service.

        Args:
            memory_client: Connected MemoryClient instance.
            user_id: Optional user identifier for personalization.
            include_entities: Whether to include entities in search.
            include_preferences: Whether to include preferences in search.
            extract_on_store: Whether to extract entities when storing sessions.
        """
        self._client = memory_client
        self._user_id = user_id
        self._include_entities = include_entities
        self._include_preferences = include_preferences
        self._extract_on_store = extract_on_store

    @property
    def user_id(self) -> str | None:
        """Get the user ID."""
        return self._user_id

    @property
    def memory_client(self) -> MemoryClient:
        """Get the underlying memory client."""
        return self._client

    async def add_session_to_memory(
        self,
        session: Any,
        *,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Store session messages and extract entities.

        This method stores all messages from a session into the Neo4j
        memory store. If entity extraction is enabled, it will also
        extract entities from the messages.

        Args:
            session: The ADK Session object or dict with messages.
            session_id: Override session ID (uses session.id if not provided).
            **kwargs: Additional arguments (for API compatibility).
        """
        # Extract session ID
        if session_id is None:
            if hasattr(session, "id"):
                session_id = str(session.id)
            elif isinstance(session, dict):
                session_id = session.get("id", "default")
            else:
                session_id = "default"

        # Extract messages from session
        messages = self._extract_messages(session)

        if not messages:
            logger.debug(f"No messages to store for session {session_id}")
            return

        # Store each message
        for msg in messages:
            try:
                await self._client.short_term.add_message(
                    session_id=session_id,
                    role=msg.role,
                    content=msg.content,
                    metadata=msg.metadata,
                    extract_entities=self._extract_on_store,
                    generate_embedding=True,
                )
            except Exception as e:
                logger.warning(f"Error storing message: {e}")

        logger.debug(f"Stored {len(messages)} messages for session {session_id}")

    async def search_memories(
        self,
        query: str,
        *,
        app_name: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
        threshold: float = 0.7,
        **kwargs: Any,
    ) -> list[MemoryEntry]:
        """Search across all memory types.

        Performs hybrid vector + graph search across messages, entities,
        and preferences to find relevant memories.

        Args:
            query: The search query.
            app_name: Optional app name filter (not used currently).
            user_id: Optional user ID filter (not used currently).
            limit: Maximum number of results.
            threshold: Minimum similarity threshold.
            **kwargs: Additional arguments (for API compatibility).

        Returns:
            List of MemoryEntry objects matching the query.
        """
        results: list[MemoryEntry] = []

        try:
            # Search messages
            messages = await self._client.short_term.search_messages(
                query=query,
                limit=limit,
                threshold=threshold,
            )
            for msg in messages:
                results.append(message_to_memory_entry(msg))

            # Search entities if enabled
            if self._include_entities:
                entities = await self._client.long_term.search_entities(
                    query=query,
                    limit=limit,
                )
                for entity in entities:
                    results.append(entity_to_memory_entry(entity))

            # Search preferences if enabled
            if self._include_preferences:
                prefs = await self._client.long_term.search_preferences(
                    query=query,
                    limit=limit,
                )
                for pref in prefs:
                    results.append(preference_to_memory_entry(pref))

        except Exception as e:
            logger.error(f"Error searching memories: {e}")

        # Sort by score (descending) and limit
        results.sort(key=lambda x: x.score or 0, reverse=True)
        return results[:limit]

    async def get_memories_for_session(
        self,
        session_id: str,
        *,
        limit: int = 50,
        **kwargs: Any,
    ) -> list[MemoryEntry]:
        """Get memories relevant to a session.

        Retrieves conversation history and related memories for a session.

        Args:
            session_id: The session ID to get memories for.
            limit: Maximum number of messages.
            **kwargs: Additional arguments (for API compatibility).

        Returns:
            List of MemoryEntry objects for the session.
        """
        results: list[MemoryEntry] = []

        try:
            # Get conversation history
            conversation = await self._client.short_term.get_conversation(
                session_id=session_id,
                limit=limit,
            )

            for msg in conversation.messages:
                results.append(message_to_memory_entry(msg))

        except Exception as e:
            logger.error(f"Error getting session memories: {e}")

        return results

    async def add_memory(
        self,
        content: str,
        *,
        memory_type: str = "message",
        session_id: str = "default",
        role: str = "user",
        category: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> MemoryEntry | None:
        """Add a single memory entry.

        Convenience method for adding individual memories.

        Args:
            content: The memory content.
            memory_type: Type of memory ("message", "preference").
            session_id: Session ID for messages.
            role: Message role (for message type).
            category: Preference category (for preference type).
            metadata: Optional metadata.
            **kwargs: Additional arguments.

        Returns:
            The created MemoryEntry or None on error.
        """
        try:
            if memory_type == "message":
                msg = await self._client.short_term.add_message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    metadata=metadata,
                    extract_entities=self._extract_on_store,
                    generate_embedding=True,
                )
                return message_to_memory_entry(msg)

            elif memory_type == "preference":
                if not category:
                    category = "general"
                pref = await self._client.long_term.add_preference(
                    category=category,
                    preference=content,
                    generate_embedding=True,
                )
                return preference_to_memory_entry(pref)

            else:
                logger.warning(f"Unknown memory type: {memory_type}")
                return None

        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return None

    async def clear_session(self, session_id: str) -> None:
        """Clear all memories for a session.

        Args:
            session_id: The session ID to clear.
        """
        try:
            await self._client.short_term.clear_session(session_id)
            logger.debug(f"Cleared session {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session: {e}")

    def _extract_messages(self, session: Any) -> list[SessionMessage]:
        """Extract messages from various session formats.

        Args:
            session: Session object or dict.

        Returns:
            List of SessionMessage objects.
        """
        messages: list[SessionMessage] = []

        # Handle ADK Session object
        if hasattr(session, "messages"):
            for msg in session.messages:
                if hasattr(msg, "role") and hasattr(msg, "content"):
                    messages.append(
                        SessionMessage(
                            role=str(msg.role) if hasattr(msg.role, "value") else msg.role,
                            content=msg.content,
                            timestamp=getattr(msg, "timestamp", None),
                            metadata=getattr(msg, "metadata", None),
                        )
                    )
                elif isinstance(msg, dict):
                    messages.append(session_message_from_dict(msg))

        # Handle dict with messages
        elif isinstance(session, dict) and "messages" in session:
            for msg in session["messages"]:
                if isinstance(msg, dict):
                    messages.append(session_message_from_dict(msg))

        # Handle list of messages directly
        elif isinstance(session, list):
            for msg in session:
                if isinstance(msg, dict):
                    messages.append(session_message_from_dict(msg))
                elif hasattr(msg, "role") and hasattr(msg, "content"):
                    messages.append(
                        SessionMessage(
                            role=str(msg.role),
                            content=msg.content,
                        )
                    )

        return messages
