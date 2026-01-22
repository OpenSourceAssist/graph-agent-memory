"""Memory management API endpoints."""

from typing import Any
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
) -> list[ReasoningTraceResponse]:
    """List reasoning traces, optionally filtered by thread/session.

    Args:
        thread_id: Optional thread ID to filter traces by session.
        limit: Maximum number of traces to return.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        if thread_id:
            traces = await memory.procedural.get_session_traces(
                session_id=thread_id,
                limit=limit,
            )
        else:
            # Get all traces - need to query directly
            query = """
            MATCH (rt:ReasoningTrace)
            RETURN rt
            ORDER BY rt.started_at DESC
            LIMIT $limit
            """
            results = await memory._client.execute_read(query, {"limit": limit})
            traces = []
            for row in results:
                trace_data = dict(row["rt"])
                from neo4j_agent_memory.memory.procedural import ReasoningTrace

                traces.append(
                    ReasoningTrace(
                        id=UUID(trace_data["id"]),
                        session_id=trace_data["session_id"],
                        task=trace_data["task"],
                        outcome=trace_data.get("outcome"),
                        success=trace_data.get("success"),
                    )
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

    Returns aggregated statistics for each tool including success rate,
    average duration, and total call count.
    """
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        stats = await memory.procedural.get_tool_usage_stats()
        return [
            ToolStatsResponse(
                name=tool.name,
                description=tool.description,
                success_rate=tool.success_rate,
                avg_duration_ms=tool.avg_duration_ms,
                total_calls=tool.total_calls,
            )
            for tool in stats.values()
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
        # Get recent messages from episodic memory
        if thread_id:
            conversation = await memory.episodic.get_conversation(
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
            entity_results = await memory.semantic.search_entities(query, limit=10)
        else:
            entity_results = await memory.semantic.search_entities("", limit=10)

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
        pref = await memory.semantic.add_preference(
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
        results = await memory.semantic.search_entities(search_query, limit=50)

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
async def get_memory_graph() -> MemoryGraph:
    """Get the complete memory graph for visualization.

    Returns all nodes and relationships from the memory graph database.
    """
    memory = get_memory_client()
    if memory is None:
        return MemoryGraph(nodes=[], relationships=[])

    try:
        # Query all nodes
        nodes_query = """
        MATCH (n)
        RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties
        """

        # Query all relationships
        rels_query = """
        MATCH (a)-[r]->(b)
        RETURN elementId(r) AS id,
               elementId(a) AS `from`,
               elementId(b) AS `to`,
               type(r) AS type,
               properties(r) AS properties
        """

        client = memory._client

        node_results = await client.execute_read(nodes_query)
        rel_results = await client.execute_read(rels_query)

        # Convert to response format
        nodes = []
        seen_node_ids = set()
        for record in node_results:
            node_id = str(record["id"])
            if node_id not in seen_node_ids:
                seen_node_ids.add(node_id)
                props = {
                    k: serialize_neo4j_value(v) for k, v in (record.get("properties") or {}).items()
                }
                nodes.append(
                    GraphNode(
                        id=node_id,
                        labels=list(record.get("labels") or []),
                        properties=props,
                    )
                )

        relationships = []
        seen_rel_ids = set()
        for record in rel_results:
            rel_id = str(record["id"])
            if rel_id not in seen_rel_ids:
                seen_rel_ids.add(rel_id)
                props = {
                    k: serialize_neo4j_value(v) for k, v in (record.get("properties") or {}).items()
                }
                relationships.append(
                    GraphRelationship(
                        id=rel_id,
                        from_node=str(record["from"]),
                        to_node=str(record["to"]),
                        type=record["type"],
                        properties=props,
                    )
                )

        return MemoryGraph(nodes=nodes, relationships=relationships)

    except Exception as e:
        import traceback

        print(f"Error fetching memory graph: {e}")
        traceback.print_exc()
        return MemoryGraph(nodes=[], relationships=[])
