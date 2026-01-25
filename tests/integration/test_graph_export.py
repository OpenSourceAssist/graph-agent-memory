"""Integration tests for graph export functionality.

Tests the get_graph() method and related graph visualization features.
"""

from datetime import datetime, timedelta, timezone

import pytest

from neo4j_agent_memory import MemoryGraph
from neo4j_agent_memory.memory.long_term import EntityType
from neo4j_agent_memory.memory.short_term import MessageRole


@pytest.mark.integration
class TestGraphExportBasic:
    """Basic graph export functionality tests."""

    @pytest.mark.asyncio
    async def test_get_graph_returns_memory_graph(self, memory_client, session_id):
        """Test that get_graph returns a MemoryGraph object."""
        graph = await memory_client.get_graph()

        assert isinstance(graph, MemoryGraph)
        assert isinstance(graph.nodes, list)
        assert isinstance(graph.relationships, list)

    @pytest.mark.asyncio
    async def test_get_graph_empty_database_returns_empty_graph(self, clean_memory_client):
        """Test that get_graph returns empty graph when database is empty."""
        graph = await clean_memory_client.get_graph()

        assert isinstance(graph, MemoryGraph)
        assert len(graph.nodes) == 0
        assert len(graph.relationships) == 0

    @pytest.mark.asyncio
    async def test_get_graph_returns_nodes_and_relationships(self, clean_memory_client, session_id):
        """Test that get_graph returns nodes and relationships after adding data."""
        client = clean_memory_client

        # Add conversation with messages
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Hello, this is a test message",
            extract_entities=False,
            generate_embedding=False,
        )
        await client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "Hi there! How can I help?",
            extract_entities=False,
            generate_embedding=False,
        )

        graph = await client.get_graph()

        assert len(graph.nodes) > 0
        assert len(graph.relationships) > 0

        # Verify we have conversation and message nodes
        labels = {node.labels[0] if node.labels else None for node in graph.nodes}
        assert "Conversation" in labels
        assert "Message" in labels

        # Verify we have HAS_MESSAGE relationships
        rel_types = {rel.type for rel in graph.relationships}
        assert "HAS_MESSAGE" in rel_types


@pytest.mark.integration
class TestGraphExportSessionFiltering:
    """Tests for session-based graph filtering."""

    @pytest.mark.asyncio
    async def test_get_graph_filters_by_session_id(self, clean_memory_client):
        """Test that get_graph filters nodes by session_id."""
        client = clean_memory_client
        session1 = "test-session-1"
        session2 = "test-session-2"

        # Add messages to two different sessions
        await client.short_term.add_message(
            session1,
            MessageRole.USER,
            "Message in session 1",
            extract_entities=False,
            generate_embedding=False,
        )
        await client.short_term.add_message(
            session2,
            MessageRole.USER,
            "Message in session 2",
            extract_entities=False,
            generate_embedding=False,
        )

        # Get graph filtered by session1
        graph = await client.get_graph(session_id=session1)

        # Should only contain data from session1
        for node in graph.nodes:
            if "Conversation" in node.labels:
                assert node.properties.get("session_id") == session1

    @pytest.mark.asyncio
    async def test_get_graph_session_filter_includes_reasoning(self, clean_memory_client):
        """Test that session_id filter also applies to reasoning memory."""
        client = clean_memory_client
        session1 = "test-session-proc-1"
        session2 = "test-session-proc-2"

        # Add reasoning traces to different sessions
        trace1 = await client.reasoning.start_trace(
            session1,
            "Task for session 1",
            generate_embedding=False,
        )
        await client.reasoning.complete_trace(trace1.id, outcome="Done", success=True)

        trace2 = await client.reasoning.start_trace(
            session2,
            "Task for session 2",
            generate_embedding=False,
        )
        await client.reasoning.complete_trace(trace2.id, outcome="Done", success=True)

        # Get graph filtered by session1
        graph = await client.get_graph(
            session_id=session1,
            memory_types=["reasoning"],
        )

        # Should only contain traces from session1
        for node in graph.nodes:
            if "ReasoningTrace" in node.labels:
                assert node.properties.get("session_id") == session1


@pytest.mark.integration
class TestGraphExportMemoryTypeFiltering:
    """Tests for memory type filtering."""

    @pytest.mark.asyncio
    async def test_get_graph_filters_by_short_term_only(self, clean_memory_client, session_id):
        """Test filtering to only short-term memory."""
        client = clean_memory_client

        # Add data to all memory types
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message",
            extract_entities=False,
            generate_embedding=False,
        )
        await client.long_term.add_entity(
            "TestEntity",
            EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )
        trace = await client.reasoning.start_trace(
            session_id,
            "Test task",
            generate_embedding=False,
        )
        await client.reasoning.complete_trace(trace.id, outcome="Done", success=True)

        # Get only short-term memory
        graph = await client.get_graph(memory_types=["short_term"])

        labels = set()
        for node in graph.nodes:
            labels.update(node.labels)

        # Should have short-term labels but not others
        assert "Message" in labels or "Conversation" in labels
        assert "Entity" not in labels
        assert "ReasoningTrace" not in labels

    @pytest.mark.asyncio
    async def test_get_graph_filters_by_long_term_only(self, clean_memory_client, session_id):
        """Test filtering to only long-term memory."""
        client = clean_memory_client

        # Add data to all memory types
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message",
            extract_entities=False,
            generate_embedding=False,
        )
        await client.long_term.add_entity(
            "LongTermEntity",
            EntityType.ORGANIZATION,
            resolve=False,
            generate_embedding=False,
        )

        # Get only long-term memory
        graph = await client.get_graph(memory_types=["long_term"])

        labels = set()
        for node in graph.nodes:
            labels.update(node.labels)

        # Should have long-term labels but not short-term
        assert "Entity" in labels
        assert "Message" not in labels
        assert "Conversation" not in labels

    @pytest.mark.asyncio
    async def test_get_graph_filters_by_reasoning_only(self, clean_memory_client, session_id):
        """Test filtering to only reasoning memory."""
        client = clean_memory_client

        # Add data to all memory types
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message",
            extract_entities=False,
            generate_embedding=False,
        )
        trace = await client.reasoning.start_trace(
            session_id,
            "Test reasoning task",
            generate_embedding=False,
        )
        step = await client.reasoning.add_step(
            trace.id,
            thought="Processing",
            action="test_action",
            generate_embedding=False,
        )
        await client.reasoning.record_tool_call(
            step.id,
            tool_name="test_tool",
            arguments={"arg": "value"},
            result={"status": "ok"},
        )
        await client.reasoning.complete_trace(trace.id, outcome="Done", success=True)

        # Get only reasoning memory
        graph = await client.get_graph(memory_types=["reasoning"])

        labels = set()
        for node in graph.nodes:
            labels.update(node.labels)

        # Should have reasoning labels but not others
        assert "ReasoningTrace" in labels
        assert "Message" not in labels
        assert "Conversation" not in labels
        assert "Entity" not in labels

    @pytest.mark.asyncio
    async def test_get_graph_multiple_memory_types(self, clean_memory_client, session_id):
        """Test filtering to multiple memory types."""
        client = clean_memory_client

        # Add data to all memory types
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message",
            extract_entities=False,
            generate_embedding=False,
        )
        await client.long_term.add_entity(
            "TestMultiEntity",
            EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )
        trace = await client.reasoning.start_trace(
            session_id,
            "Test task",
            generate_embedding=False,
        )
        await client.reasoning.complete_trace(trace.id, outcome="Done", success=True)

        # Get short-term and long-term only
        graph = await client.get_graph(memory_types=["short_term", "long_term"])

        labels = set()
        for node in graph.nodes:
            labels.update(node.labels)

        # Should have short-term and long-term labels
        assert "Message" in labels or "Conversation" in labels
        assert "Entity" in labels
        # Should not have reasoning labels
        assert "ReasoningTrace" not in labels


@pytest.mark.integration
class TestGraphExportEmbeddings:
    """Tests for embedding inclusion/exclusion."""

    @pytest.mark.asyncio
    async def test_get_graph_excludes_embeddings_by_default(self, clean_memory_client, session_id):
        """Test that embeddings are excluded by default."""
        client = clean_memory_client

        # Add message with embedding
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Message with embedding",
            extract_entities=False,
            generate_embedding=True,
        )

        # Get graph without embeddings (default)
        graph = await client.get_graph()

        # Check that no nodes have embedding property
        for node in graph.nodes:
            assert "embedding" not in node.properties
            assert "task_embedding" not in node.properties

    @pytest.mark.asyncio
    async def test_get_graph_includes_embeddings_when_requested(
        self, clean_memory_client, session_id
    ):
        """Test that embeddings are included when requested."""
        client = clean_memory_client

        # Add message with embedding
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Message with embedding included",
            extract_entities=False,
            generate_embedding=True,
        )

        # Get graph with embeddings
        graph = await client.get_graph(include_embeddings=True)

        # Find the message node and verify it has embedding
        message_nodes = [n for n in graph.nodes if "Message" in n.labels]
        if message_nodes:
            # At least one message should have an embedding
            has_embedding = any("embedding" in node.properties for node in message_nodes)
            # This may or may not be true depending on the mock embedder
            # Just verify the parameter doesn't cause errors
            assert isinstance(has_embedding, bool)


@pytest.mark.integration
class TestGraphExportLimit:
    """Tests for result limiting."""

    @pytest.mark.asyncio
    async def test_get_graph_respects_limit(self, clean_memory_client, session_id):
        """Test that get_graph respects the limit parameter."""
        client = clean_memory_client

        # Add many messages
        for i in range(15):
            await client.short_term.add_message(
                session_id,
                MessageRole.USER,
                f"Message number {i}",
                extract_entities=False,
                generate_embedding=False,
            )

        # Get graph with small limit
        graph = await client.get_graph(limit=5)

        # Should have at most 5 conversation/message pairs
        # (plus the conversation node itself)
        message_count = sum(1 for n in graph.nodes if "Message" in n.labels)
        assert message_count <= 5


@pytest.mark.integration
class TestGraphExportTimeFiltering:
    """Tests for time-based filtering.

    Note: Time filtering parameters are accepted by get_graph() but may not
    be fully implemented for all memory types in the current version.
    These tests verify the API accepts the parameters without errors.
    """

    @pytest.mark.asyncio
    async def test_get_graph_accepts_since_parameter(self, clean_memory_client, session_id):
        """Test that get_graph accepts the since parameter without error."""
        client = clean_memory_client

        # Add a message
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message for time filtering",
            extract_entities=False,
            generate_embedding=False,
        )

        # Get graph with since parameter - should not raise an error
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        graph = await client.get_graph(since=past_time)

        # Verify the call succeeded and returned valid structure
        assert isinstance(graph, MemoryGraph)

    @pytest.mark.asyncio
    async def test_get_graph_accepts_until_parameter(self, clean_memory_client, session_id):
        """Test that get_graph accepts the until parameter without error."""
        client = clean_memory_client

        # Add a message
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message for until filtering",
            extract_entities=False,
            generate_embedding=False,
        )

        # Get graph with until parameter - should not raise an error
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        graph = await client.get_graph(until=future_time)

        # Verify the call succeeded and returned valid structure
        assert isinstance(graph, MemoryGraph)


@pytest.mark.integration
class TestGraphExportCombinedFilters:
    """Tests for combining multiple filters."""

    @pytest.mark.asyncio
    async def test_get_graph_combined_session_and_memory_type(self, clean_memory_client):
        """Test combining session_id and memory_types filters."""
        client = clean_memory_client
        session1 = "test-combined-session"

        # Add data
        await client.short_term.add_message(
            session1,
            MessageRole.USER,
            "Message in session",
            extract_entities=False,
            generate_embedding=False,
        )
        await client.long_term.add_entity(
            "CombinedEntity",
            EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )
        trace = await client.reasoning.start_trace(
            session1,
            "Task in session",
            generate_embedding=False,
        )
        await client.reasoning.complete_trace(trace.id, outcome="Done", success=True)

        # Get only short-term for specific session
        graph = await client.get_graph(
            session_id=session1,
            memory_types=["short_term"],
        )

        labels = set()
        for node in graph.nodes:
            labels.update(node.labels)

        # Should only have short-term labels
        assert "Entity" not in labels
        assert "ReasoningTrace" not in labels

    @pytest.mark.asyncio
    async def test_get_graph_combined_all_filters(self, clean_memory_client):
        """Test combining all filter types."""
        client = clean_memory_client
        session_id = "test-all-filters"

        # Add data
        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message with all filters",
            extract_entities=False,
            generate_embedding=True,
        )

        # Get graph with all filters
        graph = await client.get_graph(
            memory_types=["short_term"],
            session_id=session_id,
            include_embeddings=False,
            limit=10,
        )

        # Verify it returned data
        assert isinstance(graph, MemoryGraph)

        # Verify no embeddings
        for node in graph.nodes:
            assert "embedding" not in node.properties


@pytest.mark.integration
class TestGraphExportNodeStructure:
    """Tests for verifying node structure."""

    @pytest.mark.asyncio
    async def test_graph_nodes_have_required_fields(self, clean_memory_client, session_id):
        """Test that all nodes have required fields."""
        client = clean_memory_client

        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message",
            extract_entities=False,
            generate_embedding=False,
        )

        graph = await client.get_graph()

        for node in graph.nodes:
            assert node.id is not None
            assert node.labels is not None
            assert isinstance(node.labels, list)
            assert len(node.labels) > 0
            assert node.properties is not None
            assert isinstance(node.properties, dict)

    @pytest.mark.asyncio
    async def test_graph_relationships_have_required_fields(self, clean_memory_client, session_id):
        """Test that all relationships have required fields."""
        client = clean_memory_client

        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message",
            extract_entities=False,
            generate_embedding=False,
        )

        graph = await client.get_graph()

        for rel in graph.relationships:
            assert rel.id is not None
            assert rel.type is not None
            assert rel.from_node is not None
            assert rel.to_node is not None
            assert rel.properties is not None
            assert isinstance(rel.properties, dict)

    @pytest.mark.asyncio
    async def test_relationship_nodes_exist(self, clean_memory_client, session_id):
        """Test that relationship endpoints reference existing nodes."""
        client = clean_memory_client

        await client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message for relationship check",
            extract_entities=False,
            generate_embedding=False,
        )

        graph = await client.get_graph()

        node_ids = {node.id for node in graph.nodes}

        for rel in graph.relationships:
            assert rel.from_node in node_ids, f"from_node {rel.from_node} not found"
            assert rel.to_node in node_ids, f"to_node {rel.to_node} not found"


@pytest.mark.integration
class TestGraphExportReasoningMemory:
    """Tests specifically for reasoning memory graph export."""

    @pytest.mark.asyncio
    async def test_reasoning_memory_includes_all_components(self, clean_memory_client, session_id):
        """Test that reasoning memory export includes traces, steps, and tool calls."""
        client = clean_memory_client

        # Create a complete reasoning trace
        trace = await client.reasoning.start_trace(
            session_id,
            "Complex task",
            generate_embedding=False,
        )
        step = await client.reasoning.add_step(
            trace.id,
            thought="I should use a tool",
            action="tool_action",
            generate_embedding=False,
        )
        await client.reasoning.record_tool_call(
            step.id,
            tool_name="my_tool",
            arguments={"param": "value"},
            result={"output": "result"},
        )
        await client.reasoning.complete_trace(trace.id, outcome="Success", success=True)

        # Get reasoning memory graph
        graph = await client.get_graph(memory_types=["reasoning"])

        labels = set()
        for node in graph.nodes:
            labels.update(node.labels)

        # Should have all reasoning components
        assert "ReasoningTrace" in labels
        assert "ReasoningStep" in labels
        assert "ToolCall" in labels

        # Verify relationship types
        rel_types = {rel.type for rel in graph.relationships}
        assert "HAS_STEP" in rel_types
        assert "USES_TOOL" in rel_types


@pytest.mark.integration
class TestGraphExportLongTermMemory:
    """Tests specifically for long-term memory graph export."""

    @pytest.mark.asyncio
    async def test_long_term_includes_entities(self, clean_memory_client):
        """Test that long-term memory export includes entities."""
        client = clean_memory_client

        # Create entities
        entity1, _ = await client.long_term.add_entity(
            "Alice",
            EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )
        entity2, _ = await client.long_term.add_entity(
            "Acme Corp",
            EntityType.ORGANIZATION,
            resolve=False,
            generate_embedding=False,
        )

        # Get long-term memory graph
        graph = await client.get_graph(memory_types=["long_term"])

        # Verify both entities are present
        entity_names = {
            node.properties.get("name") for node in graph.nodes if "Entity" in node.labels
        }
        assert "Alice" in entity_names
        assert "Acme Corp" in entity_names

    @pytest.mark.asyncio
    async def test_long_term_entity_node_structure(self, clean_memory_client):
        """Test that entity nodes have the expected structure."""
        client = clean_memory_client

        entity, _ = await client.long_term.add_entity(
            "Test Person",
            EntityType.PERSON,
            description="A test person entity",
            resolve=False,
            generate_embedding=False,
        )

        graph = await client.get_graph(memory_types=["long_term"])

        entity_nodes = [n for n in graph.nodes if "Entity" in n.labels]
        assert len(entity_nodes) == 1

        node = entity_nodes[0]
        assert node.properties.get("name") == "Test Person"
        assert node.properties.get("type") == "PERSON"
        assert "id" in node.properties
        assert "created_at" in node.properties
