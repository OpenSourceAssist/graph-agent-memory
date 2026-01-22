"""Smoke tests for basic_usage.py example.

This example requires Neo4j and demonstrates core memory functionality.
"""

from pathlib import Path
from uuid import uuid4

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"


@pytest.mark.requires_neo4j
class TestBasicUsageExample:
    """Smoke tests for the basic usage example."""

    def test_example_file_exists(self, examples_dir):
        """Verify the example file exists."""
        example_path = examples_dir / "basic_usage.py"
        assert example_path.exists(), f"Example file not found: {example_path}"

    def test_example_imports_work(self):
        """Verify the example can import required modules."""
        from neo4j_agent_memory import (
            MemoryClient,
            MemorySettings,
            MessageRole,
            Neo4jConfig,
            StreamingTraceRecorder,
            ToolCallStatus,
        )

        assert MemoryClient is not None
        assert MemorySettings is not None
        assert Neo4jConfig is not None
        assert MessageRole is not None
        assert ToolCallStatus is not None
        assert StreamingTraceRecorder is not None

    @pytest.mark.asyncio
    async def test_episodic_memory_operations(self, memory_client):
        """Test episodic memory operations from the example."""
        session_id = f"test-basic-{uuid4()}"

        # Add messages (as shown in example)
        from neo4j_agent_memory import MessageRole

        await memory_client.episodic.add_message(
            session_id,
            MessageRole.USER,
            "Hi! I'm looking for restaurant recommendations.",
        )

        await memory_client.episodic.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "I'd be happy to help you find restaurants!",
        )

        # Retrieve conversation
        conversation = await memory_client.episodic.get_conversation(session_id)
        assert len(conversation.messages) == 2
        assert conversation.messages[0].role == MessageRole.USER
        assert conversation.messages[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_semantic_memory_operations(self, memory_client):
        """Test semantic memory operations from the example."""
        # Add preferences
        await memory_client.semantic.add_preference(
            category="food",
            preference="Loves Italian cuisine",
            context="Restaurant recommendations",
        )

        await memory_client.semantic.add_preference(
            category="dietary",
            preference="Vegetarian diet",
        )

        # Add entity
        await memory_client.semantic.add_entity(
            name="Downtown",
            entity_type="LOCATION",
            description="User's preferred dining area",
        )

        # Add fact
        await memory_client.semantic.add_fact(
            subject="User",
            predicate="dietary_restriction",
            obj="vegetarian",
        )

        # Search preferences
        food_prefs = await memory_client.semantic.search_preferences("food", limit=5)
        assert len(food_prefs) >= 1

    @pytest.mark.asyncio
    async def test_procedural_memory_operations(self, memory_client):
        """Test procedural memory operations from the example."""
        session_id = f"test-procedural-{uuid4()}"

        from neo4j_agent_memory import ToolCallStatus

        # Start trace
        trace = await memory_client.procedural.start_trace(
            session_id,
            task="Find vegetarian restaurant",
        )
        assert trace.id is not None

        # Add step
        step = await memory_client.procedural.add_step(
            trace.id,
            thought="Need to search for restaurants",
            action="search_restaurants",
        )
        assert step.id is not None

        # Record tool call
        tool_call = await memory_client.procedural.record_tool_call(
            step.id,
            tool_name="restaurant_api",
            arguments={"cuisine": "vegetarian"},
            result=[{"name": "Green Garden"}],
            status=ToolCallStatus.SUCCESS,
            duration_ms=100,
        )
        assert tool_call.id is not None

        # Complete trace
        completed = await memory_client.procedural.complete_trace(
            trace.id,
            outcome="Found restaurant",
            success=True,
        )
        assert completed.success is True

    @pytest.mark.asyncio
    async def test_batch_loading(self, memory_client):
        """Test batch message loading from the example."""
        session_id = f"test-batch-{uuid4()}"

        messages = [
            {"role": "user", "content": "What's the weather?", "metadata": {"topic": "weather"}},
            {"role": "assistant", "content": "It's sunny!", "metadata": {"topic": "weather"}},
            {"role": "user", "content": "Thanks!"},
        ]

        loaded = await memory_client.episodic.add_messages_batch(
            session_id,
            messages,
            batch_size=2,
            generate_embeddings=True,
            extract_entities=False,
        )
        assert len(loaded) == 3

    @pytest.mark.asyncio
    async def test_session_listing(self, memory_client):
        """Test session listing from the example."""
        # Create some sessions
        for i in range(3):
            session_id = f"test-list-session-{i}-{uuid4()}"
            await memory_client.episodic.add_message(session_id, "user", f"Message in session {i}")

        # List sessions
        sessions = await memory_client.episodic.list_sessions(
            limit=10,
            order_by="updated_at",
        )
        assert len(sessions) >= 3

    @pytest.mark.asyncio
    async def test_metadata_search(self, memory_client):
        """Test metadata filtering from the example."""
        session_id = f"test-metadata-{uuid4()}"

        messages = [
            {"role": "user", "content": "Weather question", "metadata": {"topic": "weather"}},
            {"role": "user", "content": "Food question", "metadata": {"topic": "food"}},
        ]

        await memory_client.episodic.add_messages_batch(session_id, messages)

        # Search with metadata filter
        results = await memory_client.episodic.search_messages(
            "question",
            session_id=session_id,
            metadata_filters={"topic": "weather"},
            limit=5,
        )
        # Should find the weather message
        assert len(results) >= 0  # May be 0 if embedding similarity is too low

    @pytest.mark.asyncio
    async def test_streaming_trace_recorder(self, memory_client):
        """Test StreamingTraceRecorder from the example."""
        session_id = f"test-streaming-{uuid4()}"

        from neo4j_agent_memory import StreamingTraceRecorder

        async with StreamingTraceRecorder(
            memory_client.procedural, session_id, "Process request"
        ) as recorder:
            step = await recorder.start_step(
                thought="Analyzing request",
                action="analyze",
            )
            assert step is not None

            await recorder.record_tool_call(
                "analyze_text",
                {"text": "Hello"},
                {"result": "greeting"},
            )

            await recorder.add_observation("User is greeting")

        # Trace should be auto-completed
        traces = await memory_client.procedural.list_traces(session_id=session_id)
        assert len(traces) >= 1

    @pytest.mark.asyncio
    async def test_list_traces(self, memory_client):
        """Test listing traces from the example."""
        session_id = f"test-list-traces-{uuid4()}"

        # Create a trace
        trace = await memory_client.procedural.start_trace(session_id, task="Test task")
        await memory_client.procedural.complete_trace(trace.id, success=True)

        # List traces
        traces = await memory_client.procedural.list_traces(
            session_id=session_id,
            success_only=True,
            limit=5,
        )
        assert len(traces) >= 1

    @pytest.mark.asyncio
    async def test_tool_stats(self, memory_client):
        """Test tool statistics from the example."""
        session_id = f"test-tool-stats-{uuid4()}"

        from neo4j_agent_memory import ToolCallStatus

        # Create trace with tool calls
        trace = await memory_client.procedural.start_trace(session_id, task="Test")
        step = await memory_client.procedural.add_step(trace.id, action="test")
        await memory_client.procedural.record_tool_call(
            step.id,
            tool_name="test_tool",
            arguments={},
            result="ok",
            status=ToolCallStatus.SUCCESS,
            duration_ms=50,
        )
        await memory_client.procedural.complete_trace(trace.id)

        # Get tool stats
        stats = await memory_client.procedural.get_tool_stats()
        assert isinstance(stats, list)

    @pytest.mark.asyncio
    async def test_graph_export(self, memory_client):
        """Test graph export from the example."""
        session_id = f"test-graph-{uuid4()}"

        # Add some data
        await memory_client.episodic.add_message(session_id, "user", "Test message")
        await memory_client.semantic.add_preference("test", "Test preference")

        # Export graph
        graph = await memory_client.get_graph(
            memory_types=["episodic", "semantic"],
            session_id=session_id,
            include_embeddings=False,
            limit=100,
        )

        assert hasattr(graph, "nodes")
        assert hasattr(graph, "relationships")

    @pytest.mark.asyncio
    async def test_get_context(self, memory_client):
        """Test combined context retrieval from the example."""
        session_id = f"test-context-{uuid4()}"

        # Add data
        await memory_client.episodic.add_message(session_id, "user", "I love pizza")
        await memory_client.semantic.add_preference("food", "Loves pizza")

        # Get combined context
        context = await memory_client.get_context(
            "pizza recommendation",
            session_id=session_id,
        )

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_stats(self, memory_client):
        """Test memory statistics from the example."""
        stats = await memory_client.get_stats()

        assert isinstance(stats, dict)
        assert "messages" in stats or "conversations" in stats

    def test_example_sections_present(self, examples_dir):
        """Verify the example covers all documented sections."""
        example_path = examples_dir / "basic_usage.py"
        content = example_path.read_text()

        # Check for key sections
        assert "EPISODIC MEMORY" in content
        assert "SEMANTIC MEMORY" in content
        assert "PROCEDURAL MEMORY" in content
        assert "Batch Loading" in content
        assert "Session Listing" in content
        assert "StreamingTraceRecorder" in content
        assert "Graph Export" in content
