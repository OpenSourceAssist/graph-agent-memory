"""Configuration settings for neo4j-agent-memory."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    CUSTOM = "custom"


class LLMProvider(str, Enum):
    """Supported LLM providers for extraction."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ExtractorType(str, Enum):
    """Supported entity extractor types."""

    LLM = "llm"
    GLINER = "gliner"
    NONE = "none"


class ResolverStrategy(str, Enum):
    """Supported entity resolution strategies."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    COMPOSITE = "composite"
    NONE = "none"


class Neo4jConfig(BaseModel):
    """Neo4j connection configuration."""

    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: SecretStr = Field(description="Neo4j password")
    database: str = Field(default="neo4j", description="Neo4j database name")
    max_connection_pool_size: int = Field(
        default=50, ge=1, description="Maximum connection pool size"
    )
    connection_timeout: float = Field(
        default=30.0, gt=0, description="Connection timeout in seconds"
    )
    max_transaction_retry_time: float = Field(
        default=30.0, gt=0, description="Maximum transaction retry time in seconds"
    )


class EmbeddingConfig(BaseModel):
    """Embedding provider configuration."""

    provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OPENAI, description="Embedding provider to use"
    )
    model: str = Field(default="text-embedding-3-small", description="Embedding model name")
    dimensions: int = Field(default=1536, ge=1, description="Embedding dimensions")
    api_key: SecretStr | None = Field(default=None, description="API key for embedding provider")
    batch_size: int = Field(default=100, ge=1, description="Batch size for embeddings")
    # Sentence Transformers specific
    device: str = Field(default="cpu", description="Device for sentence transformers (cpu/cuda)")


class LLMConfig(BaseModel):
    """LLM provider configuration for extraction."""

    provider: LLMProvider = Field(default=LLMProvider.OPENAI, description="LLM provider to use")
    model: str = Field(default="gpt-4o-mini", description="LLM model name")
    api_key: SecretStr | None = Field(default=None, description="API key for LLM provider")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens for LLM")


class ExtractionConfig(BaseModel):
    """Entity extraction configuration."""

    extractor_type: ExtractorType = Field(
        default=ExtractorType.LLM, description="Type of entity extractor"
    )
    entity_types: list[str] = Field(
        default=[
            "PERSON",
            "ORGANIZATION",
            "LOCATION",
            "EVENT",
            "CONCEPT",
            "PREFERENCE",
        ],
        description="Entity types to extract",
    )
    extract_relations: bool = Field(default=True, description="Whether to extract relations")
    extract_preferences: bool = Field(default=True, description="Whether to extract preferences")
    confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )
    # GLiNER specific
    gliner_model: str = Field(default="urchade/gliner_base", description="GLiNER model name")
    gliner_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="GLiNER confidence threshold"
    )


class ResolutionConfig(BaseModel):
    """Entity resolution configuration."""

    strategy: ResolverStrategy = Field(
        default=ResolverStrategy.COMPOSITE, description="Resolution strategy"
    )
    exact_threshold: float = Field(default=1.0, ge=0.0, le=1.0, description="Exact match threshold")
    fuzzy_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Fuzzy match threshold"
    )
    semantic_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Semantic match threshold"
    )
    fuzzy_scorer: str = Field(default="token_sort_ratio", description="Fuzzy matching scorer")


class MemoryConfig(BaseModel):
    """Memory behavior configuration."""

    # Episodic memory
    default_conversation_limit: int = Field(
        default=50, ge=1, description="Default conversation message limit"
    )
    message_embedding_enabled: bool = Field(default=True, description="Enable message embeddings")
    # Semantic memory
    preference_confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Preference confidence threshold"
    )
    fact_deduplication_enabled: bool = Field(default=True, description="Enable fact deduplication")
    # Procedural memory
    trace_embedding_enabled: bool = Field(
        default=True, description="Enable reasoning trace embeddings"
    )
    tool_stats_enabled: bool = Field(default=True, description="Enable tool usage statistics")


class SearchConfig(BaseModel):
    """Search configuration."""

    default_limit: int = Field(default=10, ge=1, description="Default search limit")
    default_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Default similarity threshold"
    )
    hybrid_search_enabled: bool = Field(default=True, description="Enable hybrid search")
    graph_depth: int = Field(default=2, ge=1, description="Graph traversal depth for search")


class MemorySettings(BaseSettings):
    """
    Main configuration class for neo4j-agent-memory.

    Configuration can be loaded from:
    - Environment variables (prefixed with NAM_)
    - .env files
    - Direct instantiation

    Example:
        settings = MemorySettings(
            neo4j=Neo4jConfig(password=SecretStr("password"))
        )
    """

    model_config = SettingsConfigDict(
        env_prefix="NAM_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    neo4j: Neo4jConfig = Field(default_factory=lambda: Neo4jConfig(password=SecretStr("")))
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    resolution: ResolutionConfig = Field(default_factory=ResolutionConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "MemorySettings":
        """Create settings from a dictionary."""
        return cls(**config)
