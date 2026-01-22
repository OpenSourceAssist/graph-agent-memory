"""Neo4j schema management for indexes and constraints."""

from typing import TYPE_CHECKING

from neo4j_agent_memory.core.exceptions import SchemaError

if TYPE_CHECKING:
    from neo4j_agent_memory.graph.client import Neo4jClient


# Default vector dimensions
DEFAULT_VECTOR_DIMENSIONS = 1536


class SchemaManager:
    """
    Manages Neo4j schema for agent memory.

    Handles creation of indexes and constraints for all memory types.
    """

    def __init__(
        self,
        client: "Neo4jClient",
        *,
        vector_dimensions: int = DEFAULT_VECTOR_DIMENSIONS,
    ):
        """
        Initialize schema manager.

        Args:
            client: Neo4j client
            vector_dimensions: Dimensions for vector indexes
        """
        self._client = client
        self._vector_dimensions = vector_dimensions

    async def setup_all(self) -> None:
        """Set up all indexes and constraints."""
        await self.setup_constraints()
        await self.setup_indexes()
        await self.setup_vector_indexes()

    async def setup_constraints(self) -> None:
        """Create unique constraints for all node types."""
        constraints = [
            # Short-term memory
            ("conversation_id", "Conversation", "id"),
            ("message_id", "Message", "id"),
            # Long-term memory
            ("entity_id", "Entity", "id"),
            ("preference_id", "Preference", "id"),
            ("fact_id", "Fact", "id"),
            # Procedural memory
            ("reasoning_trace_id", "ReasoningTrace", "id"),
            ("reasoning_step_id", "ReasoningStep", "id"),
            ("tool_name", "Tool", "name"),
            ("tool_call_id", "ToolCall", "id"),
        ]

        for constraint_name, label, property_name in constraints:
            await self._create_constraint(constraint_name, label, property_name)

    async def setup_indexes(self) -> None:
        """Create regular indexes for common queries."""
        indexes = [
            # Short-term memory
            ("conversation_session_idx", "Conversation", "session_id"),
            ("message_timestamp_idx", "Message", "timestamp"),
            ("message_role_idx", "Message", "role"),
            # Long-term memory
            ("entity_type_idx", "Entity", "type"),
            ("entity_name_idx", "Entity", "name"),
            ("entity_canonical_idx", "Entity", "canonical_name"),
            ("preference_category_idx", "Preference", "category"),
            # Procedural memory
            ("trace_session_idx", "ReasoningTrace", "session_id"),
            ("trace_success_idx", "ReasoningTrace", "success"),
            ("tool_call_status_idx", "ToolCall", "status"),
        ]

        for index_name, label, property_name in indexes:
            await self._create_index(index_name, label, property_name)

    async def setup_vector_indexes(self) -> None:
        """Create vector indexes for semantic search."""
        vector_indexes = [
            ("message_embedding_idx", "Message", "embedding"),
            ("entity_embedding_idx", "Entity", "embedding"),
            ("preference_embedding_idx", "Preference", "embedding"),
            ("fact_embedding_idx", "Fact", "embedding"),
            ("task_embedding_idx", "ReasoningTrace", "task_embedding"),
        ]

        for index_name, label, property_name in vector_indexes:
            await self._create_vector_index(index_name, label, property_name)

    async def _create_constraint(
        self,
        constraint_name: str,
        label: str,
        property_name: str,
    ) -> None:
        """Create a unique constraint if it doesn't exist."""
        try:
            exists = await self._client.check_constraint_exists(constraint_name)
            if exists:
                return

            query = f"""
            CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
            FOR (n:{label})
            REQUIRE n.{property_name} IS UNIQUE
            """
            await self._client.execute_write(query)
        except Exception as e:
            raise SchemaError(f"Failed to create constraint {constraint_name}: {e}") from e

    async def _create_index(
        self,
        index_name: str,
        label: str,
        property_name: str,
    ) -> None:
        """Create a regular index if it doesn't exist."""
        try:
            exists = await self._client.check_index_exists(index_name)
            if exists:
                return

            query = f"""
            CREATE INDEX {index_name} IF NOT EXISTS
            FOR (n:{label})
            ON (n.{property_name})
            """
            await self._client.execute_write(query)
        except Exception as e:
            raise SchemaError(f"Failed to create index {index_name}: {e}") from e

    async def _create_vector_index(
        self,
        index_name: str,
        label: str,
        property_name: str,
    ) -> None:
        """Create a vector index if it doesn't exist."""
        try:
            exists = await self._client.check_index_exists(index_name)
            if exists:
                return

            query = f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS
            FOR (n:{label})
            ON (n.{property_name})
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {self._vector_dimensions},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """
            await self._client.execute_write(query)
        except Exception as e:
            # Vector indexes require Neo4j 5.11+, log warning but don't fail
            # as the package can still work without vector search
            pass

    async def drop_all(self) -> None:
        """Drop all memory-related indexes and constraints."""
        # Get all constraints
        constraints = await self._client.execute_read("SHOW CONSTRAINTS YIELD name RETURN name")
        for constraint in constraints:
            name = constraint["name"]
            if self._is_memory_schema(name):
                await self._client.execute_write(f"DROP CONSTRAINT {name} IF EXISTS")

        # Get all indexes
        indexes = await self._client.execute_read("SHOW INDEXES YIELD name RETURN name")
        for index in indexes:
            name = index["name"]
            if self._is_memory_schema(name):
                await self._client.execute_write(f"DROP INDEX {name} IF EXISTS")

    def _is_memory_schema(self, name: str) -> bool:
        """Check if a schema element belongs to agent memory."""
        memory_prefixes = [
            "conversation_",
            "message_",
            "entity_",
            "preference_",
            "fact_",
            "reasoning_",
            "trace_",
            "tool_",
            "task_",
        ]
        return any(name.startswith(prefix) for prefix in memory_prefixes)

    async def get_schema_info(self) -> dict:
        """Get information about the current schema."""
        constraints = await self._client.execute_read(
            "SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN *"
        )
        indexes = await self._client.execute_read(
            "SHOW INDEXES YIELD name, type, labelsOrTypes, properties RETURN *"
        )

        return {
            "constraints": [
                {
                    "name": c["name"],
                    "type": c["type"],
                    "labels": c["labelsOrTypes"],
                    "properties": c["properties"],
                }
                for c in constraints
                if self._is_memory_schema(c["name"])
            ],
            "indexes": [
                {
                    "name": i["name"],
                    "type": i["type"],
                    "labels": i["labelsOrTypes"],
                    "properties": i["properties"],
                }
                for i in indexes
                if self._is_memory_schema(i["name"])
            ],
        }
