"""Unit tests for MCP tool handler behavior via FastMCP Client.

Tests tool execution logic using FastMCP's in-memory Client.
Replaces direct MCPHandlers tests with FastMCP test patterns.
"""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client, FastMCP


def _make_mock_client():
    """Create a mock MemoryClient with all required sub-clients."""
    client = MagicMock()
    client.short_term = MagicMock()
    client.long_term = MagicMock()
    client.reasoning = MagicMock()
    client.graph = MagicMock()
    return client


def _create_server_with_mock(mock_client):
    """Create a FastMCP server with tools registered and a mock client in lifespan."""

    @asynccontextmanager
    async def mock_lifespan(server):
        yield {"client": mock_client}

    mcp = FastMCP("test-handlers", lifespan=mock_lifespan)

    from neo4j_agent_memory.mcp._tools import register_tools

    register_tools(mcp)
    return mcp


class TestReadOnlyQueryValidation:
    """Tests for Cypher query read-only validation."""

    def test_allows_match(self):
        from neo4j_agent_memory.mcp._tools import _is_read_only_query

        assert _is_read_only_query("MATCH (n) RETURN n") is True
        assert _is_read_only_query("MATCH (n:Person) RETURN n.name") is True

    def test_blocks_create(self):
        from neo4j_agent_memory.mcp._tools import _is_read_only_query

        assert _is_read_only_query("CREATE (n:Person {name: 'Alice'})") is False
        assert _is_read_only_query("MATCH (n) CREATE (m:Copy) SET m = n") is False

    def test_blocks_merge(self):
        from neo4j_agent_memory.mcp._tools import _is_read_only_query

        assert _is_read_only_query("MERGE (n:Person {name: 'Alice'})") is False

    def test_blocks_delete(self):
        from neo4j_agent_memory.mcp._tools import _is_read_only_query

        assert _is_read_only_query("MATCH (n) DELETE n") is False
        assert _is_read_only_query("MATCH (n) DETACH DELETE n") is False

    def test_blocks_set(self):
        from neo4j_agent_memory.mcp._tools import _is_read_only_query

        assert _is_read_only_query("MATCH (n) SET n.name = 'Bob'") is False

    def test_blocks_remove(self):
        from neo4j_agent_memory.mcp._tools import _is_read_only_query

        assert _is_read_only_query("MATCH (n) REMOVE n.name") is False

    def test_case_insensitive(self):
        from neo4j_agent_memory.mcp._tools import _is_read_only_query

        assert _is_read_only_query("match (n) return n") is True
        assert _is_read_only_query("create (n)") is False
        assert _is_read_only_query("CREATE (n)") is False


class TestMemorySearchHandler:
    """Tests for memory_search tool execution."""

    @pytest.mark.asyncio
    async def test_search_messages(self):
        mock_client = _make_mock_client()
        mock_msg = MagicMock()
        mock_msg.id = "msg-1"
        mock_msg.role = MagicMock(value="user")
        mock_msg.content = "Test message"
        mock_msg.created_at = None
        mock_msg.metadata = {"similarity": 0.9}

        mock_client.short_term.search_messages = AsyncMock(return_value=[mock_msg])
        mock_client.long_term.search_entities = AsyncMock(return_value=[])
        mock_client.long_term.search_preferences = AsyncMock(return_value=[])

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "memory_search",
                {"query": "test", "memory_types": ["messages"]},
            )

        data = json.loads(result.content[0].text)
        assert "results" in data
        assert "messages" in data["results"]
        assert len(data["results"]["messages"]) == 1
        mock_client.short_term.search_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_defaults_to_three_types(self):
        mock_client = _make_mock_client()
        mock_client.short_term.search_messages = AsyncMock(return_value=[])
        mock_client.long_term.search_entities = AsyncMock(return_value=[])
        mock_client.long_term.search_preferences = AsyncMock(return_value=[])

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            await client.call_tool("memory_search", {"query": "test"})

        mock_client.short_term.search_messages.assert_called_once()
        mock_client.long_term.search_entities.assert_called_once()
        mock_client.long_term.search_preferences.assert_called_once()


class TestMemoryStoreHandler:
    """Tests for memory_store tool execution."""

    @pytest.mark.asyncio
    async def test_store_message(self):
        mock_client = _make_mock_client()
        mock_msg = MagicMock()
        mock_msg.id = "msg-new"
        mock_client.short_term.add_message = AsyncMock(return_value=mock_msg)

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "memory_store",
                {
                    "memory_type": "message",
                    "content": "Hello world",
                    "session_id": "session-123",
                    "role": "user",
                },
            )

        data = json.loads(result.content[0].text)
        assert data["stored"] is True
        assert data["type"] == "message"
        assert data["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_store_message_requires_session_id(self):
        mock_client = _make_mock_client()
        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "memory_store",
                {"memory_type": "message", "content": "Hello"},
            )

        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "session_id" in data["error"]

    @pytest.mark.asyncio
    async def test_store_preference(self):
        mock_client = _make_mock_client()
        mock_pref = MagicMock()
        mock_pref.id = "pref-new"
        mock_client.long_term.add_preference = AsyncMock(return_value=mock_pref)

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "memory_store",
                {
                    "memory_type": "preference",
                    "content": "Likes dark mode",
                    "category": "ui",
                },
            )

        data = json.loads(result.content[0].text)
        assert data["stored"] is True
        assert data["type"] == "preference"
        assert data["category"] == "ui"

    @pytest.mark.asyncio
    async def test_store_preference_requires_category(self):
        mock_client = _make_mock_client()
        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "memory_store",
                {"memory_type": "preference", "content": "Likes dark mode"},
            )

        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "category" in data["error"]

    @pytest.mark.asyncio
    async def test_store_fact(self):
        mock_client = _make_mock_client()
        mock_fact = MagicMock()
        mock_fact.id = "fact-new"
        mock_client.long_term.add_fact = AsyncMock(return_value=mock_fact)

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "memory_store",
                {
                    "memory_type": "fact",
                    "content": "",
                    "subject": "Alice",
                    "predicate": "WORKS_AT",
                    "object_value": "Acme Corp",
                },
            )

        data = json.loads(result.content[0].text)
        assert data["stored"] is True
        assert data["type"] == "fact"
        assert "Alice" in data["triple"]
        assert "WORKS_AT" in data["triple"]

    @pytest.mark.asyncio
    async def test_store_fact_requires_full_triple(self):
        mock_client = _make_mock_client()
        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "memory_store",
                {"memory_type": "fact", "content": "", "subject": "Alice"},
            )

        data = json.loads(result.content[0].text)
        assert "error" in data


class TestEntityLookupHandler:
    """Tests for entity_lookup tool execution."""

    @pytest.mark.asyncio
    async def test_entity_found(self):
        mock_client = _make_mock_client()
        mock_entity = MagicMock()
        mock_entity.id = "entity-1"
        mock_entity.display_name = "Alice"
        mock_entity.type = MagicMock(value="PERSON")
        mock_entity.description = "A person"
        mock_entity.aliases = ["Al"]
        mock_client.long_term.search_entities = AsyncMock(return_value=[mock_entity])
        mock_client.graph.execute_read = AsyncMock(return_value=[])

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "entity_lookup",
                {"name": "Alice", "include_neighbors": False},
            )

        data = json.loads(result.content[0].text)
        assert data["found"] is True
        assert data["entity"]["name"] == "Alice"
        assert data["entity"]["type"] == "PERSON"

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        mock_client = _make_mock_client()
        mock_client.long_term.search_entities = AsyncMock(return_value=[])

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "entity_lookup",
                {"name": "Unknown"},
            )

        data = json.loads(result.content[0].text)
        assert data["found"] is False
        assert data["name"] == "Unknown"


class TestConversationHistoryHandler:
    """Tests for conversation_history tool execution."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        mock_client = _make_mock_client()
        mock_msg = MagicMock()
        mock_msg.id = "msg-1"
        mock_msg.role = MagicMock(value="user")
        mock_msg.content = "Hello"
        mock_msg.created_at = None
        mock_msg.metadata = None
        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_msg]
        mock_client.short_term.get_conversation = AsyncMock(return_value=mock_conversation)

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "conversation_history",
                {"session_id": "session-123"},
            )

        data = json.loads(result.content[0].text)
        assert data["session_id"] == "session-123"
        assert data["message_count"] == 1
        assert len(data["messages"]) == 1


class TestGraphQueryHandler:
    """Tests for graph_query tool execution."""

    @pytest.mark.asyncio
    async def test_read_only_query_succeeds(self):
        mock_client = _make_mock_client()
        mock_client.graph.execute_read = AsyncMock(return_value=[{"n.name": "Alice"}])

        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "graph_query",
                {"query": "MATCH (n:Person) RETURN n.name"},
            )

        data = json.loads(result.content[0].text)
        assert data["success"] is True
        assert data["row_count"] == 1

    @pytest.mark.asyncio
    async def test_blocks_create_query(self):
        mock_client = _make_mock_client()
        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            result = await client.call_tool(
                "graph_query",
                {"query": "CREATE (n:Person {name: 'Alice'})"},
            )

        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "read-only" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_blocks_write_queries(self):
        mock_client = _make_mock_client()
        server = _create_server_with_mock(mock_client)
        async with Client(server) as client:
            for write_query in [
                "MERGE (n:Person {name: 'Alice'})",
                "MATCH (n) DELETE n",
                "MATCH (n) SET n.name = 'Bob'",
            ]:
                result = await client.call_tool(
                    "graph_query",
                    {"query": write_query},
                )
                data = json.loads(result.content[0].text)
                assert "error" in data, f"Expected error for query: {write_query}"
