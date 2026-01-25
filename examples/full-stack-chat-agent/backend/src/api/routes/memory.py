"""Memory management API endpoints.

Uses neo4j-agent-memory's new features for improved memory operations.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from neo4j_agent_memory.memory.long_term import Preference as LongTermPreference
from src.api.schemas import (
    Entity,
    GraphNode,
    GraphRelationship,
    MemoryContext,
    MemoryGraph,
    Preference,
    PreferenceRequest,
    RecentMessage,
)
from src.memory.client import get_memory_client

router = APIRouter()


@router.get("/memory/context", response_model=MemoryContext)
async def get_memory_context(
    thread_id: str | None = None,
    query: str | None = None,
) -> MemoryContext:
    """Get memory context for display.

    Args:
        thread_id: Optional thread ID to scope the context.
        query: Optional query to find relevant memories.
    """
    preferences = []
    entities = []
    recent_topics = []
    recent_messages = []

    memory = get_memory_client()
    if memory is None:
        return MemoryContext(
            preferences=preferences,
            entities=entities,
            recent_topics=recent_topics,
            recent_messages=recent_messages,
        )

    try:
        # Get recent messages from short-term memory
        if thread_id:
            conversation = await memory.short_term.get_conversation(
                session_id=thread_id,
                limit=10,
            )
            for msg in conversation.messages[-10:]:
                recent_messages.append(
                    RecentMessage(
                        id=str(msg.id),
                        role=msg.role.value,
                        content=msg.content[:200] + ("..." if len(msg.content) > 200 else ""),
                        created_at=msg.created_at.isoformat() if msg.created_at else None,
                    )
                )

        # Get preferences
        if query:
            pref_results = await memory.long_term.search_preferences(query, limit=10)
        else:
            # Get all preferences when no query - use direct database query
            try:
                results = await memory._client.execute_read(
                    "MATCH (p:Preference) RETURN p ORDER BY p.created_at DESC LIMIT 10"
                )
                pref_results = []
                for row in results:
                    p = dict(row["p"])
                    pref_results.append(
                        LongTermPreference(
                            id=UUID(p["id"]),
                            category=p.get("category", "general"),
                            preference=p.get("preference", ""),
                            context=p.get("context"),
                            confidence=p.get("confidence", 1.0),
                        )
                    )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(f"Failed to get preferences: {e}")
                pref_results = []

        for pref in pref_results:
            preferences.append(
                Preference(
                    id=str(pref.id),
                    category=pref.category,
                    preference=pref.preference,
                    context=pref.context,
                    confidence=pref.confidence,
                    created_at=getattr(pref, "created_at", None),
                )
            )

        # Get entities
        if query:
            entity_results = await memory.long_term.search_entities(query, limit=10)
        else:
            entity_results = await memory.long_term.search_entities("", limit=10)

        for ent in entity_results:
            entities.append(
                Entity(
                    id=ent.id,
                    name=ent.name,
                    type=ent.type if isinstance(ent.type, str) else ent.type.value,
                    subtype=getattr(ent, "subtype", None),
                    description=ent.description,
                )
            )

    except Exception as e:
        # Return empty context on error
        import logging

        logging.getLogger(__name__).warning(f"Failed to get memory context: {e}")

    return MemoryContext(
        preferences=preferences,
        entities=entities,
        recent_topics=recent_topics,
        recent_messages=recent_messages,
    )


@router.get("/preferences", response_model=list[Preference])
async def list_preferences(
    category: str | None = None,
) -> list[Preference]:
    """List user preferences, optionally filtered by category."""
    preferences = []

    memory = get_memory_client()
    if memory is None:
        return preferences

    try:
        # Get preferences via direct query for better reliability
        if category:
            query = "MATCH (p:Preference {category: $category}) RETURN p ORDER BY p.created_at DESC LIMIT 50"
            params = {"category": category}
        else:
            query = "MATCH (p:Preference) RETURN p ORDER BY p.created_at DESC LIMIT 50"
            params = {}

        results = await memory._client.execute_read(query, params)

        for row in results:
            p = dict(row["p"])
            preferences.append(
                Preference(
                    id=p["id"],
                    category=p.get("category", "general"),
                    preference=p.get("preference", ""),
                    context=p.get("context"),
                    confidence=p.get("confidence", 1.0),
                    created_at=None,  # Neo4j datetime needs conversion
                )
            )

    except Exception:
        pass

    return preferences


@router.post("/preferences", response_model=Preference)
async def add_preference(
    request: PreferenceRequest,
) -> Preference:
    """Add a new user preference."""
    memory = get_memory_client()
    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        pref = await memory.long_term.add_preference(
            category=request.category,
            preference=request.preference,
            context=request.context or "Added via API",
        )

        return Preference(
            id=pref.id,
            category=pref.category,
            preference=pref.preference,
            context=pref.context,
            confidence=pref.confidence,
            created_at=getattr(pref, "created_at", None),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/preferences/{preference_id}")
async def delete_preference(
    preference_id: str,
) -> dict:
    """Delete a preference by ID."""
    memory = get_memory_client()
    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        # Delete via direct query
        await memory._client.execute_write(
            "MATCH (p:Preference {id: $id}) DETACH DELETE p",
            {"id": preference_id},
        )
        return {"status": "deleted", "preference_id": preference_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities", response_model=list[Entity])
async def list_entities(
    type: str | None = None,
    query: str | None = None,
) -> list[Entity]:
    """List extracted entities, optionally filtered by type or search query."""
    entities = []

    memory = get_memory_client()
    if memory is None:
        return entities

    try:
        search_query = query or type or ""
        results = await memory.long_term.search_entities(search_query, limit=50)

        for ent in results:
            ent_type = ent.type if isinstance(ent.type, str) else ent.type.value
            if type is None or ent_type == type:
                entities.append(
                    Entity(
                        id=ent.id,
                        name=ent.name,
                        type=ent_type,
                        subtype=getattr(ent, "subtype", None),
                        description=ent.description,
                    )
                )

    except Exception:
        pass

    return entities


@router.get("/memory/graph", response_model=MemoryGraph)
async def get_memory_graph(
    session_id: str | None = None,
    include_embeddings: bool = False,
) -> MemoryGraph:
    """Get the memory graph for visualization.

    Uses the new get_graph() API for efficient graph export.

    Args:
        session_id: Optional session ID to filter the graph.
        include_embeddings: Whether to include embedding vectors (can be large).
    """
    memory = get_memory_client()
    if memory is None:
        return MemoryGraph(nodes=[], relationships=[])

    try:
        # Use the new get_graph() API
        graph = await memory.get_graph(
            memory_types=["short_term", "long_term", "procedural"],
            session_id=session_id,
            include_embeddings=include_embeddings,
            limit=500,
        )

        # Convert to response format
        nodes = []
        for node in graph.nodes:
            nodes.append(
                GraphNode(
                    id=node.id,
                    labels=node.labels,
                    properties=node.properties,
                )
            )

        relationships = []
        for rel in graph.relationships:
            relationships.append(
                GraphRelationship(
                    id=rel.id,
                    from_node=rel.from_node,
                    to_node=rel.to_node,
                    type=rel.type,
                    properties=rel.properties,
                )
            )

        return MemoryGraph(nodes=nodes, relationships=relationships)

    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Error fetching memory graph: {e}")
        return MemoryGraph(nodes=[], relationships=[])


@router.get("/memory/traces")
async def list_traces(
    session_id: str | None = None,
    success_only: bool | None = None,
    limit: int = 50,
) -> list[dict]:
    """List reasoning traces.

    Uses the new list_traces() API for efficient trace listing.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        traces = await memory.procedural.list_traces(
            session_id=session_id,
            success_only=success_only,
            limit=limit,
        )

        return [
            {
                "id": str(trace.id),
                "session_id": trace.session_id,
                "task": trace.task,
                "success": trace.success,
                "outcome": trace.outcome,
                "started_at": trace.started_at.isoformat() if trace.started_at else None,
                "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
                "step_count": len(trace.steps) if trace.steps else 0,
            }
            for trace in traces
        ]

    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Error listing traces: {e}")
        return []


@router.get("/memory/tool-stats")
async def get_tool_stats() -> list[dict]:
    """Get tool usage statistics.

    Uses the optimized get_tool_stats() API with pre-aggregated stats.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        stats = await memory.procedural.get_tool_stats()

        return [
            {
                "name": stat.name,
                "description": stat.description,
                "total_calls": stat.total_calls,
                "successful_calls": stat.successful_calls,
                "failed_calls": stat.failed_calls,
                "success_rate": stat.success_rate,
                "avg_duration_ms": stat.avg_duration_ms,
                "last_used_at": stat.last_used_at.isoformat() if stat.last_used_at else None,
            }
            for stat in stats
        ]

    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Error getting tool stats: {e}")
        return []


@router.delete("/memory/messages/{message_id}")
async def delete_message(
    message_id: str,
    cascade: bool = True,
) -> dict:
    """Delete a specific message from short-term memory.

    Uses the new delete_message() API.

    Args:
        message_id: The ID of the message to delete.
        cascade: Whether to also delete related MENTIONS relationships.
    """
    memory = get_memory_client()
    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        deleted = await memory.short_term.delete_message(message_id, cascade=cascade)

        if deleted:
            return {"status": "deleted", "message_id": message_id}
        else:
            raise HTTPException(status_code=404, detail="Message not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def serialize_neo4j_value(value: Any) -> Any:
    """Serialize Neo4j values to JSON-compatible format."""
    if value is None:
        return None

    # Handle Neo4j Integer
    if hasattr(value, "__class__") and value.__class__.__name__ == "Integer":
        return int(value)

    # Handle Neo4j DateTime
    if hasattr(value, "iso_format"):
        return value.iso_format()

    # Handle datetime objects
    if hasattr(value, "isoformat"):
        return value.isoformat()

    # Handle lists
    if isinstance(value, list):
        return [serialize_neo4j_value(v) for v in value]

    # Handle dicts
    if isinstance(value, dict):
        return {k: serialize_neo4j_value(v) for k, v in value.items()}

    return value


@router.get("/memory/graph/neighbors/{node_id}", response_model=MemoryGraph)
async def get_node_neighbors(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=50, ge=1, le=200),
) -> MemoryGraph:
    """Get neighbors of a specific node for graph expansion.

    This endpoint allows incremental graph exploration by fetching
    the neighbors of a specific node.

    Args:
        node_id: The ID of the node to expand.
        depth: How many hops away to retrieve (1 or 2). Default is 1.
        limit: Maximum number of neighbors to return. Default is 50.

    Returns:
        MemoryGraph containing the source node, its neighbors, and
        the relationships connecting them.
    """
    memory = get_memory_client()
    if memory is None:
        return MemoryGraph(nodes=[], relationships=[])

    try:
        # First get the source node with explicit scalar values
        source_query = """
        MATCH (n) WHERE n.id = $node_id
        RETURN n.id AS id, labels(n) AS labels, properties(n) AS props
        LIMIT 1
        """
        source_results = await memory._client.execute_read(source_query, {"node_id": node_id})

        nodes = []
        relationships = []
        seen_node_ids = set()
        seen_rel_ids = set()

        # Add the source node
        for row in source_results:
            if row["id"] and row["id"] not in seen_node_ids:
                seen_node_ids.add(row["id"])
                props = row["props"] or {}
                nodes.append(
                    GraphNode(
                        id=row["id"],
                        labels=row["labels"] or [],
                        properties={
                            k: serialize_neo4j_value(v)
                            for k, v in props.items()
                            if k != "embedding"
                        },
                    )
                )

        # Now get neighbors and relationships with explicit scalar values
        if depth == 1:
            neighbor_query = """
            MATCH (n)-[r]-(neighbor) WHERE n.id = $node_id
            RETURN neighbor.id AS neighbor_id,
                   labels(neighbor) AS neighbor_labels,
                   properties(neighbor) AS neighbor_props,
                   type(r) AS rel_type,
                   elementId(r) AS rel_id,
                   properties(r) AS rel_props,
                   startNode(r).id AS start_id,
                   endNode(r).id AS end_id
            LIMIT $limit
            """
        else:
            # depth == 2: get 2-hop neighbors
            neighbor_query = """
            MATCH path = (n)-[*1..2]-(neighbor) WHERE n.id = $node_id AND neighbor <> n
            WITH neighbor, relationships(path) AS rels
            UNWIND rels AS r
            RETURN DISTINCT neighbor.id AS neighbor_id,
                   labels(neighbor) AS neighbor_labels,
                   properties(neighbor) AS neighbor_props,
                   type(r) AS rel_type,
                   elementId(r) AS rel_id,
                   properties(r) AS rel_props,
                   startNode(r).id AS start_id,
                   endNode(r).id AS end_id
            LIMIT $limit
            """

        neighbor_results = await memory._client.execute_read(
            neighbor_query, {"node_id": node_id, "limit": limit}
        )

        for row in neighbor_results:
            # Add neighbor node
            neighbor_id = row["neighbor_id"]
            if neighbor_id and neighbor_id not in seen_node_ids:
                seen_node_ids.add(neighbor_id)
                props = row["neighbor_props"] or {}
                nodes.append(
                    GraphNode(
                        id=neighbor_id,
                        labels=row["neighbor_labels"] or [],
                        properties={
                            k: serialize_neo4j_value(v)
                            for k, v in props.items()
                            if k != "embedding"
                        },
                    )
                )

            # Add relationship
            rel_id = row["rel_id"]
            if rel_id and rel_id not in seen_rel_ids:
                seen_rel_ids.add(rel_id)
                rel_props = row["rel_props"] or {}
                relationships.append(
                    GraphRelationship(
                        id=rel_id,
                        from_node=row["start_id"],
                        to_node=row["end_id"],
                        type=row["rel_type"],
                        properties={k: serialize_neo4j_value(v) for k, v in rel_props.items()},
                    )
                )

        return MemoryGraph(nodes=nodes, relationships=relationships)

    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Error fetching node neighbors: {e}")
        return MemoryGraph(nodes=[], relationships=[])
