"""Integration tests for MCP server with Neo4j.

Uses FastMCP's in-memory Client for testing tools against real Neo4j.
"""

import json
from contextlib import asynccontextmanager

import pytest
from fastmcp import Client, FastMCP

from neo4j_agent_memory.mcp._resources import register_resources
from neo4j_agent_memory.mcp._tools import register_tools
from neo4j_agent_memory.memory.long_term import EntityType
from neo4j_agent_memory.memory.short_term import MessageRole


def _create_server_with_client(memory_client):
    """Create a FastMCP server with a real memory client in lifespan."""

    @asynccontextmanager
    async def real_lifespan(server):
        yield {"client": memory_client}

    mcp = FastMCP("integration-test", lifespan=real_lifespan)
    register_tools(mcp)
    register_resources(mcp)
    return mcp


@pytest.mark.integration
class TestMCPToolsIntegration:
    """Integration tests for MCP tools with real Neo4j database."""

    @pytest.fixture
    def mcp_server(self, memory_client):
        return _create_server_with_client(memory_client)

    @pytest.mark.asyncio
    async def test_memory_search_messages(self, mcp_server, memory_client, session_id):
        """Test memory_search tool finds messages."""
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

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "memory_search",
                {
                    "query": "restaurants San Francisco",
                    "limit": 10,
                    "memory_types": ["messages"],
                },
            )

        data = json.loads(result.content[0].text)
        assert "results" in data
        assert "messages" in data["results"]
        assert len(data["results"]["messages"]) >= 1
        assert any(
            "restaurant" in m.get("content", "").lower() for m in data["results"]["messages"]
        )

    @pytest.mark.asyncio
    async def test_memory_search_entities(self, mcp_server, memory_client, session_id):
        """Test memory_search tool finds entities."""
        await memory_client.long_term.add_entity(
            name="OpenAI",
            entity_type=EntityType.ORGANIZATION,
            description="AI research company",
            generate_embedding=True,
            resolve=False,
        )

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "memory_search",
                {"query": "AI company", "limit": 10, "memory_types": ["entities"]},
            )

        data = json.loads(result.content[0].text)
        assert "results" in data
        assert "entities" in data["results"]
        assert len(data["results"]["entities"]) >= 1

    @pytest.mark.asyncio
    async def test_memory_search_preferences(self, mcp_server, memory_client, session_id):
        """Test memory_search tool finds preferences."""
        await memory_client.long_term.add_preference(
            category="food",
            preference="Loves spicy Thai food",
            context="dining preferences",
            generate_embedding=True,
        )

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "memory_search",
                {
                    "query": "food preferences Thai",
                    "limit": 10,
                    "memory_types": ["preferences"],
                },
            )

        data = json.loads(result.content[0].text)
        assert "results" in data
        assert "preferences" in data["results"]
        assert len(data["results"]["preferences"]) >= 1

    @pytest.mark.asyncio
    async def test_memory_store_message(self, mcp_server, memory_client, session_id):
        """Test memory_store tool stores messages."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "memory_store",
                {
                    "memory_type": "message",
                    "content": "This is a test message from MCP",
                    "session_id": session_id,
                    "role": "user",
                },
            )

        data = json.loads(result.content[0].text)
        assert data["stored"] is True
        assert data["type"] == "message"
        assert data["session_id"] == session_id

        # Verify message was stored
        conversation = await memory_client.short_term.get_conversation(session_id)
        assert len(conversation.messages) == 1
        assert "test message from MCP" in conversation.messages[0].content

    @pytest.mark.asyncio
    async def test_memory_store_preference(self, mcp_server, memory_client, session_id):
        """Test memory_store tool stores preferences."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "memory_store",
                {
                    "memory_type": "preference",
                    "content": "Prefers dark mode interfaces",
                    "category": "ui",
                },
            )

        data = json.loads(result.content[0].text)
        assert data["stored"] is True
        assert data["type"] == "preference"
        assert data["category"] == "ui"

    @pytest.mark.asyncio
    async def test_memory_store_fact(self, mcp_server, memory_client, session_id):
        """Test memory_store tool stores facts."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "memory_store",
                {
                    "memory_type": "fact",
                    "content": "",
                    "subject": "Alice",
                    "predicate": "WORKS_AT",
                    "object_value": "TechCorp",
                },
            )

        data = json.loads(result.content[0].text)
        assert data["stored"] is True
        assert data["type"] == "fact"
        assert "Alice" in data["triple"]
        assert "WORKS_AT" in data["triple"]
        assert "TechCorp" in data["triple"]

    @pytest.mark.asyncio
    async def test_entity_lookup_found(self, mcp_server, memory_client, session_id):
        """Test entity_lookup tool finds existing entity."""
        await memory_client.long_term.add_entity(
            name="Anthropic",
            entity_type=EntityType.ORGANIZATION,
            description="AI safety company that created Claude",
            generate_embedding=True,
            resolve=False,
        )

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "entity_lookup",
                {"name": "Anthropic", "include_neighbors": False},
            )

        data = json.loads(result.content[0].text)
        assert data["found"] is True
        assert data["entity"]["name"] == "Anthropic"
        assert data["entity"]["type"] == "ORGANIZATION"

    @pytest.mark.asyncio
    async def test_entity_lookup_not_found(self, mcp_server, memory_client, session_id):
        """Test entity_lookup tool handles missing entity."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "entity_lookup",
                {"name": "NonExistentEntity12345", "include_neighbors": False},
            )

        data = json.loads(result.content[0].text)
        assert data["found"] is False
        assert data["name"] == "NonExistentEntity12345"

    @pytest.mark.asyncio
    async def test_conversation_history(self, mcp_server, memory_client, session_id):
        """Test conversation_history tool retrieves messages."""
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

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "conversation_history",
                {"session_id": session_id, "limit": 50},
            )

        data = json.loads(result.content[0].text)
        assert data["session_id"] == session_id
        assert data["message_count"] == 3
        assert len(data["messages"]) == 3

    @pytest.mark.asyncio
    async def test_graph_query_read_only(self, mcp_server, memory_client, session_id):
        """Test graph_query tool executes read-only queries."""
        await memory_client.long_term.add_entity(
            name="TestQueryEntity",
            entity_type=EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "graph_query",
                {
                    "query": "MATCH (e:Entity) WHERE e.name CONTAINS 'TestQuery' RETURN e.name AS name"
                },
            )

        data = json.loads(result.content[0].text)
        assert data["success"] is True
        assert data["row_count"] >= 1
        assert any(row.get("name") == "TestQueryEntity" for row in data["rows"])

    @pytest.mark.asyncio
    async def test_graph_query_blocks_write(self, mcp_server, memory_client, session_id):
        """Test graph_query tool blocks write queries."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "graph_query",
                {"query": "CREATE (n:TestNode {name: 'Malicious'})"},
            )

        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "read-only" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_graph_query_with_parameters(self, mcp_server, memory_client, session_id):
        """Test graph_query tool with parameterized queries."""
        await memory_client.long_term.add_entity(
            name="ParameterTestEntity",
            entity_type=EntityType.PERSON,
            resolve=False,
            generate_embedding=False,
        )

        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "graph_query",
                {
                    "query": "MATCH (e:Entity) WHERE e.name = $name RETURN e.name AS name",
                    "parameters": {"name": "ParameterTestEntity"},
                },
            )

        data = json.loads(result.content[0].text)
        assert data["success"] is True
        assert data["row_count"] == 1


@pytest.mark.integration
class TestMCPServerIntegration:
    """Integration tests for the full MCP server."""

    @pytest.mark.asyncio
    async def test_server_initialization(self, memory_client):
        """Test MCP server initializes correctly with backward-compat wrapper."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        server = Neo4jMemoryMCPServer(memory_client)
        assert server is not None
        assert server._client is memory_client

    @pytest.mark.asyncio
    async def test_server_has_tools(self, memory_client):
        """Test server exposes all 6 tools via FastMCP Client."""
        server = _create_server_with_client(memory_client)
        async with Client(server) as client:
            tools = await client.list_tools()
            assert len(tools) == 6
            tool_names = {t.name for t in tools}
            assert tool_names == {
                "memory_search",
                "memory_store",
                "entity_lookup",
                "conversation_history",
                "graph_query",
                "add_reasoning_trace",
            }

    @pytest.mark.asyncio
    async def test_server_has_resources(self, memory_client):
        """Test server exposes resources via FastMCP Client."""
        server = _create_server_with_client(memory_client)
        async with Client(server) as client:
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
            assert len(resources) == 1  # graph/stats
            assert len(templates) == 3  # conversations, entities, preferences
