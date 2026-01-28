"""Hybrid Memory Provider combining AgentCore Memory with Context Graphs.

This module provides a HybridMemoryProvider that routes queries appropriately
between short-term (AgentCore-style) and long-term (Neo4j Context Graph) memory.

Example:
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.integrations.agentcore import HybridMemoryProvider

    async with MemoryClient(settings) as client:
        provider = HybridMemoryProvider(
            memory_client=client,
            routing_strategy="auto",
            sync_entities=True,
        )

        # Queries are routed to the appropriate backend
        results = await provider.search_memory(
            query="What is the user's food preference?",
            include_relationships=True,
        )
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING, Any

from neo4j_agent_memory.integrations.agentcore.memory_provider import (
    Neo4jMemoryProvider,
)
from neo4j_agent_memory.integrations.agentcore.types import (
    Memory,
    MemorySearchResult,
    MemoryType,
)

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Strategy for routing queries between memory backends."""

    AUTO = "auto"  # Automatically detect query type
    EXPLICIT = "explicit"  # Use explicit memory_type parameter
    ALL = "all"  # Search all backends for every query
    SHORT_TERM_FIRST = "short_term_first"  # Prioritize short-term, fallback to long-term
    LONG_TERM_FIRST = "long_term_first"  # Prioritize long-term, fallback to short-term


# Keywords that suggest relationship/graph queries
RELATIONSHIP_KEYWORDS = {
    "related",
    "connected",
    "relationship",
    "connection",
    "link",
    "association",
    "knows",
    "works",
    "works with",
    "works at",
    "reports to",
    "manages",
    "belongs to",
    "part of",
    "between",
    "how does",
    "who does",
    "what connects",
}

# Keywords that suggest fact/entity queries
ENTITY_KEYWORDS = {
    "who is",
    "what is",
    "where is",
    "entity",
    "person",
    "organization",
    "company",
    "location",
    "place",
    "project",
    "team",
    "customer",
}

# Keywords that suggest preference queries
PREFERENCE_KEYWORDS = {
    "prefer",
    "preference",
    "likes",
    "dislikes",
    "favorite",
    "favourite",
    "choice",
    "default",
    "setting",
    "configuration",
}

# Keywords that suggest recent/short-term queries
SHORT_TERM_KEYWORDS = {
    "recent",
    "just",
    "earlier",
    "today",
    "yesterday",
    "last",
    "previous",
    "conversation",
    "said",
    "mentioned",
    "told",
    "asked",
}


class HybridMemoryProvider(Neo4jMemoryProvider):
    """Combines AgentCore Memory with Context Graphs.

    This provider intelligently routes queries to the appropriate memory
    backend based on query analysis or explicit configuration:

    - Short-term queries → Messages, recent conversations, working memory
    - Relationship queries → Entity graph traversal, connections
    - Preference queries → User preferences, settings
    - Entity queries → Named entities, facts

    The provider supports multiple routing strategies:
    - `auto`: Automatically detect query type from keywords
    - `explicit`: Use the memory_types parameter explicitly
    - `all`: Search all backends for every query
    - `short_term_first`: Prioritize short-term, expand if needed
    - `long_term_first`: Prioritize long-term, expand if needed

    Attributes:
        routing_strategy: How to route queries between backends.
        sync_entities: Whether to sync entities between backends.
        relationship_depth: Max depth for relationship traversal.

    Example:
        provider = HybridMemoryProvider(
            memory_client=client,
            routing_strategy="auto",
            sync_entities=True,
        )

        # Auto-routes to short-term memory
        results = await provider.search_memory(
            query="What did the user say earlier?"
        )

        # Auto-routes to entity graph
        results = await provider.search_memory(
            query="How is John connected to the Acme project?"
        )

        # Auto-routes to preferences
        results = await provider.search_memory(
            query="What are the user's food preferences?"
        )
    """

    def __init__(
        self,
        memory_client: MemoryClient,
        *,
        namespace: str = "default",
        routing_strategy: str | RoutingStrategy = RoutingStrategy.AUTO,
        sync_entities: bool = True,
        relationship_depth: int = 2,
        extract_entities: bool = True,
        generate_embeddings: bool = True,
    ) -> None:
        """Initialize the Hybrid Memory Provider.

        Args:
            memory_client: A connected MemoryClient instance.
            namespace: Namespace for multi-tenant isolation.
            routing_strategy: How to route queries (auto, explicit, all).
            sync_entities: Whether to sync entities between stores.
            relationship_depth: Max depth for relationship traversal.
            extract_entities: Whether to extract entities when storing.
            generate_embeddings: Whether to generate embeddings.
        """
        super().__init__(
            memory_client=memory_client,
            namespace=namespace,
            extract_entities=extract_entities,
            generate_embeddings=generate_embeddings,
        )

        self._routing_strategy = (
            RoutingStrategy(routing_strategy)
            if isinstance(routing_strategy, str)
            else routing_strategy
        )
        self._sync_entities = sync_entities
        self._relationship_depth = relationship_depth

    @property
    def routing_strategy(self) -> RoutingStrategy:
        """Get the current routing strategy."""
        return self._routing_strategy

    def _analyze_query(self, query: str) -> list[str]:
        """Analyze query to determine which memory types to search.

        Args:
            query: The search query.

        Returns:
            List of memory types to search.
        """
        query_lower = query.lower()
        memory_types: set[str] = set()

        # Check for relationship keywords
        for keyword in RELATIONSHIP_KEYWORDS:
            if keyword in query_lower:
                memory_types.add("entity")
                break

        # Check for entity keywords
        for keyword in ENTITY_KEYWORDS:
            if keyword in query_lower:
                memory_types.add("entity")
                break

        # Check for preference keywords
        for keyword in PREFERENCE_KEYWORDS:
            if keyword in query_lower:
                memory_types.add("preference")
                break

        # Check for short-term keywords
        for keyword in SHORT_TERM_KEYWORDS:
            if keyword in query_lower:
                memory_types.add("message")
                break

        # Default to all if no specific keywords found
        if not memory_types:
            memory_types = {"message", "entity", "preference"}

        return list(memory_types)

    async def search_memory(
        self,
        query: str,
        session_id: str | None = None,
        user_id: str | None = None,
        top_k: int = 10,
        *,
        memory_types: list[str] | None = None,
        threshold: float = 0.5,
        include_relationships: bool = True,
        include_entities: bool = True,
        include_preferences: bool = True,
    ) -> MemorySearchResult:
        """Search both backends and merge results.

        This method routes queries to appropriate backends based on the
        configured routing strategy and query analysis.

        Args:
            query: The search query.
            session_id: Optional session ID to scope the search.
            user_id: Optional user ID to scope the search.
            top_k: Maximum number of results to return.
            memory_types: Explicit memory types to search.
            threshold: Minimum similarity threshold.
            include_relationships: Include relationship traversal.
            include_entities: Include entity search.
            include_preferences: Include preference search.

        Returns:
            MemorySearchResult with merged results from all backends.
        """
        # Determine which memory types to search
        if self._routing_strategy == RoutingStrategy.EXPLICIT:
            if memory_types is None:
                memory_types = ["message", "entity", "preference"]
        elif self._routing_strategy == RoutingStrategy.ALL:
            memory_types = ["message", "entity", "preference"]
        elif self._routing_strategy == RoutingStrategy.AUTO:
            memory_types = self._analyze_query(query)
        elif self._routing_strategy == RoutingStrategy.SHORT_TERM_FIRST:
            memory_types = ["message"]
        elif self._routing_strategy == RoutingStrategy.LONG_TERM_FIRST:
            memory_types = ["entity", "preference"]

        # Apply includes filtering
        if memory_types:
            if not include_entities:
                memory_types = [t for t in memory_types if t != "entity"]
            if not include_preferences:
                memory_types = [t for t in memory_types if t != "preference"]

        # Perform the search using parent implementation
        result = await super().search_memory(
            query=query,
            session_id=session_id,
            user_id=user_id,
            top_k=top_k,
            memory_types=memory_types,
            threshold=threshold,
            include_entities=include_entities,
            include_preferences=include_preferences,
        )

        # If using short_term_first and no results, expand to long-term
        if self._routing_strategy == RoutingStrategy.SHORT_TERM_FIRST and len(result.memories) == 0:
            result = await super().search_memory(
                query=query,
                session_id=session_id,
                user_id=user_id,
                top_k=top_k,
                memory_types=["entity", "preference"],
                threshold=threshold,
                include_entities=include_entities,
                include_preferences=include_preferences,
            )

        # If using long_term_first and no results, expand to short-term
        if self._routing_strategy == RoutingStrategy.LONG_TERM_FIRST and len(result.memories) == 0:
            result = await super().search_memory(
                query=query,
                session_id=session_id,
                user_id=user_id,
                top_k=top_k,
                memory_types=["message"],
                threshold=threshold,
            )

        # Add relationship data if requested
        if include_relationships and result.memories:
            result = await self._enrich_with_relationships(result)

        # Update filters to reflect routing
        result.filters_applied["routing_strategy"] = self._routing_strategy.value
        result.filters_applied["memory_types_searched"] = memory_types

        return result

    async def _enrich_with_relationships(
        self,
        result: MemorySearchResult,
    ) -> MemorySearchResult:
        """Enrich entity memories with relationship data.

        Args:
            result: The search result to enrich.

        Returns:
            Enriched MemorySearchResult.
        """
        enriched_memories: list[Memory] = []

        for memory in result.memories:
            if memory.memory_type == MemoryType.ENTITY:
                # Get relationships for this entity
                entity_name = memory.metadata.get("display_name", "")
                if entity_name:
                    try:
                        rel_query = """
                        MATCH (e:Entity {displayName: $name})-[r]-(other:Entity)
                        RETURN type(r) AS relationship,
                               other.displayName AS related_entity,
                               other.type AS related_type
                        LIMIT $limit
                        """
                        relationships = await self._client._client.execute_read(
                            rel_query,
                            {"name": entity_name, "limit": self._relationship_depth * 5},
                        )

                        if relationships:
                            memory.metadata["relationships"] = [
                                {
                                    "type": r["relationship"],
                                    "entity": r["related_entity"],
                                    "entity_type": r["related_type"],
                                }
                                for r in relationships
                            ]
                    except Exception as e:
                        logger.debug(f"Failed to get relationships: {e}")

            enriched_memories.append(memory)

        return MemorySearchResult(
            memories=enriched_memories,
            total_count=result.total_count,
            query=result.query,
            filters_applied=result.filters_applied,
        )

    async def store_memory(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        *,
        memory_type: str = "message",
        user_id: str | None = None,
        role: str = "user",
    ) -> Memory:
        """Store content with optional entity synchronization.

        When sync_entities is enabled, entities extracted from messages
        are also stored in the long-term entity graph.

        Args:
            session_id: Session ID for the memory.
            content: The content to store.
            metadata: Optional metadata.
            memory_type: Type of memory.
            user_id: Optional user ID.
            role: Role for messages.

        Returns:
            The stored Memory object.
        """
        memory = await super().store_memory(
            session_id=session_id,
            content=content,
            metadata=metadata,
            memory_type=memory_type,
            user_id=user_id,
            role=role,
        )

        # Entity sync is handled by the extract_entities flag in parent
        # Additional cross-store sync could be added here if needed

        return memory

    async def get_entity_relationships(
        self,
        entity_name: str,
        *,
        depth: int | None = None,
        relationship_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get relationships for an entity from the knowledge graph.

        This is a convenience method for querying the entity graph directly.

        Args:
            entity_name: The name of the entity.
            depth: Max relationship depth (defaults to provider setting).
            relationship_types: Filter by relationship types.

        Returns:
            Dictionary with entity and its relationships.
        """
        effective_depth = depth or self._relationship_depth

        # Build relationship type filter
        rel_filter = ""
        params: dict[str, Any] = {
            "name": entity_name,
            "depth": effective_depth,
        }

        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_filter = f":{rel_types}"

        query = f"""
        MATCH (e:Entity)
        WHERE e.displayName = $name OR $name IN e.aliases
        OPTIONAL MATCH path = (e)-[r{rel_filter}*1..{effective_depth}]-(connected:Entity)
        WITH e, connected, relationships(path) AS rels
        UNWIND CASE WHEN rels IS NULL THEN [null] ELSE rels END AS rel
        WITH e, connected,
             CASE WHEN rel IS NOT NULL THEN startNode(rel) END AS from_node,
             CASE WHEN rel IS NOT NULL THEN endNode(rel) END AS to_node,
             CASE WHEN rel IS NOT NULL THEN type(rel) END AS rel_type
        RETURN DISTINCT
            e.displayName AS entity_name,
            e.type AS entity_type,
            e.description AS entity_description,
            from_node.displayName AS from_entity,
            rel_type AS relationship,
            to_node.displayName AS to_entity
        LIMIT 50
        """

        try:
            records = await self._client._client.execute_read(query, params)

            if not records:
                return {"found": False, "entity_name": entity_name}

            # Build result structure
            first = records[0]
            result: dict[str, Any] = {
                "found": True,
                "entity": {
                    "name": first["entity_name"],
                    "type": first["entity_type"],
                    "description": first["entity_description"],
                },
                "relationships": [],
            }

            seen_rels: set[tuple[str, str, str]] = set()
            for record in records:
                if record["relationship"]:
                    rel_key = (
                        record["from_entity"] or "",
                        record["relationship"],
                        record["to_entity"] or "",
                    )
                    if rel_key not in seen_rels:
                        seen_rels.add(rel_key)
                        result["relationships"].append(
                            {
                                "from": record["from_entity"],
                                "type": record["relationship"],
                                "to": record["to_entity"],
                            }
                        )

            return result

        except Exception as e:
            logger.error(f"Failed to get entity relationships: {e}")
            return {"found": False, "entity_name": entity_name, "error": str(e)}
