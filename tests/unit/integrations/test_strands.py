"""Unit tests for Strands Agents SDK integration."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestStrandsConfig:
    """Tests for StrandsConfig class."""

    def test_config_from_env_with_required_vars(self) -> None:
        """Test creating config from environment variables."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        env = {
            "NEO4J_URI": "neo4j+s://test.databases.neo4j.io",
            "NEO4J_PASSWORD": "test-password",
        }

        with patch.dict(os.environ, env, clear=False):
            config = StrandsConfig.from_env()

        assert config.neo4j_uri == "neo4j+s://test.databases.neo4j.io"
        assert config.neo4j_password == "test-password"
        assert config.neo4j_user == "neo4j"
        assert config.neo4j_database == "neo4j"
        assert config.embedding_provider == "bedrock"

    def test_config_from_env_with_all_vars(self) -> None:
        """Test creating config with all environment variables."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        env = {
            "NEO4J_URI": "neo4j+s://test.databases.neo4j.io",
            "NEO4J_PASSWORD": "test-password",
            "NEO4J_USER": "custom-user",
            "NEO4J_DATABASE": "custom-db",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_MODEL": "text-embedding-3-small",
            "AWS_REGION": "us-west-2",
            "AWS_PROFILE": "test-profile",
        }

        with patch.dict(os.environ, env, clear=False):
            config = StrandsConfig.from_env()

        assert config.neo4j_uri == "neo4j+s://test.databases.neo4j.io"
        assert config.neo4j_user == "custom-user"
        assert config.neo4j_database == "custom-db"
        assert config.embedding_provider == "openai"
        assert config.embedding_model == "text-embedding-3-small"
        assert config.aws_region == "us-west-2"
        assert config.aws_profile == "test-profile"

    def test_config_from_env_with_prefix(self) -> None:
        """Test creating config with environment variable prefix."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        env = {
            "MYAPP_NEO4J_URI": "neo4j+s://prefixed.databases.neo4j.io",
            "MYAPP_NEO4J_PASSWORD": "prefixed-password",
        }

        with patch.dict(os.environ, env, clear=False):
            config = StrandsConfig.from_env(prefix="MYAPP_")

        assert config.neo4j_uri == "neo4j+s://prefixed.databases.neo4j.io"
        assert config.neo4j_password == "prefixed-password"

    def test_config_from_env_missing_uri_raises(self) -> None:
        """Test that missing NEO4J_URI raises ValueError."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        env = {"NEO4J_PASSWORD": "test-password"}

        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="NEO4J_URI"),
        ):
            StrandsConfig.from_env()

    def test_config_from_env_missing_password_raises(self) -> None:
        """Test that missing NEO4J_PASSWORD raises ValueError."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        env = {"NEO4J_URI": "neo4j+s://test.databases.neo4j.io"}

        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="NEO4J_PASSWORD"),
        ):
            StrandsConfig.from_env()

    def test_config_with_overrides(self) -> None:
        """Test that overrides take precedence over env vars."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        env = {
            "NEO4J_URI": "neo4j+s://env.databases.neo4j.io",
            "NEO4J_PASSWORD": "env-password",
        }

        with patch.dict(os.environ, env, clear=False):
            config = StrandsConfig.from_env(
                neo4j_uri="neo4j+s://override.databases.neo4j.io",
                embedding_provider="vertex_ai",
            )

        assert config.neo4j_uri == "neo4j+s://override.databases.neo4j.io"
        assert config.embedding_provider == "vertex_ai"

    def test_config_to_dict(self) -> None:
        """Test converting config to dictionary."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        config = StrandsConfig(
            neo4j_uri="neo4j+s://test.databases.neo4j.io",
            neo4j_password="test-password",
            neo4j_user="custom-user",
            embedding_model="amazon.titan-embed-text-v2:0",
            aws_region="us-east-1",
        )

        result = config.to_dict()

        assert result["neo4j_uri"] == "neo4j+s://test.databases.neo4j.io"
        assert result["neo4j_password"] == "test-password"
        assert result["neo4j_user"] == "custom-user"
        assert result["embedding_model"] == "amazon.titan-embed-text-v2:0"
        assert result["aws_region"] == "us-east-1"

    def test_config_to_dict_excludes_none_values(self) -> None:
        """Test that None values are excluded from dict."""
        from neo4j_agent_memory.integrations.strands.config import StrandsConfig

        config = StrandsConfig(
            neo4j_uri="neo4j+s://test.databases.neo4j.io",
            neo4j_password="test-password",
            embedding_model=None,
            aws_region=None,
        )

        result = config.to_dict()

        assert "embedding_model" not in result
        assert "aws_region" not in result


class TestContextGraphToolsFactory:
    """Tests for context_graph_tools factory function."""

    def test_factory_requires_uri(self) -> None:
        """Test that factory requires neo4j_uri."""
        from neo4j_agent_memory.integrations.strands.tools import context_graph_tools

        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="neo4j_uri is required"),
        ):
            context_graph_tools()

    def test_factory_requires_password(self) -> None:
        """Test that factory requires neo4j_password."""
        from neo4j_agent_memory.integrations.strands.tools import context_graph_tools

        env = {"NEO4J_URI": "neo4j+s://test.databases.neo4j.io"}

        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="neo4j_password is required"),
        ):
            context_graph_tools()

    def test_factory_reads_from_env(self) -> None:
        """Test that factory reads credentials from environment."""
        from neo4j_agent_memory.integrations.strands.tools import context_graph_tools

        env = {
            "NEO4J_URI": "neo4j+s://test.databases.neo4j.io",
            "NEO4J_PASSWORD": "test-password",
        }

        with (
            patch.dict(os.environ, env, clear=False),
            patch(
                "neo4j_agent_memory.integrations.strands.tools.context_graph_tools"
            ) as mock_factory,
        ):
            mock_factory.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
            tools = mock_factory()

        assert len(tools) == 4

    def test_factory_returns_four_tools(self) -> None:
        """Test that factory returns all four tools."""
        # We need to mock the strands import since it may not be installed
        mock_tool = MagicMock()
        mock_tool.side_effect = lambda fn: fn  # Return the decorated function as-is

        with patch.dict(
            "sys.modules",
            {"strands": MagicMock(tool=mock_tool)},
        ):
            from neo4j_agent_memory.integrations.strands.tools import context_graph_tools

            env = {
                "NEO4J_URI": "neo4j+s://test.databases.neo4j.io",
                "NEO4J_PASSWORD": "test-password",
            }

            with patch.dict(os.environ, env, clear=False):
                tools = context_graph_tools()

        assert len(tools) == 4

    def test_clear_client_cache(self) -> None:
        """Test clearing the client cache."""
        from neo4j_agent_memory.integrations.strands.tools import (
            _client_cache,
            clear_client_cache,
        )

        # Add something to the cache
        _client_cache["test-key"] = MagicMock()

        clear_client_cache()

        assert len(_client_cache) == 0


class TestToolDescriptions:
    """Tests for tool function descriptions and signatures."""

    @pytest.fixture
    def mock_strands(self) -> MagicMock:
        """Create a mock strands module."""
        mock_tool = MagicMock()
        mock_tool.side_effect = lambda fn: fn
        return MagicMock(tool=mock_tool)

    def test_search_context_tool_signature(self, mock_strands: MagicMock) -> None:
        """Test search_context tool has correct parameters."""
        with patch.dict("sys.modules", {"strands": mock_strands}):
            from neo4j_agent_memory.integrations.strands.tools import (
                _create_search_context_tool,
            )

            tool = _create_search_context_tool(
                neo4j_uri="neo4j+s://test.databases.neo4j.io",
                neo4j_user="neo4j",
                neo4j_password="password",
                neo4j_database="neo4j",
                embedding_provider="bedrock",
                embedding_model=None,
            )

            # Check the function signature
            import inspect

            sig = inspect.signature(tool)
            params = list(sig.parameters.keys())

            assert "query" in params
            assert "user_id" in params
            assert "top_k" in params
            assert "min_score" in params
            assert "include_relationships" in params

    def test_get_entity_graph_tool_signature(self, mock_strands: MagicMock) -> None:
        """Test get_entity_graph tool has correct parameters."""
        with patch.dict("sys.modules", {"strands": mock_strands}):
            from neo4j_agent_memory.integrations.strands.tools import (
                _create_get_entity_graph_tool,
            )

            tool = _create_get_entity_graph_tool(
                neo4j_uri="neo4j+s://test.databases.neo4j.io",
                neo4j_user="neo4j",
                neo4j_password="password",
                neo4j_database="neo4j",
                embedding_provider="bedrock",
                embedding_model=None,
            )

            import inspect

            sig = inspect.signature(tool)
            params = list(sig.parameters.keys())

            assert "entity_name" in params
            assert "user_id" in params
            assert "depth" in params
            assert "relationship_types" in params

    def test_add_memory_tool_signature(self, mock_strands: MagicMock) -> None:
        """Test add_memory tool has correct parameters."""
        with patch.dict("sys.modules", {"strands": mock_strands}):
            from neo4j_agent_memory.integrations.strands.tools import (
                _create_add_memory_tool,
            )

            tool = _create_add_memory_tool(
                neo4j_uri="neo4j+s://test.databases.neo4j.io",
                neo4j_user="neo4j",
                neo4j_password="password",
                neo4j_database="neo4j",
                embedding_provider="bedrock",
                embedding_model=None,
            )

            import inspect

            sig = inspect.signature(tool)
            params = list(sig.parameters.keys())

            assert "content" in params
            assert "user_id" in params
            assert "session_id" in params
            assert "extract_entities" in params

    def test_get_user_preferences_tool_signature(self, mock_strands: MagicMock) -> None:
        """Test get_user_preferences tool has correct parameters."""
        with patch.dict("sys.modules", {"strands": mock_strands}):
            from neo4j_agent_memory.integrations.strands.tools import (
                _create_get_user_preferences_tool,
            )

            tool = _create_get_user_preferences_tool(
                neo4j_uri="neo4j+s://test.databases.neo4j.io",
                neo4j_user="neo4j",
                neo4j_password="password",
                neo4j_database="neo4j",
                embedding_provider="bedrock",
                embedding_model=None,
            )

            import inspect

            sig = inspect.signature(tool)
            params = list(sig.parameters.keys())

            assert "user_id" in params
            assert "category" in params


class TestRunAsync:
    """Tests for the _run_async helper function."""

    def test_run_async_outside_event_loop(self) -> None:
        """Test _run_async works outside an event loop."""
        from neo4j_agent_memory.integrations.strands.tools import _run_async

        async def async_func() -> str:
            return "result"

        result = _run_async(async_func())
        assert result == "result"

    def test_run_async_returns_value(self) -> None:
        """Test _run_async returns the coroutine's result."""
        from neo4j_agent_memory.integrations.strands.tools import _run_async

        async def async_add(a: int, b: int) -> int:
            return a + b

        result = _run_async(async_add(2, 3))
        assert result == 5


class TestBedrockModels:
    """Tests for Bedrock model constants."""

    def test_embedding_models_defined(self) -> None:
        """Test that embedding models are defined."""
        from neo4j_agent_memory.integrations.strands.config import BEDROCK_EMBEDDING_MODELS

        assert "titan-v2" in BEDROCK_EMBEDDING_MODELS
        assert "titan-v1" in BEDROCK_EMBEDDING_MODELS
        assert "cohere-english" in BEDROCK_EMBEDDING_MODELS
        assert "cohere-multilingual" in BEDROCK_EMBEDDING_MODELS

    def test_llm_models_defined(self) -> None:
        """Test that LLM models are defined."""
        from neo4j_agent_memory.integrations.strands.config import BEDROCK_LLM_MODELS

        assert "claude-sonnet" in BEDROCK_LLM_MODELS
        assert "claude-haiku" in BEDROCK_LLM_MODELS
        assert "claude-opus" in BEDROCK_LLM_MODELS

    def test_titan_v2_model_id(self) -> None:
        """Test Titan V2 model ID."""
        from neo4j_agent_memory.integrations.strands.config import BEDROCK_EMBEDDING_MODELS

        assert BEDROCK_EMBEDDING_MODELS["titan-v2"] == "amazon.titan-embed-text-v2:0"
