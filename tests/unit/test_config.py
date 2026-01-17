"""Unit tests for configuration."""

import pytest
from pydantic import SecretStr

from neo4j_agent_memory.config.settings import (
    EmbeddingConfig,
    EmbeddingProvider,
    ExtractionConfig,
    ExtractorType,
    LLMConfig,
    LLMProvider,
    MemorySettings,
    Neo4jConfig,
    ResolutionConfig,
    ResolverStrategy,
)


class TestNeo4jConfig:
    """Tests for Neo4j configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = Neo4jConfig(password=SecretStr("test"))

        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.database == "neo4j"
        assert config.max_connection_pool_size == 50

    def test_custom_values(self):
        """Test custom configuration values."""
        config = Neo4jConfig(
            uri="bolt://custom:7688",
            username="admin",
            password=SecretStr("secret"),
            database="mydb",
        )

        assert config.uri == "bolt://custom:7688"
        assert config.username == "admin"
        assert config.password.get_secret_value() == "secret"
        assert config.database == "mydb"


class TestEmbeddingConfig:
    """Tests for embedding configuration."""

    def test_default_values(self):
        """Test default embedding config."""
        config = EmbeddingConfig()

        assert config.provider == EmbeddingProvider.OPENAI
        assert config.model == "text-embedding-3-small"
        assert config.dimensions == 1536

    def test_sentence_transformers_config(self):
        """Test sentence transformers config."""
        config = EmbeddingConfig(
            provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
            model="all-MiniLM-L6-v2",
            dimensions=384,
            device="cuda",
        )

        assert config.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
        assert config.device == "cuda"


class TestExtractionConfig:
    """Tests for extraction configuration."""

    def test_default_values(self):
        """Test default extraction config."""
        config = ExtractionConfig()

        assert config.extractor_type == ExtractorType.LLM
        assert "PERSON" in config.entity_types
        assert config.extract_relations is True

    def test_gliner_config(self):
        """Test GLiNER extraction config."""
        config = ExtractionConfig(
            extractor_type=ExtractorType.GLINER,
            gliner_model="urchade/gliner_base",
            gliner_threshold=0.6,
        )

        assert config.extractor_type == ExtractorType.GLINER
        assert config.gliner_threshold == 0.6


class TestResolutionConfig:
    """Tests for resolution configuration."""

    def test_default_values(self):
        """Test default resolution config."""
        config = ResolutionConfig()

        assert config.strategy == ResolverStrategy.COMPOSITE
        assert config.fuzzy_threshold == 0.85
        assert config.semantic_threshold == 0.8

    def test_custom_thresholds(self):
        """Test custom thresholds."""
        config = ResolutionConfig(
            strategy=ResolverStrategy.FUZZY,
            fuzzy_threshold=0.9,
        )

        assert config.strategy == ResolverStrategy.FUZZY
        assert config.fuzzy_threshold == 0.9


class TestMemorySettings:
    """Tests for main settings class."""

    def test_minimal_settings(self):
        """Test creating settings with minimal config."""
        settings = MemorySettings(neo4j=Neo4jConfig(password=SecretStr("test")))

        assert settings.neo4j.password.get_secret_value() == "test"
        assert settings.embedding.provider == EmbeddingProvider.OPENAI

    def test_full_settings(self):
        """Test creating settings with full config."""
        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri="bolt://custom:7687",
                password=SecretStr("secret"),
            ),
            embedding=EmbeddingConfig(
                provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
                model="all-MiniLM-L6-v2",
            ),
            extraction=ExtractionConfig(
                extractor_type=ExtractorType.NONE,
            ),
            resolution=ResolutionConfig(
                strategy=ResolverStrategy.EXACT,
            ),
        )

        assert settings.neo4j.uri == "bolt://custom:7687"
        assert settings.embedding.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS
        assert settings.extraction.extractor_type == ExtractorType.NONE
        assert settings.resolution.strategy == ResolverStrategy.EXACT

    def test_from_dict(self):
        """Test creating settings from dictionary."""
        config_dict = {
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "password": "test",
            }
        }

        settings = MemorySettings.from_dict(config_dict)

        assert settings.neo4j.uri == "bolt://localhost:7687"
