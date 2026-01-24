"""Memory management API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from neo4j_agent_memory.memory.long_term import Preference as LongTermPreference
from src.api.schemas import (
    ConversationRef,
    Entity,
    GraphNode,
    GraphRelationship,
    LocationEntity,
    MemoryContext,
    MemoryGraph,
    Preference,
    PreferenceRequest,
    ReasoningStepResponse,
    ReasoningTraceResponse,
    RecentMessage,
    ToolCallResponse,
    ToolStatsResponse,
)
from src.memory.client import get_memory_client

router = APIRouter()


# ============================================================================
# Procedural Memory Endpoints
# ============================================================================


@router.get("/memory/traces", response_model=list[ReasoningTraceResponse])
async def list_traces(
    thread_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    success_only: bool | None = None,
) -> list[ReasoningTraceResponse]:
    """List reasoning traces, optionally filtered by thread/session.

    Uses the new list_traces() API from neo4j-agent-memory for efficient
    trace listing with filtering and pagination.

    Args:
        thread_id: Optional thread ID to filter traces by session.
        limit: Maximum number of traces to return.
        offset: Number of traces to skip (for pagination).
        success_only: Filter by success status (True/False/None for all).
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        # Use the new list_traces() API for efficient listing
        traces = await memory.procedural.list_traces(
            session_id=thread_id,
            success_only=success_only,
            limit=limit,
            offset=offset,
            order_by="started_at",
            order_dir="desc",
        )

        return [
            ReasoningTraceResponse(
                id=str(trace.id),
                session_id=trace.session_id,
                task=trace.task,
                outcome=trace.outcome,
                success=trace.success,
                started_at=trace.started_at.isoformat() if trace.started_at else None,
                completed_at=trace.completed_at.isoformat() if trace.completed_at else None,
                step_count=len(trace.steps) if trace.steps else 0,
            )
            for trace in traces
        ]
    except Exception as e:
        import traceback

        traceback.print_exc()
        return []


@router.get("/memory/traces/{trace_id}", response_model=ReasoningTraceResponse)
async def get_trace(trace_id: str) -> ReasoningTraceResponse:
    """Get a specific reasoning trace with all steps and tool calls.

    Args:
        trace_id: The trace ID to retrieve.
    """
    memory = get_memory_client()
    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        trace = await memory.procedural.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")

        # Convert steps to response format
        steps = []
        for step in trace.steps or []:
            tool_calls = [
                ToolCallResponse(
                    id=str(tc.id),
                    tool_name=tc.tool_name,
                    arguments=tc.arguments,
                    result=tc.result,
                    status=tc.status.value,
                    duration_ms=tc.duration_ms,
                    error=tc.error,
                )
                for tc in (step.tool_calls or [])
            ]
            steps.append(
                ReasoningStepResponse(
                    id=str(step.id),
                    step_number=step.step_number,
                    thought=step.thought,
                    action=step.action,
                    observation=step.observation,
                    tool_calls=tool_calls,
                )
            )

        return ReasoningTraceResponse(
            id=str(trace.id),
            session_id=trace.session_id,
            task=trace.task,
            outcome=trace.outcome,
            success=trace.success,
            started_at=trace.started_at.isoformat() if trace.started_at else None,
            completed_at=trace.completed_at.isoformat() if trace.completed_at else None,
            step_count=len(steps),
            steps=steps,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/tool-stats", response_model=list[ToolStatsResponse])
async def get_tool_stats() -> list[ToolStatsResponse]:
    """Get usage statistics for all tools.

    Uses the new optimized get_tool_stats() API from neo4j-agent-memory
    which uses pre-aggregated statistics on Tool nodes for fast retrieval.

    Returns aggregated statistics for each tool including success rate,
    average duration, and total call count.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        # Use the new optimized get_tool_stats() API
        stats = await memory.procedural.get_tool_stats()
        return [
            ToolStatsResponse(
                name=tool.name,
                description=tool.description,
                success_rate=tool.success_rate,
                avg_duration_ms=tool.avg_duration_ms,
                total_calls=tool.total_calls,
            )
            for tool in stats
        ]
    except Exception:
        return []


@router.get("/memory/similar-traces")
async def get_similar_traces(
    task: str,
    limit: int = 5,
    success_only: bool = True,
) -> list[ReasoningTraceResponse]:
    """Find similar past reasoning traces for a given task.

    Args:
        task: The task description to find similar traces for.
        limit: Maximum number of traces to return.
        success_only: Only return successful traces.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        traces = await memory.procedural.get_similar_traces(
            task=task,
            limit=limit,
            success_only=success_only,
        )
        return [
            ReasoningTraceResponse(
                id=str(trace.id),
                session_id=trace.session_id,
                task=trace.task,
                outcome=trace.outcome,
                success=trace.success,
                started_at=trace.started_at.isoformat() if trace.started_at else None,
                completed_at=trace.completed_at.isoformat() if trace.completed_at else None,
                similarity=trace.metadata.get("similarity") if trace.metadata else None,
            )
            for trace in traces
        ]
    except Exception:
        return []


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
            if conversation and conversation.messages:
                for msg in conversation.messages[-10:]:
                    recent_messages.append(
                        RecentMessage(
                            id=str(msg.id),
                            role=msg.role.value,
                            content=(msg.content[:200] + ("..." if len(msg.content) > 200 else "")),
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
            except Exception:
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
                    id=str(ent.id),
                    name=ent.name,
                    type=ent.type if isinstance(ent.type, str) else ent.type.value,
                    subtype=getattr(ent, "subtype", None),
                    description=ent.description,
                )
            )

    except Exception:
        pass

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
                    created_at=None,
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
            id=str(pref.id),
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
    return {"status": "deleted", "preference_id": preference_id}


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
                        id=str(ent.id),
                        name=ent.name,
                        type=ent_type,
                        subtype=getattr(ent, "subtype", None),
                        description=ent.description,
                    )
                )

    except Exception:
        pass

    return entities


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


@router.get("/memory/graph", response_model=MemoryGraph)
async def get_memory_graph(
    memory_types: str | None = None,
    session_id: str | None = None,
    limit: int = 1000,
) -> MemoryGraph:
    """Get the memory graph for visualization.

    Uses the new get_graph() API from neo4j-agent-memory for efficient
    graph export with filtering options.

    Args:
        memory_types: Comma-separated list of memory types to include
                     (short_term, long_term, procedural). Defaults to all.
        session_id: Optional session ID to filter by.
        limit: Maximum number of nodes to return.

    Returns all nodes and relationships from the memory graph database.
    """
    memory = get_memory_client()
    if memory is None:
        return MemoryGraph(nodes=[], relationships=[])

    try:
        # Parse memory types if provided
        types_list = None
        if memory_types:
            types_list = [t.strip() for t in memory_types.split(",")]

        # Use the new get_graph() API
        graph = await memory.get_graph(
            memory_types=types_list,
            session_id=session_id,
            include_embeddings=False,  # Don't include embeddings for visualization
            limit=limit,
        )

        # Convert to response format (the API already returns the right structure)
        nodes = [
            GraphNode(
                id=node.id,
                labels=node.labels,
                properties={k: serialize_neo4j_value(v) for k, v in node.properties.items()},
            )
            for node in graph.nodes
        ]

        relationships = [
            GraphRelationship(
                id=rel.id,
                from_node=rel.from_node,
                to_node=rel.to_node,
                type=rel.type,
                properties={k: serialize_neo4j_value(v) for k, v in rel.properties.items()},
            )
            for rel in graph.relationships
        ]

        return MemoryGraph(nodes=nodes, relationships=relationships)

    except Exception as e:
        import traceback

        print(f"Error fetching memory graph: {e}")
        traceback.print_exc()
        return MemoryGraph(nodes=[], relationships=[])


@router.get("/locations", response_model=list[LocationEntity])
async def get_locations(
    limit: int = 500,
    has_coordinates: bool = True,
) -> list[LocationEntity]:
    """Get Location entities with coordinates for map display.

    Args:
        limit: Maximum number of locations to return (default 500, max 2000).
        has_coordinates: If True, only return locations with coordinates.

    Returns:
        List of location entities with coordinates and related conversations.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    # Clamp limit
    limit = min(max(1, limit), 2000)

    try:
        # Query for Location entities with coordinates and their related conversations
        # The relationship path: Entity <- EXTRACTED_FROM - Message <- HAS_MESSAGE - Conversation
        if has_coordinates:
            query = """
            MATCH (e:Entity)
            WHERE e.type = 'LOCATION' AND e.location IS NOT NULL
            OPTIONAL MATCH (e)<-[:EXTRACTED_FROM]-(m:Message)<-[:HAS_MESSAGE]-(c:Conversation)
            WITH e,
                 e.location.latitude AS lat,
                 e.location.longitude AS lng,
                 collect(DISTINCT CASE WHEN c IS NOT NULL
                    THEN {id: c.session_id, title: coalesce(c.title, c.session_id)}
                    ELSE NULL END) AS convs
            WHERE lat IS NOT NULL AND lng IS NOT NULL
            RETURN e.id AS id,
                   e.name AS name,
                   e.subtype AS subtype,
                   e.description AS description,
                   e.enriched_description AS enriched_description,
                   e.wikipedia_url AS wikipedia_url,
                   lat AS latitude,
                   lng AS longitude,
                   [c IN convs WHERE c IS NOT NULL] AS conversations
            LIMIT $limit
            """
        else:
            query = """
            MATCH (e:Entity)
            WHERE e.type = 'LOCATION'
            OPTIONAL MATCH (e)<-[:EXTRACTED_FROM]-(m:Message)<-[:HAS_MESSAGE]-(c:Conversation)
            WITH e,
                 e.location.latitude AS lat,
                 e.location.longitude AS lng,
                 collect(DISTINCT CASE WHEN c IS NOT NULL
                    THEN {id: c.session_id, title: coalesce(c.title, c.session_id)}
                    ELSE NULL END) AS convs
            RETURN e.id AS id,
                   e.name AS name,
                   e.subtype AS subtype,
                   e.description AS description,
                   e.enriched_description AS enriched_description,
                   e.wikipedia_url AS wikipedia_url,
                   lat AS latitude,
                   lng AS longitude,
                   [c IN convs WHERE c IS NOT NULL] AS conversations
            LIMIT $limit
            """

        results = await memory._client.execute_read(query, {"limit": limit})

        locations = []
        for row in results:
            # Skip if no coordinates (shouldn't happen with has_coordinates=True)
            if row["latitude"] is None or row["longitude"] is None:
                continue

            # Parse conversations
            convs = []
            for c in row["conversations"] or []:
                if c and isinstance(c, dict):
                    convs.append(
                        ConversationRef(
                            id=c.get("id", ""),
                            title=c.get("title"),
                        )
                    )

            locations.append(
                LocationEntity(
                    id=row["id"],
                    name=row["name"],
                    subtype=row["subtype"],
                    description=row["description"],
                    enriched_description=row["enriched_description"],
                    wikipedia_url=row["wikipedia_url"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    conversations=convs,
                )
            )

        return locations

    except Exception as e:
        import traceback

        print(f"Error fetching locations: {e}")
        traceback.print_exc()
        return []


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
        import traceback

        print(f"Error fetching node neighbors: {e}")
        traceback.print_exc()
        return MemoryGraph(nodes=[], relationships=[])
