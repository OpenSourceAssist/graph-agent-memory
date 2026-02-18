"""Product search tools."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)


async def search_products(
    client: "MemoryClient",
    query: str,
    category: str | None = None,
    brand: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock_only: bool = True,
    limit: int = 10,
) -> dict:
    """
    Search products using vector similarity and filters.

    Args:
        client: MemoryClient instance.
        query: Search query.
        category: Optional category filter.
        brand: Optional brand filter.
        max_price: Optional maximum price.
        min_price: Optional minimum price.
        in_stock_only: Only return in-stock items.
        limit: Maximum results.

    Returns:
        Dict with products list and count.
    """
    # Build filter conditions
    conditions = ["p:Product"]
    params = {"query": query, "limit": limit}

    if category:
        conditions.append("p.category = $category")
        params["category"] = category

    if brand:
        conditions.append("p.brand = $brand")
        params["brand"] = brand

    if max_price is not None:
        conditions.append("p.price <= $max_price")
        params["max_price"] = max_price

    if min_price is not None:
        conditions.append("p.price >= $min_price")
        params["min_price"] = min_price

    if in_stock_only:
        conditions.append("p.in_stock = true")

    where_clause = " AND ".join(conditions)

    try:
        # Try vector search first
        embedding = await client.embeddings.embed(query)
        params["embedding"] = embedding

        cypher = f"""
        CALL db.index.vector.queryNodes('product_embedding', $limit * 2, $embedding)
        YIELD node as p, score
        WHERE {where_clause}
        OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
        OPTIONAL MATCH (p)-[:MADE_BY]->(b:Brand)
        RETURN p {{
            .id, .name, .description, .price, .in_stock, .inventory,
            .image_url, .attributes,
            category: coalesce(c.name, p.category),
            brand: coalesce(b.name, p.brand)
        }} as product, score
        ORDER BY score DESC
        LIMIT $limit
        """

        result = await client.graph.execute_read(cypher, params)

    except Exception as e:
        logger.warning(f"Vector search failed, falling back to text search: {e}")

        # Fallback to text search
        cypher = f"""
        MATCH (p:Product)
        WHERE (toLower(p.name) CONTAINS toLower($query)
               OR toLower(p.description) CONTAINS toLower($query))
        AND {where_clause.replace("p:Product AND ", "")}
        OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
        OPTIONAL MATCH (p)-[:MADE_BY]->(b:Brand)
        RETURN p {{
            .id, .name, .description, .price, .in_stock, .inventory,
            .image_url, .attributes,
            category: coalesce(c.name, p.category),
            brand: coalesce(b.name, p.brand)
        }} as product, 1.0 as score
        ORDER BY p.popularity DESC NULLS LAST
        LIMIT $limit
        """

        result = await client.graph.execute_read(cypher, params)

    products = [{**record["product"], "relevance_score": record["score"]} for record in result]

    return {"products": products, "count": len(products)}


async def get_product_details(
    client: "MemoryClient",
    product_id: str,
) -> dict | None:
    """
    Get detailed product information.

    Args:
        client: MemoryClient instance.
        product_id: Product ID or element ID.

    Returns:
        Product details dict or None if not found.
    """
    cypher = """
    MATCH (p:Product)
    WHERE p.id = $product_id OR elementId(p) = $product_id
    OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
    OPTIONAL MATCH (p)-[:MADE_BY]->(b:Brand)
    OPTIONAL MATCH (p)-[:HAS_ATTRIBUTE]->(a:Attribute)
    OPTIONAL MATCH (p)-[:HAS_REVIEW]->(r:Review)
    WITH p, c, b, collect(DISTINCT a) as attributes, collect(DISTINCT r) as reviews
    RETURN p {
        .id, .name, .description, .price, .in_stock, .inventory,
        .image_url, .images, .specifications,
        category: c.name,
        brand: b.name,
        attributes: [attr in attributes | attr.name + ': ' + attr.value],
        rating: CASE WHEN size(reviews) > 0
                     THEN round(avg([r in reviews | r.rating]) * 10) / 10
                     ELSE null END,
        review_count: size(reviews)
    } as product
    """

    result = await client.graph.execute_read(cypher, {"product_id": product_id})

    if result:
        return result[0]["product"]
    return None


async def get_products_by_category(
    client: "MemoryClient",
    category: str,
    limit: int = 20,
    sort_by: str = "popularity",
) -> dict:
    """
    Get products in a specific category.

    Args:
        client: MemoryClient instance.
        category: Category name.
        limit: Maximum results.
        sort_by: Sort field (popularity, price_asc, price_desc, newest).

    Returns:
        Dict with products list.
    """
    order_clause = {
        "popularity": "p.popularity DESC NULLS LAST",
        "price_asc": "p.price ASC NULLS LAST",
        "price_desc": "p.price DESC NULLS LAST",
        "newest": "p.created_at DESC NULLS LAST",
    }.get(sort_by, "p.popularity DESC NULLS LAST")

    cypher = f"""
    MATCH (p:Product)-[:IN_CATEGORY]->(c:Category)
    WHERE toLower(c.name) = toLower($category)
    OPTIONAL MATCH (p)-[:MADE_BY]->(b:Brand)
    RETURN p {{
        .id, .name, .description, .price, .in_stock,
        .image_url,
        category: c.name,
        brand: b.name
    }} as product
    ORDER BY {order_clause}
    LIMIT $limit
    """

    result = await client.graph.execute_read(cypher, {"category": category, "limit": limit})

    return {"products": [r["product"] for r in result], "category": category}


async def get_brands(client: "MemoryClient", category: str | None = None) -> list[str]:
    """Get all brands, optionally filtered by category."""
    if category:
        cypher = """
        MATCH (p:Product)-[:IN_CATEGORY]->(c:Category)
        WHERE toLower(c.name) = toLower($category)
        MATCH (p)-[:MADE_BY]->(b:Brand)
        RETURN DISTINCT b.name as brand
        ORDER BY brand
        """
        params = {"category": category}
    else:
        cypher = """
        MATCH (b:Brand)
        RETURN b.name as brand
        ORDER BY brand
        """
        params = {}

    result = await client.graph.execute_read(cypher, params)
    return [r["brand"] for r in result]


async def get_categories(client: "MemoryClient") -> list[dict]:
    """Get all product categories with counts."""
    cypher = """
    MATCH (c:Category)<-[:IN_CATEGORY]-(p:Product)
    RETURN c.name as name, c.description as description, count(p) as product_count
    ORDER BY product_count DESC
    """

    result = await client.graph.execute_read(cypher, {})
    return [dict(r) for r in result]
