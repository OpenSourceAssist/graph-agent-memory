"""Unit tests for Hybrid Memory Provider integration."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestRoutingStrategy:
    """Tests for RoutingStrategy enum."""

    def test_routing_strategies_defined(self) -> None:
        """Test that all routing strategies are defined."""
        from neo4j_agent_memory.integrations.agentcore.hybrid import RoutingStrategy

        assert RoutingStrategy.AUTO == "auto"
        assert RoutingStrategy.EXPLICIT == "explicit"
        assert RoutingStrategy.ALL == "all"
        assert RoutingStrategy.SHORT_TERM_FIRST == "short_term_first"
        assert RoutingStrategy.LONG_TERM_FIRST == "long_term_first"


class TestHybridMemoryProvider:
    """Tests for HybridMemoryProvider class."""

    @pytest.fixture
    def mock_memory_client(self) -> MagicMock:
        """Create a mock MemoryClient."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client.reasoning = MagicMock()
        client._client = MagicMock()
        client.get_context = AsyncMock(return_value="Formatted context")

        # Setup default async mocks
        client.short_term.search_messages = AsyncMock(return_value=[])
        client.short_term.add_message = AsyncMock()
        client.long_term.search_entities = AsyncMock(return_value=[])
        client.long_term.search_preferences = AsyncMock(return_value=[])
        client._client.execute_read = AsyncMock(return_value=[])

        return client

    def test_provider_initialization(self, mock_memory_client: MagicMock) -> None:
        """Test HybridMemoryProvider initialization."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            namespace="test-ns",
            routing_strategy="auto",
            sync_entities=True,
        )

        assert provider.namespace == "test-ns"
        assert provider.routing_strategy.value == "auto"

    def test_provider_initialization_with_enum(self, mock_memory_client: MagicMock) -> None:
        """Test HybridMemoryProvider initialization with enum."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.EXPLICIT,
        )

        assert provider.routing_strategy == RoutingStrategy.EXPLICIT


class TestQueryAnalysis:
    """Tests for query analysis and routing."""

    @pytest.fixture
    def mock_memory_client(self) -> MagicMock:
        """Create a mock MemoryClient."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client._client = MagicMock()
        client.short_term.search_messages = AsyncMock(return_value=[])
        client.long_term.search_entities = AsyncMock(return_value=[])
        client.long_term.search_preferences = AsyncMock(return_value=[])
        return client

    def test_analyze_relationship_query(self, mock_memory_client: MagicMock) -> None:
        """Test analyzing a relationship query."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        # Relationship keywords should route to entity search
        types = provider._analyze_query("How is John connected to the project?")
        assert "entity" in types

        types = provider._analyze_query("What is the relationship between Alice and Bob?")
        assert "entity" in types

    def test_analyze_preference_query(self, mock_memory_client: MagicMock) -> None:
        """Test analyzing a preference query."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        types = provider._analyze_query("What are the user's preferences?")
        assert "preference" in types

        types = provider._analyze_query("Does the user prefer dark mode?")
        assert "preference" in types

    def test_analyze_short_term_query(self, mock_memory_client: MagicMock) -> None:
        """Test analyzing a short-term memory query."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        types = provider._analyze_query("What did the user say earlier?")
        assert "message" in types

        types = provider._analyze_query("In our recent conversation...")
        assert "message" in types

    def test_analyze_entity_query(self, mock_memory_client: MagicMock) -> None:
        """Test analyzing an entity query."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        types = provider._analyze_query("Who is John Smith?")
        assert "entity" in types

        types = provider._analyze_query("What organization does she work for?")
        assert "entity" in types

    def test_analyze_ambiguous_query(self, mock_memory_client: MagicMock) -> None:
        """Test analyzing an ambiguous query searches all types."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        # Query without clear keywords should search all
        types = provider._analyze_query("Find information about the topic")

        assert "message" in types
        assert "entity" in types
        assert "preference" in types


class TestRoutingStrategies:
    """Tests for different routing strategies."""

    @pytest.fixture
    def mock_memory_client(self) -> MagicMock:
        """Create a mock MemoryClient."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client._client = MagicMock()
        client.short_term.search_messages = AsyncMock(return_value=[])
        client.short_term.get_conversation = AsyncMock(return_value=MagicMock(messages=[]))
        client.long_term.search_entities = AsyncMock(return_value=[])
        client.long_term.search_preferences = AsyncMock(return_value=[])
        client._client.execute_read = AsyncMock(return_value=[])
        return client

    @pytest.mark.asyncio
    async def test_routing_strategy_auto(self, mock_memory_client: MagicMock) -> None:
        """Test auto routing strategy."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.AUTO,
        )

        result = await provider.search_memory("What did you say earlier?")

        # Should include routing strategy in filters
        assert result.filters_applied["routing_strategy"] == "auto"

    @pytest.mark.asyncio
    async def test_routing_strategy_all(self, mock_memory_client: MagicMock) -> None:
        """Test all routing strategy."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.ALL,
        )

        result = await provider.search_memory("test query")

        # Should search all types
        assert result.filters_applied["routing_strategy"] == "all"
        types_searched = result.filters_applied.get("memory_types_searched", [])
        assert "message" in types_searched
        assert "entity" in types_searched
        assert "preference" in types_searched

    @pytest.mark.asyncio
    async def test_routing_strategy_explicit(self, mock_memory_client: MagicMock) -> None:
        """Test explicit routing strategy."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.EXPLICIT,
        )

        result = await provider.search_memory(
            "test query",
            memory_types=["message"],
        )

        assert result.filters_applied["routing_strategy"] == "explicit"

    @pytest.mark.asyncio
    async def test_routing_strategy_short_term_first(self, mock_memory_client: MagicMock) -> None:
        """Test short_term_first routing strategy."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.SHORT_TERM_FIRST,
        )

        result = await provider.search_memory("test query")

        assert result.filters_applied["routing_strategy"] == "short_term_first"

    @pytest.mark.asyncio
    async def test_routing_strategy_long_term_first(self, mock_memory_client: MagicMock) -> None:
        """Test long_term_first routing strategy."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.LONG_TERM_FIRST,
        )

        result = await provider.search_memory("test query")

        assert result.filters_applied["routing_strategy"] == "long_term_first"


class TestMergeResults:
    """Tests for result merging."""

    @pytest.fixture
    def mock_memory_client(self) -> MagicMock:
        """Create a mock MemoryClient with results."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client._client = MagicMock()

        # Create mock message
        mock_message = MagicMock()
        mock_message.id = "msg-1"
        mock_message.content = "Test message"
        mock_message.role = MagicMock(value="user")
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {"similarity": 0.9}

        # Create mock entity
        mock_entity = MagicMock()
        mock_entity.id = "ent-1"
        mock_entity.display_name = "John Doe"
        mock_entity.type = MagicMock(value="PERSON")
        mock_entity.description = "A developer"

        # Create mock preference
        mock_preference = MagicMock()
        mock_preference.id = "pref-1"
        mock_preference.preference = "Prefers dark mode"
        mock_preference.category = "ui"
        mock_preference.context = None
        mock_preference.confidence = 0.85

        client.short_term.search_messages = AsyncMock(return_value=[mock_message])
        client.long_term.search_entities = AsyncMock(return_value=[mock_entity])
        client.long_term.search_preferences = AsyncMock(return_value=[mock_preference])
        client._client.execute_read = AsyncMock(return_value=[])

        return client

    @pytest.mark.asyncio
    async def test_merge_all_memory_types(self, mock_memory_client: MagicMock) -> None:
        """Test merging results from all memory types."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.ALL,
        )

        result = await provider.search_memory("test query")

        # Should have results from all types
        assert len(result.memories) == 3
        memory_types = {m.memory_type.value for m in result.memories}
        assert "message" in memory_types
        assert "entity" in memory_types
        assert "preference" in memory_types

    @pytest.mark.asyncio
    async def test_results_sorted_by_score(self, mock_memory_client: MagicMock) -> None:
        """Test that results are sorted by score."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.ALL,
        )

        result = await provider.search_memory("test query")

        # First result should have highest score (message with 0.9)
        assert result.memories[0].score == 0.9


class TestEntityRelationships:
    """Tests for entity relationship retrieval."""

    @pytest.fixture
    def mock_memory_client(self) -> MagicMock:
        """Create a mock MemoryClient."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client._client = MagicMock()
        client.short_term.search_messages = AsyncMock(return_value=[])
        client.long_term.search_entities = AsyncMock(return_value=[])
        client.long_term.search_preferences = AsyncMock(return_value=[])
        return client

    @pytest.mark.asyncio
    async def test_get_entity_relationships_found(self, mock_memory_client: MagicMock) -> None:
        """Test getting relationships for an existing entity."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        mock_memory_client._client.execute_read = AsyncMock(
            return_value=[
                {
                    "entity_name": "John Doe",
                    "entity_type": "PERSON",
                    "entity_description": "A developer",
                    "from_entity": "John Doe",
                    "relationship": "WORKS_AT",
                    "to_entity": "Acme Corp",
                },
                {
                    "entity_name": "John Doe",
                    "entity_type": "PERSON",
                    "entity_description": "A developer",
                    "from_entity": "John Doe",
                    "relationship": "KNOWS",
                    "to_entity": "Jane Smith",
                },
            ]
        )

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        result = await provider.get_entity_relationships("John Doe")

        assert result["found"] is True
        assert result["entity"]["name"] == "John Doe"
        assert len(result["relationships"]) == 2

    @pytest.mark.asyncio
    async def test_get_entity_relationships_not_found(self, mock_memory_client: MagicMock) -> None:
        """Test getting relationships for a non-existent entity."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        mock_memory_client._client.execute_read = AsyncMock(return_value=[])

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        result = await provider.get_entity_relationships("Unknown Entity")

        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_get_entity_relationships_with_types(self, mock_memory_client: MagicMock) -> None:
        """Test filtering relationships by type."""
        from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

        mock_memory_client._client.execute_read = AsyncMock(return_value=[])

        provider = HybridMemoryProvider(memory_client=mock_memory_client)

        await provider.get_entity_relationships(
            "John Doe",
            relationship_types=["WORKS_AT", "MANAGES"],
        )

        # Check that execute_read was called (query was executed)
        mock_memory_client._client.execute_read.assert_called_once()


class TestIncludeFilters:
    """Tests for include_* filters."""

    @pytest.fixture
    def mock_memory_client(self) -> MagicMock:
        """Create a mock MemoryClient."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client._client = MagicMock()
        client.short_term.search_messages = AsyncMock(return_value=[])
        client.long_term.search_entities = AsyncMock(return_value=[])
        client.long_term.search_preferences = AsyncMock(return_value=[])
        client._client.execute_read = AsyncMock(return_value=[])
        return client

    @pytest.mark.asyncio
    async def test_exclude_entities(self, mock_memory_client: MagicMock) -> None:
        """Test excluding entities from search."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.ALL,
        )

        await provider.search_memory(
            "test query",
            include_entities=False,
        )

        # Entity search should not be called
        mock_memory_client.long_term.search_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_exclude_preferences(self, mock_memory_client: MagicMock) -> None:
        """Test excluding preferences from search."""
        from neo4j_agent_memory.integrations.agentcore import (
            HybridMemoryProvider,
            RoutingStrategy,
        )

        provider = HybridMemoryProvider(
            memory_client=mock_memory_client,
            routing_strategy=RoutingStrategy.ALL,
        )

        await provider.search_memory(
            "test query",
            include_preferences=False,
        )

        # Preference search should not be called
        mock_memory_client.long_term.search_preferences.assert_not_called()
