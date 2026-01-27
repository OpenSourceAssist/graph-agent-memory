"""Microsoft Agent Framework ContextProvider implementation.

Provides Neo4j-backed context injection and memory extraction for
Microsoft Agent Framework agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from ..base import (
    format_context_section,
    truncate_text,
    validate_limit,
    validate_session_id,
)

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

    from .gds import GDSConfig

logger = logging.getLogger(__name__)

try:
    from agent_framework import Context, ContextProvider

    class Neo4jContextProvider(ContextProvider):
        """
        Microsoft Agent Framework ContextProvider backed by Neo4j Agent Memory.

        Provides automatic context injection before agent invocation and memory
        extraction after agent responses. Supports all three memory types:
        short-term (conversation), long-term (entities/preferences), and
        reasoning (similar past traces).

        .. warning::
            This class targets Microsoft Agent Framework v1.0.0b251223.
            The ContextProvider API may change before GA release.

        Example:
            from neo4j_agent_memory import MemoryClient, MemorySettings
            from neo4j_agent_memory.integrations.microsoft_agent import Neo4jContextProvider
            from agent_framework import ChatAgent

            async with MemoryClient(settings) as client:
                provider = Neo4jContextProvider(
                    memory_client=client,
                    session_id="user-123",
                    include_short_term=True,
                    include_long_term=True,
                    include_reasoning=True,
                )

                agent = ChatAgent(
                    chat_client=chat_client,
                    name="assistant",
                    context_providers=[provider],
                )

                thread = await agent.create_thread()
                response = await agent.run("Hello!", thread=thread)

        Attributes:
            session_id: The session identifier for memory operations.
            user_id: Optional user identifier for personalization.
            include_short_term: Whether to include conversation history.
            include_long_term: Whether to include entities and preferences.
            include_reasoning: Whether to include similar past traces.
        """

        DEFAULT_CONTEXT_TEMPLATE = """You have access to the following memory context:

{context}

Use this information to provide personalized, contextually relevant responses."""

        def __init__(
            self,
            memory_client: MemoryClient,
            session_id: str,
            *,
            user_id: str | None = None,
            include_short_term: bool = True,
            include_long_term: bool = True,
            include_reasoning: bool = True,
            max_context_items: int = 10,
            max_recent_messages: int = 5,
            extract_entities: bool = True,
            extract_entities_async: bool = True,
            context_template: str | None = None,
            gds_config: GDSConfig | None = None,
            similarity_threshold: float = 0.7,
        ):
            """
            Initialize the Neo4j context provider.

            Args:
                memory_client: Connected MemoryClient instance.
                session_id: Session identifier for conversation tracking.
                user_id: Optional user identifier for personalization.
                include_short_term: Include recent conversation in context.
                include_long_term: Include entities and preferences in context.
                include_reasoning: Include similar past reasoning traces.
                max_context_items: Maximum items per memory type in context.
                max_recent_messages: Maximum recent messages to include.
                extract_entities: Whether to extract entities from messages.
                extract_entities_async: Use background extraction (non-blocking).
                context_template: Custom template for formatting context.
                gds_config: Configuration for GDS algorithm integration.
                similarity_threshold: Minimum similarity score for retrieval.
            """
            self._client = memory_client
            self._session_id = validate_session_id(session_id)
            self._user_id = user_id
            self._include_short_term = include_short_term
            self._include_long_term = include_long_term
            self._include_reasoning = include_reasoning
            self._max_context_items = validate_limit(max_context_items, max_limit=100)
            self._max_recent_messages = validate_limit(max_recent_messages, max_limit=50)
            self._extract_entities = extract_entities
            self._extract_entities_async = extract_entities_async
            self._context_template = context_template or self.DEFAULT_CONTEXT_TEMPLATE
            self._gds_config = gds_config
            self._similarity_threshold = similarity_threshold

            # Extraction queue for background processing
            self._extraction_queue: list[tuple[str, str]] = []

            # Thread mapping for serialization
            self._thread_id: str | None = None

        @property
        def session_id(self) -> str:
            """Get the session ID."""
            return self._session_id

        @property
        def user_id(self) -> str | None:
            """Get the user ID."""
            return self._user_id

        @property
        def memory_client(self) -> MemoryClient:
            """Get the underlying memory client."""
            return self._client

        async def invoking(
            self,
            messages: Any,
            **kwargs: Any,
        ) -> Context:
            """
            Inject context from Neo4j before agent invocation.

            This method is called by the Microsoft Agent Framework just before
            the model is invoked. It retrieves relevant context from all
            configured memory types and returns it for injection.

            .. note::
                Microsoft Agent Framework API - may change before GA.
                Currently targets v1.0.0b251223.

            Args:
                messages: The conversation messages (ChatMessage or sequence).
                **kwargs: Additional framework-provided arguments.

            Returns:
                Context object containing instructions, messages, and tools.
            """
            # Extract query from messages
            query = self._extract_query_from_messages(messages)
            if not query:
                return Context()

            # Gather context from all memory types
            context_parts: list[str] = []

            try:
                # Short-term memory (conversation history)
                if self._include_short_term:
                    short_term = await self._get_short_term_context(query)
                    if short_term:
                        context_parts.append(short_term)

                # Long-term memory (entities, preferences)
                if self._include_long_term:
                    long_term = await self._get_long_term_context(query)
                    if long_term:
                        context_parts.append(long_term)

                # Reasoning memory (similar past traces)
                if self._include_reasoning:
                    reasoning = await self._get_reasoning_context(query)
                    if reasoning:
                        context_parts.append(reasoning)

            except Exception as e:
                logger.warning(f"Error retrieving memory context: {e}")
                # Continue with whatever context we have

            if not context_parts:
                return Context()

            # Format combined context
            combined_context = "\n\n".join(context_parts)
            instructions = self._context_template.format(context=combined_context)

            return Context(
                instructions=instructions,
                messages=[],
                tools=[],
            )

        async def invoked(
            self,
            request_messages: Any,
            response_messages: Any | None = None,
            invoke_exception: Exception | None = None,
            **kwargs: Any,
        ) -> None:
            """
            Extract and store memories after agent response.

            This method is called by the Microsoft Agent Framework after
            receiving a response from the model. It saves messages and
            optionally extracts entities for the knowledge graph.

            .. note::
                Microsoft Agent Framework API - may change before GA.
                Currently targets v1.0.0b251223.

            Args:
                request_messages: The request messages sent to the model.
                response_messages: The response messages from the model.
                invoke_exception: Any exception that occurred during invocation.
                **kwargs: Additional framework-provided arguments.
            """
            if invoke_exception is not None:
                logger.debug(f"Skipping memory extraction due to exception: {invoke_exception}")
                return

            try:
                # Save request messages
                request_list = self._normalize_messages(request_messages)
                for msg in request_list:
                    role = self._get_message_role(msg)
                    content = self._get_message_content(msg)
                    if role and content:
                        await self._client.short_term.add_message(
                            session_id=self._session_id,
                            role=role,
                            content=content,
                            extract_entities=not self._extract_entities_async,
                            generate_embedding=True,
                        )
                        if self._extract_entities and self._extract_entities_async:
                            self._extraction_queue.append((role, content))

                # Save response messages
                if response_messages:
                    response_list = self._normalize_messages(response_messages)
                    for msg in response_list:
                        role = self._get_message_role(msg)
                        content = self._get_message_content(msg)
                        if role and content:
                            await self._client.short_term.add_message(
                                session_id=self._session_id,
                                role=role,
                                content=content,
                                extract_entities=not self._extract_entities_async,
                                generate_embedding=True,
                            )
                            if self._extract_entities and self._extract_entities_async:
                                self._extraction_queue.append((role, content))

                # Trigger background extraction if needed
                if self._extraction_queue and self._extract_entities_async:
                    await self._trigger_background_extraction()

            except Exception as e:
                logger.warning(f"Error saving messages to memory: {e}")

        async def thread_created(self, thread_id: str | None) -> None:
            """
            Handle thread creation event.

            .. note::
                Microsoft Agent Framework API - may change before GA.

            Args:
                thread_id: The ID of the newly created thread.
            """
            self._thread_id = thread_id
            logger.debug(f"Thread created: {thread_id}, session: {self._session_id}")

        def serialize(self) -> str:
            """
            Serialize provider state for thread persistence.

            .. warning::
                Does NOT serialize the Neo4j connection. When deserializing,
                a fresh MemoryClient must be provided.

            Returns:
                JSON string containing serializable state.
            """
            # Flush extraction queue before serializing
            if self._extraction_queue:
                logger.debug(
                    f"Extraction queue has {len(self._extraction_queue)} items "
                    "that will be lost during serialization"
                )

            state = {
                "session_id": self._session_id,
                "user_id": self._user_id,
                "thread_id": self._thread_id,
                "include_short_term": self._include_short_term,
                "include_long_term": self._include_long_term,
                "include_reasoning": self._include_reasoning,
                "max_context_items": self._max_context_items,
                "max_recent_messages": self._max_recent_messages,
                "extract_entities": self._extract_entities,
                "extract_entities_async": self._extract_entities_async,
                "similarity_threshold": self._similarity_threshold,
                "gds_enabled": self._gds_config.enabled if self._gds_config else False,
            }
            return json.dumps(state)

        @classmethod
        def deserialize(
            cls,
            serialized_state: str,
            memory_client: MemoryClient,
            context_template: str | None = None,
            gds_config: GDSConfig | None = None,
        ) -> Neo4jContextProvider:
            """
            Deserialize provider from saved state.

            .. warning::
                Requires a fresh MemoryClient to be provided. Database
                connections cannot be serialized.

            Args:
                serialized_state: Previously serialized state string.
                memory_client: A connected MemoryClient instance.
                context_template: Optional custom context template.
                gds_config: Optional GDS configuration.

            Returns:
                Restored Neo4jContextProvider instance.
            """
            state = json.loads(serialized_state)

            provider = cls(
                memory_client=memory_client,
                session_id=state["session_id"],
                user_id=state.get("user_id"),
                include_short_term=state.get("include_short_term", True),
                include_long_term=state.get("include_long_term", True),
                include_reasoning=state.get("include_reasoning", True),
                max_context_items=state.get("max_context_items", 10),
                max_recent_messages=state.get("max_recent_messages", 5),
                extract_entities=state.get("extract_entities", True),
                extract_entities_async=state.get("extract_entities_async", True),
                context_template=context_template,
                gds_config=gds_config,
                similarity_threshold=state.get("similarity_threshold", 0.7),
            )
            provider._thread_id = state.get("thread_id")

            return provider

        # --- Private helper methods ---

        def _extract_query_from_messages(self, messages: Any) -> str | None:
            """Extract query string from the latest user message."""
            msg_list = self._normalize_messages(messages)

            # Find latest user message
            for msg in reversed(msg_list):
                role = self._get_message_role(msg)
                content = self._get_message_content(msg)
                if role == "user" and content:
                    return truncate_text(content, max_length=500, suffix="")

            return None

        def _normalize_messages(self, messages: Any) -> list[Any]:
            """Normalize messages to a list."""
            if messages is None:
                return []
            if isinstance(messages, (list, tuple)):
                return list(messages)
            return [messages]

        def _get_message_role(self, msg: Any) -> str | None:
            """Extract role from a message object."""
            if hasattr(msg, "role"):
                role = msg.role
                return role.value if hasattr(role, "value") else str(role)
            if isinstance(msg, dict):
                return msg.get("role")
            return None

        def _get_message_content(self, msg: Any) -> str | None:
            """Extract content from a message object."""
            if hasattr(msg, "content"):
                return msg.content
            if isinstance(msg, dict):
                return msg.get("content")
            return None

        async def _get_short_term_context(self, query: str) -> str | None:
            """Get short-term memory context."""
            parts: list[str] = []

            # Recent conversation history
            try:
                conv = await self._client.short_term.get_conversation(
                    session_id=self._session_id,
                    limit=self._max_recent_messages,
                )
                if conv.messages:
                    recent_items = []
                    for msg in conv.messages[-self._max_recent_messages :]:
                        role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                        content = truncate_text(msg.content, max_length=200)
                        recent_items.append(f"**{role}**: {content}")
                    if recent_items:
                        parts.append(format_context_section("Recent Conversation", recent_items))
            except Exception as e:
                logger.debug(f"Error getting conversation: {e}")

            # Semantically relevant past messages
            try:
                relevant = await self._client.short_term.search_messages(
                    query=query,
                    session_id=self._session_id,
                    limit=self._max_context_items // 2,
                    threshold=self._similarity_threshold,
                )
                if relevant:
                    relevant_items = []
                    for msg in relevant:
                        role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                        content = truncate_text(msg.content, max_length=150)
                        score = msg.metadata.get("similarity", 0) if msg.metadata else 0
                        relevant_items.append(f"[{role}] {content} (relevance: {score:.2f})")
                    if relevant_items:
                        parts.append(
                            format_context_section("Relevant Past Messages", relevant_items)
                        )
            except Exception as e:
                logger.debug(f"Error searching messages: {e}")

            return "\n\n".join(parts) if parts else None

        async def _get_long_term_context(self, query: str) -> str | None:
            """Get long-term memory context (entities, preferences)."""
            parts: list[str] = []

            # User preferences
            try:
                preferences = await self._client.long_term.search_preferences(
                    query=query,
                    limit=self._max_context_items,
                )
                if preferences:
                    pref_items = []
                    for pref in preferences:
                        line = f"[{pref.category}] {pref.preference}"
                        if pref.context:
                            line += f" (when: {pref.context})"
                        pref_items.append(line)
                    if pref_items:
                        parts.append(format_context_section("User Preferences", pref_items))
            except Exception as e:
                logger.debug(f"Error searching preferences: {e}")

            # Relevant entities
            try:
                entities = await self._client.long_term.search_entities(
                    query=query,
                    limit=self._max_context_items,
                )
                if entities:
                    entity_items = []
                    for entity in entities:
                        # Get entity type
                        entity_type = (
                            entity.type.value if hasattr(entity.type, "value") else str(entity.type)
                        )
                        line = f"**{entity.display_name}** ({entity_type})"
                        if entity.description:
                            line += f": {truncate_text(entity.description, 100)}"
                        entity_items.append(line)
                    if entity_items:
                        parts.append(format_context_section("Relevant Knowledge", entity_items))
            except Exception as e:
                logger.debug(f"Error searching entities: {e}")

            return "\n\n".join(parts) if parts else None

        async def _get_reasoning_context(self, query: str) -> str | None:
            """Get reasoning memory context (similar past traces)."""
            try:
                traces = await self._client.reasoning.get_similar_traces(
                    task=query,
                    limit=self._max_context_items // 3,
                )

                if not traces:
                    return None

                trace_items = []
                for trace in traces:
                    item = f"**Task**: {truncate_text(trace.task, 100)}"
                    if trace.outcome:
                        item += f" | Outcome: {truncate_text(trace.outcome, 80)}"
                    if trace.success is not None:
                        status = "Success" if trace.success else "Failed"
                        item += f" | {status}"
                    trace_items.append(item)

                if trace_items:
                    return format_context_section("Similar Past Tasks", trace_items)

            except Exception as e:
                logger.debug(f"Error getting similar traces: {e}")

            return None

        async def _trigger_background_extraction(self) -> None:
            """Trigger background entity extraction without blocking."""
            if not self._extraction_queue:
                return

            # Clear queue (we'll use session-level extraction)
            self._extraction_queue.clear()

            async def extract_batch() -> None:
                try:
                    # Use session-level extraction
                    await self._client.short_term.extract_entities_from_session(
                        session_id=self._session_id,
                        batch_size=10,
                    )
                except Exception as e:
                    logger.debug(f"Background extraction error: {e}")

            # Fire and forget
            asyncio.create_task(extract_batch())


except ImportError:
    # Microsoft Agent Framework not installed
    pass
