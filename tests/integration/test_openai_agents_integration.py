"""Integration tests for OpenAI Agents SDK integration."""

import pytest

from neo4j_agent_memory.memory.short_term import MessageRole

# Check if OpenAI is available
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestNeo4jOpenAIMemoryInitialization:
    """Test Neo4jOpenAIMemory initialization."""

    @pytest.mark.asyncio
    async def test_memory_initialization(self, memory_client, session_id):
        """Test basic memory initialization."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        assert memory.session_id == session_id
        assert memory.user_id is None
        assert memory.memory_client is memory_client

    @pytest.mark.asyncio
    async def test_memory_initialization_with_user_id(self, memory_client, session_id):
        """Test memory initialization with user ID."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
            user_id="user-456",
        )

        assert memory.session_id == session_id
        assert memory.user_id == "user-456"

    @pytest.mark.asyncio
    async def test_memory_properties(self, memory_client, session_id):
        """Test memory property accessors."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
            user_id="test-user",
        )

        assert memory.session_id == session_id
        assert memory.user_id == "test-user"
        assert memory.memory_client is memory_client


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestNeo4jOpenAIMemoryContext:
    """Test Neo4jOpenAIMemory context operations."""

    @pytest.mark.asyncio
    async def test_get_context_empty(self, memory_client, session_id):
        """Test get_context with empty memory."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        context = await memory.get_context("test query")

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_context_with_history(self, memory_client, session_id):
        """Test get_context with conversation history."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        # Add some messages
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I love Italian food",
            extract_entities=False,
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        context = await memory.get_context("food preferences")

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_context_with_entities(self, memory_client, session_id):
        """Test get_context includes entity knowledge."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory
        from neo4j_agent_memory.memory.long_term import EntityType

        # Add an entity
        await memory_client.long_term.add_entity(
            name="Rome",
            entity_type=EntityType.LOCATION,
            description="Capital city of Italy",
            resolve=False,
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        context = await memory.get_context("Italian cities")

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_context_with_preferences(self, memory_client, session_id):
        """Test get_context includes preferences."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        # Add a preference
        await memory_client.long_term.add_preference(
            category="food",
            preference="Prefers vegetarian options",
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        context = await memory.get_context("dietary preferences")

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_context_filter_memory_types(self, memory_client, session_id):
        """Test get_context with memory type filters."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        context = await memory.get_context(
            "test query",
            include_short_term=False,
            include_long_term=True,
            include_reasoning=False,
        )

        assert isinstance(context, str)


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestNeo4jOpenAIMemoryMessages:
    """Test Neo4jOpenAIMemory message operations."""

    @pytest.mark.asyncio
    async def test_save_message_user(self, memory_client, session_id):
        """Test saving a user message."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        msg = await memory.save_message(
            role="user",
            content="Hello, how are you?",
        )

        assert msg is not None
        assert msg.content == "Hello, how are you?"

    @pytest.mark.asyncio
    async def test_save_message_assistant(self, memory_client, session_id):
        """Test saving an assistant message."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        msg = await memory.save_message(
            role="assistant",
            content="I'm doing well, thank you!",
        )

        assert msg is not None
        assert msg.role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_save_message_system(self, memory_client, session_id):
        """Test saving a system message."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        msg = await memory.save_message(
            role="system",
            content="You are a helpful assistant.",
        )

        assert msg is not None
        assert msg.role == MessageRole.SYSTEM

    @pytest.mark.asyncio
    async def test_save_message_with_tool_calls(self, memory_client, session_id):
        """Test saving an assistant message with tool calls."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "search_memory",
                    "arguments": '{"query": "user preferences"}',
                },
            }
        ]

        msg = await memory.save_message(
            role="assistant",
            content="",
            tool_calls=tool_calls,
        )

        assert msg is not None
        assert msg.metadata.get("tool_calls") == tool_calls

    @pytest.mark.asyncio
    async def test_get_conversation_returns_openai_format(self, memory_client, session_id):
        """Test that get_conversation returns OpenAI message format."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Save some messages
        await memory.save_message("user", "Hello")
        await memory.save_message("assistant", "Hi there!")

        messages = await memory.get_conversation()

        assert isinstance(messages, list)
        assert len(messages) >= 2
        for msg in messages:
            assert "role" in msg
            assert "content" in msg

    @pytest.mark.asyncio
    async def test_get_conversation_respects_limit(self, memory_client, session_id):
        """Test that get_conversation respects limit parameter."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Save multiple messages
        for i in range(10):
            await memory.save_message("user", f"Message {i}")

        messages = await memory.get_conversation(limit=5)

        assert len(messages) <= 5

    @pytest.mark.asyncio
    async def test_get_conversation_includes_tool_calls(self, memory_client, session_id):
        """Test that get_conversation includes tool_calls in messages."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        tool_calls = [{"id": "call_1", "function": {"name": "test"}}]
        await memory.save_message("assistant", "", tool_calls=tool_calls)

        messages = await memory.get_conversation()

        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) > 0


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestNeo4jOpenAIMemorySearch:
    """Test Neo4jOpenAIMemory search operations."""

    @pytest.mark.asyncio
    async def test_search_messages(self, memory_client, session_id):
        """Test searching messages."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        # Add a message
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I want to learn about machine learning",
            extract_entities=False,
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        results = await memory.search(
            query="machine learning",
            include_messages=True,
            include_entities=False,
            include_preferences=False,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_entities(self, memory_client, session_id):
        """Test searching entities."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory
        from neo4j_agent_memory.memory.long_term import EntityType

        # Add an entity
        await memory_client.long_term.add_entity(
            name="TensorFlow",
            entity_type=EntityType.CONCEPT,
            description="Machine learning framework by Google",
            resolve=False,
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        results = await memory.search(
            query="machine learning framework",
            include_messages=False,
            include_entities=True,
            include_preferences=False,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_preferences(self, memory_client, session_id):
        """Test searching preferences."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        # Add a preference
        await memory_client.long_term.add_preference(
            category="learning",
            preference="Prefers hands-on tutorials over theory",
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        results = await memory.search(
            query="learning style",
            include_messages=False,
            include_entities=False,
            include_preferences=True,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_combined(self, memory_client, session_id):
        """Test searching all memory types."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        results = await memory.search(
            query="test query",
            include_messages=True,
            include_entities=True,
            include_preferences=True,
        )

        assert isinstance(results, list)


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestNeo4jOpenAIMemoryPreferences:
    """Test Neo4jOpenAIMemory preference operations."""

    @pytest.mark.asyncio
    async def test_add_preference(self, memory_client, session_id):
        """Test adding a preference."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        pref = await memory.add_preference(
            category="communication",
            preference="Prefers formal language",
        )

        assert pref is not None

    @pytest.mark.asyncio
    async def test_search_preferences_by_query(self, memory_client, session_id):
        """Test searching preferences by query."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        # Add preferences
        await memory_client.long_term.add_preference(
            category="style",
            preference="Likes concise answers",
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        prefs = await memory.search_preferences(query="concise")

        assert isinstance(prefs, list)

    @pytest.mark.asyncio
    async def test_search_preferences_by_category(self, memory_client, session_id):
        """Test searching preferences by category."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        # Add preferences with different categories
        await memory_client.long_term.add_preference(
            category="food",
            preference="Loves spicy food",
            generate_embedding=True,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        prefs = await memory.search_preferences(
            query="food",
            category="food",
        )

        assert isinstance(prefs, list)


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestMemoryToolCreation:
    """Test memory tool creation."""

    @pytest.mark.asyncio
    async def test_create_memory_tools_returns_list(self, memory_client, session_id):
        """Test that create_memory_tools returns a list."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            create_memory_tools,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        tools = create_memory_tools(memory)

        assert isinstance(tools, list)
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_search_memory_tool_schema(self, memory_client, session_id):
        """Test search_memory tool has correct schema."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            create_memory_tools,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        tools = create_memory_tools(memory)
        search_tool = next(t for t in tools if t["function"]["name"] == "search_memory")

        assert search_tool["type"] == "function"
        assert "description" in search_tool["function"]
        assert "parameters" in search_tool["function"]
        assert "query" in search_tool["function"]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_save_preference_tool_schema(self, memory_client, session_id):
        """Test save_preference tool has correct schema."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            create_memory_tools,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        tools = create_memory_tools(memory)
        save_tool = next(t for t in tools if t["function"]["name"] == "save_preference")

        assert save_tool["type"] == "function"
        params = save_tool["function"]["parameters"]["properties"]
        assert "category" in params
        assert "preference" in params

    @pytest.mark.asyncio
    async def test_recall_preferences_tool_schema(self, memory_client, session_id):
        """Test recall_preferences tool has correct schema."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            create_memory_tools,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        tools = create_memory_tools(memory)
        recall_tool = next(t for t in tools if t["function"]["name"] == "recall_preferences")

        assert recall_tool["type"] == "function"
        params = recall_tool["function"]["parameters"]["properties"]
        assert "query" in params

    @pytest.mark.asyncio
    async def test_search_entities_tool_schema(self, memory_client, session_id):
        """Test search_entities tool has correct schema."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            create_memory_tools,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        tools = create_memory_tools(memory)
        search_tool = next(t for t in tools if t["function"]["name"] == "search_entities")

        assert search_tool["type"] == "function"
        params = search_tool["function"]["parameters"]["properties"]
        assert "query" in params
        assert "entity_type" in params


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestMemoryToolExecution:
    """Test memory tool execution."""

    @pytest.mark.asyncio
    async def test_execute_search_memory_tool(self, memory_client, session_id):
        """Test executing search_memory tool."""
        import json

        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory
        from neo4j_agent_memory.integrations.openai_agents.memory import execute_memory_tool

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        result = await execute_memory_tool(
            memory=memory,
            tool_name="search_memory",
            arguments={"query": "test", "limit": 5},
        )

        result_data = json.loads(result)
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_execute_save_preference_tool(self, memory_client, session_id):
        """Test executing save_preference tool."""
        import json

        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory
        from neo4j_agent_memory.integrations.openai_agents.memory import execute_memory_tool

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        result = await execute_memory_tool(
            memory=memory,
            tool_name="save_preference",
            arguments={
                "category": "test",
                "preference": "Test preference",
            },
        )

        result_data = json.loads(result)
        assert result_data["status"] == "saved"

    @pytest.mark.asyncio
    async def test_execute_recall_preferences_tool(self, memory_client, session_id):
        """Test executing recall_preferences tool."""
        import json

        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory
        from neo4j_agent_memory.integrations.openai_agents.memory import execute_memory_tool

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        result = await execute_memory_tool(
            memory=memory,
            tool_name="recall_preferences",
            arguments={"query": "test"},
        )

        result_data = json.loads(result)
        assert "preferences" in result_data

    @pytest.mark.asyncio
    async def test_execute_search_entities_tool(self, memory_client, session_id):
        """Test executing search_entities tool."""
        import json

        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory
        from neo4j_agent_memory.integrations.openai_agents.memory import execute_memory_tool

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        result = await execute_memory_tool(
            memory=memory,
            tool_name="search_entities",
            arguments={"query": "test", "limit": 5},
        )

        result_data = json.loads(result)
        assert "entities" in result_data

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, memory_client, session_id):
        """Test executing unknown tool returns error."""
        import json

        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory
        from neo4j_agent_memory.integrations.openai_agents.memory import execute_memory_tool

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        result = await execute_memory_tool(
            memory=memory,
            tool_name="unknown_tool",
            arguments={},
        )

        result_data = json.loads(result)
        assert "error" in result_data


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestAgentTraceRecording:
    """Test agent trace recording."""

    @pytest.mark.asyncio
    async def test_record_trace_basic(self, memory_client, session_id):
        """Test basic trace recording."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            record_agent_trace,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 equals 4."},
        ]

        trace = await record_agent_trace(
            memory=memory,
            messages=messages,
            task="Answer math question",
            success=True,
        )

        assert trace is not None
        assert trace.task == "Answer math question"
        assert trace.success is True

    @pytest.mark.asyncio
    async def test_record_trace_with_tool_calls(self, memory_client, session_id):
        """Test trace recording with tool calls."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            record_agent_trace,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = [
            {"role": "user", "content": "Search for my preferences"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "search_memory",
                            "arguments": '{"query": "preferences"}',
                        },
                    }
                ],
            },
            {"role": "tool", "content": '{"results": []}', "tool_call_id": "call_1"},
            {"role": "assistant", "content": "No preferences found."},
        ]

        trace = await record_agent_trace(
            memory=memory,
            messages=messages,
            task="Search preferences",
        )

        assert trace is not None

    @pytest.mark.asyncio
    async def test_record_trace_failure(self, memory_client, session_id):
        """Test trace recording for failed task."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            record_agent_trace,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = [
            {"role": "user", "content": "Do something impossible"},
            {"role": "assistant", "content": "I cannot complete this task."},
        ]

        trace = await record_agent_trace(
            memory=memory,
            messages=messages,
            task="Impossible task",
            outcome="Task could not be completed",
            success=False,
        )

        assert trace is not None
        assert trace.success is False
        assert trace.outcome == "Task could not be completed"

    @pytest.mark.asyncio
    async def test_record_trace_with_explicit_tool_calls(self, memory_client, session_id):
        """Test trace recording with explicit tool_calls parameter."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            record_agent_trace,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        messages = [
            {"role": "user", "content": "Help me"},
            {"role": "assistant", "content": "Done!"},
        ]

        tool_calls = [
            {
                "name": "search_memory",
                "arguments": {"query": "test"},
                "result": {"results": []},
                "status": "success",
            }
        ]

        trace = await record_agent_trace(
            memory=memory,
            messages=messages,
            task="Help task",
            tool_calls=tool_calls,
        )

        assert trace is not None


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestSimilarTraces:
    """Test similar trace retrieval."""

    @pytest.mark.asyncio
    async def test_get_similar_traces(self, memory_client, session_id):
        """Test retrieving similar traces."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            record_agent_trace,
        )
        from neo4j_agent_memory.integrations.openai_agents.tracing import get_similar_traces

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Create a trace
        await record_agent_trace(
            memory=memory,
            messages=[{"role": "user", "content": "Test"}],
            task="Test task for similarity",
            generate_embedding=True,
        )

        # Find similar traces
        traces = await get_similar_traces(
            memory=memory,
            task="Similar test task",
            limit=5,
        )

        assert isinstance(traces, list)


@pytest.mark.integration
@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI not installed")
class TestNeo4jOpenAIMemoryEdgeCases:
    """Test edge cases for OpenAI integration."""

    @pytest.mark.asyncio
    async def test_empty_messages(self, memory_client, session_id):
        """Test handling of empty message list."""
        from neo4j_agent_memory.integrations.openai_agents import (
            Neo4jOpenAIMemory,
            record_agent_trace,
        )

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        trace = await record_agent_trace(
            memory=memory,
            messages=[],
            task="Empty message task",
        )

        assert trace is not None

    @pytest.mark.asyncio
    async def test_large_conversation(self, memory_client, session_id):
        """Test handling of large conversation."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Save many messages
        for i in range(20):
            await memory.save_message("user", f"Message {i}")
            await memory.save_message("assistant", f"Response {i}")

        messages = await memory.get_conversation(limit=50)

        assert isinstance(messages, list)

    @pytest.mark.asyncio
    async def test_special_characters(self, memory_client, session_id):
        """Test handling of special characters."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        special_content = "Special: <>&\"'`\n\t日本語 emoji 🎉"
        await memory.save_message("user", special_content)

        messages = await memory.get_conversation()

        assert any(special_content in m["content"] for m in messages)

    @pytest.mark.asyncio
    async def test_clear_session(self, memory_client, session_id):
        """Test clearing session."""
        from neo4j_agent_memory.integrations.openai_agents import Neo4jOpenAIMemory

        memory = Neo4jOpenAIMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Add messages
        await memory.save_message("user", "Hello")
        await memory.save_message("assistant", "Hi!")

        # Clear session
        await memory.clear_session()

        # Verify cleared
        messages = await memory.get_conversation()
        assert len(messages) == 0
