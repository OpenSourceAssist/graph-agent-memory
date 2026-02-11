"""Graph API routes for Context Graph queries and visualization."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.memory_service import (
    FinancialMemoryService,
    get_initialized_memory_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["graph"])


class CypherQueryRequest(BaseModel):
    """Request model for Cypher queries."""

    query: str = Field(..., description="Cypher query (read-only)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Query parameters")


class CypherQueryResponse(BaseModel):
    """Response model for Cypher queries."""

    query: str
    results: list[dict[str, Any]]
    count: int


class EntityNeighborsRequest(BaseModel):
    """Request for entity neighbors."""

    entity_id: str
    depth: int = Field(default=1, ge=1, le=3)
    relationship_types: list[str] | None = None


@router.post("/query", response_model=CypherQueryResponse)
async def execute_cypher_query(
    request: CypherQueryRequest,
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> CypherQueryResponse:
    """Execute a read-only Cypher query against the Context Graph.

    Only read operations (MATCH, RETURN) are allowed.
    """
    # Security check - only allow read queries
    query_upper = request.query.upper().strip()
    # NOTE: Demo-only blocklist. For production, use an allowlist or run
    # queries via a read-only Neo4j user/role.
    forbidden_keywords = [
        "CREATE",
        "MERGE",
        "DELETE",
        "REMOVE",
        "SET",
        "DROP",
        "DETACH",
        "CALL",
        "LOAD",
        "FOREACH",
    ]

    for keyword in forbidden_keywords:
        if keyword in query_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Write operations ({keyword}) are not allowed. Use read-only queries.",
            )

    try:
        # Execute query through the memory client
        client = memory_service.client
        async with client._driver.session(database=client._database) as session:
            result = await session.run(request.query, request.parameters)
            records = await result.data()

        return CypherQueryResponse(
            query=request.query,
            results=records,
            count=len(records),
        )

    except Exception as e:
        logger.error(f"Cypher query error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/neighbors/{entity_id}")
async def get_entity_neighbors(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3, description="Traversal depth"),
    limit: int = Query(50, ge=1, le=200, description="Maximum neighbors"),
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> dict[str, Any]:
    """Get neighbors of an entity from the Context Graph.

    Returns nodes and relationships for visualization.
    """
    try:
        # Build a query to get neighbors
        query = """
        MATCH path = (start)-[r*1..{depth}]-(neighbor)
        WHERE start.id = $entity_id OR start.name = $entity_id
        WITH start, neighbor, r, path
        LIMIT $limit
        RETURN
            start.id as start_id,
            start.name as start_name,
            labels(start) as start_labels,
            neighbor.id as neighbor_id,
            neighbor.name as neighbor_name,
            labels(neighbor) as neighbor_labels,
            [rel in r | type(rel)] as relationship_types
        """.replace("{depth}", str(depth))

        client = memory_service.client
        async with client._driver.session(database=client._database) as session:
            result = await session.run(
                query,
                {"entity_id": entity_id, "limit": limit},
            )
            records = await result.data()

        # Format for visualization
        nodes = {}
        edges = []

        for record in records:
            # Add start node
            start_id = record["start_id"] or record["start_name"]
            if start_id and start_id not in nodes:
                nodes[start_id] = {
                    "id": start_id,
                    "label": record["start_name"] or start_id,
                    "type": record["start_labels"][0] if record["start_labels"] else "Unknown",
                    "isRoot": True,
                }

            # Add neighbor node
            neighbor_id = record["neighbor_id"] or record["neighbor_name"]
            if neighbor_id and neighbor_id not in nodes:
                nodes[neighbor_id] = {
                    "id": neighbor_id,
                    "label": record["neighbor_name"] or neighbor_id,
                    "type": record["neighbor_labels"][0]
                    if record["neighbor_labels"]
                    else "Unknown",
                    "isRoot": False,
                }

            # Add edge
            if start_id and neighbor_id and record["relationship_types"]:
                edges.append(
                    {
                        "from": start_id,
                        "to": neighbor_id,
                        "relationship": record["relationship_types"][0]
                        if record["relationship_types"]
                        else "RELATED",
                    }
                )

        return {
            "entity_id": entity_id,
            "depth": depth,
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    except Exception as e:
        logger.error(f"Error getting neighbors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats(
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> dict[str, Any]:
    """Get statistics about the Context Graph."""
    try:
        client = memory_service.client
        async with client._driver.session(database=client._database) as session:
            # Get node counts by label
            node_result = await session.run("""
                MATCH (n)
                RETURN labels(n) as label, count(*) as count
                ORDER BY count DESC
            """)
            node_counts = await node_result.data()

            # Get relationship counts by type
            rel_result = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            """)
            rel_counts = await rel_result.data()

            # Get total counts
            total_result = await session.run("""
                MATCH (n) WITH count(n) as nodes
                MATCH ()-[r]->() WITH nodes, count(r) as rels
                RETURN nodes, rels
            """)
            totals = await total_result.single()

        return {
            "total_nodes": totals["nodes"] if totals else 0,
            "total_relationships": totals["rels"] if totals else 0,
            "nodes_by_label": {
                r["label"][0] if r["label"] else "Unknown": r["count"] for r in node_counts
            },
            "relationships_by_type": {r["type"]: r["count"] for r in rel_counts},
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
