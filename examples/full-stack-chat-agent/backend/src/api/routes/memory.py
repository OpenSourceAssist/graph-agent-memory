"""Memory management API endpoints.

Uses neo4j-agent-memory's new features for improved memory operations.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from neo4j_agent_memory.memory.semantic import Preference as SemanticPreference
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
        # Get recent messages from episodic memory
        if thread_id:
            conversation = await memory.episodic.get_conversation(
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
            pref_results = await memory.semantic.search_preferences(query, limit=10)
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
                        SemanticPreference(
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
            entity_results = await memory.semantic.search_entities(query, limit=10)
        else:
            entity_results = await memory.semantic.search_entities("", limit=10)

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
        pref = await memory.semantic.add_preference(
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
        results = await memory.semantic.search_entities(search_query, limit=50)

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
            memory_types=["episodic", "semantic", "procedural"],
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
    """Delete a specific message from episodic memory.

    Uses the new delete_message() API.

    Args:
        message_id: The ID of the message to delete.
        cascade: Whether to also delete related MENTIONS relationships.
    """
    memory = get_memory_client()
    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        deleted = await memory.episodic.delete_message(message_id, cascade=cascade)

        if deleted:
            return {"status": "deleted", "message_id": message_id}
        else:
            raise HTTPException(status_code=404, detail="Message not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
