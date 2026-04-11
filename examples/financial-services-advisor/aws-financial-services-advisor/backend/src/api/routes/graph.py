"""Graph API routes for visualization and exploration.

Queries the Neo4j Context Graph via Neo4jDomainService and direct Cypher.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["graph"])


def _get_neo4j_service(request: Request):
    svc = getattr(request.app.state, "neo4j_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Neo4j service not available")
    return svc


class CypherQueryRequest(BaseModel):
    query: str = Field(..., description="Cypher query (read-only)")
    parameters: dict[str, Any] = Field(default_factory=dict)


class CypherQueryResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    count: int


@router.post("/query", response_model=CypherQueryResponse)
async def execute_cypher_query(request: Request, body: CypherQueryRequest) -> CypherQueryResponse:
    """Execute a read-only Cypher query against the Context Graph."""
    neo4j_service = _get_neo4j_service(request)

    query_upper = body.query.upper().strip()
    forbidden = ["CREATE", "MERGE", "DELETE", "REMOVE", "SET", "DROP", "DETACH", "LOAD", "FOREACH"]
    for keyword in forbidden:
        if keyword in query_upper:
            raise HTTPException(status_code=400, detail=f"Write operations ({keyword}) are not allowed.")

    try:
        results = await neo4j_service._graph.execute_read(body.query, body.parameters)
        return CypherQueryResponse(query=body.query, results=results, count=len(results))
    except Exception as e:
        logger.error(f"Cypher query error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/neighbors/{entity_id}")
async def get_entity_neighbors(
    request: Request,
    entity_id: str,
    depth: int = Query(1, ge=1, le=3),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Get neighbors of an entity from the Context Graph."""
    neo4j_service = _get_neo4j_service(request)

    conn_data = await neo4j_service.find_connections(entity_id, depth=depth)

    nodes = {}
    edges = []

    # Add root node
    root_query = """
    MATCH (n) WHERE n.id = $id OR n.name = $id
    RETURN n.id AS id, n.name AS name, labels(n) AS labels LIMIT 1
    """
    root_results = await neo4j_service._graph.execute_read(root_query, {"id": entity_id})
    if root_results:
        r = root_results[0]
        root_id = r["id"] or entity_id
        nodes[root_id] = {
            "id": root_id,
            "label": r["name"] or root_id,
            "type": r["labels"][0] if r["labels"] else "Unknown",
            "isRoot": True,
        }

    for conn in conn_data.get("connections", [])[:limit]:
        entity = conn.get("entity", {})
        eid = entity.get("id") or entity.get("name")
        if eid and eid not in nodes:
            nodes[eid] = {
                "id": eid,
                "label": entity.get("name") or eid,
                "type": entity.get("type") or "Unknown",
                "isRoot": False,
            }
        rel_types = conn.get("rel_types", [])
        if eid:
            edges.append({
                "from": entity_id,
                "to": eid,
                "relationship": rel_types[0] if rel_types else "RELATED",
            })

    return {
        "entity_id": entity_id,
        "depth": depth,
        "nodes": list(nodes.values()),
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@router.get("/entity/{entity_name}")
async def get_entity_graph(
    request: Request,
    entity_name: str,
    depth: int = Query(2, ge=1, le=3),
) -> dict[str, Any]:
    """Get subgraph around a named entity."""
    return await get_entity_neighbors(request, entity_name, depth=depth)


@router.post("/search")
async def search_entities(
    request: Request,
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Search for entities in the graph."""
    neo4j_service = _get_neo4j_service(request)

    cypher = """
    MATCH (n)
    WHERE n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($query)
    RETURN n.id AS id, n.name AS name, labels(n)[0] AS type, n.jurisdiction AS jurisdiction
    LIMIT $limit
    """
    results = await neo4j_service._graph.execute_read(cypher, {"query": query, "limit": limit})
    return [
        {
            "id": r.get("id") or r.get("name"),
            "name": r.get("name"),
            "type": r.get("type"),
            "jurisdiction": r.get("jurisdiction"),
        }
        for r in results
    ]


@router.get("/stats")
async def get_graph_statistics(request: Request) -> dict[str, Any]:
    """Get statistics about the Context Graph."""
    neo4j_service = _get_neo4j_service(request)
    return await neo4j_service.get_graph_stats()


@router.get("/memory")
async def get_memory_graph(
    request: Request,
    session_id: str | None = Query(None, description="Filter by session"),
    limit: int = Query(500, ge=1, le=2000),
) -> dict[str, Any]:
    """Get the full memory graph for NVL visualization.

    Returns domain nodes (Customer, Organization, Transaction, Alert, etc.)
    and their relationships in a format suitable for the Neo4j Visualization Library.
    """
    neo4j_service = _get_neo4j_service(request)
    return await neo4j_service.get_memory_graph(session_id=session_id, limit=limit)
