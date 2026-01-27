"""Product recommendation tools using graph traversals and GDS algorithms."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)


async def get_recommendations(
    client: "MemoryClient",
    user_id: str | None = None,
    session_id: str | None = None,
    category: str | None = None,
    limit: int = 5,
) -> dict:
    """
    Get personalized product recommendations.

    Uses a combination of:
    - User preferences from long-term memory
    - Products viewed/discussed in session
    - Graph-based collaborative filtering
    - GDS PageRank for popular items (if available)

    Args:
        client: MemoryClient instance.
        user_id: Optional user ID for personalization.
        session_id: Optional session ID for context.
        category: Optional category filter.
        limit: Maximum recommendations.

    Returns:
        Dict with recommendations and reasoning.
    """
    recommendations = []
    reasons = []

    # 1. Get user preferences
    preferences = []
    try:
        prefs = await client.long_term.get_preferences(limit=10)
        preferences = [{"category": p.category, "value": p.preference} for p in prefs]
    except Exception as e:
        logger.debug(f"Could not get preferences: {e}")

    # 2. Get products from session context
    session_products = []
    if session_id:
        try:
            cypher = """
            MATCH (m:Message {session_id: $session_id})-[:MENTIONS]->(e:Entity)
            WHERE e.type = 'Product'
            RETURN DISTINCT e.name as product_name
            LIMIT 10
            """
            result = await client.graph.execute_query(cypher, {"session_id": session_id})
            session_products = [r["product_name"] for r in result]
        except Exception as e:
            logger.debug(f"Could not get session products: {e}")

    # 3. Build recommendation query based on available context
    if preferences or session_products:
        # Personalized recommendations
        pref_brands = [p["value"] for p in preferences if p["category"] == "brand"]
        pref_categories = [p["value"] for p in preferences if p["category"] == "category"]
        pref_styles = [p["value"] for p in preferences if p["category"] == "style"]

        cypher = """
        // Start with products matching preferences
        MATCH (p:Product)
        WHERE p.in_stock = true
        AND (
            p.brand IN $brands
            OR p.category IN $categories
            OR p.style IN $styles
            OR p.name IN $session_products
        )

        // Calculate relevance score
        WITH p,
             CASE WHEN p.brand IN $brands THEN 2 ELSE 0 END +
             CASE WHEN p.category IN $categories THEN 2 ELSE 0 END +
             CASE WHEN p.style IN $styles THEN 1 ELSE 0 END +
             CASE WHEN p.name IN $session_products THEN 3 ELSE 0 END as preference_score

        // Get related products through graph
        OPTIONAL MATCH (p)-[:SIMILAR_TO]-(similar:Product)
        WHERE similar.in_stock = true

        WITH p, preference_score, collect(DISTINCT similar)[0..3] as similar_products

        RETURN p {
            .id, .name, .description, .price, .category, .brand, .image_url
        } as product,
        preference_score,
        'Based on your preferences' as reason
        ORDER BY preference_score DESC, p.popularity DESC
        LIMIT $limit
        """

        params = {
            "brands": pref_brands,
            "categories": (pref_categories + [category]) if category else pref_categories,
            "styles": pref_styles,
            "session_products": session_products,
            "limit": limit,
        }

        try:
            result = await client.graph.execute_query(cypher, params)
            for r in result:
                recommendations.append(r["product"])
                reasons.append(r["reason"])
        except Exception as e:
            logger.warning(f"Personalized recommendation query failed: {e}")

    # 4. Fill remaining slots with popular items
    if len(recommendations) < limit:
        remaining = limit - len(recommendations)
        existing_ids = [p.get("id") for p in recommendations]

        # Try GDS PageRank for importance
        try:
            cypher = """
            CALL gds.pageRank.stream({
                nodeProjection: 'Product',
                relationshipProjection: {
                    SIMILAR_TO: {type: 'SIMILAR_TO', orientation: 'UNDIRECTED'},
                    BOUGHT_TOGETHER: {type: 'BOUGHT_TOGETHER', orientation: 'UNDIRECTED'}
                }
            })
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) as p, score
            WHERE p.in_stock = true AND NOT p.id IN $existing
            RETURN p {
                .id, .name, .description, .price, .category, .brand, .image_url
            } as product, score, 'Popular product' as reason
            ORDER BY score DESC
            LIMIT $limit
            """
            result = await client.graph.execute_query(
                cypher, {"existing": existing_ids, "limit": remaining}
            )
            for r in result:
                recommendations.append(r["product"])
                reasons.append(r["reason"])

        except Exception as e:
            logger.debug(f"GDS PageRank not available, using popularity: {e}")

            # Fallback to simple popularity
            category_filter = "AND p.category = $category" if category else ""
            cypher = f"""
            MATCH (p:Product)
            WHERE p.in_stock = true AND NOT p.id IN $existing
            {category_filter}
            RETURN p {{
                .id, .name, .description, .price, .category, .brand, .image_url
            }} as product, 'Popular product' as reason
            ORDER BY p.popularity DESC
            LIMIT $limit
            """
            params = {"existing": existing_ids, "limit": remaining}
            if category:
                params["category"] = category

            result = await client.graph.execute_query(cypher, params)
            for r in result:
                recommendations.append(r["product"])
                reasons.append(r["reason"])

    return {
        "recommendations": recommendations,
        "reasons": reasons,
        "personalized": bool(preferences or session_products),
    }


async def get_related_products(
    client: "MemoryClient",
    product_id: str,
    relationship_types: list[str] | None = None,
    limit: int = 5,
) -> dict:
    """
    Find products related to a given product through graph relationships.

    Args:
        client: MemoryClient instance.
        product_id: Source product ID.
        relationship_types: Types of relationships to consider.
        limit: Maximum results.

    Returns:
        Dict with related products and relationship info.
    """
    if relationship_types is None:
        relationship_types = ["SIMILAR_TO", "IN_CATEGORY", "MADE_BY", "BOUGHT_TOGETHER"]

    # Build relationship pattern
    rel_patterns = "|".join(relationship_types)

    cypher = f"""
    MATCH (source:Product)
    WHERE source.id = $product_id OR elementId(source) = $product_id

    // Find related through various paths
    CALL {{
        WITH source
        MATCH (source)-[:IN_CATEGORY]->(c)<-[:IN_CATEGORY]-(related:Product)
        WHERE related <> source AND related.in_stock = true
        RETURN related, 'Same category: ' + c.name as relationship, 2 as weight

        UNION

        WITH source
        MATCH (source)-[:MADE_BY]->(b)<-[:MADE_BY]-(related:Product)
        WHERE related <> source AND related.in_stock = true
        RETURN related, 'Same brand: ' + b.name as relationship, 2 as weight

        UNION

        WITH source
        MATCH (source)-[:SIMILAR_TO]-(related:Product)
        WHERE related.in_stock = true
        RETURN related, 'Similar product' as relationship, 3 as weight

        UNION

        WITH source
        MATCH (source)-[:BOUGHT_TOGETHER]-(related:Product)
        WHERE related.in_stock = true
        RETURN related, 'Frequently bought together' as relationship, 4 as weight

        UNION

        WITH source
        MATCH (source)-[:HAS_ATTRIBUTE]->(a)<-[:HAS_ATTRIBUTE]-(related:Product)
        WHERE related <> source AND related.in_stock = true
        RETURN related, 'Shared attribute: ' + a.name as relationship, 1 as weight
    }}

    WITH related, relationship, weight
    ORDER BY weight DESC

    RETURN related {{
        .id, .name, .description, .price, .category, .brand, .image_url
    }} as product,
    collect(DISTINCT relationship)[0..3] as relationships,
    sum(weight) as relevance_score
    ORDER BY relevance_score DESC
    LIMIT $limit
    """

    result = await client.graph.execute_query(cypher, {"product_id": product_id, "limit": limit})

    return {
        "source_product_id": product_id,
        "related_products": [
            {
                **r["product"],
                "relationships": r["relationships"],
                "relevance_score": r["relevance_score"],
            }
            for r in result
        ],
    }


async def get_bought_together(
    client: "MemoryClient",
    product_id: str,
    limit: int = 3,
) -> dict:
    """
    Get products frequently bought together with the given product.

    Args:
        client: MemoryClient instance.
        product_id: Source product ID.
        limit: Maximum results.

    Returns:
        Dict with frequently bought together products.
    """
    cypher = """
    MATCH (source:Product)-[r:BOUGHT_TOGETHER]-(related:Product)
    WHERE (source.id = $product_id OR elementId(source) = $product_id)
    AND related.in_stock = true
    RETURN related {
        .id, .name, .price, .image_url
    } as product,
    r.frequency as purchase_frequency,
    r.confidence as confidence
    ORDER BY r.frequency DESC, r.confidence DESC
    LIMIT $limit
    """

    result = await client.graph.execute_query(cypher, {"product_id": product_id, "limit": limit})

    return {
        "source_product_id": product_id,
        "frequently_bought_together": [
            {
                **r["product"],
                "purchase_frequency": r.get("purchase_frequency", 0),
                "confidence": r.get("confidence", 0),
            }
            for r in result
        ],
    }


async def explain_product_connection(
    client: "MemoryClient",
    product_id_1: str,
    product_id_2: str,
    max_hops: int = 4,
) -> dict:
    """
    Explain how two products are connected in the graph.

    Uses shortest path to find the connection and explains
    the relationship in natural language.

    Args:
        client: MemoryClient instance.
        product_id_1: First product ID.
        product_id_2: Second product ID.
        max_hops: Maximum path length to search.

    Returns:
        Dict with path explanation.
    """
    cypher = """
    MATCH (p1:Product), (p2:Product)
    WHERE (p1.id = $id1 OR elementId(p1) = $id1)
    AND (p2.id = $id2 OR elementId(p2) = $id2)

    CALL apoc.path.expandConfig(p1, {
        terminatorNodes: [p2],
        maxLevel: $max_hops,
        relationshipFilter: 'IN_CATEGORY|MADE_BY|SIMILAR_TO|BOUGHT_TOGETHER|HAS_ATTRIBUTE'
    })
    YIELD path

    WITH path, length(path) as pathLength
    ORDER BY pathLength
    LIMIT 1

    UNWIND range(0, size(nodes(path))-1) as idx
    WITH nodes(path)[idx] as node,
         CASE WHEN idx < size(relationships(path))
              THEN relationships(path)[idx]
              ELSE null END as rel

    RETURN collect({
        node: labels(node)[0] + ': ' + coalesce(node.name, 'unknown'),
        relationship: CASE WHEN rel IS NOT NULL THEN type(rel) ELSE null END
    }) as path_steps
    """

    try:
        result = await client.graph.execute_query(
            cypher,
            {"id1": product_id_1, "id2": product_id_2, "max_hops": max_hops},
        )

        if result and result[0]["path_steps"]:
            steps = result[0]["path_steps"]
            explanation_parts = []

            for i, step in enumerate(steps):
                if i == 0:
                    explanation_parts.append(step["node"])
                elif step["relationship"]:
                    rel_name = step["relationship"].replace("_", " ").lower()
                    explanation_parts.append(f"is {rel_name}")
                    explanation_parts.append(step["node"])

            return {
                "connected": True,
                "path_length": len(steps) - 1,
                "path": steps,
                "explanation": " → ".join(explanation_parts),
            }

    except Exception as e:
        logger.warning(f"Path finding failed: {e}")

    # Fallback: check for direct common attributes
    cypher = """
    MATCH (p1:Product), (p2:Product)
    WHERE (p1.id = $id1 OR elementId(p1) = $id1)
    AND (p2.id = $id2 OR elementId(p2) = $id2)

    OPTIONAL MATCH (p1)-[:IN_CATEGORY]->(c)<-[:IN_CATEGORY]-(p2)
    OPTIONAL MATCH (p1)-[:MADE_BY]->(b)<-[:MADE_BY]-(p2)

    RETURN p1.name as product1, p2.name as product2,
           collect(DISTINCT c.name) as shared_categories,
           collect(DISTINCT b.name) as shared_brands
    """

    result = await client.graph.execute_query(cypher, {"id1": product_id_1, "id2": product_id_2})

    if result:
        r = result[0]
        shared = []
        if r["shared_categories"]:
            shared.append(f"same category ({', '.join(r['shared_categories'])})")
        if r["shared_brands"]:
            shared.append(f"same brand ({', '.join(r['shared_brands'])})")

        if shared:
            return {
                "connected": True,
                "path_length": 2,
                "explanation": f"{r['product1']} and {r['product2']} share the {' and '.join(shared)}",
            }

    return {
        "connected": False,
        "explanation": "No direct connection found between these products",
    }
