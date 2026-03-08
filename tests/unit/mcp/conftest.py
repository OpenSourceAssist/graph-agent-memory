"""Shared fixtures for MCP unit tests.

Provides reusable mock objects and server factories for testing
FastMCP tools, resources, and prompts.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP


def make_mock_client() -> MagicMock:
    """Create a mock MemoryClient with all required sub-clients.

    Returns:
        MagicMock with short_term, long_term, reasoning, and graph attributes.
    """
    client = MagicMock()
    client.short_term = MagicMock()
    client.long_term = MagicMock()
    client.reasoning = MagicMock()
    client.graph = MagicMock()
    return client


def create_tool_server(mock_client: MagicMock) -> FastMCP:
    """Create a FastMCP server with tools registered and a mock client.

    Args:
        mock_client: Mock MemoryClient to inject via lifespan.

    Returns:
        Configured FastMCP server with tools registered.
    """

    @asynccontextmanager
    async def mock_lifespan(server):
        yield {"client": mock_client}

    mcp = FastMCP("test-tools", lifespan=mock_lifespan)

    from neo4j_agent_memory.mcp._tools import register_tools

    register_tools(mcp)
    return mcp


def create_resource_server(mock_client: MagicMock) -> FastMCP:
    """Create a FastMCP server with resources registered and a mock client.

    Args:
        mock_client: Mock MemoryClient to inject via lifespan.

    Returns:
        Configured FastMCP server with resources registered.
    """

    @asynccontextmanager
    async def mock_lifespan(server):
        yield {"client": mock_client}

    mcp = FastMCP("test-resources", lifespan=mock_lifespan)

    from neo4j_agent_memory.mcp._resources import register_resources

    register_resources(mcp)
    return mcp


@pytest.fixture
def mock_client() -> MagicMock:
    """Fixture providing a fresh mock MemoryClient."""
    return make_mock_client()
