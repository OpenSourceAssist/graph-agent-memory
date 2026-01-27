"""LlamaIndex memory integration."""

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

# Module-level executor for async operations
_executor: concurrent.futures.ThreadPoolExecutor | None = None


def _get_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Get or create the shared thread pool executor."""
    global _executor
    if _executor is None:
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    return _executor


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

            Uses a thread pool to run the coroutine in a separate thread
            with its own event loop, avoiding conflicts with any existing
            running event loop.
            """

            def run_in_thread():
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            executor = _get_executor()
            future = executor.submit(run_in_thread)
            return future.result(timeout=30)

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
                    # entity.type may be a string or enum
                    entity_type = (
                        entity.type.value if hasattr(entity.type, "value") else str(entity.type)
                    )
                    nodes.append(
                        TextNode(
                            text=text,
                            metadata={
                                "source": "long_term",
                                "entity_type": entity_type,
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
