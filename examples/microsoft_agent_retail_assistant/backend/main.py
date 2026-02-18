"""FastAPI server for the retail shopping assistant.

This server provides:
- SSE streaming for chat responses
- Memory context and graph visualization endpoints
- Product search and recommendations
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import uuid4

from agent import create_agent, run_agent_stream
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from memory_config import Settings, create_memory, get_memory_settings
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from neo4j_agent_memory import MemoryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()

# Global memory client (managed via lifespan)
memory_client: MemoryClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global memory_client

    # Startup: Connect to Neo4j
    logger.info("Connecting to Neo4j...")
    memory_client = MemoryClient(get_memory_settings())
    await memory_client.connect()
    logger.info("Connected to Neo4j")

    yield

    # Shutdown: Disconnect from Neo4j
    if memory_client:
        await memory_client.close()
        logger.info("Disconnected from Neo4j")


app = FastAPI(
    title="Smart Shopping Assistant API",
    description="Retail assistant powered by Microsoft Agent Framework and Neo4j Agent Memory",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    session_id: str | None = None
    user_id: str | None = None


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    response: str
    session_id: str


class MemoryContextResponse(BaseModel):
    """Memory context response."""

    short_term: list[dict]
    long_term: dict
    reasoning: list[dict]


class ProductSearchRequest(BaseModel):
    """Product search request."""

    query: str
    category: str | None = None
    max_price: float | None = None
    limit: int = 10


class ProductResponse(BaseModel):
    """Product details response."""

    id: str
    name: str
    description: str
    price: float
    category: str
    brand: str
    in_stock: bool


# --- Session Management ---

# In-memory session storage (use Redis in production)
sessions: dict[str, dict] = {}


def get_or_create_session(session_id: str | None, user_id: str | None = None) -> str:
    """Get existing session or create new one."""
    if session_id and session_id in sessions:
        return session_id

    new_session_id = session_id or str(uuid4())
    sessions[new_session_id] = {
        "user_id": user_id,
        "created_at": asyncio.get_event_loop().time(),
    }
    return new_session_id


# --- Chat Endpoints ---


@app.post("/chat")
async def chat_stream(request: ChatRequest):
    """
    Chat endpoint with SSE streaming.

    Sends:
    - token: Individual response tokens
    - tool_call: When agent uses a tool
    - done: When response is complete
    - error: On error
    """
    session_id = get_or_create_session(request.session_id, request.user_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # Create memory for this session
            memory = await create_memory(session_id, request.user_id)

            # Create agent with memory
            agent = await create_agent(memory)

            # Stream agent response
            async for event in run_agent_stream(agent, request.message, memory):
                yield event

            # Final event
            yield {"event": "done", "data": json.dumps({"session_id": session_id})}

        except Exception as e:
            logger.exception("Error in chat stream")
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@app.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """Non-streaming chat endpoint for simple requests."""
    session_id = get_or_create_session(request.session_id, request.user_id)

    try:
        memory = await create_memory(session_id, request.user_id)
        agent = await create_agent(memory)

        # Collect full response
        full_response = ""
        async for event in run_agent_stream(agent, request.message, memory):
            if event.get("event") == "token":
                data = json.loads(event["data"])
                full_response += data.get("content", "")

        return ChatResponse(response=full_response, session_id=session_id)

    except Exception as e:
        logger.exception("Error in sync chat")
        raise HTTPException(status_code=500, detail=str(e))


# --- Memory Endpoints ---


@app.get("/memory/context")
async def get_memory_context(
    session_id: str = Query(..., description="Session ID"),
    query: str = Query("", description="Query for relevant context"),
):
    """Get current memory context for visualization."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Get short-term (conversation)
        conversation = await memory_client.short_term.get_conversation(session_id, limit=20)
        short_term = [
            {
                "id": str(m.id),
                "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else None,
            }
            for m in conversation.messages
        ]

        # Get long-term (entities and preferences)
        entities = await memory_client.long_term.search_entities(
            query=query or "all", limit=20
        )
        preferences = await memory_client.long_term.search_preferences(
            query=query or "all", limit=10
        )
        long_term = {
            "entities": [
                {
                    "id": str(e.id),
                    "name": e.display_name,
                    "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                    "description": e.description,
                }
                for e in entities
            ],
            "preferences": [
                {
                    "id": str(p.id),
                    "category": p.category,
                    "preference": p.preference,
                    "context": p.context,
                }
                for p in preferences
            ],
        }

        # Get reasoning traces
        traces = []
        if query:
            trace_results = await memory_client.reasoning.get_similar_traces(task=query, limit=5)
            traces = [
                {
                    "id": str(t.id),
                    "task": t.task[:100],
                    "outcome": t.outcome,
                    "steps": len(t.steps) if t.steps else 0,
                }
                for t in trace_results
            ]

        return {
            "short_term": short_term,
            "long_term": long_term,
            "reasoning": traces,
        }

    except Exception as e:
        logger.exception("Error getting memory context")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/graph")
async def get_memory_graph(
    session_id: str = Query(..., description="Session ID"),
    center_entity: str | None = Query(None, description="Center entity for graph"),
    max_hops: int = Query(2, description="Maximum relationship hops"),
):
    """Get memory graph for visualization."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Build graph query based on center entity
        if center_entity:
            query = """
            MATCH (center:Entity {name: $center})
            CALL (center) {
                MATCH path = (center)-[*1..$max_hops]-(related)
                UNWIND nodes(path) AS n
                UNWIND relationships(path) AS r
                RETURN collect(DISTINCT {
                    id: elementId(n),
                    label: coalesce(n.name, 'Unknown'),
                    type: labels(n)[0],
                    properties: properties(n)
                }) AS nodes,
                collect(DISTINCT {
                    id: elementId(r),
                    source: elementId(startNode(r)),
                    target: elementId(endNode(r)),
                    type: type(r)
                }) AS relationships
            }
            RETURN nodes, relationships
            """
            result = await memory_client.graph.execute_read(
                query, {"center": center_entity, "max_hops": max_hops}
            )
        else:
            # Get recent entities from session
            query = """
            MATCH (m:Message {session_id: $session_id})-[:MENTIONS]->(e:Entity)
            WITH e, count(m) as mentions
            ORDER BY mentions DESC
            LIMIT 20
            OPTIONAL MATCH (e)-[r]-(related:Entity)
            WITH collect(DISTINCT e) + collect(DISTINCT related) AS allNodes,
                 collect(DISTINCT r) AS allRels
            RETURN [n IN allNodes WHERE n IS NOT NULL | {
                id: elementId(n),
                label: coalesce(n.name, 'Unknown'),
                type: labels(n)[0],
                properties: properties(n)
            }] AS nodes,
            [r IN allRels WHERE r IS NOT NULL | {
                id: elementId(r),
                source: elementId(startNode(r)),
                target: elementId(endNode(r)),
                type: type(r)
            }] AS relationships
            """
            result = await memory_client.graph.execute_read(query, {"session_id": session_id})

        if not result:
            return {"nodes": [], "edges": []}

        record = result[0]
        return {
            "nodes": record.get("nodes", []),
            "edges": record.get("relationships", []),
        }

    except Exception as e:
        logger.exception("Error getting memory graph")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/preferences")
async def get_preferences(
    session_id: str = Query(..., description="Session ID"),
    category: str | None = Query(None, description="Filter by category"),
):
    """Get learned user preferences."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        if category:
            preferences = await memory_client.long_term.get_preferences_by_category(
                category=category, limit=50
            )
        else:
            preferences = await memory_client.long_term.search_preferences(
                query="all", limit=50
            )

        return {
            "preferences": [
                {
                    "id": str(p.id),
                    "category": p.category,
                    "preference": p.preference,
                    "context": p.context,
                    "confidence": getattr(p, "confidence", 1.0),
                }
                for p in preferences
            ]
        }

    except Exception as e:
        logger.exception("Error getting preferences")
        raise HTTPException(status_code=500, detail=str(e))


# --- Product Endpoints ---


@app.get("/products/search")
async def search_products(
    query: str = Query(..., description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    brand: str | None = Query(None, description="Filter by brand"),
    max_price: float | None = Query(None, description="Maximum price"),
    limit: int = Query(10, description="Maximum results"),
):
    """Search product catalog."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        # Build product search query with projected fields
        conditions = ["p:Product"]
        params: dict[str, Any] = {"query": query, "limit": limit}

        if category:
            conditions.append("p.category = $category")
            params["category"] = category

        if brand:
            conditions.append("p.brand = $brand")
            params["brand"] = brand

        if max_price is not None:
            conditions.append("p.price <= $max_price")
            params["max_price"] = max_price

        where_clause = " AND ".join(conditions)

        # Vector search with filters — project fields in Cypher
        cypher = f"""
        CALL db.index.vector.queryNodes('product_embedding', $limit, $embedding)
        YIELD node as p, score
        WHERE {where_clause}
        RETURN elementId(p) AS id, p.name AS name,
               coalesce(p.description, '') AS description,
               coalesce(p.price, 0) AS price,
               coalesce(p.category, '') AS category,
               coalesce(p.brand, '') AS brand,
               coalesce(p.in_stock, true) AS in_stock,
               score
        ORDER BY score DESC
        """

        # Get embedding for query
        embedding = await memory_client._embedder.embed(query)
        params["embedding"] = embedding

        result = await memory_client.graph.execute_read(cypher, params)
        products = [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "price": r["price"],
                "category": r["category"],
                "brand": r["brand"],
                "in_stock": r["in_stock"],
                "score": r["score"],
            }
            for r in result
        ]

        return {"products": products, "total": len(products)}

    except Exception as e:
        logger.exception("Error searching products")
        # Fallback to basic text search if vector search fails
        try:
            cypher = """
            MATCH (p:Product)
            WHERE p.name CONTAINS $query OR p.description CONTAINS $query
            RETURN elementId(p) AS id, p.name AS name,
                   coalesce(p.description, '') AS description,
                   coalesce(p.price, 0) AS price,
                   coalesce(p.category, '') AS category,
                   coalesce(p.brand, '') AS brand,
                   coalesce(p.in_stock, true) AS in_stock
            LIMIT $limit
            """
            result = await memory_client.graph.execute_read(
                cypher, {"query": query, "limit": limit}
            )
            products = [
                {**r, "score": 1.0} for r in result
            ]

            return {"products": products, "total": len(products)}

        except Exception as fallback_error:
            raise HTTPException(status_code=500, detail=str(fallback_error))


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    """Get product details by ID."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        cypher = """
        MATCH (p:Product)
        WHERE elementId(p) = $product_id OR p.id = $product_id
        OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
        OPTIONAL MATCH (p)-[:MADE_BY]->(b:Brand)
        RETURN elementId(p) AS id, p.name AS name,
               coalesce(p.description, '') AS description,
               coalesce(p.price, 0) AS price,
               coalesce(c.name, p.category, '') AS category,
               coalesce(b.name, p.brand, '') AS brand,
               coalesce(p.in_stock, true) AS in_stock,
               coalesce(p.inventory, 0) AS inventory,
               p.image_url AS image_url
        """
        result = await memory_client.graph.execute_read(cypher, {"product_id": product_id})

        if not result:
            raise HTTPException(status_code=404, detail="Product not found")

        return result[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting product")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/{product_id}/related")
async def get_related_products(
    product_id: str,
    limit: int = Query(5, description="Maximum results"),
    relationship_type: str | None = Query(None, description="Filter by relationship"),
):
    """Get products related to a given product."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        if relationship_type:
            cypher = f"""
            MATCH (p:Product)-[:{relationship_type}]->(shared)<-[:{relationship_type}]-(related:Product)
            WHERE (elementId(p) = $product_id OR p.id = $product_id)
            AND related <> p
            RETURN elementId(related) AS id, related.name AS name,
                   coalesce(related.description, '')[..100] AS description,
                   coalesce(related.price, 0) AS price,
                   coalesce(related.category, '') AS category,
                   coalesce(related.brand, '') AS brand,
                   count(shared) AS shared_count
            ORDER BY shared_count DESC
            LIMIT $limit
            """
        else:
            # Find related through any shared attributes
            cypher = """
            MATCH (p:Product)
            WHERE elementId(p) = $product_id OR p.id = $product_id
            CALL (p) {
                MATCH (p)-[:IN_CATEGORY]->(c)<-[:IN_CATEGORY]-(related:Product)
                WHERE related <> p
                RETURN related, 'category' as relation_type, c.name as shared
                UNION
                MATCH (p)-[:MADE_BY]->(b)<-[:MADE_BY]-(related:Product)
                WHERE related <> p
                RETURN related, 'brand' as relation_type, b.name as shared
                UNION
                MATCH (p)-[:HAS_ATTRIBUTE]->(a)<-[:HAS_ATTRIBUTE]-(related:Product)
                WHERE related <> p
                RETURN related, 'attribute' as relation_type, a.name as shared
            }
            WITH related,
                 collect(DISTINCT {type: relation_type, value: shared}) AS connections
            RETURN elementId(related) AS id, related.name AS name,
                   coalesce(related.description, '')[..100] AS description,
                   coalesce(related.price, 0) AS price,
                   coalesce(related.category, '') AS category,
                   coalesce(related.brand, '') AS brand,
                   connections
            LIMIT $limit
            """

        result = await memory_client.graph.execute_read(
            cypher, {"product_id": product_id, "limit": limit}
        )

        return {"related_products": result}

    except Exception as e:
        logger.exception("Error getting related products")
        raise HTTPException(status_code=500, detail=str(e))


# --- Health Check ---


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_connected = memory_client is not None and memory_client.is_connected

    return {
        "status": "healthy" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
