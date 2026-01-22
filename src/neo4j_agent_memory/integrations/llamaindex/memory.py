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

        def get(self, input: str | None = None, **kwargs: Any) -> list[TextNode]:
            """
            Get memory nodes relevant to the input.

            Args:
                input: Optional query to find relevant memories
                **kwargs: Additional arguments

            Returns:
                List of TextNode objects
            """
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._get_async(input, **kwargs))
                    return future.result()
            else:
                return asyncio.run(self._get_async(input, **kwargs))

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
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            role = node.metadata.get("role", "user")

            if loop is not None:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._client.short_term.add_message(self._session_id, role, node.text),
                    )
                    future.result()
            else:
                asyncio.run(self._client.short_term.add_message(self._session_id, role, node.text))

        def reset(self) -> None:
            """Reset memory for this session."""
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._client.short_term.clear_session(self._session_id),
                    )
                    future.result()
            else:
                asyncio.run(self._client.short_term.clear_session(self._session_id))

except ImportError:
    # LlamaIndex not installed
    pass
