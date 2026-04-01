"""Unit tests for MCP tool error handling.

Verifies that every tool returns {"error": ...} JSON when the backend
raises an exception, rather than crashing the MCP server.

Core tools delegate to MemoryIntegration, which catches errors internally.
Extended tools have their own try/except blocks around MemoryClient calls.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client

from tests.unit.mcp.conftest import (
    create_tool_server,
    make_mock_client,
    make_mock_integration,
)


class TestCoreToolErrorPaths:
    """Test that core tools propagate integration-layer errors correctly.

    Core tools delegate to MemoryIntegration, which catches exceptions
    and returns {"error": ...} dicts. These tests verify that pattern.
    """

    @pytest.mark.asyncio
    async def test_memory_search_returns_error_from_integration(self):
        mock_client = make_mock_client()
        mock_integration = make_mock_integration(mock_client)
        mock_integration.search = AsyncMock(return_value={"error": "search failed"})
        server = create_tool_server(mock_client, profile="core", mock_integration=mock_integration)

        async with Client(server) as client:
            result = await client.call_tool("memory_search", {"query": "test"})
            data = json.loads(result.content[0].text)
            assert "error" in data
            assert data["error"] == "search failed"

    @pytest.mark.asyncio
    async def test_memory_get_context_returns_error(self):
        mock_client = make_mock_client()
        mock_integration = make_mock_integration(mock_client)
        mock_integration.get_context = AsyncMock(return_value={"error": "context failed"})
        server = create_tool_server(mock_client, profile="core", mock_integration=mock_integration)

        async with Client(server) as client:
            result = await client.call_tool("memory_get_context", {})
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_store_message_returns_error(self):
        mock_client = make_mock_client()
        mock_integration = make_mock_integration(mock_client)
        mock_integration.store_message = AsyncMock(return_value={"error": "store failed"})
        server = create_tool_server(mock_client, profile="core", mock_integration=mock_integration)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_store_message", {"content": "test", "role": "user"}
            )
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_add_entity_returns_error(self):
        mock_client = make_mock_client()
        mock_integration = make_mock_integration(mock_client)
        mock_integration.add_entity = AsyncMock(return_value={"error": "entity failed"})
        server = create_tool_server(mock_client, profile="core", mock_integration=mock_integration)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_add_entity", {"name": "Test", "entity_type": "PERSON"}
            )
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_add_preference_returns_error(self):
        mock_client = make_mock_client()
        mock_integration = make_mock_integration(mock_client)
        mock_integration.add_preference = AsyncMock(return_value={"error": "pref failed"})
        server = create_tool_server(mock_client, profile="core", mock_integration=mock_integration)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_add_preference", {"category": "food", "preference": "test"}
            )
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_add_fact_returns_error(self):
        mock_client = make_mock_client()
        mock_integration = make_mock_integration(mock_client)
        mock_integration.add_fact = AsyncMock(return_value={"error": "fact failed"})
        server = create_tool_server(mock_client, profile="core", mock_integration=mock_integration)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_add_fact",
                {"subject": "A", "predicate": "B", "object_value": "C"},
            )
            data = json.loads(result.content[0].text)
            assert "error" in data


class TestExtendedToolErrorPaths:
    """Test that extended tools return error JSON on backend exceptions.

    Extended tools call MemoryClient directly and have their own try/except.
    """

    @pytest.mark.asyncio
    async def test_memory_get_conversation_error(self):
        mock_client = make_mock_client()
        mock_client.short_term.get_conversation = AsyncMock(side_effect=Exception("conv failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("memory_get_conversation", {"session_id": "s1"})
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_list_sessions_error(self):
        mock_client = make_mock_client()
        mock_client.short_term.list_sessions = AsyncMock(side_effect=Exception("sessions failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("memory_list_sessions", {})
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_get_entity_error(self):
        mock_client = make_mock_client()
        mock_client.long_term.search_entities = AsyncMock(
            side_effect=Exception("entity search failed")
        )
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("memory_get_entity", {"name": "Test"})
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_export_graph_error(self):
        mock_client = make_mock_client()
        mock_client.get_graph = AsyncMock(side_effect=Exception("graph failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("memory_export_graph", {})
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_create_relationship_source_not_found(self):
        mock_client = make_mock_client()
        mock_client.long_term.search_entities = AsyncMock(return_value=[])
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_create_relationship",
                {
                    "source_name": "Unknown",
                    "target_name": "Also Unknown",
                    "relationship_type": "KNOWS",
                },
            )
            data = json.loads(result.content[0].text)
            assert "error" in data
            assert "Unknown" in data["error"]

    @pytest.mark.asyncio
    async def test_memory_create_relationship_target_not_found(self):
        mock_client = make_mock_client()
        mock_entity = MagicMock()
        mock_entity.id = "e1"
        mock_entity.display_name = "Source"
        mock_client.long_term.search_entities = AsyncMock(side_effect=[[mock_entity], []])
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_create_relationship",
                {
                    "source_name": "Source",
                    "target_name": "Missing",
                    "relationship_type": "KNOWS",
                },
            )
            data = json.loads(result.content[0].text)
            assert "error" in data
            assert "Missing" in data["error"]

    @pytest.mark.asyncio
    async def test_memory_create_relationship_backend_error(self):
        mock_client = make_mock_client()
        mock_entity = MagicMock()
        mock_entity.id = "e1"
        mock_entity.display_name = "Entity"
        mock_client.long_term.search_entities = AsyncMock(return_value=[mock_entity])
        mock_client.long_term.add_relationship = AsyncMock(side_effect=Exception("rel failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_create_relationship",
                {
                    "source_name": "A",
                    "target_name": "B",
                    "relationship_type": "KNOWS",
                },
            )
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_start_trace_error(self):
        mock_client = make_mock_client()
        mock_client.reasoning.start_trace = AsyncMock(side_effect=Exception("trace failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_start_trace", {"session_id": "s1", "task": "test"}
            )
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_record_step_error(self):
        mock_client = make_mock_client()
        mock_client.reasoning.add_step = AsyncMock(side_effect=Exception("step failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool(
                "memory_record_step", {"trace_id": "t1", "thought": "test"}
            )
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_complete_trace_error(self):
        mock_client = make_mock_client()
        mock_client.reasoning.complete_trace = AsyncMock(side_effect=Exception("complete failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("memory_complete_trace", {"trace_id": "t1"})
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_memory_get_observations_fallback_error(self):
        """Test fallback path when no observer and client also fails."""
        mock_client = make_mock_client()
        mock_client.short_term.get_conversation = AsyncMock(side_effect=Exception("obs failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("memory_get_observations", {"session_id": "s1"})
            data = json.loads(result.content[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_graph_query_write_blocked(self):
        mock_client = make_mock_client()
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("graph_query", {"query": "CREATE (n:Test)"})
            data = json.loads(result.content[0].text)
            assert "error" in data
            assert "read-only" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_graph_query_backend_error(self):
        mock_client = make_mock_client()
        mock_client.graph.execute_read = AsyncMock(side_effect=Exception("query failed"))
        server = create_tool_server(mock_client)

        async with Client(server) as client:
            result = await client.call_tool("graph_query", {"query": "MATCH (n) RETURN n LIMIT 1"})
            data = json.loads(result.content[0].text)
            assert "error" in data
