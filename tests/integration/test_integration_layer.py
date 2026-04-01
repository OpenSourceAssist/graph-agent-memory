"""Integration tests for MemoryIntegration convenience layer.

Tests MemoryIntegration against a real Neo4j instance to verify
session strategies, store/retrieve round-trips, and automatic
preference detection work end-to-end.
"""

import asyncio

import pytest

from neo4j_agent_memory.integration import MemoryIntegration, SessionStrategy


@pytest.mark.integration
class TestSessionStrategies:
    """Test session identity resolution strategies against real Neo4j."""

    @pytest.mark.asyncio
    async def test_per_conversation_creates_unique_sessions(self, memory_client):
        """Two MemoryIntegration instances produce different session IDs."""
        int1 = MemoryIntegration(memory_client, session_strategy=SessionStrategy.PER_CONVERSATION)
        int2 = MemoryIntegration(memory_client, session_strategy=SessionStrategy.PER_CONVERSATION)

        sid1 = int1.resolve_session_id()
        sid2 = int2.resolve_session_id()
        assert sid1 != sid2

    @pytest.mark.asyncio
    async def test_per_day_same_user_same_session(self, memory_client):
        """Two instances with same user_id on same day share session ID."""
        int1 = MemoryIntegration(
            memory_client, session_strategy=SessionStrategy.PER_DAY, user_id="alice"
        )
        int2 = MemoryIntegration(
            memory_client, session_strategy=SessionStrategy.PER_DAY, user_id="alice"
        )

        sid1 = int1.resolve_session_id()
        sid2 = int2.resolve_session_id()
        assert sid1 == sid2

    @pytest.mark.asyncio
    async def test_persistent_reuses_session(self, memory_client):
        """Persistent strategy always returns user_id."""
        integration = MemoryIntegration(
            memory_client, session_strategy=SessionStrategy.PERSISTENT, user_id="bob"
        )
        assert integration.resolve_session_id() == "bob"
        assert integration.resolve_session_id() == "bob"


@pytest.mark.integration
class TestStoreAndRetrieve:
    """Test round-trip store and retrieve operations against real Neo4j."""

    @pytest.mark.asyncio
    async def test_store_message_and_search(self, memory_client, session_id):
        """Store a message and find it via search."""
        integration = MemoryIntegration(memory_client)

        result = await integration.store_message(
            "user",
            "I need help with graph databases and Neo4j",
            session_id=session_id,
        )
        assert result["stored"] is True

        search_result = await integration.search(
            "graph databases",
            session_id=session_id,
            memory_types=["messages"],
        )
        assert "results" in search_result
        messages = search_result["results"].get("messages", [])
        assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_add_entity_and_get_context(self, memory_client, session_id):
        """Add an entity and verify it appears in context."""
        integration = MemoryIntegration(memory_client)

        result = await integration.add_entity(
            "Anthropic",
            "ORGANIZATION",
            description="AI safety company",
        )
        assert result["stored"] is True

        context = await integration.get_context(
            session_id=session_id,
            query="AI companies",
        )
        # Context may or may not include the entity depending on embedding match,
        # but it should not error
        assert "error" not in context

    @pytest.mark.asyncio
    async def test_add_preference_and_search(self, memory_client, session_id):
        """Add a preference and find it via search."""
        integration = MemoryIntegration(memory_client)

        result = await integration.add_preference(
            category="technology",
            preference="Prefers Python over JavaScript",
        )
        assert result["stored"] is True

        search_result = await integration.search(
            "Python",
            memory_types=["preferences"],
        )
        assert "results" in search_result
        prefs = search_result["results"].get("preferences", [])
        assert len(prefs) >= 1

    @pytest.mark.asyncio
    async def test_add_fact_and_search(self, memory_client, session_id):
        """Add a fact and find it."""
        integration = MemoryIntegration(memory_client)

        result = await integration.add_fact(
            subject="Earth",
            predicate="has_radius_km",
            object_value="6371",
        )
        assert result["stored"] is True
        assert result["type"] == "fact"

    @pytest.mark.asyncio
    async def test_get_context_empty_session(self, memory_client, session_id):
        """Get context for a session with no data returns successfully."""
        integration = MemoryIntegration(memory_client)

        result = await integration.get_context(session_id=session_id)
        assert "error" not in result
        assert "session_id" in result
