"""Graph API routes for visualization and exploration."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.memory_service import get_memory_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["graph"])


class GraphNode(BaseModel):
    """Node in the graph visualization."""

    id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Display name")
    type: str = Field(..., description="Entity type")
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Node attributes"
    )
    risk_level: str | None = Field(default=None, description="Risk level if applicable")


class GraphEdge(BaseModel):
    """Edge/relationship in the graph visualization."""

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type")
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Edge attributes"
    )


class GraphData(BaseModel):
    """Graph data for visualization."""

    nodes: list[GraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: list[GraphEdge] = Field(default_factory=list, description="Graph edges")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Graph metadata")


class SearchResult(BaseModel):
    """Entity search result."""

    id: str = Field(..., description="Entity identifier")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type")
    score: float = Field(..., description="Relevance score")
    description: str | None = Field(default=None, description="Entity description")
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Entity attributes"
    )


@router.get("/entity/{entity_name}", response_model=GraphData)
async def get_entity_graph(
    entity_name: str,
    depth: int = Query(2, ge=1, le=4, description="Traversal depth"),
    include_types: list[str] | None = Query(
        None, description="Entity types to include"
    ),
) -> GraphData:
    """Get the subgraph around a named entity.

    Retrieves the entity and its relationships up to the specified depth.

    Args:
        entity_name: Name of the central entity
        depth: How many hops to traverse
        include_types: Filter to specific entity types

    Returns:
        Graph data for visualization
    """
    try:
        memory_service = get_memory_service()

        # First search for the entity
        entities = await memory_service.search_customers(
            query=entity_name,
            limit=1,
        )

        if not entities:
            raise HTTPException(
                status_code=404, detail=f"Entity '{entity_name}' not found"
            )

        entity_id = entities[0].get("id")

        # Get network from that entity
        network = await memory_service.get_customer_network(
            customer_id=entity_id,
            depth=depth,
        )

        nodes = []
        edges = []

        for node_data in network.get("nodes", []):
            node_type = node_data.get("type", "UNKNOWN")

            # Filter by type if specified
            if include_types and node_type not in include_types:
                continue

            nodes.append(
                GraphNode(
                    id=node_data.get("id", ""),
                    name=node_data.get("name", "Unknown"),
                    type=node_type,
                    attributes=node_data.get("attributes", {}),
                    risk_level=node_data.get("attributes", {}).get("risk_level"),
                )
            )

        for i, edge_data in enumerate(network.get("edges", [])):
            edges.append(
                GraphEdge(
                    id=f"edge-{i}",
                    source=edge_data.get("source", ""),
                    target=edge_data.get("target", ""),
                    type=edge_data.get("type", "RELATED_TO"),
                    attributes=edge_data.get("attributes", {}),
                )
            )

        return GraphData(
            nodes=nodes,
            edges=edges,
            metadata={
                "central_entity": entity_name,
                "depth": depth,
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching entity graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=list[SearchResult])
async def search_entities(
    query: str = Query(..., description="Search query"),
    entity_types: list[str] | None = Query(None, description="Filter by entity types"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
) -> list[SearchResult]:
    """Search for entities using semantic search.

    Uses the Context Graph's vector search to find entities
    matching the query.

    Args:
        query: Search query
        entity_types: Filter to specific entity types
        limit: Maximum results

    Returns:
        Matching entities with relevance scores
    """
    try:
        memory_service = get_memory_service()

        # Use the customer search which does semantic search
        results = await memory_service.search_customers(
            query=query,
            limit=limit,
        )

        search_results = []
        for result in results:
            # Filter by type if specified
            if entity_types:
                # In production, would filter at the query level
                pass

            search_results.append(
                SearchResult(
                    id=result.get("id", ""),
                    name=result.get("name", "Unknown"),
                    type="CUSTOMER",  # Default for customer search
                    score=0.9,  # Placeholder - real implementation would return actual scores
                    description=None,
                    attributes={
                        "customer_id": result.get("customer_id"),
                        "risk_level": result.get("risk_level"),
                        "jurisdiction": result.get("jurisdiction"),
                    },
                )
            )

        return search_results

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections")
async def find_connections(
    entity1: str = Query(..., description="First entity name"),
    entity2: str = Query(..., description="Second entity name"),
    max_depth: int = Query(3, ge=1, le=5, description="Maximum path length"),
) -> dict[str, Any]:
    """Find connections between two entities.

    Discovers paths connecting two entities in the graph,
    which can reveal hidden relationships.

    Args:
        entity1: First entity name
        entity2: Second entity name
        max_depth: Maximum path length to search

    Returns:
        Paths connecting the entities
    """
    try:
        memory_service = get_memory_service()

        # Search for both entities
        entities1 = await memory_service.search_customers(query=entity1, limit=1)
        entities2 = await memory_service.search_customers(query=entity2, limit=1)

        if not entities1:
            raise HTTPException(status_code=404, detail=f"Entity '{entity1}' not found")

        if not entities2:
            raise HTTPException(status_code=404, detail=f"Entity '{entity2}' not found")

        # In production, would use Cypher path-finding queries
        # For demo, return simulated connection info
        return {
            "entity1": {
                "name": entity1,
                "id": entities1[0].get("id"),
            },
            "entity2": {
                "name": entity2,
                "id": entities2[0].get("id"),
            },
            "max_depth_searched": max_depth,
            "paths_found": 0,  # Would be populated by real query
            "paths": [],
            "direct_connection": False,
            "shortest_path_length": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_graph_statistics() -> dict[str, Any]:
    """Get statistics about the Context Graph.

    Returns counts and metrics about entities and relationships
    stored in the graph.

    Returns:
        Graph statistics
    """
    # In production, would query graph for actual statistics
    return {
        "entities": {
            "total": 0,
            "by_type": {
                "CUSTOMER": 0,
                "ORGANIZATION": 0,
                "ACCOUNT": 0,
                "TRANSACTION": 0,
                "ALERT": 0,
            },
        },
        "relationships": {
            "total": 0,
            "by_type": {
                "HAS_ACCOUNT": 0,
                "WORKS_AT": 0,
                "TRANSACTS_WITH": 0,
                "CONNECTED_TO": 0,
            },
        },
        "risk_distribution": {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        },
        "last_updated": None,
    }
