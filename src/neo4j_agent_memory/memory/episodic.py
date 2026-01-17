"""Episodic memory for conversations and messages."""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from neo4j_agent_memory.core.memory import BaseMemory, MemoryEntry
from neo4j_agent_memory.graph import queries


def _serialize_metadata(metadata: dict[str, Any] | None) -> str | None:
    """Serialize metadata dict to JSON string for Neo4j storage."""
    if metadata is None or metadata == {}:
        return None
    return json.dumps(metadata)


def _deserialize_metadata(metadata_str: str | None) -> dict[str, Any]:
    """Deserialize metadata from JSON string."""
    if metadata_str is None:
        return {}
    try:
        return json.loads(metadata_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def _to_python_datetime(neo4j_datetime) -> datetime:
    """Convert Neo4j DateTime to Python datetime."""
    if neo4j_datetime is None:
        return datetime.utcnow()
    if isinstance(neo4j_datetime, datetime):
        return neo4j_datetime
    # Neo4j DateTime has to_native() method
    try:
        return neo4j_datetime.to_native()
    except AttributeError:
        return datetime.utcnow()


if TYPE_CHECKING:
    from neo4j_agent_memory.embeddings.base import Embedder
    from neo4j_agent_memory.extraction.base import EntityExtractor
    from neo4j_agent_memory.graph.client import Neo4jClient


class MessageRole(str, Enum):
    """Message role in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(MemoryEntry):
    """A single message in a conversation."""

    role: MessageRole = Field(description="Message role")
    content: str = Field(description="Message content")
    conversation_id: UUID | None = Field(default=None, description="Parent conversation ID")
    tool_calls: list[dict[str, Any]] | None = Field(default=None, description="Tool calls if any")


class Conversation(BaseModel):
    """A conversation thread containing messages."""

    id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(description="User/agent session identifier")
    title: str | None = Field(default=None, description="Conversation title")
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EpisodicMemory(BaseMemory[Message]):
    """
    Episodic memory stores conversation history and experiences.

    Provides:
    - Thread-based organization of messages
    - Message embeddings for semantic retrieval
    - Entity linking from conversations
    - Session-based conversation management
    """

    def __init__(
        self,
        client: "Neo4jClient",
        embedder: "Embedder | None" = None,
        extractor: "EntityExtractor | None" = None,
    ):
        """Initialize episodic memory."""
        super().__init__(client, embedder, extractor)

    async def add(self, content: str, **kwargs: Any) -> Message:
        """Add content as a message."""
        session_id = kwargs.get("session_id", "default")
        role = kwargs.get("role", MessageRole.USER)
        return await self.add_message(session_id, role, content, **kwargs)

    async def add_message(
        self,
        session_id: str,
        role: MessageRole | str,
        content: str,
        *,
        conversation_id: UUID | str | None = None,
        extract_entities: bool = True,
        generate_embedding: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """
        Add a message to a conversation.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system, tool)
            content: Message content
            conversation_id: Optional specific conversation ID
            extract_entities: Whether to extract entities from content
            generate_embedding: Whether to generate embedding
            metadata: Optional metadata

        Returns:
            The created message
        """
        # Normalize role
        if isinstance(role, str):
            role = MessageRole(role.lower())

        # Get or create conversation
        conv_id = await self._ensure_conversation(session_id, conversation_id)

        # Generate embedding if enabled
        embedding = None
        if generate_embedding and self._embedder is not None:
            embedding = await self._embedder.embed(content)

        # Create message
        message = Message(
            id=uuid4(),
            role=role,
            content=content,
            conversation_id=conv_id,
            embedding=embedding,
            metadata=metadata or {},
        )

        # Store message
        await self._client.execute_write(
            queries.CREATE_MESSAGE,
            {
                "conversation_id": str(conv_id),
                "id": str(message.id),
                "role": message.role.value,
                "content": message.content,
                "embedding": message.embedding,
                "metadata": _serialize_metadata(message.metadata),
            },
        )

        # Extract and link entities if enabled
        if extract_entities and self._extractor is not None:
            await self._extract_and_link_entities(message)

        return message

    async def get_conversation(
        self,
        session_id: str,
        *,
        conversation_id: UUID | str | None = None,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> Conversation:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier
            conversation_id: Optional specific conversation ID
            limit: Maximum number of messages
            since: Only get messages after this time

        Returns:
            Conversation with messages
        """
        # Get conversation
        if conversation_id:
            conv_id = str(conversation_id) if isinstance(conversation_id, UUID) else conversation_id
            results = await self._client.execute_read(queries.GET_CONVERSATION, {"id": conv_id})
        else:
            results = await self._client.execute_read(
                queries.GET_CONVERSATION_BY_SESSION, {"session_id": session_id}
            )

        if not results:
            # Return empty conversation
            return Conversation(session_id=session_id)

        conv_data = dict(results[0]["c"])

        # Get messages
        msg_results = await self._client.execute_read(
            queries.GET_CONVERSATION_MESSAGES,
            {"conversation_id": conv_data["id"], "limit": limit or 1000},
        )

        messages = []
        for row in msg_results:
            msg_data = dict(row["m"])
            msg = Message(
                id=UUID(msg_data["id"]),
                role=MessageRole(msg_data["role"]),
                content=msg_data["content"],
                embedding=msg_data.get("embedding"),
                conversation_id=UUID(conv_data["id"]),
                created_at=_to_python_datetime(msg_data.get("timestamp")),
                metadata=_deserialize_metadata(msg_data.get("metadata")),
            )
            if since is None or msg.created_at >= since:
                messages.append(msg)

        return Conversation(
            id=UUID(conv_data["id"]),
            session_id=conv_data["session_id"],
            title=conv_data.get("title"),
            messages=messages,
            created_at=_to_python_datetime(conv_data.get("created_at")),
            updated_at=_to_python_datetime(conv_data.get("updated_at"))
            if conv_data.get("updated_at")
            else None,
        )

    async def search(self, query: str, **kwargs: Any) -> list[Message]:
        """Search for messages."""
        return await self.search_messages(query, **kwargs)

    async def search_messages(
        self,
        query: str,
        *,
        session_id: str | None = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[Message]:
        """
        Semantic search across messages.

        Args:
            query: Search query
            session_id: Optional filter by session
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of matching messages
        """
        if self._embedder is None:
            return []

        query_embedding = await self._embedder.embed(query)

        results = await self._client.execute_read(
            queries.SEARCH_MESSAGES_BY_EMBEDDING,
            {
                "embedding": query_embedding,
                "limit": limit,
                "threshold": threshold,
            },
        )

        messages = []
        for row in results:
            msg_data = dict(row["m"])
            msg = Message(
                id=UUID(msg_data["id"]),
                role=MessageRole(msg_data["role"]),
                content=msg_data["content"],
                embedding=msg_data.get("embedding"),
                created_at=_to_python_datetime(msg_data.get("timestamp")),
                metadata={
                    **_deserialize_metadata(msg_data.get("metadata")),
                    "similarity": row["score"],
                },
            )
            messages.append(msg)

        return messages

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """
        Get conversation context for LLM prompts.

        Args:
            query: Query to find relevant context
            session_id: Optional session filter
            max_messages: Maximum messages to include
            include_related: Whether to include related entities

        Returns:
            Formatted context string
        """
        session_id = kwargs.get("session_id")
        max_messages = kwargs.get("max_messages", 10)

        parts = []

        # Get recent conversation if session_id provided
        if session_id:
            conv = await self.get_conversation(session_id, limit=max_messages)
            if conv.messages:
                parts.append("### Recent Conversation")
                for msg in conv.messages[-max_messages:]:
                    parts.append(f"**{msg.role.value}**: {msg.content}")

        # Search for relevant messages
        if self._embedder is not None:
            relevant = await self.search_messages(query, limit=5)
            if relevant:
                parts.append("\n### Relevant Past Messages")
                for msg in relevant:
                    score = msg.metadata.get("similarity", 0)
                    parts.append(f"- [{msg.role.value}] {msg.content} (relevance: {score:.2f})")

        return "\n".join(parts)

    async def clear_session(self, session_id: str) -> None:
        """Clear all data for a session."""
        await self._client.execute_write(queries.DELETE_SESSION_DATA, {"session_id": session_id})

    async def _ensure_conversation(
        self,
        session_id: str,
        conversation_id: UUID | str | None = None,
    ) -> UUID:
        """Ensure a conversation exists and return its ID."""
        if conversation_id:
            return UUID(str(conversation_id))

        # Check for existing conversation
        results = await self._client.execute_read(
            queries.GET_CONVERSATION_BY_SESSION, {"session_id": session_id}
        )

        if results:
            return UUID(results[0]["c"]["id"])

        # Create new conversation
        new_id = uuid4()
        await self._client.execute_write(
            queries.CREATE_CONVERSATION,
            {
                "id": str(new_id),
                "session_id": session_id,
                "title": None,
            },
        )
        return new_id

    async def _extract_and_link_entities(self, message: Message) -> None:
        """Extract entities from message and link them."""
        if self._extractor is None:
            return

        result = await self._extractor.extract(message.content)

        for entity in result.entities:
            # Create or get entity
            entity_id = str(uuid4())
            await self._client.execute_write(
                queries.CREATE_ENTITY,
                {
                    "id": entity_id,
                    "name": entity.name,
                    "type": entity.type,
                    "canonical_name": entity.name,
                    "description": None,
                    "embedding": None,
                    "confidence": entity.confidence,
                    "metadata": None,  # Serialized as null for empty
                },
            )

            # Link message to entity
            await self._client.execute_write(
                queries.LINK_MESSAGE_TO_ENTITY,
                {
                    "message_id": str(message.id),
                    "entity_id": entity_id,
                    "confidence": entity.confidence,
                    "start_pos": entity.start_pos,
                    "end_pos": entity.end_pos,
                },
            )
