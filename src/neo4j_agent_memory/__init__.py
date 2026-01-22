"""
Neo4j Agent Memory - A comprehensive memory system for AI agents.

This package provides a unified memory system for AI agents using Neo4j as the
persistence layer. It includes three types of memory:

- **Episodic Memory**: Conversation history and experiences
- **Semantic Memory**: Facts, preferences, and entities
- **Procedural Memory**: Reasoning traces and tool usage patterns

Example usage:
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from pydantic import SecretStr

    settings = MemorySettings(
        neo4j={"uri": "bolt://localhost:7687", "password": SecretStr("password")}
    )

    async with MemoryClient(settings) as client:
        # Add a message
        await client.episodic.add_message(
            session_id="user-123",
            role="user",
            content="Hi, I'm looking for Italian restaurants"
        )

        # Add a preference
        await client.semantic.add_preference(
            category="food",
            preference="I love Italian cuisine"
        )

        # Search memories
        results = await client.semantic.search_preferences("food preferences")

        # Get combined context for LLM
        context = await client.get_context("restaurant recommendation")
"""

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
from neo4j_agent_memory.graph.client import Neo4jClient
from neo4j_agent_memory.graph.schema import SchemaManager
from neo4j_agent_memory.memory.episodic import (
    Conversation,
    EpisodicMemory,
    Message,
    MessageRole,
)
from neo4j_agent_memory.memory.procedural import (
    ProceduralMemory,
    ReasoningStep,
    ReasoningTrace,
    Tool,
    ToolCall,
    ToolCallStatus,
)
from neo4j_agent_memory.memory.semantic import (
    Entity,
    EntityType,
    Fact,
    Preference,
    Relationship,
    SemanticMemory,
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
    "EpisodicMemory",
    "SemanticMemory",
    "ProceduralMemory",
    # Models - Episodic
    "Message",
    "Conversation",
    # Models - Semantic
    "Entity",
    "Preference",
    "Fact",
    "Relationship",
    # Models - Procedural
    "ReasoningTrace",
    "ReasoningStep",
    "ToolCall",
    "Tool",
    # Base classes
    "BaseMemory",
    "MemoryEntry",
    # Graph
    "Neo4jClient",
    "SchemaManager",
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
    - episodic: Conversation history and experiences
    - semantic: Facts, preferences, and entities
    - procedural: Reasoning traces and tool usage

    Example:
        async with MemoryClient(settings) as client:
            await client.episodic.add_message(...)
            await client.semantic.add_preference(...)
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
        self._episodic: EpisodicMemory | None = None
        self._semantic: SemanticMemory | None = None
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
        self._episodic = EpisodicMemory(
            self._client,
            self._embedder,
            self._extractor,
        )
        self._semantic = SemanticMemory(
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
    def episodic(self) -> EpisodicMemory:
        """
        Access episodic memory (conversations, messages).

        Returns:
            EpisodicMemory instance

        Raises:
            NotConnectedError: If client is not connected
        """
        if self._episodic is None:
            raise NotConnectedError("Client not connected. Use 'async with' or call connect().")
        return self._episodic

    @property
    def semantic(self) -> SemanticMemory:
        """
        Access semantic memory (entities, preferences, facts).

        Returns:
            SemanticMemory instance

        Raises:
            NotConnectedError: If client is not connected
        """
        if self._semantic is None:
            raise NotConnectedError("Client not connected. Use 'async with' or call connect().")
        return self._semantic

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
        include_episodic: bool = True,
        include_semantic: bool = True,
        include_procedural: bool = True,
        max_items: int = 10,
    ) -> str:
        """
        Get combined context from all memory types for an LLM prompt.

        This method searches across all memory types and formats the results
        into a context string suitable for including in LLM prompts.

        Args:
            query: The query to search for relevant context
            session_id: Optional session ID for episodic filtering
            include_episodic: Whether to include conversation history
            include_semantic: Whether to include facts and preferences
            include_procedural: Whether to include similar task traces
            max_items: Maximum items per memory type

        Returns:
            Formatted context string suitable for LLM prompts
        """
        parts = []

        if include_episodic:
            episodic_context = await self.episodic.get_context(
                query,
                session_id=session_id,
                max_messages=max_items,
            )
            if episodic_context:
                parts.append(f"## Conversation History\n{episodic_context}")

        if include_semantic:
            semantic_context = await self.semantic.get_context(
                query,
                max_items=max_items,
            )
            if semantic_context:
                parts.append(f"## Relevant Knowledge\n{semantic_context}")

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
