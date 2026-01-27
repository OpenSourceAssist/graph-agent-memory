"""Microsoft Agent Framework ChatMessageStore implementation.

Provides Neo4j-backed persistent chat history storage for
Microsoft Agent Framework agents.
"""

from __future__ import annotations

import json
import logging
from collections.abc import MutableMapping, Sequence
from typing import TYPE_CHECKING, Any

from ..base import validate_session_id

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)

try:
    # Note: ChatMessage is the message type used by the framework
    # The exact import path may vary by version
    from agent_framework import ChatMessage

    class Neo4jChatMessageStore:
        """
        Neo4j-backed implementation of chat message storage.

        Provides persistent storage for chat messages using Neo4j,
        with support for serialization/deserialization for thread persistence.
        Messages are stored with NEXT_MESSAGE relationships forming a
        conversation chain.

        .. warning::
            This class targets Microsoft Agent Framework v1.0.0b251223.
            The ChatMessageStore API may change before GA release.

        Example:
            from neo4j_agent_memory import MemoryClient, MemorySettings
            from neo4j_agent_memory.integrations.microsoft_agent import Neo4jChatMessageStore
            from agent_framework import ChatAgent

            async with MemoryClient(settings) as client:
                message_store = Neo4jChatMessageStore(
                    memory_client=client,
                    session_id="user-123",
                )

                # Add messages
                await message_store.add_messages([
                    ChatMessage(role="user", content="Hello!"),
                    ChatMessage(role="assistant", content="Hi there!"),
                ])

                # List messages
                messages = await message_store.list_messages()

        Attributes:
            session_id: The session identifier for message storage.
            max_messages: Optional limit on messages to retrieve.
        """

        def __init__(
            self,
            memory_client: MemoryClient,
            session_id: str,
            *,
            max_messages: int | None = None,
            extract_entities: bool = False,
            generate_embeddings: bool = True,
        ):
            """
            Initialize the Neo4j chat message store.

            Args:
                memory_client: Connected MemoryClient instance.
                session_id: Session identifier for message storage.
                max_messages: Optional limit on messages to store/retrieve.
                extract_entities: Whether to extract entities on message add.
                generate_embeddings: Whether to generate embeddings for search.
            """
            self._client = memory_client
            self._session_id = validate_session_id(session_id)
            self._max_messages = max_messages
            self._extract_entities = extract_entities
            self._generate_embeddings = generate_embeddings

        @property
        def session_id(self) -> str:
            """Get the session ID."""
            return self._session_id

        @property
        def memory_client(self) -> MemoryClient:
            """Get the underlying memory client."""
            return self._client

        async def add_messages(self, messages: Sequence[ChatMessage]) -> None:
            """
            Add messages to Neo4j storage.

            Messages are stored in the graph with NEXT_MESSAGE relationships
            maintaining conversation order.

            .. note::
                Microsoft Agent Framework API - may change before GA.
                Currently targets v1.0.0b251223.

            Args:
                messages: Sequence of ChatMessage objects to store.
            """
            for msg in messages:
                role = self._get_role(msg)
                content = self._get_content(msg)

                if not content:
                    continue

                # Build metadata from message attributes
                metadata: dict[str, Any] = {}

                # Handle tool_calls if present (assistant messages)
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    metadata["tool_calls"] = self._serialize_tool_calls(msg.tool_calls)

                # Handle tool_call_id if present (tool response messages)
                if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                    metadata["tool_call_id"] = msg.tool_call_id

                # Handle name if present
                if hasattr(msg, "name") and msg.name:
                    metadata["name"] = msg.name

                await self._client.short_term.add_message(
                    session_id=self._session_id,
                    role=role,
                    content=content,
                    extract_entities=self._extract_entities,
                    generate_embedding=self._generate_embeddings,
                    metadata=metadata if metadata else None,
                )

        async def list_messages(self) -> list[ChatMessage]:
            """
            Retrieve messages from Neo4j in chronological order.

            .. note::
                Microsoft Agent Framework API - may change before GA.
                Currently targets v1.0.0b251223.

            Returns:
                List of ChatMessage objects in conversation order.
            """
            limit = self._max_messages or 1000

            conv = await self._client.short_term.get_conversation(
                session_id=self._session_id,
                limit=limit,
            )

            messages: list[ChatMessage] = []
            for msg in conv.messages:
                role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                content = msg.content

                # Build ChatMessage with appropriate attributes
                chat_msg = ChatMessage(role=role, content=content)

                # Restore tool_calls if present
                if msg.metadata:
                    if msg.metadata.get("tool_calls"):
                        try:
                            chat_msg.tool_calls = self._deserialize_tool_calls(
                                msg.metadata["tool_calls"]
                            )
                        except Exception as e:
                            logger.debug(f"Error deserializing tool_calls: {e}")

                    if msg.metadata.get("tool_call_id"):
                        chat_msg.tool_call_id = msg.metadata["tool_call_id"]

                    if msg.metadata.get("name"):
                        chat_msg.name = msg.metadata["name"]

                messages.append(chat_msg)

            return messages

        async def clear(self) -> None:
            """
            Clear all messages for this session.

            This removes all messages from the conversation but preserves
            any entities or preferences that were extracted.
            """
            await self._client.short_term.clear_session(self._session_id)

        async def serialize(self) -> MutableMapping[str, Any]:
            """
            Serialize store state for persistence.

            .. note::
                Microsoft Agent Framework API - may change before GA.

            Returns:
                Dictionary containing serializable state.
            """
            return {
                "session_id": self._session_id,
                "max_messages": self._max_messages,
                "extract_entities": self._extract_entities,
                "generate_embeddings": self._generate_embeddings,
            }

        @classmethod
        async def deserialize(
            cls,
            serialized_state: MutableMapping[str, Any],
            memory_client: MemoryClient,
        ) -> Neo4jChatMessageStore:
            """
            Restore store from serialized state.

            .. warning::
                Requires a fresh MemoryClient to be provided. Database
                connections cannot be serialized.

            Args:
                serialized_state: Previously serialized state.
                memory_client: A connected MemoryClient instance.

            Returns:
                Restored Neo4jChatMessageStore instance.
            """
            return cls(
                memory_client=memory_client,
                session_id=serialized_state["session_id"],
                max_messages=serialized_state.get("max_messages"),
                extract_entities=serialized_state.get("extract_entities", False),
                generate_embeddings=serialized_state.get("generate_embeddings", True),
            )

        # --- Private helper methods ---

        def _get_role(self, msg: ChatMessage) -> str:
            """Extract role from ChatMessage."""
            if hasattr(msg, "role"):
                role = msg.role
                return role.value if hasattr(role, "value") else str(role)
            return "user"

        def _get_content(self, msg: ChatMessage) -> str:
            """Extract content from ChatMessage."""
            if hasattr(msg, "content"):
                return msg.content or ""
            return ""

        def _serialize_tool_calls(self, tool_calls: Any) -> list[dict]:
            """Serialize tool calls for storage."""
            if not tool_calls:
                return []

            serialized = []
            for tc in tool_calls:
                if isinstance(tc, dict):
                    serialized.append(tc)
                elif hasattr(tc, "model_dump"):
                    # Pydantic model
                    serialized.append(tc.model_dump())
                elif hasattr(tc, "dict"):
                    # Pydantic v1
                    serialized.append(tc.dict())
                elif hasattr(tc, "id") and hasattr(tc, "function"):
                    # OpenAI-style tool call
                    serialized.append(
                        {
                            "id": tc.id,
                            "type": getattr(tc, "type", "function"),
                            "function": {
                                "name": tc.function.name
                                if hasattr(tc.function, "name")
                                else tc.function.get("name"),
                                "arguments": tc.function.arguments
                                if hasattr(tc.function, "arguments")
                                else tc.function.get("arguments"),
                            },
                        }
                    )
                else:
                    # Best effort serialization
                    try:
                        serialized.append(json.loads(json.dumps(tc, default=str)))
                    except Exception:
                        logger.debug(f"Could not serialize tool call: {tc}")

            return serialized

        def _deserialize_tool_calls(self, tool_calls_data: list[dict]) -> list[Any]:
            """Deserialize tool calls from storage."""
            # Return as-is for now; framework may have specific types
            return tool_calls_data


except ImportError:
    # Microsoft Agent Framework not installed
    pass
