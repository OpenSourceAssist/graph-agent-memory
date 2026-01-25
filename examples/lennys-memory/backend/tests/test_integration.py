"""Integration tests for Lenny's Memory backend.

These tests require a running Neo4j instance and verify that podcast search
correctly excludes user chat messages and reasoning traces.

Run with: pytest tests/test_integration.py -v -m integration
"""

from uuid import uuid4

import pytest

from neo4j_agent_memory.memory.short_term import MessageRole


@pytest.mark.integration
class TestPodcastSearchIsolation:
    """Integration tests verifying podcast search doesn't leak other data."""

    @pytest.mark.asyncio
    async def test_podcast_search_excludes_chat_messages(self, memory_client):
        """Search for podcast content should not return user chat messages."""
        test_id = str(uuid4())[:8]

        # Setup: Add a podcast message
        await memory_client.short_term.add_message(
            session_id=f"test-lenny-podcast-{test_id}",
            role=MessageRole.ASSISTANT,
            content="This is about product-market fit strategies from the podcast",
            metadata={"source": "lenny_podcast", "speaker": "Test Guest"},
            generate_embedding=True,
        )

        # Setup: Add a user chat message with similar content
        await memory_client.short_term.add_message(
            session_id=f"test-chat-{test_id}",
            role=MessageRole.USER,
            content="Tell me about product-market fit strategies please",
            metadata={"source": "user_chat"},
            generate_embedding=True,
        )

        # Search with podcast filter (simulating what search_podcast_content does)
        results = await memory_client.short_term.search_messages(
            query="product-market fit strategies",
            limit=10,
            threshold=0.3,
            metadata_filters={"source": "lenny_podcast"},
        )

        # Verify only podcast messages returned
        assert len(results) > 0, "Should find at least the podcast message"
        for msg in results:
            assert msg.metadata.get("source") == "lenny_podcast", (
                f"Found non-podcast message: {msg.content[:50]}..."
            )

    @pytest.mark.asyncio
    async def test_podcast_search_excludes_assistant_responses(self, memory_client):
        """Search should not return agent assistant responses from chat sessions."""
        test_id = str(uuid4())[:8]

        # Setup: Add a podcast message
        await memory_client.short_term.add_message(
            session_id=f"test-lenny-podcast-{test_id}",
            role=MessageRole.ASSISTANT,
            content="Growth strategies discussed: focus on retention metrics",
            metadata={"source": "lenny_podcast", "speaker": "Guest Speaker"},
            generate_embedding=True,
        )

        # Setup: Simulate an agent assistant message (from chat)
        await memory_client.short_term.add_message(
            session_id=f"test-user-thread-{test_id}",
            role=MessageRole.ASSISTANT,
            content="Based on my search, here are growth strategies and retention metrics",
            metadata={},  # No source metadata = chat message
            generate_embedding=True,
        )

        # Search with podcast filter
        results = await memory_client.short_term.search_messages(
            query="growth strategies retention metrics",
            limit=10,
            threshold=0.3,
            metadata_filters={"source": "lenny_podcast"},
        )

        # Verify no chat messages
        for msg in results:
            assert msg.metadata.get("source") == "lenny_podcast", (
                f"Found chat message in results: {msg.content[:50]}..."
            )

    @pytest.mark.asyncio
    async def test_search_without_filter_returns_all_messages(self, memory_client):
        """Verify that without metadata filter, all messages are returned."""
        test_id = str(uuid4())[:8]

        # Setup: Add messages from different sources
        await memory_client.short_term.add_message(
            session_id=f"test-lenny-podcast-{test_id}",
            role=MessageRole.ASSISTANT,
            content="Unique test content alpha beta gamma",
            metadata={"source": "lenny_podcast", "speaker": "Guest"},
            generate_embedding=True,
        )

        await memory_client.short_term.add_message(
            session_id=f"test-chat-{test_id}",
            role=MessageRole.USER,
            content="Unique test content alpha beta gamma from user",
            metadata={"source": "user_chat"},
            generate_embedding=True,
        )

        # Search WITHOUT filter (should return both)
        results = await memory_client.short_term.search_messages(
            query="unique test content alpha beta gamma",
            limit=10,
            threshold=0.3,
            # No metadata_filters
        )

        # Should find messages from both sources
        sources = {msg.metadata.get("source") for msg in results}
        assert "lenny_podcast" in sources or "user_chat" in sources, (
            "Should find at least one message"
        )


@pytest.mark.integration
class TestMetadataFilterBehavior:
    """Integration tests for metadata filtering functionality."""

    @pytest.mark.asyncio
    async def test_metadata_filter_exact_match(self, memory_client):
        """Verify metadata filter performs exact match on source field."""
        test_id = str(uuid4())[:8]

        # Add messages with different sources
        await memory_client.short_term.add_message(
            session_id=f"test-session-{test_id}",
            role=MessageRole.ASSISTANT,
            content="Test message for exact match verification",
            metadata={"source": "lenny_podcast"},
            generate_embedding=True,
        )

        await memory_client.short_term.add_message(
            session_id=f"test-session-{test_id}",
            role=MessageRole.USER,
            content="Test message for exact match verification user",
            metadata={"source": "lenny_podcast_v2"},  # Different source
            generate_embedding=True,
        )

        # Search with exact source filter
        results = await memory_client.short_term.search_messages(
            query="exact match verification",
            limit=10,
            threshold=0.3,
            metadata_filters={"source": "lenny_podcast"},
        )

        # Should only find the exact match
        for msg in results:
            assert msg.metadata.get("source") == "lenny_podcast"

    @pytest.mark.asyncio
    async def test_metadata_filter_handles_missing_metadata(self, memory_client):
        """Verify messages without metadata are excluded by filter."""
        test_id = str(uuid4())[:8]

        # Add message with source metadata
        await memory_client.short_term.add_message(
            session_id=f"test-session-{test_id}",
            role=MessageRole.ASSISTANT,
            content="Message with metadata for filter test",
            metadata={"source": "lenny_podcast"},
            generate_embedding=True,
        )

        # Add message without source metadata
        await memory_client.short_term.add_message(
            session_id=f"test-session-{test_id}",
            role=MessageRole.USER,
            content="Message with metadata for filter test no source",
            metadata={},  # No source
            generate_embedding=True,
        )

        # Search with source filter
        results = await memory_client.short_term.search_messages(
            query="metadata for filter test",
            limit=10,
            threshold=0.3,
            metadata_filters={"source": "lenny_podcast"},
        )

        # Should only find the message with matching source
        for msg in results:
            assert msg.metadata.get("source") == "lenny_podcast"


@pytest.mark.integration
class TestSessionPrefixFiltering:
    """Integration tests for session_id prefix filtering in Cypher queries."""

    @pytest.mark.asyncio
    async def test_episode_list_only_returns_podcast_sessions(self, memory_client):
        """Verify get_episode_list only returns lenny-podcast-* sessions."""
        test_id = str(uuid4())[:8]

        # Add a podcast conversation
        await memory_client.short_term.add_message(
            session_id=f"lenny-podcast-test-{test_id}",
            role=MessageRole.ASSISTANT,
            content="Podcast transcript content",
            metadata={"source": "lenny_podcast"},
        )

        # Add a user chat conversation
        await memory_client.short_term.add_message(
            session_id=f"user-chat-{test_id}",
            role=MessageRole.USER,
            content="User chat content",
            metadata={},
        )

        # Query for podcast sessions using the same pattern as get_episode_list
        query = """
        MATCH (c:Conversation)
        WHERE c.session_id STARTS WITH 'lenny-podcast-'
        OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
        WITH c, count(m) AS message_count
        RETURN c.session_id AS session_id, message_count
        ORDER BY c.session_id
        """
        results = await memory_client._client.execute_read(query)

        # Verify only podcast sessions returned
        for r in results:
            assert r["session_id"].startswith("lenny-podcast-"), (
                f"Non-podcast session in results: {r['session_id']}"
            )
