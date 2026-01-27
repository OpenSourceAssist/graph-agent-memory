"""Unit tests for MCP handlers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPHandlers:
    """Tests for MCPHandlers class."""

    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory client."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client.reasoning = MagicMock()
        client._driver = MagicMock()
        client._database = "neo4j"
        return client

    @pytest.fixture
    def handlers(self, mock_memory_client):
        """Create handlers with mock client."""
        from neo4j_agent_memory.mcp.handlers import MCPHandlers

        return MCPHandlers(mock_memory_client)

    def test_is_read_only_query_allows_match(self, handlers):
        """Test that MATCH queries are allowed."""
        assert handlers._is_read_only_query("MATCH (n) RETURN n") is True
        assert handlers._is_read_only_query("MATCH (n:Person) RETURN n.name") is True

    def test_is_read_only_query_blocks_create(self, handlers):
        """Test that CREATE queries are blocked."""
        assert handlers._is_read_only_query("CREATE (n:Person {name: 'Alice'})") is False
        assert handlers._is_read_only_query("MATCH (n) CREATE (m:Copy) SET m = n") is False

    def test_is_read_only_query_blocks_merge(self, handlers):
        """Test that MERGE queries are blocked."""
        assert handlers._is_read_only_query("MERGE (n:Person {name: 'Alice'})") is False

    def test_is_read_only_query_blocks_delete(self, handlers):
        """Test that DELETE queries are blocked."""
        assert handlers._is_read_only_query("MATCH (n) DELETE n") is False
        assert handlers._is_read_only_query("MATCH (n) DETACH DELETE n") is False

    def test_is_read_only_query_blocks_set(self, handlers):
        """Test that SET queries are blocked."""
        assert handlers._is_read_only_query("MATCH (n) SET n.name = 'Bob'") is False

    def test_is_read_only_query_blocks_remove(self, handlers):
        """Test that REMOVE queries are blocked."""
        assert handlers._is_read_only_query("MATCH (n) REMOVE n.name") is False

    def test_is_read_only_query_case_insensitive(self, handlers):
        """Test that query checking is case insensitive."""
        assert handlers._is_read_only_query("match (n) return n") is True
        assert handlers._is_read_only_query("create (n)") is False
        assert handlers._is_read_only_query("CREATE (n)") is False

    @pytest.mark.asyncio
    async def test_handle_memory_search(self, handlers, mock_memory_client):
        """Test memory_search handler."""
        # Setup mocks
        mock_message = MagicMock()
        mock_message.id = "msg-1"
        mock_message.role = MagicMock(value="user")
        mock_message.content = "Test message"
        mock_message.timestamp = None
        mock_message.metadata = {"similarity": 0.9}

        mock_memory_client.short_term.search_messages = AsyncMock(return_value=[mock_message])
        mock_memory_client.long_term.search_entities = AsyncMock(return_value=[])
        mock_memory_client.long_term.search_preferences = AsyncMock(return_value=[])

        result = await handlers.handle_memory_search(
            query="test",
            limit=10,
            memory_types=["messages"],
        )

        assert "results" in result
        assert "messages" in result["results"]
        assert len(result["results"]["messages"]) == 1
        mock_memory_client.short_term.search_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_memory_store_message(self, handlers, mock_memory_client):
        """Test memory_store handler for messages."""
        mock_message = MagicMock()
        mock_message.id = "msg-new"

        mock_memory_client.short_term.add_message = AsyncMock(return_value=mock_message)

        result = await handlers.handle_memory_store(
            type="message",
            content="Hello world",
            session_id="session-123",
            role="user",
        )

        assert result["stored"] is True
        assert result["type"] == "message"
        assert result["session_id"] == "session-123"
        mock_memory_client.short_term.add_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_memory_store_message_requires_session(self, handlers):
        """Test memory_store requires session_id for messages."""
        result = await handlers.handle_memory_store(
            type="message",
            content="Hello world",
        )

        assert "error" in result
        assert "session_id" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_memory_store_preference(self, handlers, mock_memory_client):
        """Test memory_store handler for preferences."""
        mock_pref = MagicMock()
        mock_pref.id = "pref-new"

        mock_memory_client.long_term.add_preference = AsyncMock(return_value=mock_pref)

        result = await handlers.handle_memory_store(
            type="preference",
            content="Likes dark mode",
            category="ui",
        )

        assert result["stored"] is True
        assert result["type"] == "preference"
        assert result["category"] == "ui"

    @pytest.mark.asyncio
    async def test_handle_memory_store_preference_requires_category(self, handlers):
        """Test memory_store requires category for preferences."""
        result = await handlers.handle_memory_store(
            type="preference",
            content="Likes dark mode",
        )

        assert "error" in result
        assert "category" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_memory_store_fact(self, handlers, mock_memory_client):
        """Test memory_store handler for facts."""
        mock_fact = MagicMock()
        mock_fact.id = "fact-new"

        mock_memory_client.long_term.add_fact = AsyncMock(return_value=mock_fact)

        result = await handlers.handle_memory_store(
            type="fact",
            content="",
            subject="Alice",
            predicate="WORKS_AT",
            object="Acme Corp",
        )

        assert result["stored"] is True
        assert result["type"] == "fact"
        assert "Alice" in result["triple"]
        assert "WORKS_AT" in result["triple"]
        assert "Acme Corp" in result["triple"]

    @pytest.mark.asyncio
    async def test_handle_memory_store_fact_requires_triple(self, handlers):
        """Test memory_store requires full triple for facts."""
        result = await handlers.handle_memory_store(
            type="fact",
            content="",
            subject="Alice",
            # Missing predicate and object
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_entity_lookup_found(self, handlers, mock_memory_client):
        """Test entity_lookup when entity is found."""
        mock_entity = MagicMock()
        mock_entity.id = "entity-1"
        mock_entity.display_name = "Alice"
        mock_entity.type = MagicMock(value="PERSON")
        mock_entity.description = "A person"
        mock_entity.aliases = ["Al"]

        mock_memory_client.long_term.search_entities = AsyncMock(return_value=[mock_entity])

        result = await handlers.handle_entity_lookup(
            name="Alice",
            include_neighbors=False,
        )

        assert result["found"] is True
        assert result["entity"]["name"] == "Alice"
        assert result["entity"]["type"] == "PERSON"

    @pytest.mark.asyncio
    async def test_handle_entity_lookup_not_found(self, handlers, mock_memory_client):
        """Test entity_lookup when entity is not found."""
        mock_memory_client.long_term.search_entities = AsyncMock(return_value=[])

        result = await handlers.handle_entity_lookup(name="Unknown")

        assert result["found"] is False
        assert result["name"] == "Unknown"

    @pytest.mark.asyncio
    async def test_handle_conversation_history(self, handlers, mock_memory_client):
        """Test conversation_history handler."""
        mock_message = MagicMock()
        mock_message.id = "msg-1"
        mock_message.role = MagicMock(value="user")
        mock_message.content = "Hello"
        mock_message.timestamp = None
        mock_message.metadata = None

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_message]

        mock_memory_client.short_term.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await handlers.handle_conversation_history(
            session_id="session-123",
            limit=50,
        )

        assert result["session_id"] == "session-123"
        assert result["message_count"] == 1
        assert len(result["messages"]) == 1

    @pytest.mark.asyncio
    async def test_handle_graph_query_read_only(self, handlers, mock_memory_client):
        """Test graph_query allows read-only queries."""
        # Mock the _client._client.execute_read method
        mock_neo4j_client = MagicMock()
        mock_neo4j_client.execute_read = AsyncMock(return_value=[{"n.name": "Alice"}])
        mock_memory_client._client = mock_neo4j_client

        result = await handlers.handle_graph_query(
            query="MATCH (n:Person) RETURN n.name",
        )

        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["rows"] == [{"n.name": "Alice"}]

    @pytest.mark.asyncio
    async def test_handle_graph_query_blocks_write(self, handlers):
        """Test graph_query blocks write queries."""
        result = await handlers.handle_graph_query(
            query="CREATE (n:Person {name: 'Alice'})",
        )

        assert "error" in result
        assert "read-only" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, handlers):
        """Test execute_tool returns error for unknown tool."""
        result = await handlers.execute_tool("unknown_tool", {})
        data = json.loads(result)

        assert "error" in data
        assert "Unknown tool" in data["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_memory_search(self, handlers, mock_memory_client):
        """Test execute_tool routes to correct handler."""
        mock_memory_client.short_term.search_messages = AsyncMock(return_value=[])
        mock_memory_client.long_term.search_entities = AsyncMock(return_value=[])
        mock_memory_client.long_term.search_preferences = AsyncMock(return_value=[])

        result = await handlers.execute_tool(
            "memory_search",
            {"query": "test", "memory_types": ["messages"]},
        )
        data = json.loads(result)

        assert "results" in data
