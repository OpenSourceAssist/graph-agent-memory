"""MCP resource definitions for Neo4j Agent Memory.

Defines 4 resources that expose memory data via URI templates:
- memory://conversations/{session_id}: Conversation history
- memory://entities/{entity_name}: Entity details
- memory://preferences/{category}: User preferences
- memory://graph/stats: Knowledge graph statistics
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


def register_resources(mcp: FastMCP) -> None:
    """Register all MCP resources on the server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.resource("memory://conversations/{session_id}")
    async def get_conversation(session_id: str, ctx: Context) -> str:
        """Get conversation history for a session.

        Returns the full message history for the given session ID.
        """
        client = get_client(ctx)
        conversation = await client.short_term.get_conversation(session_id=session_id, limit=100)
        messages = [
            {
                "id": str(msg.id),
                "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                "content": msg.content,
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in conversation.messages
        ]
        return json.dumps({"session_id": session_id, "messages": messages}, default=str)

    @mcp.resource("memory://entities/{entity_name}")
    async def get_entity(entity_name: str, ctx: Context) -> str:
        """Get entity details and relationships from the knowledge graph.

        Looks up an entity by name and returns its properties.
        """
        client = get_client(ctx)
        entities = await client.long_term.search_entities(query=entity_name, limit=1)
        if not entities:
            return json.dumps({"found": False, "name": entity_name})

        entity = entities[0]
        return json.dumps(
            {
                "found": True,
                "entity": {
                    "id": str(entity.id),
                    "name": entity.display_name,
                    "type": (
                        entity.type.value if hasattr(entity.type, "value") else str(entity.type)
                    ),
                    "description": entity.description,
                    "aliases": entity.aliases if hasattr(entity, "aliases") else [],
                },
            },
            default=str,
        )

    @mcp.resource("memory://preferences/{category}")
    async def get_preferences(category: str, ctx: Context) -> str:
        """Get user preferences for a category.

        Returns all stored preferences matching the given category.
        """
        client = get_client(ctx)
        preferences = await client.long_term.search_preferences(query=category, limit=50)
        prefs = [
            {
                "id": str(p.id),
                "category": p.category,
                "preference": p.preference,
                "context": p.context,
            }
            for p in preferences
        ]
        return json.dumps({"category": category, "preferences": prefs}, default=str)

    @mcp.resource("memory://graph/stats")
    async def get_graph_stats(ctx: Context) -> str:
        """Get knowledge graph statistics.

        Returns node/relationship counts and entity type distribution.
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
