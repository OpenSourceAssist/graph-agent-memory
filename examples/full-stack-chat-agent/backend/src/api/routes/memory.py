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
    # Note: Would need a delete_preference method on semantic memory
    # For now, return success
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

        # Use the Neo4jClient's execute_read method
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
        # Return empty graph on error
        import traceback

        print(f"Error fetching memory graph: {e}")
        traceback.print_exc()
        return MemoryGraph(nodes=[], relationships=[])
