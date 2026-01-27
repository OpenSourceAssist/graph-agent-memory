"""LlamaIndex memory integration."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

try:
    from llama_index.core.memory import BaseMemory
    from llama_index.core.schema import TextNode

    class Neo4jLlamaIndexMemory(BaseMemory):
        """
        LlamaIndex memory backed by Neo4j Agent Memory.

        Example:
            from neo4j_agent_memory import MemoryClient, MemorySettings
            from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

            async with MemoryClient(settings) as client:
                memory = Neo4jLlamaIndexMemory(
                    memory_client=client,
                    session_id="user-123"
                )
                # Use with LlamaIndex agent
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

        def _run_async(self, coro: Any) -> Any:
            """
            Run an async coroutine from sync context.

            Handles the case where we're already in an async context by
            scheduling the coroutine on the existing event loop.
            """
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                # We're in an async context - schedule on the existing loop
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                return future.result(timeout=30)
            else:
                # Not in async context - create a new loop
                return asyncio.run(coro)

        def get(self, input: str | None = None, **kwargs: Any) -> list[TextNode]:
            """
            Get memory nodes relevant to the input.

            Args:
                input: Optional query to find relevant memories
                **kwargs: Additional arguments

            Returns:
                List of TextNode objects
            """
            return self._run_async(self._get_async(input, **kwargs))

        async def _get_async(self, input: str | None = None, **kwargs: Any) -> list[TextNode]:
            """Async implementation of get."""
            nodes = []

            if input:
                # Semantic search across memories
                messages = await self._client.short_term.search_messages(input, limit=5)
                for msg in messages:
                    nodes.append(
                        TextNode(
                            text=msg.content,
                            metadata={
                                "source": "short_term",
                                "role": msg.role.value,
                                "id": str(msg.id),
                            },
                        )
                    )

                entities = await self._client.long_term.search_entities(input, limit=5)
                for entity in entities:
                    text = f"{entity.display_name}"
                    if entity.description:
                        text += f": {entity.description}"
                    nodes.append(
                        TextNode(
                            text=text,
                            metadata={
                                "source": "long_term",
                                "entity_type": entity.type.value,
                                "id": str(entity.id),
                            },
                        )
                    )
            else:
                # Get recent conversation
                conv = await self._client.short_term.get_conversation(self._session_id, limit=10)
                for msg in conv.messages:
                    nodes.append(
                        TextNode(
                            text=msg.content,
                            metadata={
                                "source": "short_term",
                                "role": msg.role.value,
                                "id": str(msg.id),
                            },
                        )
                    )

            return nodes

        def put(self, node: TextNode) -> None:
            """
            Store a node in memory.

            Args:
                node: TextNode to store
            """
            role = node.metadata.get("role", "user")
            self._run_async(self._client.short_term.add_message(self._session_id, role, node.text))

        def reset(self) -> None:
            """Reset memory for this session."""
            self._run_async(self._client.short_term.clear_session(self._session_id))

        def set(self, nodes: list[TextNode]) -> None:
            """
            Set memory to the given nodes, replacing existing content.

            Args:
                nodes: List of TextNode objects to store
            """
            # Reset and then add all nodes
            self.reset()
            for node in nodes:
                self.put(node)

        def get_all(self) -> list[TextNode]:
            """
            Get all memory nodes for this session.

            Returns:
                List of all TextNode objects in memory
            """
            # Delegate to get() with no query to get all recent messages
            return self.get(input=None)

        @classmethod
        def from_defaults(
            cls,
            memory_client: "MemoryClient",
            session_id: str,
            **kwargs: Any,  # noqa: ARG003 - required by base class signature
        ) -> "Neo4jLlamaIndexMemory":
            """
            Create a Neo4jLlamaIndexMemory instance with default settings.

            Args:
                memory_client: Neo4j Agent Memory client
                session_id: Session identifier
                **kwargs: Additional arguments (ignored)

            Returns:
                Neo4jLlamaIndexMemory instance
            """
            return cls(memory_client=memory_client, session_id=session_id)

except ImportError:
    # LlamaIndex not installed
    pass
