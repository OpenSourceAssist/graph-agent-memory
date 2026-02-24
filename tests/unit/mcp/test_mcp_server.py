"""Unit tests for FastMCP server creation and configuration."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCreateMCPServer:
    """Tests for the create_mcp_server factory function."""

    def test_create_mcp_server_returns_fastmcp_instance(self):
        """Test that create_mcp_server returns a FastMCP server."""
        from fastmcp import FastMCP

        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server()
        assert isinstance(server, FastMCP)

    def test_create_mcp_server_default_name(self):
        """Test that the default server name is 'neo4j-agent-memory'."""
        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server()
        assert server.name == "neo4j-agent-memory"

    def test_create_mcp_server_custom_name(self):
        """Test that a custom server name can be provided."""
        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server(server_name="custom-server")
        assert server.name == "custom-server"

    def test_create_mcp_server_with_settings_is_configured(self):
        """Test that a server created with settings is a valid FastMCP instance."""
        from fastmcp import FastMCP

        from neo4j_agent_memory.mcp.server import create_mcp_server

        mock_settings = MagicMock()
        server = create_mcp_server(settings=mock_settings)
        assert isinstance(server, FastMCP)
        assert server.name == "neo4j-agent-memory"

    def test_create_mcp_server_without_settings_registers_tools(self):
        """Test that a server without settings has tools registered and accessible."""
        import asyncio

        from fastmcp import Client

        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server()

        async def _check():
            async with Client(server) as client:
                tools = await client.list_tools()
                assert len(tools) == 6

        asyncio.run(_check())


class TestNeo4jMemoryMCPServerBackwardCompat:
    """Tests for backward-compatible Neo4jMemoryMCPServer wrapper."""

    def test_neo4j_memory_mcp_server_accepts_client(self):
        """Test that Neo4jMemoryMCPServer can be created with a pre-connected client."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client)
        assert server._client is mock_client

    def test_neo4j_memory_mcp_server_has_mcp_attribute(self):
        """Test that the wrapper exposes the underlying FastMCP instance."""
        from fastmcp import FastMCP

        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client)
        assert isinstance(server._mcp, FastMCP)

    def test_neo4j_memory_mcp_server_default_name(self):
        """Test the default server name in backward-compat mode."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client)
        assert server._mcp.name == "neo4j-agent-memory"

    def test_neo4j_memory_mcp_server_custom_name(self):
        """Test custom server name in backward-compat mode."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client, server_name="custom")
        assert server._mcp.name == "custom"


class TestCLIEntryPoint:
    """Tests for the CLI entry point."""

    def test_main_function_exists(self):
        """Test that main() is importable."""
        from neo4j_agent_memory.mcp.server import main

        assert callable(main)

    def test_run_server_function_exists(self):
        """Test that run_server() is importable."""
        from neo4j_agent_memory.mcp.server import run_server

        assert callable(run_server)


class TestModuleExports:
    """Tests for module-level exports."""

    def test_init_exports_create_mcp_server(self):
        """Test that create_mcp_server is exported from __init__."""
        from neo4j_agent_memory.mcp import create_mcp_server

        assert callable(create_mcp_server)

    def test_init_exports_neo4j_memory_mcp_server(self):
        """Test that Neo4jMemoryMCPServer is exported from __init__."""
        from neo4j_agent_memory.mcp import Neo4jMemoryMCPServer

        assert Neo4jMemoryMCPServer is not None
