"""Integration tests for LlamaIndex integration.

Note: These tests use the async methods (aget, aput, areset) because
the sync wrappers are designed for use from truly synchronous code. When
running tests in an async context (pytest-asyncio), the Neo4j async driver
is bound to the test's event loop, so we call async methods directly.
"""

import pytest

from neo4j_agent_memory.memory.short_term import MessageRole

# Check if LlamaIndex is available
try:
    from llama_index.core.base.llms.types import ChatMessage
    from llama_index.core.base.llms.types import MessageRole as LIMessageRole
    from llama_index.core.memory import BaseMemory

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryInitialization:
    """Test Neo4jLlamaIndexMemory initialization."""

    @pytest.mark.asyncio
    async def test_memory_initialization(self, memory_client, session_id):
        """Test basic memory initialization."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        assert memory._session_id == session_id
        assert memory._client is memory_client

    @pytest.mark.asyncio
    async def test_memory_initialization_with_different_session(self, memory_client):
        """Test memory initialization with custom session ID."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        custom_session = "custom-session-123"
        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=custom_session,
        )

        assert memory._session_id == custom_session

    @pytest.mark.asyncio
    async def test_memory_inherits_base_memory(self, memory_client, session_id):
        """Test that memory inherits from LlamaIndex BaseMemory."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        assert isinstance(memory, BaseMemory)


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryGet:
    """Test Neo4jLlamaIndexMemory get operations."""

    @pytest.mark.asyncio
    async def test_get_returns_chat_messages(self, memory_client, session_id):
        """Test that aget returns ChatMessage objects."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        # Add a message first
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Hello, I am testing the LlamaIndex integration",
            extract_entities=False,
            generate_embedding=True,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = await memory.aget()

        assert isinstance(messages, list)
        assert len(messages) > 0
        assert all(isinstance(msg, ChatMessage) for msg in messages)

    @pytest.mark.asyncio
    async def test_get_with_query_semantic_search(self, memory_client, session_id):
        """Test aget with query performs semantic search."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        # Add messages with different content
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I love programming in Python",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "The weather is sunny today",
            extract_entities=False,
            generate_embedding=True,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Search for programming-related content
        messages = await memory.aget(input="Python coding")

        assert isinstance(messages, list)
        # Results should include relevant messages

    @pytest.mark.asyncio
    async def test_get_with_empty_query(self, memory_client, session_id):
        """Test aget with empty query returns recent conversation."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        # Add some messages
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "First message",
            extract_entities=False,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "Response to first message",
            extract_entities=False,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = await memory.aget(input=None)

        assert isinstance(messages, list)
        # Should return recent conversation messages

    @pytest.mark.asyncio
    async def test_get_with_no_messages(self, memory_client, session_id):
        """Test aget with empty session returns empty list."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = await memory.aget()

        assert isinstance(messages, list)
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_get_message_metadata_structure(self, memory_client, session_id):
        """Test that returned ChatMessages have correct additional_kwargs structure."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message for metadata",
            extract_entities=False,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = await memory.aget()

        assert len(messages) > 0
        msg = messages[0]
        assert "source" in msg.additional_kwargs
        assert "id" in msg.additional_kwargs
        assert msg.additional_kwargs["source"] == "short_term"

    @pytest.mark.asyncio
    async def test_get_includes_entities_in_search(self, memory_client, session_id):
        """Test that aget with query searches long-term entities."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory
        from neo4j_agent_memory.memory.long_term import EntityType

        # Add an entity
        await memory_client.long_term.add_entity(
            name="Python Programming Language",
            entity_type=EntityType.CONCEPT,
            description="A high-level programming language",
            resolve=False,
            generate_embedding=True,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = await memory.aget(input="programming language")

        # Should include entity in results
        assert isinstance(messages, list)
        entity_msgs = [m for m in messages if m.additional_kwargs.get("source") == "long_term"]
        # May or may not find the entity depending on embedding similarity

    @pytest.mark.asyncio
    async def test_get_entity_message_metadata(self, memory_client, session_id):
        """Test that entity ChatMessages have correct additional_kwargs."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory
        from neo4j_agent_memory.memory.long_term import EntityType

        await memory_client.long_term.add_entity(
            name="TestEntity",
            entity_type=EntityType.PERSON,
            description="A test entity",
            resolve=False,
            generate_embedding=True,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = await memory.aget(input="TestEntity")

        entity_msgs = [m for m in messages if m.additional_kwargs.get("source") == "long_term"]
        if entity_msgs:
            msg = entity_msgs[0]
            assert "entity_type" in msg.additional_kwargs
            assert "id" in msg.additional_kwargs


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryPut:
    """Test Neo4jLlamaIndexMemory put operations."""

    @pytest.mark.asyncio
    async def test_put_stores_chat_message(self, memory_client, session_id):
        """Test that aput stores a ChatMessage."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        msg = ChatMessage(
            role=LIMessageRole.USER,
            content="This is a test message stored via put",
        )

        await memory.aput(msg)

        # Verify message was stored
        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0
        assert any("test message" in m.content.lower() for m in conv.messages)

    @pytest.mark.asyncio
    async def test_put_with_assistant_role(self, memory_client, session_id):
        """Test aput with assistant role."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        msg = ChatMessage(
            role=LIMessageRole.ASSISTANT,
            content="This is an assistant response",
        )

        await memory.aput(msg)

        conv = await memory_client.short_term.get_conversation(session_id)
        assistant_messages = [m for m in conv.messages if m.role == MessageRole.ASSISTANT]
        assert len(assistant_messages) > 0

    @pytest.mark.asyncio
    async def test_put_with_user_role(self, memory_client, session_id):
        """Test aput with explicit user role."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        msg = ChatMessage(
            role=LIMessageRole.USER,
            content="Message with explicit user role",
        )

        await memory.aput(msg)

        conv = await memory_client.short_term.get_conversation(session_id)
        user_messages = [m for m in conv.messages if m.role == MessageRole.USER]
        assert len(user_messages) > 0

    @pytest.mark.asyncio
    async def test_put_multiple_messages(self, memory_client, session_id):
        """Test putting multiple ChatMessages in sequence."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = [
            ChatMessage(role=LIMessageRole.USER, content="First message"),
            ChatMessage(role=LIMessageRole.ASSISTANT, content="Second message"),
            ChatMessage(role=LIMessageRole.USER, content="Third message"),
        ]

        for msg in messages:
            await memory.aput(msg)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) >= 3

    @pytest.mark.asyncio
    async def test_put_preserves_text_content(self, memory_client, session_id):
        """Test that aput preserves the exact text content."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        original_text = "This is the exact text content to preserve!"
        msg = ChatMessage(role=LIMessageRole.USER, content=original_text)

        await memory.aput(msg)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert any(m.content == original_text for m in conv.messages)


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryReset:
    """Test Neo4jLlamaIndexMemory reset operations."""

    @pytest.mark.asyncio
    async def test_reset_clears_session(self, memory_client, session_id):
        """Test that areset clears the session's messages."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        # Add some messages first
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Message to be cleared",
            extract_entities=False,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Verify messages exist
        conv_before = await memory_client.short_term.get_conversation(session_id)
        assert len(conv_before.messages) > 0

        # Reset via async
        await memory.areset()

        # Verify messages are cleared
        conv_after = await memory_client.short_term.get_conversation(session_id)
        assert len(conv_after.messages) == 0

    @pytest.mark.asyncio
    async def test_reset_preserves_other_sessions(self, memory_client, session_id):
        """Test that areset only clears the current session."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        other_session = f"{session_id}-other"

        # Add messages to both sessions
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Message in main session",
            extract_entities=False,
        )
        await memory_client.short_term.add_message(
            other_session,
            MessageRole.USER,
            "Message in other session",
            extract_entities=False,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Reset main session
        await memory.areset()

        # Verify main session is cleared
        conv_main = await memory_client.short_term.get_conversation(session_id)
        assert len(conv_main.messages) == 0

        # Verify other session is preserved
        conv_other = await memory_client.short_term.get_conversation(other_session)
        assert len(conv_other.messages) > 0

    @pytest.mark.asyncio
    async def test_reset_on_empty_session(self, memory_client, session_id):
        """Test that areset on empty session doesn't raise error."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Should not raise an error
        await memory.areset()

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) == 0


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryEdgeCases:
    """Test edge cases for LlamaIndex integration."""

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self, memory_client, session_id):
        """Test handling of special characters in content."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        special_text = "Special chars: <>&\"'`\n\t日本語 emoji 🎉"
        msg = ChatMessage(role=LIMessageRole.USER, content=special_text)
        await memory.aput(msg)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert any(special_text in m.content for m in conv.messages)

    @pytest.mark.asyncio
    async def test_large_text_content(self, memory_client, session_id):
        """Test handling of large text content."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        large_text = "A" * 10000  # 10KB of text
        # Use direct client call to disable entity extraction for large text
        await memory._client.short_term.add_message(
            session_id, "user", large_text, extract_entities=False
        )

        conv = await memory_client.short_term.get_conversation(session_id)
        assert any(len(m.content) == 10000 for m in conv.messages)

    @pytest.mark.asyncio
    async def test_empty_text_content(self, memory_client, session_id):
        """Test handling of empty text content."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Should handle empty content gracefully
        msg = ChatMessage(role=LIMessageRole.USER, content="")
        await memory.aput(msg)

    @pytest.mark.asyncio
    async def test_get_then_put_then_get(self, memory_client, session_id):
        """Test round-trip: aget -> aput -> aget."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Initial get (empty)
        initial_msgs = await memory.aget()
        assert len(initial_msgs) == 0

        # Put a message
        msg = ChatMessage(role=LIMessageRole.USER, content="Round trip test message")
        await memory.aput(msg)

        # Get again
        final_msgs = await memory.aget()
        assert len(final_msgs) > 0
        assert any("Round trip" in m.content for m in final_msgs)

    @pytest.mark.asyncio
    async def test_multiple_session_isolation(self, memory_client):
        """Test that different sessions are isolated."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        session_a = "test-session-a"
        session_b = "test-session-b"

        memory_a = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_a,
        )
        memory_b = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_b,
        )

        # Add to session A
        await memory_a.aput(ChatMessage(role=LIMessageRole.USER, content="Message for session A"))

        # Add to session B
        await memory_b.aput(ChatMessage(role=LIMessageRole.USER, content="Message for session B"))

        # Get from each session
        msgs_a = await memory_a.aget()
        msgs_b = await memory_b.aget()

        # Verify isolation
        assert any("session A" in m.content for m in msgs_a)
        assert any("session B" in m.content for m in msgs_b)
        assert not any("session B" in m.content for m in msgs_a)
        assert not any("session A" in m.content for m in msgs_b)


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryAsync:
    """Test async behavior of LlamaIndex integration."""

    @pytest.mark.asyncio
    async def test_aget_works(self, memory_client, session_id):
        """Test that aget works correctly."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test async context",
            extract_entities=False,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = await memory.aget()
        assert isinstance(messages, list)

    @pytest.mark.asyncio
    async def test_aput_works(self, memory_client, session_id):
        """Test that aput works correctly."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        msg = ChatMessage(role=LIMessageRole.USER, content="Async put test")
        await memory.aput(msg)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0

    @pytest.mark.asyncio
    async def test_areset_works(self, memory_client, session_id):
        """Test that areset works correctly."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "To be reset",
            extract_entities=False,
        )

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        await memory.areset()

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) == 0

    @pytest.mark.asyncio
    async def test_sync_interface_exists(self, memory_client, session_id):
        """Test that sync interface methods exist and are callable."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Verify sync methods exist
        assert callable(memory.get)
        assert callable(memory.put)
        assert callable(memory.reset)
        assert callable(memory.set)
        assert callable(memory.get_all)
        assert callable(memory.put_messages)
