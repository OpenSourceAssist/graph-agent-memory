"""Unit tests for FastMCP tool registration.

Tests that tools register correctly on a FastMCP server with proper
names, descriptions, and schemas. Replaces old tools.py schema tests.
"""

import pytest
from fastmcp import FastMCP


class TestFastMCPToolRegistration:
    """Tests that all tools register correctly."""

    @pytest.fixture
    def mcp_server(self):
        """Create a FastMCP server with tools registered."""
        from neo4j_agent_memory.mcp._tools import register_tools

        mcp = FastMCP("test-server")
        register_tools(mcp)
        return mcp

    @pytest.mark.asyncio
    async def test_all_6_tools_registered(self, mcp_server):
        """Test that exactly 6 tools are registered."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            assert len(tools) == 6

    @pytest.mark.asyncio
    async def test_tool_names(self, mcp_server):
        """Test that the expected tool names are registered."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert names == {
                "memory_search",
                "memory_store",
                "entity_lookup",
                "conversation_history",
                "graph_query",
                "add_reasoning_trace",
            }

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self, mcp_server):
        """Test that all tools have non-empty descriptions."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            for tool in tools:
                assert tool.description, f"Tool {tool.name} has no description"

    @pytest.mark.asyncio
    async def test_memory_search_schema(self, mcp_server):
        """Test memory_search has correct required params."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "memory_search")
            assert "query" in tool.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def test_memory_store_schema(self, mcp_server):
        """Test memory_store has correct required params."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "memory_store")
            required = tool.inputSchema.get("required", [])
            assert "memory_type" in required
            assert "content" in required

    @pytest.mark.asyncio
    async def test_entity_lookup_schema(self, mcp_server):
        """Test entity_lookup has correct required params."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "entity_lookup")
            assert "name" in tool.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def test_conversation_history_schema(self, mcp_server):
        """Test conversation_history has correct required params."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "conversation_history")
            assert "session_id" in tool.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def test_graph_query_schema(self, mcp_server):
        """Test graph_query has correct required params."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "graph_query")
            assert "query" in tool.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def test_memory_search_description_mentions_search(self, mcp_server):
        """Test memory_search description is meaningful."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "memory_search")
            assert "search" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_graph_query_description_mentions_read_only(self, mcp_server):
        """Test graph_query description mentions read-only."""
        from fastmcp import Client

        async with Client(mcp_server) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "graph_query")
            assert "read-only" in tool.description.lower()
