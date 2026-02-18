"""Unit tests for FastMCP resource registration and execution.

Tests the _resources.py module that exposes memory data via MCP resources.
Uses FastMCP's Client for in-memory testing.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client

from tests.unit.mcp.conftest import create_resource_server, make_mock_client


class TestResourceRegistration:
    """Tests that all 4 resources register correctly on a FastMCP server."""

    @pytest.fixture
    def server(self):
        """Create a resource server with a mock client."""
        return create_resource_server(make_mock_client())

    @pytest.mark.asyncio
    async def test_registers_3_resource_templates(self, server):
        """Three templated resources should be registered."""
        async with Client(server) as client:
            templates = await client.list_resource_templates()
            assert len(templates) == 3

    @pytest.mark.asyncio
    async def test_registers_1_static_resource(self, server):
        """One static resource (graph stats) should be registered."""
        async with Client(server) as client:
            resources = await client.list_resources()
            assert len(resources) == 1

    @pytest.mark.asyncio
    async def test_template_uris(self, server):
        """Resource templates should have expected URI patterns."""
        async with Client(server) as client:
            templates = await client.list_resource_templates()
            uris = {t.uriTemplate for t in templates}
            assert "memory://conversations/{session_id}" in uris
            assert "memory://entities/{entity_name}" in uris
            assert "memory://preferences/{category}" in uris

    @pytest.mark.asyncio
    async def test_static_resource_uri(self, server):
        """Static resource should have expected URI."""
        async with Client(server) as client:
            resources = await client.list_resources()
            uris = {str(r.uri) for r in resources}
            assert "memory://graph/stats" in uris

    @pytest.mark.asyncio
    async def test_resources_have_descriptions(self, server):
        """Every resource should have a non-empty description."""
        async with Client(server) as client:
            templates = await client.list_resource_templates()
            for template in templates:
                assert template.description, (
                    f"Resource template {template.uriTemplate} has no description"
                )

            resources = await client.list_resources()
            for resource in resources:
                assert resource.description, f"Resource {resource.uri} has no description"


class TestConversationResource:
    """Tests for the conversations resource."""

    @pytest.mark.asyncio
    async def test_returns_conversation_messages(self):
        """Conversation resource returns messages for a session."""
        mock_client = make_mock_client()
        mock_msg = MagicMock()
        mock_msg.id = "msg-1"
        mock_msg.role = MagicMock(value="user")
        mock_msg.content = "Hello there"
        mock_msg.created_at = None

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_msg]
        mock_client.short_term.get_conversation = AsyncMock(return_value=mock_conversation)

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://conversations/session-123")

        data = json.loads(result[0].text)
        assert data["session_id"] == "session-123"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello there"

    @pytest.mark.asyncio
    async def test_empty_conversation(self):
        """Conversation resource handles empty session."""
        mock_client = make_mock_client()
        mock_conversation = MagicMock()
        mock_conversation.messages = []
        mock_client.short_term.get_conversation = AsyncMock(return_value=mock_conversation)

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://conversations/empty-session")

        data = json.loads(result[0].text)
        assert data["session_id"] == "empty-session"
        assert len(data["messages"]) == 0


class TestEntityResource:
    """Tests for the entities resource."""

    @pytest.mark.asyncio
    async def test_returns_entity_data(self):
        """Entity resource returns entity details when found."""
        mock_client = make_mock_client()
        mock_entity = MagicMock()
        mock_entity.id = "entity-1"
        mock_entity.display_name = "Alice"
        mock_entity.type = MagicMock(value="PERSON")
        mock_entity.description = "A person"
        mock_entity.aliases = ["Al"]
        mock_client.long_term.search_entities = AsyncMock(return_value=[mock_entity])

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://entities/Alice")

        data = json.loads(result[0].text)
        assert data["found"] is True
        assert data["entity"]["name"] == "Alice"
        assert data["entity"]["type"] == "PERSON"

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        """Entity resource returns found=False when not found."""
        mock_client = make_mock_client()
        mock_client.long_term.search_entities = AsyncMock(return_value=[])

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://entities/Unknown")

        data = json.loads(result[0].text)
        assert data["found"] is False
        assert data["name"] == "Unknown"


class TestPreferencesResource:
    """Tests for the preferences resource."""

    @pytest.mark.asyncio
    async def test_returns_preferences(self):
        """Preferences resource returns preferences for a category."""
        mock_client = make_mock_client()
        mock_pref = MagicMock()
        mock_pref.id = "pref-1"
        mock_pref.category = "ui"
        mock_pref.preference = "Dark mode"
        mock_pref.context = "Always"
        mock_client.long_term.search_preferences = AsyncMock(return_value=[mock_pref])

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://preferences/ui")

        data = json.loads(result[0].text)
        assert data["category"] == "ui"
        assert len(data["preferences"]) == 1
        assert data["preferences"][0]["preference"] == "Dark mode"

    @pytest.mark.asyncio
    async def test_empty_preferences(self):
        """Preferences resource handles empty results."""
        mock_client = make_mock_client()
        mock_client.long_term.search_preferences = AsyncMock(return_value=[])

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://preferences/unknown")

        data = json.loads(result[0].text)
        assert data["category"] == "unknown"
        assert len(data["preferences"]) == 0


class TestGraphStatsResource:
    """Tests for the graph stats resource."""

    @pytest.mark.asyncio
    async def test_returns_stats(self):
        """Graph stats resource returns node counts."""
        mock_client = make_mock_client()
        mock_client.graph.execute_read = AsyncMock(
            return_value=[
                {"labels": ["Entity"], "count": 42},
                {"labels": ["Message"], "count": 100},
            ]
        )

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://graph/stats")

        data = json.loads(result[0].text)
        assert "stats" in data
        assert len(data["stats"]) == 2

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self):
        """Graph stats resource handles errors without crashing."""
        mock_client = make_mock_client()
        mock_client.graph.execute_read = AsyncMock(side_effect=Exception("Connection lost"))

        server = create_resource_server(mock_client)
        async with Client(server) as client:
            result = await client.read_resource("memory://graph/stats")

        data = json.loads(result[0].text)
        assert "error" in data
