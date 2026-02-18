"""MCP tool implementations for Neo4j Agent Memory.

Defines the 5 core tools as FastMCP @mcp.tool decorated functions:
- memory_search: Hybrid vector + graph search
- memory_store: Store memories (messages, facts, preferences)
- entity_lookup: Get entity with relationships
- conversation_history: Get conversation for session
- graph_query: Execute read-only Cypher queries
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from fastmcp import Context

from neo4j_agent_memory.mcp._common import get_client

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Patterns for detecting write operations in Cypher (matched against uppercased query).
# Note: CALL db.* and CALL apoc.* are allowed since many procedures are read-only
# (e.g., db.index.vector.queryNodes, apoc.meta.data). The database itself will
# reject writes when executed via execute_read().
WRITE_PATTERNS = [
    r"\bCREATE\b",
    r"\bMERGE\b",
    r"\bDELETE\b",
    r"\bDETACH\s+DELETE\b",
    r"\bSET\b",
    r"\bREMOVE\b",
    r"\bDROP\b",
    r"\bLOAD\s+CSV\b",
    r"\bFOREACH\b",
    r"\bCALL\s+\{",
    r"\bIN\s+TRANSACTIONS\b",
]


def _is_read_only_query(query: str) -> bool:
    """Check if a Cypher query is read-only.

    Args:
        query: The Cypher query to check.

    Returns:
        True if the query contains no write operations.
    """
    query_upper = query.upper()
    return all(not re.search(pattern, query_upper) for pattern in WRITE_PATTERNS)


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.tool()
    async def memory_search(
        ctx: Context,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        session_id: str | None = None,
        threshold: float = 0.7,
    ) -> str:
        """Search across all memory types using hybrid vector + graph search.

        Finds relevant messages, entities, preferences, and reasoning traces.
        """
        client = get_client(ctx)

        if memory_types is None:
            memory_types = ["messages", "entities", "preferences"]

        results: dict[str, list[dict[str, Any]]] = {}

        try:
            if "messages" in memory_types:
                messages = await client.short_term.search_messages(
                    query=query,
                    session_id=session_id,
                    limit=limit,
                    threshold=threshold,
                )
                results["messages"] = [
                    {
                        "id": str(msg.id),
                        "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                        "similarity": msg.metadata.get("similarity") if msg.metadata else None,
                    }
                    for msg in messages
                ]

            if "entities" in memory_types:
                entities = await client.long_term.search_entities(
                    query=query,
                    limit=limit,
                )
                results["entities"] = [
                    {
                        "id": str(entity.id),
                        "name": entity.display_name,
                        "type": (
                            entity.type.value if hasattr(entity.type, "value") else str(entity.type)
                        ),
                        "description": entity.description,
                    }
                    for entity in entities
                ]

            if "preferences" in memory_types:
                preferences = await client.long_term.search_preferences(
                    query=query,
                    limit=limit,
                )
                results["preferences"] = [
                    {
                        "id": str(pref.id),
                        "category": pref.category,
                        "preference": pref.preference,
                        "context": pref.context,
                    }
                    for pref in preferences
                ]

            if "traces" in memory_types:
                traces = await client.reasoning.get_similar_traces(
                    task=query,
                    limit=limit,
                )
                results["traces"] = [
                    {
                        "id": str(trace.id),
                        "task": trace.task,
                        "outcome": trace.outcome,
                        "success": trace.success,
                    }
                    for trace in traces
                ]

        except Exception as e:
            logger.error(f"Error in memory_search: {e}")
            return json.dumps({"error": str(e)})

        return json.dumps({"results": results, "query": query}, default=str)

    @mcp.tool()
    async def memory_store(
        ctx: Context,
        memory_type: str,
        content: str,
        session_id: str | None = None,
        role: str = "user",
        category: str | None = None,
        subject: str | None = None,
        predicate: str | None = None,
        object_value: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory in the knowledge graph.

        Supports messages, facts (SPO triples), and user preferences.
        Automatically extracts entities from message content.

        Args:
            memory_type: Type of memory - 'message', 'fact', or 'preference'.
            content: The content to store.
            session_id: Session ID (required for message type).
            role: Message role - 'user', 'assistant', or 'system' (default: 'user').
            category: Preference category (required for preference type).
            subject: Fact subject (required for fact type).
            predicate: Fact predicate/relationship (required for fact type).
            object_value: Fact object (required for fact type).
            metadata: Optional metadata to attach.
        """
        client = get_client(ctx)

        try:
            if memory_type == "message":
                if not session_id:
                    return json.dumps({"error": "session_id required for message storage"})

                message = await client.short_term.add_message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    metadata=metadata,
                    extract_entities=True,
                    generate_embedding=True,
                )
                return json.dumps(
                    {
                        "stored": True,
                        "type": "message",
                        "id": str(message.id),
                        "session_id": session_id,
                    }
                )

            elif memory_type == "preference":
                if not category:
                    return json.dumps({"error": "category required for preference storage"})

                preference = await client.long_term.add_preference(
                    category=category,
                    preference=content,
                    generate_embedding=True,
                )
                return json.dumps(
                    {
                        "stored": True,
                        "type": "preference",
                        "id": str(preference.id),
                        "category": category,
                    }
                )

            elif memory_type == "fact":
                if not all([subject, predicate, object_value]):
                    return json.dumps(
                        {"error": "subject, predicate, and object_value required for fact storage"}
                    )

                fact = await client.long_term.add_fact(
                    subject=subject,
                    predicate=predicate,
                    obj=object_value,
                )
                return json.dumps(
                    {
                        "stored": True,
                        "type": "fact",
                        "id": str(fact.id) if hasattr(fact, "id") else None,
                        "triple": f"{subject} -> {predicate} -> {object_value}",
                    }
                )

            else:
                return json.dumps({"error": f"Unknown memory type: {memory_type}"})

        except Exception as e:
            logger.error(f"Error in memory_store: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def entity_lookup(
        ctx: Context,
        name: str,
        entity_type: str | None = None,
        include_neighbors: bool = True,
        max_hops: int = 1,
    ) -> str:
        """Look up an entity and retrieve its relationships and neighbors.

        Searches the knowledge graph for entities by name, with optional
        graph traversal to find related entities.
        """
        client = get_client(ctx)

        try:
            entities = await client.long_term.search_entities(
                query=name,
                entity_types=[entity_type] if entity_type else None,
                limit=1,
            )

            if not entities:
                return json.dumps({"found": False, "name": name})

            entity = entities[0]
            result: dict[str, Any] = {
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
            }

            if include_neighbors:
                neighbors = await _get_entity_neighbors(client, str(entity.id), max_hops)
                result["neighbors"] = neighbors

            return json.dumps(result, default=str)

        except Exception as e:
            logger.error(f"Error in entity_lookup: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def conversation_history(
        ctx: Context,
        session_id: str,
        limit: int = 50,
        before: str | None = None,
        include_metadata: bool = True,
    ) -> str:
        """Retrieve conversation history for a session.

        Returns messages in chronological order with role, content, and metadata.
        """
        client = get_client(ctx)

        try:
            conversation = await client.short_term.get_conversation(
                session_id=session_id,
                limit=limit,
            )

            messages = []
            for msg in conversation.messages:
                msg_data: dict[str, Any] = {
                    "id": str(msg.id),
                    "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                }
                if include_metadata and msg.metadata:
                    msg_data["metadata"] = msg.metadata
                messages.append(msg_data)

            return json.dumps(
                {
                    "session_id": session_id,
                    "message_count": len(messages),
                    "messages": messages,
                },
                default=str,
            )

        except Exception as e:
            logger.error(f"Error in conversation_history: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def graph_query(
        ctx: Context,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """Execute a read-only Cypher query against the knowledge graph.

        Only MATCH/RETURN queries are allowed. Write operations
        (CREATE, MERGE, DELETE, SET, REMOVE) are blocked for safety.
        """
        if not _is_read_only_query(query):
            return json.dumps(
                {
                    "error": "Only read-only queries are allowed. "
                    "Write operations (CREATE, MERGE, DELETE, SET, REMOVE) are not permitted."
                }
            )

        client = get_client(ctx)

        try:
            records = await client.graph.execute_read(query, parameters or {})
            return json.dumps(
                {
                    "success": True,
                    "row_count": len(records),
                    "rows": records,
                },
                default=str,
            )

        except Exception as e:
            logger.error(f"Error in graph_query: {e}")
            return json.dumps({"error": str(e)})


async def _get_entity_neighbors(
    client,
    entity_id: str,
    max_hops: int = 1,
) -> list[dict[str, Any]]:
    """Get neighboring entities via graph traversal.

    Args:
        client: MemoryClient instance.
        entity_id: Starting entity ID.
        max_hops: Maximum relationship depth (clamped to 1-3).

    Returns:
        List of neighboring entities with relationships.
    """
    max_hops = min(max(max_hops, 1), 3)
    query = f"""
    MATCH (e:Entity {{id: $entity_id}})-[r*1..{max_hops}]-(neighbor:Entity)
    WHERE neighbor.id <> $entity_id
    WITH DISTINCT neighbor, r
    RETURN neighbor.id AS id,
           neighbor.name AS name,
           neighbor.type AS type,
           neighbor.description AS description
    LIMIT 20
    """

    try:
        records = await client.graph.execute_read(
            query,
            {"entity_id": entity_id},
        )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "description": r["description"],
            }
            for r in records
        ]
    except Exception as e:
        logger.debug(f"Error getting neighbors: {e}")
        return []
