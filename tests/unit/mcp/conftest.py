"""Shared fixtures for MCP unit tests.

Provides reusable mock objects and server factories for testing
FastMCP tools, resources, and prompts with profile support.
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


def make_mock_integration(mock_client: MagicMock | None = None) -> MagicMock:
    """Create a mock MemoryIntegration.

    Args:
        mock_client: Optional mock client to attach.

    Returns:
        MagicMock with MemoryIntegration method signatures.
    """
    integration = MagicMock()
    integration.client = mock_client or make_mock_client()
    integration.resolve_session_id = MagicMock(return_value="test-session")
    return integration


def create_tool_server(
    mock_client: MagicMock,
    *,
    profile: str = "extended",
    mock_integration: MagicMock | None = None,
) -> FastMCP:
    """Create a FastMCP server with tools registered and a mock client.

    Args:
        mock_client: Mock MemoryClient to inject via lifespan.
        profile: Tool profile - 'core' or 'extended'.
        mock_integration: Optional mock MemoryIntegration. Created from
            mock_client if not provided.

    Returns:
        Configured FastMCP server with tools registered.
    """
    integration = mock_integration or make_mock_integration(mock_client)

    @asynccontextmanager
    async def mock_lifespan(server):
        yield {"client": mock_client, "integration": integration}

    mcp = FastMCP("test-tools", lifespan=mock_lifespan)

    from neo4j_agent_memory.mcp._tools import register_tools

    register_tools(mcp, profile=profile)
    return mcp


def create_resource_server(
    mock_client: MagicMock,
    *,
    profile: str = "extended",
) -> FastMCP:
    """Create a FastMCP server with resources registered and a mock client.

    Args:
        mock_client: Mock MemoryClient to inject via lifespan.
        profile: Tool profile - 'core' or 'extended'.

    Returns:
        Configured FastMCP server with resources registered.
    """
    integration = make_mock_integration(mock_client)

    @asynccontextmanager
    async def mock_lifespan(server):
        yield {"client": mock_client, "integration": integration}

    mcp = FastMCP("test-resources", lifespan=mock_lifespan)

    from neo4j_agent_memory.mcp._resources import register_resources

    register_resources(mcp, profile=profile)
    return mcp


def create_prompt_server(
    *,
    profile: str = "extended",
) -> FastMCP:
    """Create a FastMCP server with prompts registered.

    Args:
        profile: Tool profile - 'core' or 'extended'.

    Returns:
        Configured FastMCP server with prompts registered.
    """
    mcp = FastMCP("test-prompts")

    from neo4j_agent_memory.mcp._prompts import register_prompts

    register_prompts(mcp, profile=profile)
    return mcp


@pytest.fixture
def mock_client() -> MagicMock:
    """Fixture providing a fresh mock MemoryClient."""
    return make_mock_client()
