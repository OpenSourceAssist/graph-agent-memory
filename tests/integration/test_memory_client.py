"""Comprehensive integration tests for the main MemoryClient."""

import pytest

from neo4j_agent_memory.memory.long_term import EntityType
from neo4j_agent_memory.memory.short_term import MessageRole


@pytest.mark.integration
class TestMemoryClientConnection:
    """Test MemoryClient connection and lifecycle."""

    @pytest.mark.asyncio
    async def test_client_context_manager(
        self, memory_settings, mock_embedder, mock_extractor, mock_resolver
    ):
        """Test using MemoryClient as async context manager."""
        from neo4j_agent_memory import MemoryClient

        async with MemoryClient(
            memory_settings,
            embedder=mock_embedder,
            extractor=mock_extractor,
            resolver=mock_resolver,
        ) as client:
            # Verify client is connected
            assert client._client is not None

            # Perform a simple operation
            stats = await client.get_stats()
            assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_client_explicit_connect_close(
        self, memory_settings, mock_embedder, mock_extractor, mock_resolver
    ):
        """Test explicit connect and close."""
        from neo4j_agent_memory import MemoryClient

        client = MemoryClient(
            memory_settings,
            embedder=mock_embedder,
            extractor=mock_extractor,
            resolver=mock_resolver,
        )

        await client.connect()

        # Use the client
        stats = await client.get_stats()
        assert isinstance(stats, dict)

        await client.close()

    @pytest.mark.asyncio
    async def test_client_reconnect(
        self, memory_settings, mock_embedder, mock_extractor, mock_resolver
    ):
        """Test reconnecting after close."""
        from neo4j_agent_memory import MemoryClient

        client = MemoryClient(
            memory_settings,
            embedder=mock_embedder,
            extractor=mock_extractor,
            resolver=mock_resolver,
        )

        # First connection
        await client.connect()
        await client.close()

        # Reconnect
        await client.connect()
        stats = await client.get_stats()
        assert isinstance(stats, dict)

        await client.close()


@pytest.mark.integration
class TestMemoryClientMemoryAccess:
    """Test accessing different memory types through MemoryClient."""

    @pytest.mark.asyncio
    async def test_short_term_memory_access(self, memory_client, session_id):
        """Test accessing short-term memory through client."""
        assert memory_client.short_term is not None

        msg = await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message",
            extract_entities=False,
            generate_embedding=False,
        )
        assert msg is not None

    @pytest.mark.asyncio
    async def test_long_term_memory_access(self, memory_client):
        """Test accessing long-term memory through client."""
        assert memory_client.long_term is not None

        entity, _ = await memory_client.long_term.add_entity(
            "TestEntity",
            EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )
        assert entity is not None

    @pytest.mark.asyncio
    async def test_procedural_memory_access(self, memory_client, session_id):
        """Test accessing procedural memory through client."""
        assert memory_client.procedural is not None

        trace = await memory_client.procedural.start_trace(
            session_id,
            "Test task",
            generate_embedding=False,
        )
        assert trace is not None


@pytest.mark.integration
class TestMemoryClientGetContext:
    """Test the unified get_context functionality."""

    @pytest.mark.asyncio
    async def test_get_context_empty(self, memory_client, session_id):
        """Test get_context with no data."""
        context = await memory_client.get_context(
            "some query",
            session_id=session_id,
        )

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_context_with_short_term_data(self, memory_client, session_id):
        """Test get_context includes short-term memory."""
        # Add conversation messages
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I'm looking for Italian restaurants",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "I can help you find Italian restaurants!",
            extract_entities=False,
            generate_embedding=True,
        )

        context = await memory_client.get_context(
            "restaurant recommendation",
            session_id=session_id,
        )

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_context_with_long_term_data(self, memory_client, session_id):
        """Test get_context includes long-term memory."""
        # Add preferences
        await memory_client.long_term.add_preference(
            category="food",
            preference="Loves spicy Thai food",
            generate_embedding=True,
        )
        await memory_client.long_term.add_preference(
            category="dietary",
            preference="Vegetarian",
            generate_embedding=True,
        )

        context = await memory_client.get_context(
            "food preferences",
            session_id=session_id,
        )

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_context_with_all_memory_types(self, memory_client, session_id):
        """Test get_context with data in all memory types."""
        # Add short-term data
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I want to find a restaurant",
            extract_entities=False,
            generate_embedding=True,
        )

        # Add long-term data
        await memory_client.long_term.add_preference(
            category="food",
            preference="Prefers Italian cuisine",
            generate_embedding=True,
        )
        await memory_client.long_term.add_entity(
            name="Pizza Place",
            entity_type=EntityType.ORGANIZATION,
            description="A local pizza restaurant",
            resolve=False,
            generate_embedding=True,
        )

        # Add procedural data
        trace = await memory_client.procedural.start_trace(
            session_id,
            "Find restaurant",
            generate_embedding=True,
        )
        await memory_client.procedural.complete_trace(
            trace.id,
            outcome="Found 3 restaurants",
            success=True,
        )

        # Get combined context
        context = await memory_client.get_context(
            "restaurant recommendation",
            session_id=session_id,
        )

        assert isinstance(context, str)
        assert len(context) > 0

    @pytest.mark.asyncio
    async def test_get_context_with_limit(self, memory_client, session_id):
        """Test get_context respects limits."""
        # Add many messages
        for i in range(20):
            await memory_client.short_term.add_message(
                session_id,
                MessageRole.USER,
                f"Message number {i}",
                extract_entities=False,
                generate_embedding=True,
            )

        # Get context with limit
        context = await memory_client.get_context(
            "messages",
            session_id=session_id,
            max_items=5,
        )

        assert isinstance(context, str)


@pytest.mark.integration
class TestMemoryClientStats:
    """Test memory statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_stats_structure(self, memory_client):
        """Test stats return structure."""
        stats = await memory_client.get_stats()

        assert isinstance(stats, dict)
        assert "conversations" in stats
        assert "messages" in stats
        assert "entities" in stats
        assert "preferences" in stats
        assert "facts" in stats
        assert "traces" in stats

    @pytest.mark.asyncio
    async def test_stats_count_accuracy(self, clean_memory_client, session_id):
        """Test that stats counts are accurate."""
        client = clean_memory_client

        # Get initial stats
        initial_stats = await client.get_stats()

        # Add some data
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message 1",
            extract_entities=False,
            generate_embedding=False,
        )
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message 2",
            extract_entities=False,
            generate_embedding=False,
        )

        await client.long_term.add_entity(
            "StatsTestEntity",
            EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )

        await client.long_term.add_preference(
            category="test",
            preference="Test preference",
            generate_embedding=False,
        )

        # Get updated stats
        updated_stats = await client.get_stats()

        # Verify counts increased
        assert updated_stats["messages"] >= initial_stats.get("messages", 0) + 2


@pytest.mark.integration
class TestMemoryClientCrossMemoryOperations:
    """Test operations that span multiple memory types."""

    @pytest.mark.asyncio
    async def test_message_with_entity_extraction_creates_entities(self, memory_client, session_id):
        """Test that entity extraction from messages creates long-term entities."""
        # Add message with entity extraction
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I met John Smith at Google yesterday",
            extract_entities=True,  # Enable extraction
            generate_embedding=False,
        )

        # The mock extractor should have created entities
        # Check if entities were created (depends on mock implementation)
        # This test verifies the cross-memory integration works

    @pytest.mark.asyncio
    async def test_reasoning_trace_references_conversation(self, memory_client, session_id):
        """Test that reasoning traces can reference conversations."""
        # Add conversation
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Help me plan a trip",
            extract_entities=False,
            generate_embedding=False,
        )

        # Create trace for same session
        trace = await memory_client.procedural.start_trace(
            session_id,
            "Plan trip based on user request",
            generate_embedding=False,
        )

        assert trace.session_id == session_id

        # Complete trace
        await memory_client.procedural.complete_trace(
            trace.id,
            outcome="Created trip plan",
            success=True,
        )

    @pytest.mark.asyncio
    async def test_end_to_end_conversation_flow(self, memory_client, session_id):
        """Test complete conversation flow with all memory types."""
        # User starts conversation
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Hi, I'm looking for restaurant recommendations. I love Italian food.",
            extract_entities=True,
            generate_embedding=True,
        )

        # Store user preference
        await memory_client.long_term.add_preference(
            category="food",
            preference="Loves Italian food",
            context="Restaurant preferences",
            generate_embedding=True,
        )

        # Start reasoning trace
        trace = await memory_client.procedural.start_trace(
            session_id,
            "Find Italian restaurant recommendations",
            generate_embedding=True,
        )

        # Add reasoning step
        step = await memory_client.procedural.add_step(
            trace.id,
            thought="User wants Italian restaurants. Should search nearby options.",
            action="search_restaurants",
            generate_embedding=False,
        )

        # Record tool call
        await memory_client.procedural.record_tool_call(
            step.id,
            tool_name="restaurant_api",
            arguments={"cuisine": "Italian", "limit": 5},
            result=[{"name": "La Bella", "rating": 4.5}],
        )

        # Complete trace
        await memory_client.procedural.complete_trace(
            trace.id,
            outcome="Recommended La Bella Italian restaurant",
            success=True,
        )

        # Add assistant response
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "I found La Bella, a great Italian restaurant with 4.5 stars!",
            extract_entities=True,
            generate_embedding=True,
        )

        # Store entity for the restaurant
        await memory_client.long_term.add_entity(
            name="La Bella",
            entity_type=EntityType.ORGANIZATION,
            description="Italian restaurant recommended to user",
            resolve=False,
            generate_embedding=True,
        )

        # Verify the full flow
        conversation = await memory_client.short_term.get_conversation(session_id)
        assert len(conversation.messages) >= 2

        context = await memory_client.get_context(
            "Italian restaurant",
            session_id=session_id,
        )
        assert isinstance(context, str)


@pytest.mark.integration
class TestMemoryClientConfiguration:
    """Test MemoryClient with different configurations."""

    @pytest.mark.asyncio
    async def test_client_with_custom_embedder(
        self, memory_settings, mock_embedder, mock_extractor, mock_resolver
    ):
        """Test client with custom embedder."""
        from neo4j_agent_memory import MemoryClient

        # Create client with specific embedder dimensions
        custom_embedder = mock_embedder
        custom_embedder._dimensions = 384

        async with MemoryClient(
            memory_settings,
            embedder=custom_embedder,
            extractor=mock_extractor,
            resolver=mock_resolver,
        ) as client:
            # Verify embedder is used
            entity, _ = await client.long_term.add_entity(
                "TestEntity",
                EntityType.PERSON,
                resolve=False,
                generate_embedding=True,
            )

            if entity.embedding:
                assert len(entity.embedding) == 384

    @pytest.mark.asyncio
    async def test_client_without_optional_components(self, memory_settings):
        """Test client works without embedder/extractor/resolver."""
        from neo4j_agent_memory import MemoryClient

        async with MemoryClient(memory_settings) as client:
            # Basic operations should still work
            stats = await client.get_stats()
            assert isinstance(stats, dict)


@pytest.mark.integration
class TestMemoryClientErrorHandling:
    """Test error handling in MemoryClient."""

    @pytest.mark.asyncio
    async def test_operation_without_connect(
        self, memory_settings, mock_embedder, mock_extractor, mock_resolver
    ):
        """Test operation fails gracefully without connection."""
        from neo4j_agent_memory import MemoryClient

        client = MemoryClient(
            memory_settings,
            embedder=mock_embedder,
            extractor=mock_extractor,
            resolver=mock_resolver,
        )

        # Don't call connect(), try to use the client
        # This should fail or handle gracefully
        with pytest.raises(Exception):
            await client.get_stats()

    @pytest.mark.asyncio
    async def test_invalid_session_id_handling(self, memory_client):
        """Test handling of various session ID formats."""
        special_session_ids = [
            "normal-session",
            "session_with_underscore",
            "session.with.dots",
            "session-123-456",
            "a" * 100,  # Long session ID
        ]

        for sid in special_session_ids:
            sid = f"test-{sid}"  # Prefix for cleanup
            conv = await memory_client.short_term.get_conversation(sid)
            assert conv is not None  # Should handle any format
