"""LlamaIndex memory integration."""

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

try:
    from llama_index.core.base.llms.types import ChatMessage, MessageRole
    from llama_index.core.memory import BaseMemory

    class Neo4jLlamaIndexMemory(BaseMemory):
        """
        LlamaIndex memory backed by Neo4j Agent Memory.

        Uses the current BaseMemory interface (ChatMessage-based).

        Example:
            from neo4j_agent_memory import MemoryClient, MemorySettings
            from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

            async with MemoryClient(settings) as client:
                memory = Neo4jLlamaIndexMemory(
                    memory_client=client,
                    session_id="user-123"
                )
                # Use with LlamaIndex agent
                response = await agent.run("Hello!", memory=memory)
        """

        def __init__(
            self,
            memory_client: "MemoryClient",
            session_id: str,
        ):
            """
            Initialize LlamaIndex memory.

            Args:
                memory_client: Neo4j Agent Memory client
                session_id: Session identifier
            """
            self._client = memory_client
            self._session_id = session_id

            # Capture the event loop the neo4j client was created on.
            # All async neo4j operations must run on this loop.
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

        def _run_async(self, coro: Any) -> Any:
            """
            Run an async coroutine from sync context.

            The neo4j async driver binds its resources to the event loop it
            was created on, so we must never run coroutines on a *different*
            loop.

            - **Same thread as the original loop** (Jupyter / notebook): use
              nest_asyncio to allow a reentrant run_until_complete().
            - **Different thread** (FastAPI background task, thread-pool
              dispatch, etc.): schedule on the original loop with
              run_coroutine_threadsafe().
            - **No original loop** (client was created synchronously): fall
              back to asyncio.run().
            """
            if self._loop is None or self._loop.is_closed():
                return asyncio.run(coro)

            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None

            if running is self._loop:
                # Same thread as the running loop (e.g. Jupyter)
                import nest_asyncio

                nest_asyncio.apply()
                return self._loop.run_until_complete(coro)

            # Different thread — schedule on the original loop
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result(timeout=30)

        @staticmethod
        def _parse_role(role_value: str) -> MessageRole:
            """Convert a role string to MessageRole enum."""
            try:
                return MessageRole(role_value)
            except ValueError:
                return MessageRole.USER

        # ------------------------------------------------------------------
        # Sync interface
        # ------------------------------------------------------------------

        def get(self, input: str | None = None, **kwargs: Any) -> list[ChatMessage]:
            """
            Get memory messages relevant to the input.

            Args:
                input: Optional query to find relevant memories.
                       If None, returns recent conversation history.
                **kwargs: Additional arguments.

            Returns:
                List of ChatMessage objects.
            """
            return self._run_async(self.aget(input, **kwargs))

        def put(self, message: ChatMessage) -> None:
            """
            Store a ChatMessage in memory.

            Args:
                message: ChatMessage to store.
            """
            self._run_async(self.aput(message))

        def get_all(self) -> list[ChatMessage]:
            """
            Get all memory messages for this session.

            Returns:
                List of all ChatMessage objects in memory.
            """
            return self._run_async(self.aget_all())

        def set(self, messages: list[ChatMessage]) -> None:
            """
            Set memory to the given messages, replacing existing content.

            Args:
                messages: List of ChatMessage objects to store.
            """
            self._run_async(self.aset(messages))

        def reset(self) -> None:
            """Reset memory for this session."""
            self._run_async(self.areset())

        def put_messages(self, messages: list[ChatMessage]) -> None:
            """
            Store multiple ChatMessages in memory.

            Args:
                messages: List of ChatMessage objects to store.
            """
            for msg in messages:
                self.put(msg)

        # ------------------------------------------------------------------
        # Async interface
        # ------------------------------------------------------------------

        async def aget(self, input: str | None = None, **kwargs: Any) -> list[ChatMessage]:
            """
            Async: get memory messages relevant to the input.

            Args:
                input: Optional query to find relevant memories.
                **kwargs: Additional arguments.

            Returns:
                List of ChatMessage objects.
            """
            messages: list[ChatMessage] = []

            if input:
                # Semantic search across short-term memories
                short_term_results = await self._client.short_term.search_messages(input, limit=5)
                for msg in short_term_results:
                    role_str = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                    messages.append(
                        ChatMessage(
                            role=self._parse_role(role_str),
                            content=msg.content,
                            additional_kwargs={
                                "source": "short_term",
                                "id": str(msg.id),
                            },
                        )
                    )

                # Semantic search across long-term entities
                entities = await self._client.long_term.search_entities(input, limit=5)
                for entity in entities:
                    text = entity.display_name
                    if entity.description:
                        text += f": {entity.description}"
                    entity_type = (
                        entity.type.value if hasattr(entity.type, "value") else str(entity.type)
                    )
                    # Inject entity knowledge as system messages
                    messages.append(
                        ChatMessage(
                            role=MessageRole.SYSTEM,
                            content=text,
                            additional_kwargs={
                                "source": "long_term",
                                "entity_type": entity_type,
                                "id": str(entity.id),
                            },
                        )
                    )
            else:
                # Return recent conversation history
                conv = await self._client.short_term.get_conversation(self._session_id, limit=10)
                for msg in conv.messages:
                    role_str = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                    messages.append(
                        ChatMessage(
                            role=self._parse_role(role_str),
                            content=msg.content,
                            additional_kwargs={
                                "source": "short_term",
                                "id": str(msg.id),
                            },
                        )
                    )

            return messages

        async def aput(self, message: ChatMessage) -> None:
            """
            Async: store a ChatMessage in memory.

            Args:
                message: ChatMessage to store.
            """
            role_str = message.role.value if hasattr(message.role, "value") else str(message.role)
            await self._client.short_term.add_message(self._session_id, role_str, message.content)

        async def aget_all(self) -> list[ChatMessage]:
            """
            Async: get all memory messages for this session.

            Returns:
                List of all ChatMessage objects in memory.
            """
            return await self.aget(input=None)

        async def aset(self, messages: list[ChatMessage]) -> None:
            """
            Async: set memory to the given messages, replacing existing content.

            Args:
                messages: List of ChatMessage objects to store.
            """
            await self.areset()
            for msg in messages:
                await self.aput(msg)

        async def areset(self) -> None:
            """Async: reset memory for this session."""
            await self._client.short_term.clear_session(self._session_id)

        @classmethod
        def from_defaults(
            cls,
            memory_client: "MemoryClient",
            session_id: str,
        ) -> "Neo4jLlamaIndexMemory":
            """
            Create a Neo4jLlamaIndexMemory instance with default settings.

            Args:
                memory_client: Neo4j Agent Memory client.
                session_id: Session identifier.
                **kwargs: Additional arguments (ignored).

            Returns:
                Neo4jLlamaIndexMemory instance.
            """
            return cls(memory_client=memory_client, session_id=session_id)

except ImportError:
    # LlamaIndex not installed
    pass
