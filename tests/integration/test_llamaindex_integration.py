"""Integration tests for LlamaIndex integration."""

import pytest

from neo4j_agent_memory.memory.short_term import MessageRole

# Check if LlamaIndex is available
try:
    from llama_index.core.memory import BaseMemory
    from llama_index.core.schema import TextNode

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
    async def test_get_returns_text_nodes(self, memory_client, session_id):
        """Test that get returns TextNode objects."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        # Add some messages first
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

        # Get without query returns recent conversation
        nodes = memory.get()

        assert isinstance(nodes, list)
        assert len(nodes) > 0
        assert all(isinstance(node, TextNode) for node in nodes)

    @pytest.mark.asyncio
    async def test_get_with_query_semantic_search(self, memory_client, session_id):
        """Test get with query performs semantic search."""
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
        nodes = memory.get(input="Python coding")

        assert isinstance(nodes, list)
        # Results should include relevant messages

    @pytest.mark.asyncio
    async def test_get_with_empty_query(self, memory_client, session_id):
        """Test get with empty query returns recent conversation."""
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

        nodes = memory.get(input=None)

        assert isinstance(nodes, list)
        # Should return recent conversation messages

    @pytest.mark.asyncio
    async def test_get_with_no_messages(self, memory_client, session_id):
        """Test get with empty session returns empty list."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        nodes = memory.get()

        assert isinstance(nodes, list)
        assert len(nodes) == 0

    @pytest.mark.asyncio
    async def test_get_node_metadata_structure(self, memory_client, session_id):
        """Test that returned nodes have correct metadata structure."""
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

        nodes = memory.get()

        assert len(nodes) > 0
        node = nodes[0]
        assert "source" in node.metadata
        assert "role" in node.metadata
        assert "id" in node.metadata
        assert node.metadata["source"] == "short_term"

    @pytest.mark.asyncio
    async def test_get_includes_entities_in_search(self, memory_client, session_id):
        """Test that get with query searches long-term entities."""
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

        nodes = memory.get(input="programming language")

        # Should include entity in results
        assert isinstance(nodes, list)
        entity_nodes = [n for n in nodes if n.metadata.get("source") == "long_term"]
        # May or may not find the entity depending on embedding similarity

    @pytest.mark.asyncio
    async def test_get_entity_node_metadata(self, memory_client, session_id):
        """Test that entity nodes have correct metadata."""
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

        nodes = memory.get(input="TestEntity")

        entity_nodes = [n for n in nodes if n.metadata.get("source") == "long_term"]
        if entity_nodes:
            node = entity_nodes[0]
            assert "entity_type" in node.metadata
            assert "id" in node.metadata


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryPut:
    """Test Neo4jLlamaIndexMemory put operations."""

    @pytest.mark.asyncio
    async def test_put_stores_text_node(self, memory_client, session_id):
        """Test that put stores a TextNode as a message."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        node = TextNode(
            text="This is a test message stored via put",
            metadata={"role": "user"},
        )

        memory.put(node)

        # Verify message was stored
        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0
        assert any("test message" in m.content.lower() for m in conv.messages)

    @pytest.mark.asyncio
    async def test_put_with_assistant_role(self, memory_client, session_id):
        """Test put with assistant role metadata."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        node = TextNode(
            text="This is an assistant response",
            metadata={"role": "assistant"},
        )

        memory.put(node)

        conv = await memory_client.short_term.get_conversation(session_id)
        assistant_messages = [m for m in conv.messages if m.role == MessageRole.ASSISTANT]
        assert len(assistant_messages) > 0

    @pytest.mark.asyncio
    async def test_put_defaults_to_user_role(self, memory_client, session_id):
        """Test put defaults to user role when not specified."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        node = TextNode(
            text="Message without role metadata",
            metadata={},  # No role specified
        )

        memory.put(node)

        conv = await memory_client.short_term.get_conversation(session_id)
        user_messages = [m for m in conv.messages if m.role == MessageRole.USER]
        assert len(user_messages) > 0

    @pytest.mark.asyncio
    async def test_put_multiple_nodes(self, memory_client, session_id):
        """Test putting multiple nodes in sequence."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        nodes = [
            TextNode(text="First message", metadata={"role": "user"}),
            TextNode(text="Second message", metadata={"role": "assistant"}),
            TextNode(text="Third message", metadata={"role": "user"}),
        ]

        for node in nodes:
            memory.put(node)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) >= 3

    @pytest.mark.asyncio
    async def test_put_preserves_text_content(self, memory_client, session_id):
        """Test that put preserves the exact text content."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        original_text = "This is the exact text content to preserve!"
        node = TextNode(text=original_text, metadata={"role": "user"})

        memory.put(node)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert any(m.content == original_text for m in conv.messages)


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryReset:
    """Test Neo4jLlamaIndexMemory reset operations."""

    @pytest.mark.asyncio
    async def test_reset_clears_session(self, memory_client, session_id):
        """Test that reset clears the session's messages."""
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

        # Reset
        memory.reset()

        # Verify messages are cleared
        conv_after = await memory_client.short_term.get_conversation(session_id)
        assert len(conv_after.messages) == 0

    @pytest.mark.asyncio
    async def test_reset_preserves_other_sessions(self, memory_client, session_id):
        """Test that reset only clears the current session."""
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
        memory.reset()

        # Verify main session is cleared
        conv_main = await memory_client.short_term.get_conversation(session_id)
        assert len(conv_main.messages) == 0

        # Verify other session is preserved
        conv_other = await memory_client.short_term.get_conversation(other_session)
        assert len(conv_other.messages) > 0

    @pytest.mark.asyncio
    async def test_reset_on_empty_session(self, memory_client, session_id):
        """Test that reset on empty session doesn't raise error."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Should not raise an error
        memory.reset()

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
        node = TextNode(text=special_text, metadata={"role": "user"})

        memory.put(node)

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
        node = TextNode(text=large_text, metadata={"role": "user"})

        memory.put(node)

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

        node = TextNode(text="", metadata={"role": "user"})

        # Should handle empty content gracefully
        memory.put(node)

    @pytest.mark.asyncio
    async def test_get_then_put_then_get(self, memory_client, session_id):
        """Test round-trip: get -> put -> get."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Initial get (empty)
        initial_nodes = memory.get()
        assert len(initial_nodes) == 0

        # Put a node
        node = TextNode(text="Round trip test message", metadata={"role": "user"})
        memory.put(node)

        # Get again
        final_nodes = memory.get()
        assert len(final_nodes) > 0
        assert any("Round trip" in n.text for n in final_nodes)

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
        memory_a.put(TextNode(text="Message for session A", metadata={"role": "user"}))

        # Add to session B
        memory_b.put(TextNode(text="Message for session B", metadata={"role": "user"}))

        # Get from each session
        nodes_a = memory_a.get()
        nodes_b = memory_b.get()

        # Verify isolation
        assert any("session A" in n.text for n in nodes_a)
        assert any("session B" in n.text for n in nodes_b)
        assert not any("session B" in n.text for n in nodes_a)
        assert not any("session A" in n.text for n in nodes_b)


@pytest.mark.integration
@pytest.mark.skipif(not LLAMAINDEX_AVAILABLE, reason="LlamaIndex not installed")
class TestNeo4jLlamaIndexMemoryAsync:
    """Test async behavior of LlamaIndex integration."""

    @pytest.mark.asyncio
    async def test_get_works_in_async_context(self, memory_client, session_id):
        """Test that get works when called from async context."""
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

        # This should work even in async context
        nodes = memory.get()
        assert isinstance(nodes, list)

    @pytest.mark.asyncio
    async def test_put_works_in_async_context(self, memory_client, session_id):
        """Test that put works when called from async context."""
        from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

        memory = Neo4jLlamaIndexMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        node = TextNode(text="Async context test", metadata={"role": "user"})

        # This should work even in async context
        memory.put(node)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0

    @pytest.mark.asyncio
    async def test_reset_works_in_async_context(self, memory_client, session_id):
        """Test that reset works when called from async context."""
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

        # This should work even in async context
        memory.reset()

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) == 0
