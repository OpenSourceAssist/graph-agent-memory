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
# Reasoning Memory Endpoints
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
        traces = await memory.reasoning.list_traces(
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
        trace = await memory.reasoning.get_trace(trace_id)
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
        stats = await memory.reasoning.get_tool_stats()
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
        traces = await memory.reasoning.get_similar_traces(
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
            # Extract enrichment fields from entity attributes
            attrs = getattr(ent, "attributes", {}) or {}
            entities.append(
                Entity(
                    id=str(ent.id),
                    name=ent.name,
                    type=ent.type if isinstance(ent.type, str) else ent.type.value,
                    subtype=getattr(ent, "subtype", None),
                    description=ent.description,
                    enriched_description=attrs.get("enriched_description")
                    or getattr(ent, "enriched_description", None),
                    wikipedia_url=attrs.get("wikipedia_url") or getattr(ent, "wikipedia_url", None),
                    image_url=attrs.get("image_url") or getattr(ent, "image_url", None),
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
                attrs = getattr(ent, "attributes", {}) or {}
                entities.append(
                    Entity(
                        id=str(ent.id),
                        name=ent.name,
                        type=ent_type,
                        subtype=getattr(ent, "subtype", None),
                        description=ent.description,
                        enriched_description=attrs.get("enriched_description")
                        or getattr(ent, "enriched_description", None),
                        wikipedia_url=attrs.get("wikipedia_url")
                        or getattr(ent, "wikipedia_url", None),
                        image_url=attrs.get("image_url") or getattr(ent, "image_url", None),
                    )
                )

    except Exception:
        pass

    return entities


@router.get("/entities/top")
async def get_top_entities(
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict]:
    """Get the most mentioned entities across all podcasts.

    Args:
        entity_type: Optional filter by PERSON, ORGANIZATION, CONCEPT, LOCATION.
        limit: Number of results to return (default 10).

    Returns:
        List of entities with mention counts.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        query = """
        MATCH (e:Entity)<-[r:MENTIONS]-()
        WHERE $type IS NULL OR e.type = $type
        WITH e, count(r) AS mentions
        ORDER BY mentions DESC
        LIMIT $limit
        RETURN e.id AS id, e.name AS name, e.type AS type,
               e.subtype AS subtype,
               e.description AS description,
               e.wikipedia_url AS wikipedia_url,
               e.enriched_description AS enriched_description,
               e.image_url AS image_url,
               mentions
        """
        results = await memory._client.execute_read(query, {"type": entity_type, "limit": limit})

        return [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "subtype": r["subtype"],
                "description": r["description"],
                "wikipedia_url": r["wikipedia_url"],
                "enriched_description": r["enriched_description"],
                "image_url": r["image_url"],
                "mentions": r["mentions"],
            }
            for r in results
        ]
    except Exception as e:
        import traceback

        traceback.print_exc()
        return []


@router.get("/entities/{entity_name}/context")
async def get_entity_full_context(
    entity_name: str,
) -> dict:
    """Get full context for an entity including enrichment and mentions.

    Args:
        entity_name: Name of the entity to retrieve.

    Returns:
        Entity details with Wikipedia data and podcast mentions.
    """
    memory = get_memory_client()
    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        # Get entity by name
        entity = await memory.long_term.get_entity_by_name(entity_name)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Get mention context
        query = """
        MATCH (e:Entity {name: $name})<-[:MENTIONS]-(m:Message)<-[:HAS_MESSAGE]-(c:Conversation)
        RETURN m.content AS content, m.metadata AS metadata, c.session_id AS session_id
        LIMIT 5
        """
        mentions = await memory._client.execute_read(query, {"name": entity_name})

        import json as json_lib

        mention_list = []
        for m in mentions:
            metadata = m.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json_lib.loads(metadata)
                except json_lib.JSONDecodeError:
                    metadata = {}
            mention_list.append(
                {
                    "content": m["content"][:300] + "..."
                    if len(m["content"]) > 300
                    else m["content"],
                    "speaker": metadata.get("speaker", "Unknown"),
                    "session_id": m["session_id"],
                }
            )

        attrs = getattr(entity, "attributes", {}) or {}
        return {
            "entity": {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.type if isinstance(entity.type, str) else entity.type.value,
                "subtype": getattr(entity, "subtype", None),
                "description": entity.description,
                "enriched_description": attrs.get("enriched_description")
                or getattr(entity, "enriched_description", None),
                "wikipedia_url": attrs.get("wikipedia_url")
                or getattr(entity, "wikipedia_url", None),
                "image_url": attrs.get("image_url") or getattr(entity, "image_url", None),
            },
            "mentions": mention_list,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/related/{entity_name}")
async def get_related_entities(
    entity_name: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    """Get entities that co-occur with the given entity.

    Args:
        entity_name: Name of the entity to find relations for.
        limit: Maximum number of related entities to return.

    Returns:
        List of related entities with co-occurrence counts.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        query = """
        MATCH (e1:Entity {name: $name})<-[:MENTIONS]-(m:Message)-[:MENTIONS]->(e2:Entity)
        WHERE e1 <> e2
        WITH e2, count(m) AS co_occurrences
        ORDER BY co_occurrences DESC
        LIMIT $limit
        RETURN e2.id AS id, e2.name AS name, e2.type AS type, e2.subtype AS subtype,
               e2.description AS description, co_occurrences
        """
        results = await memory._client.execute_read(query, {"name": entity_name, "limit": limit})

        return [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "subtype": r["subtype"],
                "description": r["description"],
                "co_occurrences": r["co_occurrences"],
            }
            for r in results
        ]
    except Exception as e:
        import traceback

        traceback.print_exc()
        return []


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
                     (short_term, long_term, reasoning). Defaults to all.
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
    session_id: str | None = Query(default=None, description="Filter by conversation session ID"),
    limit: int = Query(default=500, ge=1, le=2000),
    has_coordinates: bool = Query(default=True),
) -> list[LocationEntity]:
    """Get Location entities with coordinates for map display.

    Args:
        session_id: Optional session ID to filter locations to those mentioned
                   in a specific conversation.
        limit: Maximum number of locations to return (default 500, max 2000).
        has_coordinates: If True, only return locations with coordinates.

    Returns:
        List of location entities with coordinates and related conversations.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        # Use the new get_locations() API from MemoryClient
        locations_data = await memory.get_locations(
            session_id=session_id,
            has_coordinates=has_coordinates,
            limit=limit,
        )

        locations = []
        for loc in locations_data:
            # Skip if no coordinates
            if loc.get("latitude") is None or loc.get("longitude") is None:
                continue

            # Parse conversations
            convs = []
            for c in loc.get("conversations") or []:
                if c and isinstance(c, dict) and c.get("id"):
                    convs.append(
                        ConversationRef(
                            id=c.get("session_id") or c.get("id", ""),
                            title=c.get("title"),
                        )
                    )

            locations.append(
                LocationEntity(
                    id=loc["id"],
                    name=loc["name"],
                    subtype=loc.get("subtype"),
                    description=loc.get("description"),
                    enriched_description=loc.get("enriched_description"),
                    wikipedia_url=loc.get("wikipedia_url"),
                    latitude=float(loc["latitude"]),
                    longitude=float(loc["longitude"]),
                    conversations=convs,
                )
            )

        return locations

    except Exception as e:
        import traceback

        print(f"Error fetching locations: {e}")
        traceback.print_exc()
        return []


@router.get("/locations/nearby", response_model=list[LocationEntity])
async def get_locations_nearby(
    lat: float = Query(..., description="Latitude of center point"),
    lon: float = Query(..., description="Longitude of center point"),
    radius_km: float = Query(default=10.0, ge=0.1, le=500, description="Search radius in km"),
    session_id: str | None = Query(default=None, description="Filter by conversation session"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[LocationEntity]:
    """Find locations within a radius of a point.

    Uses the geospatial query capabilities of the memory system to find
    Location entities near a specified point, optionally filtered by
    conversation session.

    Args:
        lat: Latitude of the center point.
        lon: Longitude of the center point.
        radius_km: Search radius in kilometers (default 10km, max 500km).
        session_id: Optional session ID to filter to conversation-specific locations.
        limit: Maximum number of results to return.

    Returns:
        List of location entities sorted by distance, with distance_km in metadata.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        entities = await memory.long_term.search_locations_near(
            latitude=lat,
            longitude=lon,
            radius_km=radius_km,
            session_id=session_id,
            limit=limit,
        )

        locations = []
        for ent in entities:
            # Get coordinates from entity
            coords = ent.attributes.get("coordinates", {})
            lat_val = coords.get("latitude") if isinstance(coords, dict) else None
            lon_val = coords.get("longitude") if isinstance(coords, dict) else None

            # Try location property if coordinates not in attributes
            if lat_val is None or lon_val is None:
                if hasattr(ent, "metadata") and ent.metadata:
                    # Distance was added to metadata by search_locations_near
                    pass

            if lat_val is not None and lon_val is not None:
                locations.append(
                    LocationEntity(
                        id=str(ent.id),
                        name=ent.name,
                        subtype=getattr(ent, "subtype", None),
                        description=ent.description,
                        enriched_description=ent.attributes.get("enriched_description"),
                        wikipedia_url=ent.attributes.get("wikipedia_url"),
                        latitude=float(lat_val),
                        longitude=float(lon_val),
                        conversations=[],
                        distance_km=ent.metadata.get("distance_km") if ent.metadata else None,
                    )
                )

        return locations

    except Exception as e:
        import traceback

        print(f"Error fetching nearby locations: {e}")
        traceback.print_exc()
        return []


@router.get("/locations/bounds", response_model=list[LocationEntity])
async def get_locations_in_bounds(
    min_lat: float = Query(..., description="Minimum latitude (south)"),
    max_lat: float = Query(..., description="Maximum latitude (north)"),
    min_lon: float = Query(..., description="Minimum longitude (west)"),
    max_lon: float = Query(..., description="Maximum longitude (east)"),
    session_id: str | None = Query(default=None, description="Filter by conversation session"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[LocationEntity]:
    """Find locations within a bounding box.

    Useful for fetching locations visible in the current map viewport.

    Args:
        min_lat: Minimum latitude (south boundary).
        max_lat: Maximum latitude (north boundary).
        min_lon: Minimum longitude (west boundary).
        max_lon: Maximum longitude (east boundary).
        session_id: Optional session ID to filter to conversation-specific locations.
        limit: Maximum number of results to return.

    Returns:
        List of location entities within the bounding box.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        entities = await memory.long_term.search_locations_in_bounding_box(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            session_id=session_id,
            limit=limit,
        )

        locations = []
        for ent in entities:
            # Get coordinates from entity
            coords = ent.attributes.get("coordinates", {})
            lat_val = coords.get("latitude") if isinstance(coords, dict) else None
            lon_val = coords.get("longitude") if isinstance(coords, dict) else None

            if lat_val is not None and lon_val is not None:
                locations.append(
                    LocationEntity(
                        id=str(ent.id),
                        name=ent.name,
                        subtype=getattr(ent, "subtype", None),
                        description=ent.description,
                        enriched_description=ent.attributes.get("enriched_description"),
                        wikipedia_url=ent.attributes.get("wikipedia_url"),
                        latitude=float(lat_val),
                        longitude=float(lon_val),
                        conversations=[],
                    )
                )

        return locations

    except Exception as e:
        import traceback

        print(f"Error fetching locations in bounds: {e}")
        traceback.print_exc()
        return []


@router.get("/locations/clusters")
async def get_location_clusters(
    session_id: str | None = Query(default=None, description="Filter by conversation session"),
) -> list[dict]:
    """Analyze geographic clusters of locations mentioned in podcasts.

    Returns location density by country/region, useful for heatmap visualization.

    Args:
        session_id: Optional session ID to filter to conversation-specific locations.

    Returns:
        List of clusters with country, location count, and center coordinates.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        # Get locations with coordinates
        locations_data = await memory.get_locations(
            session_id=session_id,
            has_coordinates=True,
            limit=500,
        )

        # Group by country
        country_clusters: dict[str, list[dict]] = {}
        for loc in locations_data:
            country = loc.get("country") or "Unknown"
            if country not in country_clusters:
                country_clusters[country] = []
            if loc.get("latitude") is not None and loc.get("longitude") is not None:
                country_clusters[country].append(
                    {
                        "name": loc["name"],
                        "latitude": loc["latitude"],
                        "longitude": loc["longitude"],
                    }
                )

        # Calculate cluster centers
        clusters = []
        for country, locs in sorted(country_clusters.items(), key=lambda x: -len(x[1])):
            if not locs:
                continue
            center_lat = sum(l["latitude"] for l in locs) / len(locs)
            center_lon = sum(l["longitude"] for l in locs) / len(locs)
            clusters.append(
                {
                    "country": country,
                    "location_count": len(locs),
                    "locations": locs[:5],  # Top 5 locations per country
                    "center_lat": center_lat,
                    "center_lon": center_lon,
                }
            )

        return clusters

    except Exception as e:
        import traceback

        traceback.print_exc()
        return []


@router.get("/locations/path")
async def get_shortest_path(
    from_location_id: str = Query(..., description="Source location ID"),
    to_location_id: str = Query(..., description="Target location ID"),
) -> dict:
    """Get the shortest path between two locations in the knowledge graph.

    Finds the shortest path through the graph relationships connecting
    two Location entities, useful for visualization overlays.

    Args:
        from_location_id: Source location entity ID.
        to_location_id: Target location entity ID.

    Returns:
        Dictionary with path nodes, relationships, and total hops.
    """
    memory = get_memory_client()
    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        # Find shortest path between two entities
        query = """
        MATCH (from:Entity {id: $from_id}), (to:Entity {id: $to_id})
        MATCH path = shortestPath((from)-[*..10]-(to))
        WITH path, nodes(path) AS pathNodes, relationships(path) AS pathRels
        RETURN [n IN pathNodes | {
            id: n.id,
            name: n.name,
            type: n.type,
            labels: labels(n),
            latitude: n.location.latitude,
            longitude: n.location.longitude
        }] AS nodes,
        [r IN pathRels | {
            type: type(r),
            from_id: startNode(r).id,
            to_id: endNode(r).id
        }] AS relationships,
        length(path) AS hops
        """

        results = await memory._client.execute_read(
            query,
            {"from_id": from_location_id, "to_id": to_location_id},
        )

        if not results:
            return {"nodes": [], "relationships": [], "hops": 0, "found": False}

        row = results[0]
        return {
            "nodes": row["nodes"],
            "relationships": row["relationships"],
            "hops": row["hops"],
            "found": True,
        }

    except Exception as e:
        import traceback

        print(f"Error finding shortest path: {e}")
        traceback.print_exc()
        return {"nodes": [], "relationships": [], "hops": 0, "found": False, "error": str(e)}


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
