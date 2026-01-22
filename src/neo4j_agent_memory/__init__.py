"""
Neo4j Agent Memory - A comprehensive memory system for AI agents.

This package provides a unified memory system for AI agents using Neo4j as the
persistence layer. It includes three types of memory:

- **Short-Term Memory**: Conversation history and experiences
- **Long-Term Memory**: Facts, preferences, and entities
- **Procedural Memory**: Reasoning traces and tool usage patterns

Example usage:
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from pydantic import SecretStr

    settings = MemorySettings(
        neo4j={"uri": "bolt://localhost:7687", "password": SecretStr("password")}
    )

    async with MemoryClient(settings) as client:
        # Add a message
        await client.short_term.add_message(
            session_id="user-123",
            role="user",
            content="Hi, I'm looking for Italian restaurants"
        )

        # Add a preference
        await client.long_term.add_preference(
            category="food",
            preference="I love Italian cuisine"
        )

        # Search memories
        results = await client.long_term.search_preferences("food preferences")

        # Get combined context for LLM
        context = await client.get_context("restaurant recommendation")
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from neo4j_agent_memory.config.settings import (
    EmbeddingConfig,
    EmbeddingProvider,
    ExtractionConfig,
    ExtractorType,
    LLMConfig,
    LLMProvider,
    MemoryConfig,
    MemorySettings,
    Neo4jConfig,
    ResolutionConfig,
    ResolverStrategy,
    SearchConfig,
)
from neo4j_agent_memory.core.exceptions import (
    ConfigurationError,
    ConnectionError,
    EmbeddingError,
    ExtractionError,
    MemoryError,
    NotConnectedError,
    ResolutionError,
    SchemaError,
)
from neo4j_agent_memory.core.memory import BaseMemory, MemoryEntry


class GraphNode(BaseModel):
    """A node in the memory graph for visualization."""

    id: str = Field(description="Node identifier")
    labels: list[str] = Field(description="Node labels (e.g., ['Message'], ['Entity'])")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphRelationship(BaseModel):
    """A relationship in the memory graph for visualization."""

    id: str = Field(description="Relationship identifier")
    type: str = Field(description="Relationship type (e.g., 'HAS_MESSAGE', 'MENTIONS')")
    from_node: str = Field(description="Source node ID")
    to_node: str = Field(description="Target node ID")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relationship properties")


class MemoryGraph(BaseModel):
    """Memory graph export for visualization."""

    nodes: list[GraphNode] = Field(default_factory=list, description="Graph nodes")
    relationships: list[GraphRelationship] = Field(
        default_factory=list, description="Graph relationships"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Export metadata (filters applied, counts, etc.)",
    )


from neo4j_agent_memory.graph.client import Neo4jClient
from neo4j_agent_memory.graph.schema import SchemaManager
from neo4j_agent_memory.memory.long_term import (
    Entity,
    EntityType,
    Fact,
    LongTermMemory,
    Preference,
    Relationship,
)
from neo4j_agent_memory.memory.procedural import (
    ProceduralMemory,
    ReasoningStep,
    ReasoningTrace,
    StreamingTraceRecorder,
    Tool,
    ToolCall,
    ToolCallStatus,
    ToolStats,
)
from neo4j_agent_memory.memory.short_term import (
    Conversation,
    ConversationSummary,
    Message,
    MessageRole,
    SessionInfo,
    ShortTermMemory,
)

__version__ = "0.1.0"

__all__ = [
    # Main client
    "MemoryClient",
    # Settings
    "MemorySettings",
    "Neo4jConfig",
    "EmbeddingConfig",
    "LLMConfig",
    "ExtractionConfig",
    "ResolutionConfig",
    "MemoryConfig",
    "SearchConfig",
    # Enums
    "EmbeddingProvider",
    "LLMProvider",
    "ExtractorType",
    "ResolverStrategy",
    "MessageRole",
    "EntityType",
    "ToolCallStatus",
    # Memory types
    "ShortTermMemory",
    "LongTermMemory",
    "ProceduralMemory",
    # Models - Short-term
    "Message",
    "Conversation",
    "ConversationSummary",
    "SessionInfo",
    # Models - Long-term
    "Entity",
    "Preference",
    "Fact",
    "Relationship",
    # Models - Procedural
    "ReasoningTrace",
    "ReasoningStep",
    "ToolCall",
    "ToolStats",
    "Tool",
    "StreamingTraceRecorder",
    # Base classes
    "BaseMemory",
    "MemoryEntry",
    # Graph
    "Neo4jClient",
    "SchemaManager",
    # Graph Export
    "GraphNode",
    "GraphRelationship",
    "MemoryGraph",
    # Exceptions
    "MemoryError",
    "ConnectionError",
    "SchemaError",
    "ExtractionError",
    "ResolutionError",
    "EmbeddingError",
    "ConfigurationError",
    "NotConnectedError",
]


class MemoryClient:
    """
    Main client for interacting with the Neo4j Agent Memory system.

    Provides unified access to all three memory types:
    - short_term: Conversation history and experiences
    - long_term: Facts, preferences, and entities
    - procedural: Reasoning traces and tool usage

    Example:
        async with MemoryClient(settings) as client:
            await client.short_term.add_message(...)
            await client.long_term.add_preference(...)
            context = await client.get_context(query)
    """

    def __init__(
        self,
        settings: MemorySettings | None = None,
        *,
        embedder=None,
        extractor=None,
        resolver=None,
    ):
        """
        Initialize the memory client.

        Args:
            settings: Memory settings (uses defaults if not provided)
            embedder: Optional embedder override (for testing)
            extractor: Optional extractor override (for testing)
            resolver: Optional resolver override (for testing)
        """
        self._settings = settings or MemorySettings()
        self._client: Neo4jClient | None = None
        self._schema_manager: SchemaManager | None = None
        self._embedder_override = embedder
        self._extractor_override = extractor
        self._resolver_override = resolver
        self._embedder = None
        self._extractor = None
        self._resolver = None

        # Memory instances (initialized on connect)
        self._short_term: ShortTermMemory | None = None
        self._long_term: LongTermMemory | None = None
        self._procedural: ProceduralMemory | None = None

    async def __aenter__(self) -> "MemoryClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """
        Connect to Neo4j and initialize memory stores.

        This sets up the database connection, creates necessary indexes
        and constraints, and initializes all memory type instances.
        """
        # Create Neo4j client
        self._client = Neo4jClient(self._settings.neo4j)
        await self._client.connect()

        # Set up schema
        self._schema_manager = SchemaManager(
            self._client,
            vector_dimensions=self._settings.embedding.dimensions,
        )
        await self._schema_manager.setup_all()

        # Initialize embedder (use override if provided)
        self._embedder = self._embedder_override or self._create_embedder()

        # Initialize extractor (use override if provided)
        self._extractor = self._extractor_override or self._create_extractor()

        # Initialize resolver (use override if provided)
        self._resolver = self._resolver_override or self._create_resolver()

        # Create memory instances
        self._short_term = ShortTermMemory(
            self._client,
            self._embedder,
            self._extractor,
        )
        self._long_term = LongTermMemory(
            self._client,
            self._embedder,
            self._extractor,
            self._resolver,
        )
        self._procedural = ProceduralMemory(
            self._client,
            self._embedder,
        )

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._client is not None and self._client.is_connected

    @property
    def short_term(self) -> ShortTermMemory:
        """
        Access short-term memory (conversations, messages).

        Returns:
            ShortTermMemory instance

        Raises:
            NotConnectedError: If client is not connected
        """
        if self._short_term is None:
            raise NotConnectedError("Client not connected. Use 'async with' or call connect().")
        return self._short_term

    @property
    def long_term(self) -> LongTermMemory:
        """
        Access long-term memory (entities, preferences, facts).

        Returns:
            LongTermMemory instance

        Raises:
            NotConnectedError: If client is not connected
        """
        if self._long_term is None:
            raise NotConnectedError("Client not connected. Use 'async with' or call connect().")
        return self._long_term

    @property
    def procedural(self) -> ProceduralMemory:
        """
        Access procedural memory (reasoning traces, tool usage).

        Returns:
            ProceduralMemory instance

        Raises:
            NotConnectedError: If client is not connected
        """
        if self._procedural is None:
            raise NotConnectedError("Client not connected. Use 'async with' or call connect().")
        return self._procedural

    @property
    def schema(self) -> SchemaManager:
        """
        Access schema manager for database schema operations.

        Returns:
            SchemaManager instance

        Raises:
            NotConnectedError: If client is not connected
        """
        if self._schema_manager is None:
            raise NotConnectedError("Client not connected. Use 'async with' or call connect().")
        return self._schema_manager

    async def get_context(
        self,
        query: str,
        *,
        session_id: str | None = None,
        include_short_term: bool = True,
        include_long_term: bool = True,
        include_procedural: bool = True,
        max_items: int = 10,
    ) -> str:
        """
        Get combined context from all memory types for an LLM prompt.

        This method searches across all memory types and formats the results
        into a context string suitable for including in LLM prompts.

        Args:
            query: The query to search for relevant context
            session_id: Optional session ID for short-term filtering
            include_short_term: Whether to include conversation history
            include_long_term: Whether to include facts and preferences
            include_procedural: Whether to include similar task traces
            max_items: Maximum items per memory type

        Returns:
            Formatted context string suitable for LLM prompts
        """
        parts = []

        if include_short_term:
            short_term_context = await self.short_term.get_context(
                query,
                session_id=session_id,
                max_messages=max_items,
            )
            if short_term_context:
                parts.append(f"## Conversation History\n{short_term_context}")

        if include_long_term:
            long_term_context = await self.long_term.get_context(
                query,
                max_items=max_items,
            )
            if long_term_context:
                parts.append(f"## Relevant Knowledge\n{long_term_context}")

        if include_procedural:
            procedural_context = await self.procedural.get_context(
                query,
                max_traces=max_items // 2,
            )
            if procedural_context:
                parts.append(f"## Similar Past Tasks\n{procedural_context}")

        return "\n\n".join(parts)

    async def get_stats(self) -> dict:
        """
        Get memory statistics.

        Returns:
            Dictionary with counts for each memory type
        """
        if self._client is None:
            raise NotConnectedError("Client not connected.")

        from neo4j_agent_memory.graph.queries import GET_MEMORY_STATS

        results = await self._client.execute_read(GET_MEMORY_STATS)
        if results:
            return results[0]
        return {
            "conversations": 0,
            "messages": 0,
            "entities": 0,
            "preferences": 0,
            "facts": 0,
            "traces": 0,
        }

    async def get_graph(
        self,
        *,
        memory_types: list[Literal["short_term", "long_term", "procedural"]] | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        include_embeddings: bool = False,
        limit: int = 1000,
    ) -> MemoryGraph:
        """
        Export memory graph for visualization.

        This method retrieves nodes and relationships from the memory graph,
        formatted for visualization libraries like NVL (Neo4j Visualization Library).

        Args:
            memory_types: Which memory types to include. Defaults to all.
                         Options: 'short_term', 'long_term', 'procedural'
            session_id: Filter by session ID (for short_term and procedural)
            since: Only include data created/updated after this time
            until: Only include data created/updated before this time
            include_embeddings: Whether to include embedding vectors in properties.
                              Set to False (default) for smaller payloads.
            limit: Maximum number of nodes to return per memory type

        Returns:
            MemoryGraph with nodes, relationships, and metadata
        """
        if self._client is None:
            raise NotConnectedError("Client not connected.")

        if memory_types is None:
            memory_types = ["short_term", "long_term", "procedural"]

        all_nodes: list[GraphNode] = []
        all_relationships: list[GraphRelationship] = []
        node_ids_seen: set[str] = set()

        params = {
            "session_id": session_id,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "include_embeddings": include_embeddings,
            "limit": limit,
        }

        # Fetch short-term memory graph
        if "short_term" in memory_types:
            try:
                results = await self._client.execute_read(
                    """
                    MATCH (c:Conversation)-[r:HAS_MESSAGE]->(m:Message)
                    WHERE ($session_id IS NULL OR c.session_id = $session_id)
                    WITH c, r, m
                    LIMIT $limit
                    RETURN c, r, m
                    """,
                    params,
                )
                for row in results:
                    conv = dict(row["c"])
                    msg = dict(row["m"])

                    # Add conversation node
                    if conv.get("id") and conv["id"] not in node_ids_seen:
                        props = {k: v for k, v in conv.items() if v is not None}
                        all_nodes.append(
                            GraphNode(
                                id=conv["id"],
                                labels=["Conversation"],
                                properties=props,
                            )
                        )
                        node_ids_seen.add(conv["id"])

                    # Add message node
                    if msg.get("id") and msg["id"] not in node_ids_seen:
                        props = {k: v for k, v in msg.items() if v is not None}
                        if not include_embeddings:
                            props.pop("embedding", None)
                        all_nodes.append(
                            GraphNode(
                                id=msg["id"],
                                labels=["Message"],
                                properties=props,
                            )
                        )
                        node_ids_seen.add(msg["id"])

                    # Add relationship
                    if conv.get("id") and msg.get("id"):
                        all_relationships.append(
                            GraphRelationship(
                                id=f"{conv['id']}->{msg['id']}",
                                type="HAS_MESSAGE",
                                from_node=conv["id"],
                                to_node=msg["id"],
                                properties={},
                            )
                        )
            except Exception:
                pass  # Skip if query fails

        # Fetch long-term memory graph
        if "long_term" in memory_types:
            try:
                results = await self._client.execute_read(
                    """
                    MATCH (e:Entity)
                    WITH e LIMIT $limit
                    OPTIONAL MATCH (e)-[r:RELATED_TO]-(e2:Entity)
                    RETURN e, r, e2
                    """,
                    {"limit": limit},
                )
                for row in results:
                    entity = dict(row["e"])

                    if entity.get("id") and entity["id"] not in node_ids_seen:
                        props = {k: v for k, v in entity.items() if v is not None}
                        if not include_embeddings:
                            props.pop("embedding", None)
                        all_nodes.append(
                            GraphNode(
                                id=entity["id"],
                                labels=["Entity"],
                                properties=props,
                            )
                        )
                        node_ids_seen.add(entity["id"])

                    if row.get("r") and row.get("e2"):
                        e2 = dict(row["e2"])
                        if e2.get("id") and e2["id"] not in node_ids_seen:
                            props = {k: v for k, v in e2.items() if v is not None}
                            if not include_embeddings:
                                props.pop("embedding", None)
                            all_nodes.append(
                                GraphNode(
                                    id=e2["id"],
                                    labels=["Entity"],
                                    properties=props,
                                )
                            )
                            node_ids_seen.add(e2["id"])

                        rel = dict(row["r"])
                        all_relationships.append(
                            GraphRelationship(
                                id=f"{entity['id']}->{e2['id']}",
                                type=rel.get("type", "RELATED_TO"),
                                from_node=entity["id"],
                                to_node=e2["id"],
                                properties={
                                    k: v for k, v in rel.items() if k != "type" and v is not None
                                },
                            )
                        )
            except Exception:
                pass

        # Fetch procedural memory graph
        if "procedural" in memory_types:
            try:
                results = await self._client.execute_read(
                    """
                    MATCH (rt:ReasoningTrace)
                    WHERE ($session_id IS NULL OR rt.session_id = $session_id)
                    WITH rt LIMIT $limit
                    OPTIONAL MATCH (rt)-[r1:HAS_STEP]->(rs:ReasoningStep)
                    OPTIONAL MATCH (rs)-[r2:USES_TOOL]->(tc:ToolCall)
                    RETURN rt, r1, rs, r2, tc
                    """,
                    params,
                )
                for row in results:
                    trace = dict(row["rt"])

                    if trace.get("id") and trace["id"] not in node_ids_seen:
                        props = {k: v for k, v in trace.items() if v is not None}
                        if not include_embeddings:
                            props.pop("task_embedding", None)
                        all_nodes.append(
                            GraphNode(
                                id=trace["id"],
                                labels=["ReasoningTrace"],
                                properties=props,
                            )
                        )
                        node_ids_seen.add(trace["id"])

                    if row.get("rs"):
                        step = dict(row["rs"])
                        if step.get("id") and step["id"] not in node_ids_seen:
                            props = {k: v for k, v in step.items() if v is not None}
                            if not include_embeddings:
                                props.pop("embedding", None)
                            all_nodes.append(
                                GraphNode(
                                    id=step["id"],
                                    labels=["ReasoningStep"],
                                    properties=props,
                                )
                            )
                            node_ids_seen.add(step["id"])

                        if trace.get("id") and step.get("id"):
                            all_relationships.append(
                                GraphRelationship(
                                    id=f"{trace['id']}->{step['id']}",
                                    type="HAS_STEP",
                                    from_node=trace["id"],
                                    to_node=step["id"],
                                    properties={},
                                )
                            )

                    if row.get("tc") and row.get("rs"):
                        tc = dict(row["tc"])
                        step = dict(row["rs"])
                        if tc.get("id") and tc["id"] not in node_ids_seen:
                            props = {k: v for k, v in tc.items() if v is not None}
                            all_nodes.append(
                                GraphNode(
                                    id=tc["id"],
                                    labels=["ToolCall"],
                                    properties=props,
                                )
                            )
                            node_ids_seen.add(tc["id"])

                        if step.get("id") and tc.get("id"):
                            all_relationships.append(
                                GraphRelationship(
                                    id=f"{step['id']}->{tc['id']}",
                                    type="USES_TOOL",
                                    from_node=step["id"],
                                    to_node=tc["id"],
                                    properties={},
                                )
                            )
            except Exception:
                pass

        return MemoryGraph(
            nodes=all_nodes,
            relationships=all_relationships,
            metadata={
                "memory_types": memory_types,
                "session_id": session_id,
                "since": since.isoformat() if since else None,
                "until": until.isoformat() if until else None,
                "include_embeddings": include_embeddings,
                "node_count": len(all_nodes),
                "relationship_count": len(all_relationships),
            },
        )

    def _create_embedder(self):
        """Create embedder based on settings."""
        config = self._settings.embedding

        if config.provider == EmbeddingProvider.OPENAI:
            from neo4j_agent_memory.embeddings.openai import OpenAIEmbedder

            return OpenAIEmbedder(
                model=config.model,
                api_key=config.api_key.get_secret_value() if config.api_key else None,
                dimensions=config.dimensions if config.dimensions != 1536 else None,
                batch_size=config.batch_size,
            )
        elif config.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            from neo4j_agent_memory.embeddings.sentence_transformers import (
                SentenceTransformerEmbedder,
            )

            return SentenceTransformerEmbedder(
                model_name=config.model,
                device=config.device,
            )
        else:
            return None

    def _create_extractor(self):
        """Create extractor based on settings.

        Uses the extraction factory to create the appropriate extractor
        based on configuration. Supports:
        - NONE: No extraction
        - LLM: LLM-based extraction (OpenAI)
        - SPACY: spaCy NER extraction (local)
        - GLINER: GLiNER zero-shot NER (local)
        - PIPELINE: Multi-stage pipeline combining multiple extractors
        """
        from neo4j_agent_memory.extraction.factory import create_extractor

        config = self._settings.extraction

        if config.extractor_type == ExtractorType.NONE:
            return None

        return create_extractor(
            extraction_config=config,
            schema_config=self._settings.schema,
            llm_config=self._settings.llm,
        )

    def _create_resolver(self):
        """Create resolver based on settings."""
        config = self._settings.resolution

        if config.strategy == ResolverStrategy.NONE:
            return None

        if config.strategy == ResolverStrategy.EXACT:
            from neo4j_agent_memory.resolution.exact import ExactMatchResolver

            return ExactMatchResolver()

        if config.strategy == ResolverStrategy.FUZZY:
            from neo4j_agent_memory.resolution.fuzzy import FuzzyMatchResolver

            return FuzzyMatchResolver(threshold=config.fuzzy_threshold)

        if config.strategy == ResolverStrategy.SEMANTIC:
            from neo4j_agent_memory.resolution.semantic import SemanticMatchResolver

            if self._embedder is None:
                return None
            return SemanticMatchResolver(
                self._embedder,
                threshold=config.semantic_threshold,
            )

        if config.strategy == ResolverStrategy.COMPOSITE:
            from neo4j_agent_memory.resolution.composite import CompositeResolver

            return CompositeResolver(
                embedder=self._embedder,
                exact_threshold=config.exact_threshold,
                fuzzy_threshold=config.fuzzy_threshold,
                semantic_threshold=config.semantic_threshold,
            )

        return None
