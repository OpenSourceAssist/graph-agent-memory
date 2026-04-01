"""MCP resource definitions for Neo4j Agent Memory.

Resources provide auto-injected context to the LLM. They are organized
into profiles:
- Core: memory://context/{session_id} (assembled context for a session)
- Extended: memory://entities, memory://preferences, memory://graph/stats
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from fastmcp import Context

from neo4j_agent_memory.mcp._common import get_client

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_resources(mcp: FastMCP, *, profile: str = "extended") -> None:
    """Register MCP resources on the server based on profile.

    Args:
        mcp: FastMCP server instance.
        profile: Tool profile - 'core' or 'extended'.
    """
    _register_core_resources(mcp)
    if profile == "extended":
        _register_extended_resources(mcp)


def _register_core_resources(mcp: FastMCP) -> None:
    """Register the core resource (context template)."""

    @mcp.resource("memory://context/{session_id}")
    async def get_context(session_id: str, ctx: Context) -> str:
        """Assembled context for a session.

        Returns conversation history, relevant entities, preferences,
        and similar reasoning traces for the given session. Suitable
        for embedding in the system prompt at conversation start.
        """
        client = get_client(ctx)
        try:
            context = await client.get_context(
                query="",
                session_id=session_id,
            )
            return json.dumps(
                {
                    "session_id": session_id,
                    "context": context,
                    "has_context": bool(context),
                },
                default=str,
            )
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return json.dumps({"error": str(e)})


def _register_extended_resources(mcp: FastMCP) -> None:
    """Register extended resources (entities catalog, preferences, stats)."""

    @mcp.resource("memory://entities")
    async def get_entities_catalog(ctx: Context) -> str:
        """Catalog of all entities in the knowledge graph.

        Returns entity names, types, descriptions, and relationship counts.
        Useful for understanding what the memory system knows about.
        """
        client = get_client(ctx)
        try:
            entities = await client.long_term.search_entities(query="", limit=100)
            entity_list = [
                {
                    "id": str(e.id),
                    "name": e.display_name,
                    "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                    "subtype": e.subtype if hasattr(e, "subtype") else None,
                    "description": e.description,
                }
                for e in entities
            ]
            return json.dumps(
                {"entity_count": len(entity_list), "entities": entity_list},
                default=str,
            )
        except Exception as e:
            logger.error(f"Error getting entities catalog: {e}")
            return json.dumps({"error": str(e)})

    @mcp.resource("memory://preferences")
    async def get_all_preferences(ctx: Context) -> str:
        """All stored user preferences organized by category.

        Returns preferences for personalization. Auto-included
        when the LLM needs to personalize responses.
        """
        client = get_client(ctx)
        try:
            preferences = await client.long_term.search_preferences(query="", limit=100)
            pref_list = [
                {
                    "id": str(p.id),
                    "category": p.category,
                    "preference": p.preference,
                    "context": p.context,
                    "confidence": p.confidence if hasattr(p, "confidence") else None,
                }
                for p in preferences
            ]
            return json.dumps(
                {"preference_count": len(pref_list), "preferences": pref_list},
                default=str,
            )
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return json.dumps({"error": str(e)})

    @mcp.resource("memory://graph/stats")
    async def get_graph_stats(ctx: Context) -> str:
        """Knowledge graph statistics.

        Returns node/relationship counts and entity type distribution.
        Useful for understanding the size and composition of the memory graph.
        """
        client = get_client(ctx)
        try:
            records = await client.graph.execute_read(
                "MATCH (n) RETURN labels(n) AS labels, count(*) AS count",
                {},
            )
            return json.dumps({"stats": records}, default=str)
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return json.dumps({"error": str(e)})
