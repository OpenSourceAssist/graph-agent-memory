"""Integration tests for MCP server with Neo4j."""

import json

import pytest

from neo4j_agent_memory.memory.long_term import EntityType
from neo4j_agent_memory.memory.short_term import MessageRole


@pytest.mark.integration
class TestMCPHandlersIntegration:
    """Integration tests for MCP handlers with real Neo4j database."""

    @pytest.fixture
    def mcp_handlers(self, memory_client):
        """Create MCP handlers with real memory client."""
        from neo4j_agent_memory.mcp.handlers import MCPHandlers

        return MCPHandlers(memory_client)

    @pytest.mark.asyncio
    async def test_memory_search_messages(self, mcp_handlers, memory_client, session_id):
        """Test memory_search tool finds messages."""
        # Add test messages
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I'm looking for restaurants in San Francisco",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "I can help you find restaurants in San Francisco!",
            extract_entities=False,
            generate_embedding=True,
        )

        result = await mcp_handlers.handle_memory_search(
            query="restaurants San Francisco",
            limit=10,
            memory_types=["messages"],
        )

        assert "results" in result
        assert "messages" in result["results"]
        assert len(result["results"]["messages"]) >= 1
        assert any(
            "restaurant" in m.get("content", "").lower() for m in result["results"]["messages"]
        )

    @pytest.mark.asyncio
    async def test_memory_search_entities(self, mcp_handlers, memory_client, session_id):
        """Test memory_search tool finds entities."""
        # Add test entity
        await memory_client.long_term.add_entity(
            name="OpenAI",
            entity_type=EntityType.ORGANIZATION,
            description="AI research company",
            generate_embedding=True,
            resolve=False,
        )

        result = await mcp_handlers.handle_memory_search(
            query="AI company",
            limit=10,
            memory_types=["entities"],
        )

        assert "results" in result
        assert "entities" in result["results"]
        assert len(result["results"]["entities"]) >= 1

    @pytest.mark.asyncio
    async def test_memory_search_preferences(self, mcp_handlers, memory_client, session_id):
        """Test memory_search tool finds preferences."""
        # Add test preference
        await memory_client.long_term.add_preference(
            category="food",
            preference="Loves spicy Thai food",
            context="dining preferences",
            generate_embedding=True,
        )

        result = await mcp_handlers.handle_memory_search(
            query="food preferences Thai",
            limit=10,
            memory_types=["preferences"],
        )

        assert "results" in result
        assert "preferences" in result["results"]
        assert len(result["results"]["preferences"]) >= 1

    @pytest.mark.asyncio
    async def test_memory_search_all_types(self, mcp_handlers, memory_client, session_id):
        """Test memory_search across all memory types."""
        # Add data to all memory types
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Tell me about Python programming",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.long_term.add_entity(
            name="Python",
            entity_type=EntityType.OBJECT,
            description="Programming language",
            generate_embedding=True,
            resolve=False,
        )
        await memory_client.long_term.add_preference(
            category="programming",
            preference="Prefers Python for data science",
            generate_embedding=True,
        )

        result = await mcp_handlers.handle_memory_search(
            query="Python programming",
            limit=20,
        )

        assert "results" in result
        # Should have results from at least some memory types
        total_results = (
            len(result["results"].get("messages", []))
            + len(result["results"].get("entities", []))
            + len(result["results"].get("preferences", []))
        )
        assert total_results >= 1

    @pytest.mark.asyncio
    async def test_memory_store_message(self, mcp_handlers, memory_client, session_id):
        """Test memory_store tool stores messages."""
        result = await mcp_handlers.handle_memory_store(
            type="message",
            content="This is a test message from MCP",
            session_id=session_id,
            role="user",
        )

        assert result["stored"] is True
        assert result["type"] == "message"
        assert result["session_id"] == session_id

        # Verify message was stored
        conversation = await memory_client.short_term.get_conversation(session_id)
        assert len(conversation.messages) == 1
        assert "test message from MCP" in conversation.messages[0].content

    @pytest.mark.asyncio
    async def test_memory_store_preference(self, mcp_handlers, memory_client, session_id):
        """Test memory_store tool stores preferences."""
        result = await mcp_handlers.handle_memory_store(
            type="preference",
            content="Prefers dark mode interfaces",
            category="ui",
        )

        assert result["stored"] is True
        assert result["type"] == "preference"
        assert result["category"] == "ui"

    @pytest.mark.asyncio
    async def test_memory_store_fact(self, mcp_handlers, memory_client, session_id):
        """Test memory_store tool stores facts."""
        result = await mcp_handlers.handle_memory_store(
            type="fact",
            content="",
            subject="Alice",
            predicate="WORKS_AT",
            object="TechCorp",
        )

        assert result["stored"] is True
        assert result["type"] == "fact"
        assert "Alice" in result["triple"]
        assert "WORKS_AT" in result["triple"]
        assert "TechCorp" in result["triple"]

    @pytest.mark.asyncio
    async def test_entity_lookup_found(self, mcp_handlers, memory_client, session_id):
        """Test entity_lookup tool finds existing entity."""
        # Add entity first
        await memory_client.long_term.add_entity(
            name="Anthropic",
            entity_type=EntityType.ORGANIZATION,
            description="AI safety company that created Claude",
            generate_embedding=True,
            resolve=False,
        )

        result = await mcp_handlers.handle_entity_lookup(
            name="Anthropic",
            include_neighbors=False,
        )

        assert result["found"] is True
        assert result["entity"]["name"] == "Anthropic"
        assert result["entity"]["type"] == "ORGANIZATION"

    @pytest.mark.asyncio
    async def test_entity_lookup_not_found(self, mcp_handlers, memory_client, session_id):
        """Test entity_lookup tool handles missing entity."""
        result = await mcp_handlers.handle_entity_lookup(
            name="NonExistentEntity12345",
            include_neighbors=False,
        )

        assert result["found"] is False
        assert result["name"] == "NonExistentEntity12345"

    @pytest.mark.asyncio
    async def test_conversation_history(self, mcp_handlers, memory_client, session_id):
        """Test conversation_history tool retrieves messages."""
        # Add conversation messages
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "First message",
            extract_entities=False,
            generate_embedding=False,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "First response",
            extract_entities=False,
            generate_embedding=False,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Second message",
            extract_entities=False,
            generate_embedding=False,
        )

        result = await mcp_handlers.handle_conversation_history(
            session_id=session_id,
            limit=50,
        )

        assert result["session_id"] == session_id
        assert result["message_count"] == 3
        assert len(result["messages"]) == 3

    @pytest.mark.asyncio
    async def test_graph_query_read_only(self, mcp_handlers, memory_client, session_id):
        """Test graph_query tool executes read-only queries."""
        # Add some data first
        await memory_client.long_term.add_entity(
            name="TestQueryEntity",
            entity_type=EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )

        result = await mcp_handlers.handle_graph_query(
            query="MATCH (e:Entity) WHERE e.name CONTAINS 'TestQuery' RETURN e.name AS name",
        )

        assert result["success"] is True
        assert result["row_count"] >= 1
        assert any(row.get("name") == "TestQueryEntity" for row in result["rows"])

    @pytest.mark.asyncio
    async def test_graph_query_blocks_write(self, mcp_handlers, memory_client, session_id):
        """Test graph_query tool blocks write queries."""
        result = await mcp_handlers.handle_graph_query(
            query="CREATE (n:TestNode {name: 'Malicious'})",
        )

        assert "error" in result
        assert "read-only" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_graph_query_with_parameters(self, mcp_handlers, memory_client, session_id):
        """Test graph_query tool with parameterized queries."""
        # Add entity
        await memory_client.long_term.add_entity(
            name="ParameterTestEntity",
            entity_type=EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )

        result = await mcp_handlers.handle_graph_query(
            query="MATCH (e:Entity) WHERE e.name = $name RETURN e.name AS name",
            parameters={"name": "ParameterTestEntity"},
        )

        assert result["success"] is True
        assert result["row_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_tool_routing(self, mcp_handlers, memory_client, session_id):
        """Test execute_tool correctly routes to handlers."""
        # Test memory_search routing
        result_json = await mcp_handlers.execute_tool(
            "memory_search",
            {"query": "test", "memory_types": ["messages"]},
        )
        result = json.loads(result_json)
        assert "results" in result

        # Test conversation_history routing
        result_json = await mcp_handlers.execute_tool(
            "conversation_history",
            {"session_id": session_id, "limit": 10},
        )
        result = json.loads(result_json)
        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, mcp_handlers):
        """Test execute_tool handles unknown tools."""
        result_json = await mcp_handlers.execute_tool(
            "unknown_tool_xyz",
            {},
        )
        result = json.loads(result_json)
        assert "error" in result
        assert "Unknown tool" in result["error"]


@pytest.mark.integration
class TestMCPServerIntegration:
    """Integration tests for the full MCP server."""

    @pytest.mark.asyncio
    async def test_server_initialization(self, memory_client):
        """Test MCP server initializes correctly."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        server = Neo4jMemoryMCPServer(memory_client)
        assert server is not None
        assert server._handlers is not None

    @pytest.mark.asyncio
    async def test_server_get_tools(self, memory_client):
        """Test server returns all 5 tools."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        server = Neo4jMemoryMCPServer(memory_client)
        tools = server.get_tools()

        assert len(tools) == 5
        # Tools are Tool objects with a 'name' attribute
        tool_names = {t.name for t in tools}
        assert tool_names == {
            "memory_search",
            "memory_store",
            "entity_lookup",
            "conversation_history",
            "graph_query",
        }

    @pytest.mark.asyncio
    async def test_server_handle_tool_call(self, memory_client, session_id):
        """Test server handles tool calls correctly."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        server = Neo4jMemoryMCPServer(memory_client)

        # Add a message first
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Test message for server",
            extract_entities=False,
            generate_embedding=True,
        )

        # Call memory_search via server
        result = await server.handle_tool_call(
            "memory_search",
            {"query": "test message server", "memory_types": ["messages"]},
        )

        assert result is not None
        # Result should be a list of TextContent or similar
        assert len(result) > 0
