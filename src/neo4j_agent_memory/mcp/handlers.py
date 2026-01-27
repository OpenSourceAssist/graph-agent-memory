"""MCP tool execution handlers for Neo4j Agent Memory.

Implements the logic for each MCP tool.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)

# Patterns for detecting write operations in Cypher
WRITE_PATTERNS = [
    r"\bCREATE\b",
    r"\bMERGE\b",
    r"\bDELETE\b",
    r"\bDETACH\s+DELETE\b",
    r"\bSET\b",
    r"\bREMOVE\b",
    r"\bCALL\s+\{",  # Subqueries with potential writes
    r"\bCALL\s+db\.",  # DB procedures
    r"\bCALL\s+apoc\.",  # APOC procedures (some are write)
]


class MCPHandlers:
    """Handlers for MCP tool execution."""

    def __init__(self, memory_client: MemoryClient):
        """Initialize handlers with memory client.

        Args:
            memory_client: Connected MemoryClient instance.
        """
        self._client = memory_client

    async def handle_memory_search(
        self,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
        session_id: str | None = None,
        threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Handle memory_search tool execution.

        Args:
            query: Search query.
            limit: Maximum results.
            memory_types: Types to search.
            session_id: Optional session scope.
            threshold: Similarity threshold.

        Returns:
            Search results organized by type.
        """
        if memory_types is None:
            memory_types = ["messages", "entities", "preferences"]

        results: dict[str, list[dict[str, Any]]] = {}

        try:
            # Search messages
            if "messages" in memory_types:
                messages = await self._client.short_term.search_messages(
                    query=query,
                    session_id=session_id,
                    limit=limit,
                    threshold=threshold,
                )
                results["messages"] = [
                    {
                        "id": str(msg.id),
                        "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                        "similarity": msg.metadata.get("similarity") if msg.metadata else None,
                    }
                    for msg in messages
                ]

            # Search entities
            if "entities" in memory_types:
                entities = await self._client.long_term.search_entities(
                    query=query,
                    limit=limit,
                )
                results["entities"] = [
                    {
                        "id": str(entity.id),
                        "name": entity.display_name,
                        "type": (
                            entity.type.value if hasattr(entity.type, "value") else str(entity.type)
                        ),
                        "description": entity.description,
                    }
                    for entity in entities
                ]

            # Search preferences
            if "preferences" in memory_types:
                preferences = await self._client.long_term.search_preferences(
                    query=query,
                    limit=limit,
                )
                results["preferences"] = [
                    {
                        "id": str(pref.id),
                        "category": pref.category,
                        "preference": pref.preference,
                        "context": pref.context,
                    }
                    for pref in preferences
                ]

            # Search reasoning traces
            if "traces" in memory_types:
                traces = await self._client.reasoning.get_similar_traces(
                    task=query,
                    limit=limit,
                )
                results["traces"] = [
                    {
                        "id": str(trace.id),
                        "task": trace.task,
                        "outcome": trace.outcome,
                        "success": trace.success,
                    }
                    for trace in traces
                ]

        except Exception as e:
            logger.error(f"Error in memory_search: {e}")
            raise

        return {"results": results, "query": query}

    async def handle_memory_store(
        self,
        type: str,
        content: str,
        session_id: str | None = None,
        role: str = "user",
        category: str | None = None,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle memory_store tool execution.

        Args:
            type: Memory type (message, fact, preference).
            content: Content to store.
            session_id: Session ID for messages.
            role: Message role.
            category: Preference category.
            subject: Fact subject.
            predicate: Fact predicate.
            object: Fact object.
            metadata: Optional metadata.

        Returns:
            Stored memory confirmation.
        """
        try:
            if type == "message":
                if not session_id:
                    return {"error": "session_id required for message storage"}

                message = await self._client.short_term.add_message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    metadata=metadata,
                    extract_entities=True,
                    generate_embedding=True,
                )
                return {
                    "stored": True,
                    "type": "message",
                    "id": str(message.id),
                    "session_id": session_id,
                }

            elif type == "preference":
                if not category:
                    return {"error": "category required for preference storage"}

                preference = await self._client.long_term.add_preference(
                    category=category,
                    preference=content,
                    generate_embedding=True,
                )
                return {
                    "stored": True,
                    "type": "preference",
                    "id": str(preference.id),
                    "category": category,
                }

            elif type == "fact":
                if not all([subject, predicate, object]):
                    return {"error": "subject, predicate, and object required for fact storage"}

                fact = await self._client.long_term.add_fact(
                    subject=subject,
                    predicate=predicate,
                    obj=object,  # Map 'object' param to 'obj' for LongTermMemory.add_fact
                )
                return {
                    "stored": True,
                    "type": "fact",
                    "id": str(fact.id) if hasattr(fact, "id") else None,
                    "triple": f"{subject} -> {predicate} -> {object}",
                }

            else:
                return {"error": f"Unknown memory type: {type}"}

        except Exception as e:
            logger.error(f"Error in memory_store: {e}")
            raise

    async def handle_entity_lookup(
        self,
        name: str,
        type: str | None = None,
        include_neighbors: bool = True,
        max_hops: int = 1,
    ) -> dict[str, Any]:
        """Handle entity_lookup tool execution.

        Args:
            name: Entity name to look up.
            type: Optional entity type filter.
            include_neighbors: Include related entities.
            max_hops: Max relationship depth.

        Returns:
            Entity data with optional neighbors.
        """
        try:
            # Search for the entity by name
            entities = await self._client.long_term.search_entities(
                query=name,
                entity_types=[type] if type else None,
                limit=1,
            )

            if not entities:
                return {"found": False, "name": name}

            entity = entities[0]
            result: dict[str, Any] = {
                "found": True,
                "entity": {
                    "id": str(entity.id),
                    "name": entity.display_name,
                    "type": (
                        entity.type.value if hasattr(entity.type, "value") else str(entity.type)
                    ),
                    "description": entity.description,
                    "aliases": entity.aliases if hasattr(entity, "aliases") else [],
                },
            }

            # Get neighbors if requested
            if include_neighbors:
                neighbors = await self._get_entity_neighbors(
                    entity_id=str(entity.id),
                    max_hops=max_hops,
                )
                result["neighbors"] = neighbors

            return result

        except Exception as e:
            logger.error(f"Error in entity_lookup: {e}")
            raise

    async def _get_entity_neighbors(
        self,
        entity_id: str,
        max_hops: int = 1,
    ) -> list[dict[str, Any]]:
        """Get neighboring entities via graph traversal.

        Args:
            entity_id: Starting entity ID.
            max_hops: Maximum relationship depth.

        Returns:
            List of neighboring entities with relationships.
        """
        # Use direct Cypher query for neighbor traversal
        query = """
        MATCH (e:Entity {id: $entity_id})-[r*1..$max_hops]-(neighbor:Entity)
        WHERE neighbor.id <> $entity_id
        WITH DISTINCT neighbor, r
        RETURN neighbor.id AS id,
               neighbor.displayName AS name,
               neighbor.type AS type,
               neighbor.description AS description
        LIMIT 20
        """

        try:
            records = await self._client._client.execute_read(
                query,
                {"entity_id": entity_id, "max_hops": max_hops},
            )

            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "description": r["description"],
                }
                for r in records
            ]

        except Exception as e:
            logger.debug(f"Error getting neighbors: {e}")
            return []

    async def handle_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
        before: str | None = None,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Handle conversation_history tool execution.

        Args:
            session_id: Session to retrieve.
            limit: Max messages.
            before: Timestamp filter.
            include_metadata: Include metadata.

        Returns:
            Conversation history.
        """
        try:
            conversation = await self._client.short_term.get_conversation(
                session_id=session_id,
                limit=limit,
            )

            messages = []
            for msg in conversation.messages:
                msg_data: dict[str, Any] = {
                    "id": str(msg.id),
                    "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                }
                if include_metadata and msg.metadata:
                    msg_data["metadata"] = msg.metadata
                messages.append(msg_data)

            return {
                "session_id": session_id,
                "message_count": len(messages),
                "messages": messages,
            }

        except Exception as e:
            logger.error(f"Error in conversation_history: {e}")
            raise

    async def handle_graph_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle graph_query tool execution.

        Only allows read-only queries for safety.

        Args:
            query: Cypher query.
            parameters: Query parameters.

        Returns:
            Query results.
        """
        # Validate query is read-only
        if not self._is_read_only_query(query):
            return {
                "error": "Only read-only queries are allowed. "
                "Write operations (CREATE, MERGE, DELETE, SET, REMOVE) are not permitted."
            }

        try:
            records = await self._client._client.execute_read(query, parameters or {})

            return {
                "success": True,
                "row_count": len(records),
                "rows": records,
            }

        except Exception as e:
            logger.error(f"Error in graph_query: {e}")
            return {"error": str(e)}

    def _is_read_only_query(self, query: str) -> bool:
        """Check if a Cypher query is read-only.

        Args:
            query: The Cypher query to check.

        Returns:
            True if the query is read-only.
        """
        query_upper = query.upper()

        return all(not re.search(pattern, query_upper) for pattern in WRITE_PATTERNS)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Execute a tool by name and return JSON result.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            JSON string with results.
        """
        handlers = {
            "memory_search": self.handle_memory_search,
            "memory_store": self.handle_memory_store,
            "entity_lookup": self.handle_entity_lookup,
            "conversation_history": self.handle_conversation_history,
            "graph_query": self.handle_graph_query,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        try:
            result = await handler(**arguments)
            return json.dumps(result, default=str)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return json.dumps({"error": str(e)})
