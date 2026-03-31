"""Shared utilities for MCP tool, resource, and prompt modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient
    from neo4j_agent_memory.integration import MemoryIntegration
    from neo4j_agent_memory.mcp._observer import MemoryObserver


def get_client(ctx: Context) -> MemoryClient:
    """Get MemoryClient from lifespan context.

    Args:
        ctx: FastMCP context with lifespan data.

    Returns:
        The MemoryClient instance.
    """
    return ctx.request_context.lifespan_context["client"]


def get_integration(ctx: Context) -> MemoryIntegration:
    """Get MemoryIntegration from lifespan context.

    Args:
        ctx: FastMCP context with lifespan data.

    Returns:
        The MemoryIntegration instance.
    """
    return ctx.request_context.lifespan_context["integration"]


def get_observer(ctx: Context) -> MemoryObserver | None:
    """Get MemoryObserver from lifespan context, if available.

    Args:
        ctx: FastMCP context with lifespan data.

    Returns:
        The MemoryObserver instance, or None if not configured.
    """
    return ctx.request_context.lifespan_context.get("observer")
