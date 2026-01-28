"""Strands Agents SDK integration for neo4j-agent-memory.

This module provides @tool decorated functions for use with AWS Strands Agents.
These tools enable Strands agents to interact with Neo4j Context Graphs for
semantic memory, entity retrieval, and knowledge graph operations.

Example:
    from strands import Agent
    from neo4j_agent_memory.integrations.strands import context_graph_tools

    tools = context_graph_tools(
        neo4j_uri=os.environ["NEO4J_URI"],
        neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
        neo4j_password=os.environ["NEO4J_PASSWORD"],
        embedding_provider="bedrock",
    )

    agent = Agent(
        model="anthropic.claude-sonnet-4-20250514-v1:0",
        tools=tools,
    )
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)

# Module-level client cache for tool reuse
_client_cache: dict[str, MemoryClient] = {}


def _run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously.

    Strands tools are synchronous, but MemoryClient is async.
    This helper runs async code in the appropriate event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # We're already in an async context - create a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        # No running loop - safe to use asyncio.run
        return asyncio.run(coro)


def _get_or_create_client(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    embedding_provider: str,
    embedding_model: str | None,
    **kwargs: Any,
) -> MemoryClient:
    """Get or create a MemoryClient instance.

    Uses a cache keyed by connection URI to avoid creating multiple clients.
    """
    cache_key = f"{neo4j_uri}:{neo4j_user}:{neo4j_database}"

    if cache_key not in _client_cache:
        from neo4j_agent_memory import MemoryClient, MemorySettings
        from neo4j_agent_memory.config.settings import (
            EmbeddingConfig,
            EmbeddingProvider,
            Neo4jConfig,
        )

        # Build embedding config
        provider_map = {
            "bedrock": EmbeddingProvider.BEDROCK,
            "openai": EmbeddingProvider.OPENAI,
            "vertex_ai": EmbeddingProvider.VERTEX_AI,
            "sentence_transformers": EmbeddingProvider.SENTENCE_TRANSFORMERS,
        }

        embedding_config = EmbeddingConfig(
            provider=provider_map.get(embedding_provider, EmbeddingProvider.BEDROCK),
            model=embedding_model,
            aws_region=kwargs.get("aws_region"),
            aws_profile=kwargs.get("aws_profile"),
        )

        neo4j_config = Neo4jConfig(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=neo4j_database,
        )

        settings = MemorySettings(
            neo4j=neo4j_config,
            embedding=embedding_config,
        )

        client = MemoryClient(settings)
        _client_cache[cache_key] = client

    return _client_cache[cache_key]


def _create_search_context_tool(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    embedding_provider: str,
    embedding_model: str | None,
    **kwargs: Any,
) -> Any:
    """Create the search_context tool with bound configuration."""
    try:
        from strands import tool
    except ImportError as e:
        raise ImportError(
            "strands-agents is required for Strands integration. "
            "Install with: pip install strands-agents"
        ) from e

    @tool
    def search_context(
        query: str,
        user_id: str,
        top_k: int = 10,
        min_score: float = 0.5,
        include_relationships: bool = True,
    ) -> list[dict[str, Any]]:
        """Search the Context Graph for relevant memories and entities.

        Use this tool when the user asks about things you might know
        from previous conversations or when you need to understand
        how different entities are connected.

        Args:
            query: The search query to find relevant context.
            user_id: The user ID to scope the search.
            top_k: Maximum number of results to return (default: 10).
            min_score: Minimum similarity score threshold (default: 0.5).
            include_relationships: Whether to include entity relationships (default: True).

        Returns:
            A list of relevant context items including messages, entities, and preferences.
        """

        async def _search() -> list[dict[str, Any]]:
            client = _get_or_create_client(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                neo4j_database=neo4j_database,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                **kwargs,
            )

            async with client:
                results: list[dict[str, Any]] = []

                # Search messages
                try:
                    messages = await client.short_term.search_messages(
                        query=query,
                        limit=top_k,
                        threshold=min_score,
                    )
                    for msg in messages:
                        results.append(
                            {
                                "type": "message",
                                "role": (
                                    msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                                ),
                                "content": msg.content,
                                "timestamp": (
                                    msg.created_at.isoformat() if msg.created_at else None
                                ),
                                "score": msg.metadata.get("similarity") if msg.metadata else None,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Message search failed: {e}")

                # Search entities
                try:
                    entities = await client.long_term.search_entities(
                        query=query,
                        limit=top_k,
                    )
                    for entity in entities:
                        entity_data: dict[str, Any] = {
                            "type": "entity",
                            "entity_type": (
                                entity.type.value
                                if hasattr(entity.type, "value")
                                else str(entity.type)
                            ),
                            "name": entity.display_name,
                            "description": entity.description,
                        }

                        # Include relationships if requested
                        if include_relationships and hasattr(entity, "id"):
                            try:
                                # Get relationships via Cypher
                                rel_query = """
                                MATCH (e:Entity {id: $entity_id})-[r]-(other:Entity)
                                RETURN type(r) AS relationship,
                                       other.displayName AS related_entity,
                                       other.type AS related_type
                                LIMIT 10
                                """
                                rels = await client._client.execute_read(
                                    rel_query,
                                    {"entity_id": str(entity.id)},
                                )
                                if rels:
                                    entity_data["relationships"] = [
                                        {
                                            "type": r["relationship"],
                                            "entity": r["related_entity"],
                                            "entity_type": r["related_type"],
                                        }
                                        for r in rels
                                    ]
                            except Exception as e:
                                logger.debug(f"Relationship fetch failed: {e}")

                        results.append(entity_data)
                except Exception as e:
                    logger.debug(f"Entity search failed: {e}")

                # Search preferences
                try:
                    preferences = await client.long_term.search_preferences(
                        query=query,
                        limit=top_k,
                    )
                    for pref in preferences:
                        results.append(
                            {
                                "type": "preference",
                                "category": pref.category,
                                "preference": pref.preference,
                                "context": pref.context,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Preference search failed: {e}")

                return results

        return _run_async(_search())

    return search_context


def _create_get_entity_graph_tool(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    embedding_provider: str,
    embedding_model: str | None,
    **kwargs: Any,
) -> Any:
    """Create the get_entity_graph tool with bound configuration."""
    try:
        from strands import tool
    except ImportError as e:
        raise ImportError(
            "strands-agents is required for Strands integration. "
            "Install with: pip install strands-agents"
        ) from e

    @tool
    def get_entity_graph(
        entity_name: str,
        user_id: str,
        depth: int = 2,
        relationship_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get the relationship graph around an entity.

        Use this tool to understand how an entity connects to other
        entities (customers, projects, team members, issues, etc.).

        Args:
            entity_name: The name of the entity to explore.
            user_id: The user ID for context.
            depth: How many relationship hops to traverse (default: 2, max: 3).
            relationship_types: Optional list of relationship types to filter.

        Returns:
            A dictionary containing the entity and its relationship graph.
        """

        async def _get_graph() -> dict[str, Any]:
            client = _get_or_create_client(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                neo4j_database=neo4j_database,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                **kwargs,
            )

            async with client:
                # Find the entity first
                entities = await client.long_term.search_entities(
                    query=entity_name,
                    limit=1,
                )

                if not entities:
                    return {
                        "found": False,
                        "entity_name": entity_name,
                        "message": f"Entity '{entity_name}' not found in the knowledge graph.",
                    }

                entity = entities[0]
                entity_id = str(entity.id)

                # Clamp depth to safe range
                safe_depth = min(max(depth, 1), 3)

                # Build relationship type filter
                rel_filter = ""
                if relationship_types:
                    rel_types = "|".join(relationship_types)
                    rel_filter = f":{rel_types}"

                # Get the subgraph
                query = f"""
                MATCH path = (start:Entity {{id: $entity_id}})-[r{rel_filter}*1..{safe_depth}]-(connected:Entity)
                WITH start, connected, relationships(path) AS rels, nodes(path) AS pathNodes
                UNWIND rels AS rel
                WITH start, connected,
                     startNode(rel) AS from_node,
                     endNode(rel) AS to_node,
                     type(rel) AS rel_type
                RETURN DISTINCT
                    from_node.displayName AS from_entity,
                    from_node.type AS from_type,
                    rel_type AS relationship,
                    to_node.displayName AS to_entity,
                    to_node.type AS to_type
                LIMIT 50
                """

                try:
                    records = await client._client.execute_read(
                        query,
                        {"entity_id": entity_id},
                    )

                    # Build graph structure
                    nodes: dict[str, dict[str, Any]] = {
                        entity.display_name: {
                            "name": entity.display_name,
                            "type": (
                                entity.type.value
                                if hasattr(entity.type, "value")
                                else str(entity.type)
                            ),
                            "description": entity.description,
                            "is_center": True,
                        }
                    }

                    edges: list[dict[str, str]] = []

                    for record in records:
                        # Add nodes
                        from_name = record["from_entity"]
                        to_name = record["to_entity"]

                        if from_name and from_name not in nodes:
                            nodes[from_name] = {
                                "name": from_name,
                                "type": record["from_type"],
                                "is_center": False,
                            }

                        if to_name and to_name not in nodes:
                            nodes[to_name] = {
                                "name": to_name,
                                "type": record["to_type"],
                                "is_center": False,
                            }

                        # Add edge
                        if from_name and to_name:
                            edges.append(
                                {
                                    "from": from_name,
                                    "to": to_name,
                                    "relationship": record["relationship"],
                                }
                            )

                    return {
                        "found": True,
                        "center_entity": {
                            "name": entity.display_name,
                            "type": (
                                entity.type.value
                                if hasattr(entity.type, "value")
                                else str(entity.type)
                            ),
                            "description": entity.description,
                        },
                        "graph": {
                            "nodes": list(nodes.values()),
                            "edges": edges,
                            "node_count": len(nodes),
                            "edge_count": len(edges),
                        },
                    }

                except Exception as e:
                    logger.error(f"Graph traversal failed: {e}")
                    return {
                        "found": True,
                        "center_entity": {
                            "name": entity.display_name,
                            "type": (
                                entity.type.value
                                if hasattr(entity.type, "value")
                                else str(entity.type)
                            ),
                            "description": entity.description,
                        },
                        "graph": {"nodes": [], "edges": [], "error": str(e)},
                    }

        return _run_async(_get_graph())

    return get_entity_graph


def _create_add_memory_tool(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    embedding_provider: str,
    embedding_model: str | None,
    **kwargs: Any,
) -> Any:
    """Create the add_memory tool with bound configuration."""
    try:
        from strands import tool
    except ImportError as e:
        raise ImportError(
            "strands-agents is required for Strands integration. "
            "Install with: pip install strands-agents"
        ) from e

    @tool
    def add_memory(
        content: str,
        user_id: str,
        session_id: str | None = None,
        extract_entities: bool = True,
    ) -> dict[str, Any]:
        """Store a memory with automatic entity extraction.

        Use this tool to save important information from the conversation
        that should be remembered for future interactions.

        Args:
            content: The content to remember.
            user_id: The user ID this memory belongs to.
            session_id: Optional session ID to associate with.
            extract_entities: Whether to extract entities from the content (default: True).

        Returns:
            Confirmation of stored memory with extracted entities.
        """

        async def _add() -> dict[str, Any]:
            client = _get_or_create_client(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                neo4j_database=neo4j_database,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                **kwargs,
            )

            async with client:
                # Use session_id or generate one from user_id
                effective_session = session_id or f"strands-{user_id}"

                # Store the message
                message = await client.short_term.add_message(
                    session_id=effective_session,
                    role="user",
                    content=content,
                    extract_entities=extract_entities,
                    generate_embedding=True,
                )

                result: dict[str, Any] = {
                    "stored": True,
                    "message_id": str(message.id),
                    "session_id": effective_session,
                    "content_preview": content[:100] + "..." if len(content) > 100 else content,
                }

                # If entities were extracted, include them
                if extract_entities and message.metadata:
                    extracted = message.metadata.get("extracted_entities", [])
                    if extracted:
                        result["extracted_entities"] = extracted

                return result

        return _run_async(_add())

    return add_memory


def _create_get_user_preferences_tool(
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    embedding_provider: str,
    embedding_model: str | None,
    **kwargs: Any,
) -> Any:
    """Create the get_user_preferences tool with bound configuration."""
    try:
        from strands import tool
    except ImportError as e:
        raise ImportError(
            "strands-agents is required for Strands integration. "
            "Install with: pip install strands-agents"
        ) from e

    @tool
    def get_user_preferences(
        user_id: str,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve user preference subgraph.

        Use this tool to get known preferences for a user, optionally
        filtered by category.

        Args:
            user_id: The user ID to get preferences for.
            category: Optional category to filter preferences (e.g., "food", "travel").

        Returns:
            A list of user preferences with categories and context.
        """

        async def _get_prefs() -> list[dict[str, Any]]:
            client = _get_or_create_client(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                neo4j_database=neo4j_database,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                **kwargs,
            )

            async with client:
                results: list[dict[str, Any]] = []

                if category:
                    # Search for specific category
                    preferences = await client.long_term.search_preferences(
                        query=category,
                        limit=20,
                    )
                    # Filter by exact category match
                    preferences = [p for p in preferences if p.category.lower() == category.lower()]
                else:
                    # Get all preferences (search with broad query)
                    preferences = await client.long_term.search_preferences(
                        query="preference",
                        limit=50,
                    )

                for pref in preferences:
                    results.append(
                        {
                            "id": str(pref.id),
                            "category": pref.category,
                            "preference": pref.preference,
                            "context": pref.context,
                            "confidence": pref.confidence,
                        }
                    )

                return results

        return _run_async(_get_prefs())

    return get_user_preferences


def context_graph_tools(
    neo4j_uri: str | None = None,
    neo4j_user: str = "neo4j",
    neo4j_password: str | None = None,
    neo4j_database: str = "neo4j",
    embedding_provider: str = "bedrock",
    embedding_model: str | None = None,
    **kwargs: Any,
) -> list[Any]:
    """Create all Context Graph tools configured for use with Strands agents.

    This factory function creates a list of @tool decorated functions that can
    be passed directly to a Strands Agent.

    Args:
        neo4j_uri: Neo4j connection URI. Defaults to NEO4J_URI env var.
        neo4j_user: Neo4j username. Defaults to "neo4j".
        neo4j_password: Neo4j password. Defaults to NEO4J_PASSWORD env var.
        neo4j_database: Neo4j database name. Defaults to "neo4j".
        embedding_provider: Embedding provider ("bedrock", "openai", "vertex_ai").
            Defaults to "bedrock".
        embedding_model: Optional model override for embeddings.
        **kwargs: Additional configuration (aws_region, aws_profile, etc.)

    Returns:
        A list of tool functions ready for use with Strands Agent.

    Example:
        from strands import Agent
        from neo4j_agent_memory.integrations.strands import context_graph_tools

        tools = context_graph_tools(
            neo4j_uri="neo4j+s://xxx.databases.neo4j.io",
            neo4j_password="password",
            embedding_provider="bedrock",
            aws_region="us-east-1",
        )

        agent = Agent(
            model="anthropic.claude-sonnet-4-20250514-v1:0",
            tools=tools,
        )

        response = agent("What do you know about our project timeline?")
    """
    import os

    # Get connection details from environment if not provided
    uri = neo4j_uri or os.environ.get("NEO4J_URI")
    password = neo4j_password or os.environ.get("NEO4J_PASSWORD")

    if not uri:
        raise ValueError(
            "neo4j_uri is required. Provide it directly or set NEO4J_URI environment variable."
        )
    if not password:
        raise ValueError(
            "neo4j_password is required. Provide it directly or set NEO4J_PASSWORD environment variable."
        )

    # Common config for all tools
    config = {
        "neo4j_uri": uri,
        "neo4j_user": neo4j_user,
        "neo4j_password": password,
        "neo4j_database": neo4j_database,
        "embedding_provider": embedding_provider,
        "embedding_model": embedding_model,
        **kwargs,
    }

    return [
        _create_search_context_tool(**config),
        _create_get_entity_graph_tool(**config),
        _create_add_memory_tool(**config),
        _create_get_user_preferences_tool(**config),
    ]


def clear_client_cache() -> None:
    """Clear the cached MemoryClient instances.

    Call this when you want to force new connections to be created.
    """
    global _client_cache
    _client_cache.clear()
