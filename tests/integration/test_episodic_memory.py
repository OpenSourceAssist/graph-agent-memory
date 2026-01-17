"""Comprehensive integration tests for episodic memory."""

from datetime import datetime, timedelta

import pytest

from neo4j_agent_memory.memory.episodic import MessageRole


@pytest.mark.integration
class TestEpisodicMemoryBasicOperations:
    """Test basic episodic memory operations."""

    @pytest.mark.asyncio
    async def test_add_single_message(self, memory_client, session_id):
        """Test adding a single message to a conversation."""
        msg = await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "Hello, this is a test message",
            extract_entities=False,
            generate_embedding=False,
        )

        assert msg is not None
        assert msg.content == "Hello, this is a test message"
        assert msg.role == MessageRole.USER
        assert msg.id is not None
        assert msg.created_at is not None

    @pytest.mark.asyncio
    async def test_add_message_with_all_roles(self, memory_client, session_id):
        """Test adding messages with all supported roles."""
        roles = [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM]

        for role in roles:
            msg = await memory_client.episodic.add_message(
                session_id,
                role,
                f"Test message with role {role.value}",
                extract_entities=False,
                generate_embedding=False,
            )
            assert msg.role == role

    @pytest.mark.asyncio
    async def test_get_conversation(self, memory_client, session_id):
        """Test retrieving a full conversation."""
        # Add multiple messages
        messages = [
            (MessageRole.USER, "Hello"),
            (MessageRole.ASSISTANT, "Hi there! How can I help?"),
            (MessageRole.USER, "What's the weather?"),
            (MessageRole.ASSISTANT, "I don't have access to weather data."),
        ]

        for role, content in messages:
            await memory_client.episodic.add_message(
                session_id,
                role,
                content,
                extract_entities=False,
                generate_embedding=False,
            )

        # Retrieve conversation
        conv = await memory_client.episodic.get_conversation(session_id)

        assert conv is not None
        assert conv.session_id == session_id
        assert len(conv.messages) == 4

        # Verify message order (should be chronological)
        for i, (role, content) in enumerate(messages):
            assert conv.messages[i].role == role
            assert conv.messages[i].content == content

    @pytest.mark.asyncio
    async def test_get_conversation_with_limit(self, memory_client, session_id):
        """Test retrieving conversation with message limit."""
        # Add many messages
        for i in range(10):
            await memory_client.episodic.add_message(
                session_id,
                MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                f"Message {i}",
                extract_entities=False,
                generate_embedding=False,
            )

        # Retrieve with limit
        conv = await memory_client.episodic.get_conversation(session_id, limit=5)

        assert len(conv.messages) == 5

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, memory_client):
        """Test retrieving a conversation that doesn't exist."""
        conv = await memory_client.episodic.get_conversation("nonexistent-session-id")

        # Should return an empty conversation, not None
        assert conv is not None
        assert len(conv.messages) == 0

    @pytest.mark.asyncio
    async def test_conversation_isolation(self, memory_client):
        """Test that conversations are isolated by session_id."""
        session1 = f"test-session-1-{datetime.now().timestamp()}"
        session2 = f"test-session-2-{datetime.now().timestamp()}"

        # Add messages to session 1
        await memory_client.episodic.add_message(
            session1,
            MessageRole.USER,
            "Session 1 message",
            extract_entities=False,
            generate_embedding=False,
        )

        # Add messages to session 2
        await memory_client.episodic.add_message(
            session2,
            MessageRole.USER,
            "Session 2 message",
            extract_entities=False,
            generate_embedding=False,
        )

        # Verify isolation
        conv1 = await memory_client.episodic.get_conversation(session1)
        conv2 = await memory_client.episodic.get_conversation(session2)

        assert len(conv1.messages) == 1
        assert conv1.messages[0].content == "Session 1 message"

        assert len(conv2.messages) == 1
        assert conv2.messages[0].content == "Session 2 message"


@pytest.mark.integration
class TestEpisodicMemorySearch:
    """Test episodic memory search functionality."""

    @pytest.mark.asyncio
    async def test_search_messages_basic(self, memory_client, session_id):
        """Test basic message search."""
        # Add messages with specific content
        await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "I love Italian food",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "The weather is nice today",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "Pizza and pasta are my favorites",
            extract_entities=False,
            generate_embedding=True,
        )

        # Search for food-related messages
        results = await memory_client.episodic.search_messages(
            "Italian cuisine restaurants",
            limit=10,
        )

        # Should find food-related messages (exact results depend on embedding similarity)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_messages_empty_results(self, memory_client, session_id):
        """Test search with no matching results."""
        # Add unrelated message
        await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "Hello world",
            extract_entities=False,
            generate_embedding=True,
        )

        # Search for something very different
        results = await memory_client.episodic.search_messages(
            "quantum physics equations",
            limit=10,
        )

        # Should return empty or low-relevance results
        assert isinstance(results, list)


@pytest.mark.integration
class TestEpisodicMemoryWithEmbeddings:
    """Test episodic memory with embedding generation."""

    @pytest.mark.asyncio
    async def test_add_message_with_embedding(self, memory_client, session_id):
        """Test adding a message with embedding generation."""
        msg = await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "This message should have an embedding",
            extract_entities=False,
            generate_embedding=True,
        )

        assert msg is not None
        assert msg.embedding is not None
        assert len(msg.embedding) > 0

    @pytest.mark.asyncio
    async def test_semantic_search_with_embeddings(self, memory_client, session_id):
        """Test semantic search using embeddings."""
        # Add messages about different topics
        topics = [
            "I want to learn Python programming",
            "The best restaurants in New York serve amazing food",
            "Machine learning models require lots of data",
            "Traveling to Japan is on my bucket list",
            "Software engineering best practices include testing",
        ]

        for topic in topics:
            await memory_client.episodic.add_message(
                session_id,
                MessageRole.USER,
                topic,
                extract_entities=False,
                generate_embedding=True,
            )

        # Search for programming-related content
        results = await memory_client.episodic.search_messages(
            "coding and software development",
            limit=3,
        )

        # Results should exist
        assert isinstance(results, list)


@pytest.mark.integration
class TestEpisodicMemoryWithExtraction:
    """Test episodic memory with entity extraction."""

    @pytest.mark.asyncio
    async def test_add_message_with_entity_extraction(self, memory_client, session_id):
        """Test adding a message with entity extraction enabled."""
        msg = await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "My name is John and I work at Google",
            extract_entities=True,
            generate_embedding=False,
        )

        assert msg is not None
        # Entity extraction results depend on the extractor implementation

    @pytest.mark.asyncio
    async def test_conversation_with_mentioned_entities(self, memory_client, session_id):
        """Test conversation tracking mentioned entities."""
        await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "Hi, I'm Alice from Microsoft",
            extract_entities=True,
            generate_embedding=False,
        )
        await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "I met Bob yesterday at the conference",
            extract_entities=True,
            generate_embedding=False,
        )

        # Get conversation and verify it has messages
        conv = await memory_client.episodic.get_conversation(session_id)
        assert len(conv.messages) == 2


@pytest.mark.integration
class TestEpisodicMemoryEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_message_content(self, memory_client, session_id):
        """Test handling of empty message content."""
        msg = await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "",
            extract_entities=False,
            generate_embedding=False,
        )

        assert msg.content == ""

    @pytest.mark.asyncio
    async def test_very_long_message(self, memory_client, session_id):
        """Test handling of very long messages."""
        long_content = "This is a test message. " * 1000  # ~24KB of text

        msg = await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            long_content,
            extract_entities=False,
            generate_embedding=False,
        )

        assert msg.content == long_content

    @pytest.mark.asyncio
    async def test_special_characters_in_message(self, memory_client, session_id):
        """Test handling of special characters."""
        special_content = "Hello! @#$%^&*() 你好 مرحبا 🎉 <script>alert('test')</script>"

        msg = await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            special_content,
            extract_entities=False,
            generate_embedding=False,
        )

        assert msg.content == special_content

    @pytest.mark.asyncio
    async def test_concurrent_message_additions(self, memory_client, session_id):
        """Test concurrent message additions to same conversation."""
        import asyncio

        async def add_message(index):
            return await memory_client.episodic.add_message(
                session_id,
                MessageRole.USER,
                f"Concurrent message {index}",
                extract_entities=False,
                generate_embedding=False,
            )

        # Add 10 messages concurrently
        tasks = [add_message(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10

        # Verify all messages were added
        conv = await memory_client.episodic.get_conversation(session_id)
        assert len(conv.messages) == 10

    @pytest.mark.asyncio
    async def test_message_timestamps_are_ordered(self, memory_client, session_id):
        """Test that message timestamps are properly ordered."""
        import asyncio

        for i in range(5):
            await memory_client.episodic.add_message(
                session_id,
                MessageRole.USER,
                f"Message {i}",
                extract_entities=False,
                generate_embedding=False,
            )
            await asyncio.sleep(0.01)  # Small delay to ensure timestamp ordering

        conv = await memory_client.episodic.get_conversation(session_id)

        # Verify timestamps are in ascending order
        timestamps = [msg.created_at for msg in conv.messages]
        assert timestamps == sorted(timestamps)
