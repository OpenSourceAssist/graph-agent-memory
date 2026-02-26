"""Microsoft Agent Framework agent for the retail assistant.

This module creates and configures the shopping assistant agent with:
- Neo4j memory integration (context provider, message store)
- Product search and recommendation tools (callable FunctionTools)
- Preference learning capabilities
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Annotated, AsyncGenerator

from agent_framework import Agent, FunctionTool, Message, tool
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.openai import OpenAIChatClient
from memory_config import Settings

from neo4j_agent_memory.integrations.microsoft_agent import (
    Neo4jMicrosoftMemory,
    create_memory_tools,
    record_agent_trace,
)

if TYPE_CHECKING:
    from agent_framework import BaseChatClient

logger = logging.getLogger(__name__)

settings = Settings()

# System prompt for the retail assistant
SYSTEM_PROMPT = """You are a helpful shopping assistant for an online retail store. Your role is to:

1. Help customers find products that match their needs
2. Learn and remember their preferences (brands, styles, budget, sizes)
3. Provide personalized recommendations based on their history
4. Answer questions about products, availability, and shipping
5. Assist with comparing products and making decisions

Key behaviors:
- Always be helpful, friendly, and professional
- When customers express preferences, acknowledge and remember them
- Use the memory tools to save important preferences and recall relevant information
- When recommending products, explain why they match the customer's needs
- If a product is out of stock, suggest alternatives
- Ask clarifying questions when needs are unclear

You have access to memory tools to:
- Search your memory for relevant past conversations and preferences
- Save new preferences the customer expresses
- Find products similar to ones discussed before
- Track the customer's shopping journey

Always use the appropriate tools to provide personalized assistance."""


def get_chat_client() -> "BaseChatClient":
    """Create the chat client based on settings."""
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        # Use Azure OpenAI
        return AzureOpenAIResponsesClient(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment_name=settings.azure_openai_deployment or "gpt-4",
        )
    elif settings.openai_api_key:
        # Use OpenAI directly
        return OpenAIChatClient(
            api_key=settings.openai_api_key,
            model_id="gpt-4-turbo-preview",
        )
    else:
        raise ValueError(
            "No OpenAI configuration found. Set OPENAI_API_KEY or Azure OpenAI settings."
        )


def get_product_tools(memory: Neo4jMicrosoftMemory) -> list[FunctionTool]:
    """Get product-related callable tools bound to a memory instance."""
    client = memory.memory_client

    @tool(name="search_products", description="Search the product catalog for items matching a query. Use when customers ask about products.")
    async def search_products(
        query: Annotated[str, "Search query describing the product"],
        category: Annotated[str | None, "Optional category filter (e.g., 'shoes', 'electronics')"] = None,
        brand: Annotated[str | None, "Optional brand filter"] = None,
        max_price: Annotated[float | None, "Optional maximum price filter"] = None,
    ) -> str:
        """Search products in the catalog."""
        # Build filter conditions
        conditions = []
        params = {"query": query, "limit": 10}

        if category:
            conditions.append("p.category = $category")
            params["category"] = category
        if brand:
            conditions.append("p.brand = $brand")
            params["brand"] = brand
        if max_price:
            conditions.append("p.price <= $max_price")
            params["max_price"] = max_price

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Try vector search first
        try:
            embedding = await client.embeddings.embed(query)
            cypher = f"""
            CALL db.index.vector.queryNodes('product_embedding', 10, $embedding)
            YIELD node as p, score
            {where_clause}
            RETURN p.name as name, p.description as description, p.price as price,
                   p.category as category, p.brand as brand, p.in_stock as in_stock,
                   elementId(p) as id, score
            ORDER BY score DESC
            LIMIT 10
            """
            params["embedding"] = embedding
            result = await client.graph.execute_read(cypher, params)
        except Exception:
            # Fallback to text search
            cypher = f"""
            MATCH (p:Product)
            WHERE (p.name CONTAINS $query OR p.description CONTAINS $query)
            {" AND " + " AND ".join(conditions) if conditions else ""}
            RETURN p.name as name, p.description as description, p.price as price,
                   p.category as category, p.brand as brand, p.in_stock as in_stock,
                   elementId(p) as id, 1.0 as score
            LIMIT 10
            """
            result = await client.graph.execute_read(cypher, params)

        products = [dict(r) for r in result]
        return json.dumps({"products": products, "count": len(products)})

    @tool(name="get_product_details", description="Get detailed information about a specific product by ID.")
    async def get_product_details(
        product_id: Annotated[str, "The product ID"],
    ) -> str:
        """Get detailed product information."""
        cypher = """
        MATCH (p:Product)
        WHERE elementId(p) = $product_id OR p.id = $product_id
        RETURN p.name as name, p.description as description, p.price as price,
               p.category as category, p.brand as brand, p.in_stock as in_stock,
               p.inventory as inventory, p.attributes as attributes,
               elementId(p) as id
        """
        result = await client.graph.execute_read(cypher, {"product_id": product_id})
        if result:
            return json.dumps(dict(result[0]))
        return json.dumps({"error": "Product not found"})

    @tool(name="get_related_products", description="Find products related to a given product (similar items, accessories, etc).")
    async def get_related_products(
        product_id: Annotated[str, "The product ID to find related items for"],
        relationship_type: Annotated[str | None, "Type of relationship: similar, accessory, bundle, any"] = None,
    ) -> str:
        """Find related products."""
        rel_type = relationship_type or "any"

        if rel_type == "any":
            cypher = """
            MATCH (p:Product)
            WHERE elementId(p) = $product_id OR p.id = $product_id
            CALL (p) {
                MATCH (p)-[:IN_CATEGORY]->(c)<-[:IN_CATEGORY]-(related:Product)
                WHERE related <> p
                RETURN related, 'same category' as reason
                LIMIT 3
                UNION
                MATCH (p)-[:MADE_BY]->(b)<-[:MADE_BY]-(related:Product)
                WHERE related <> p
                RETURN related, 'same brand' as reason
                LIMIT 3
            }
            RETURN related.name as name, related.price as price,
                   elementId(related) as id, reason
            LIMIT 5
            """
        else:
            rel_map = {
                "similar": "SIMILAR_TO",
                "accessory": "ACCESSORY_FOR",
                "bundle": "BUNDLED_WITH",
            }
            rel = rel_map.get(rel_type, "SIMILAR_TO")
            cypher = f"""
            MATCH (p:Product)-[:{rel}]-(related:Product)
            WHERE elementId(p) = $product_id OR p.id = $product_id
            RETURN related.name as name, related.price as price,
                   elementId(related) as id, '{rel_type}' as reason
            LIMIT 5
            """

        result = await client.graph.execute_read(cypher, {"product_id": product_id})
        return json.dumps({"related": [dict(r) for r in result]})

    @tool(name="check_inventory", description="Check if a product is in stock and get availability info.")
    async def check_inventory(
        product_id: Annotated[str, "The product ID to check"],
    ) -> str:
        """Check product inventory status."""
        cypher = """
        MATCH (p:Product)
        WHERE elementId(p) = $product_id OR p.id = $product_id
        RETURN p.name as name, p.in_stock as in_stock, p.inventory as quantity
        """
        result = await client.graph.execute_read(cypher, {"product_id": product_id})
        if result:
            r = result[0]
            return json.dumps({
                "name": r["name"],
                "in_stock": r["in_stock"],
                "quantity": r["quantity"] or 0,
                "status": "Available" if r["in_stock"] else "Out of Stock",
            })
        return json.dumps({"error": "Product not found"})

    @tool(name="get_recommendations", description="Get personalized product recommendations for the customer based on their preferences and history.")
    async def get_recommendations(
        category: Annotated[str | None, "Optional category to get recommendations for"] = None,
        limit: Annotated[int, "Maximum number of recommendations"] = 5,
    ) -> str:
        """Get personalized product recommendations."""
        # Get user preferences from memory
        preferences = await client.long_term.search_preferences(
            query=category or "shopping preferences", limit=10
        )
        pref_categories = [p.category for p in preferences]
        pref_values = [p.preference for p in preferences]

        # Build recommendation query based on preferences
        if preferences:
            cypher = """
            MATCH (p:Product)
            WHERE p.in_stock = true
            AND (p.brand IN $prefs OR p.category IN $categories)
            RETURN p.name as name, p.price as price, p.category as category,
                   p.brand as brand, elementId(p) as id,
                   'Based on your preferences' as reason
            LIMIT $limit
            """
            params = {
                "prefs": pref_values,
                "categories": pref_categories + ([category] if category else []),
                "limit": limit,
            }
        else:
            # No preferences yet, return popular items
            cypher = """
            MATCH (p:Product)
            WHERE p.in_stock = true
            RETURN p.name as name, p.price as price, p.category as category,
                   p.brand as brand, elementId(p) as id,
                   'Popular item' as reason
            ORDER BY p.popularity DESC
            LIMIT $limit
            """
            params = {"limit": limit}

        if category:
            cypher = cypher.replace(
                "WHERE p.in_stock = true",
                "WHERE p.in_stock = true AND p.category = $category",
            )
            params["category"] = category

        result = await client.graph.execute_read(cypher, params)
        return json.dumps({"recommendations": [dict(r) for r in result]})

    return [
        search_products,
        get_product_details,
        get_related_products,
        check_inventory,
        get_recommendations,
    ]


async def create_agent(memory: Neo4jMicrosoftMemory) -> Agent:
    """Create a shopping assistant agent with Neo4j memory."""
    chat_client = get_chat_client()

    # Get memory tools (callable FunctionTools)
    memory_tools = create_memory_tools(
        memory,
        include_gds_tools=bool(memory.gds),
    )

    # Get product tools (callable FunctionTools)
    product_tools = get_product_tools(memory)

    # Combine all tools
    all_tools = memory_tools + product_tools

    # Create agent with context provider
    agent = chat_client.as_agent(
        name="ShoppingAssistant",
        instructions=SYSTEM_PROMPT,
        tools=all_tools,
        context_providers=[memory.context_provider],
    )

    return agent


async def run_agent_stream(
    agent: Agent,
    message: str,
    memory: Neo4jMicrosoftMemory,
) -> AsyncGenerator[dict, None]:
    """
    Run the agent and stream responses.

    With callable tools, the agent framework auto-invokes tools during
    streaming. This function only observes text and tool events — no
    manual tool execution needed.

    Yields:
        Events with format: {"event": str, "data": str (JSON)}
        - token: {"content": str} - Response token
        - tool_call: {"name": str, "arguments": str} - Tool invocation
        - tool_result: {"name": str, "result": str} - Tool result
        - done: {"session_id": str} - Completion
        - error: {"error": str} - Error
    """
    tool_calls_for_trace = []

    try:
        # Save user message first
        await memory.save_message("user", message)

        # Create user message
        user_msg = Message("user", [message])

        # Stream agent response — framework auto-invokes callable tools
        full_response = ""
        async for update in agent.run(user_msg, stream=True):
            # Check for text content
            if update.text:
                full_response += update.text
                yield {
                    "event": "token",
                    "data": json.dumps({"content": update.text}),
                }

            # Observe tool calls and results (framework handles execution)
            for content in update.contents:
                if content.type == "function_call":
                    yield {
                        "event": "tool_call",
                        "data": json.dumps({
                            "name": content.name,
                            "arguments": content.arguments,
                        }),
                    }

                elif content.type == "function_result":
                    tool_calls_for_trace.append({
                        "name": content.call_id,
                        "result": content.result,
                    })

                    yield {
                        "event": "tool_result",
                        "data": json.dumps({
                            "name": content.call_id,
                            "result": content.result,
                        }),
                    }

        # Save assistant response
        if full_response:
            await memory.save_message("assistant", full_response)

            # Record trace for learning
            messages_for_trace = [
                {"role": "user", "content": message},
                {"role": "assistant", "content": full_response[:500]},  # Truncate long responses
            ]

            await record_agent_trace(
                memory=memory,
                messages=messages_for_trace,
                task=message,
                tool_calls=tool_calls_for_trace,
                outcome="success",
                success=True,
                generate_embedding=True,
            )

    except Exception as e:
        logger.exception("Error in agent stream")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}),
        }
