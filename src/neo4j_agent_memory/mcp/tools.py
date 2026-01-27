"""MCP tool definitions for Neo4j Agent Memory.

Defines the 5 core tools:
- memory_search: Hybrid vector + graph search
- memory_store: Store memories (messages, facts, preferences)
- entity_lookup: Get entity with relationships
- conversation_history: Get conversation for session
- graph_query: Execute read-only Cypher queries
"""

from typing import Any

# Tool definitions in MCP format
MEMORY_TOOLS: list[dict[str, Any]] = [
    {
        "name": "memory_search",
        "description": (
            "Search across all memory types using hybrid vector + graph search. "
            "Finds relevant messages, entities, preferences, and reasoning traces."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant memories",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10,
                },
                "memory_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["messages", "entities", "preferences", "traces"],
                    },
                    "description": "Types of memory to search (defaults to all)",
                    "default": ["messages", "entities", "preferences"],
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional session ID to scope message search",
                },
                "threshold": {
                    "type": "number",
                    "description": "Minimum similarity threshold (0.0-1.0)",
                    "default": 0.7,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_store",
        "description": (
            "Store a memory in the knowledge graph. Supports messages, facts (SPO triples), "
            "and user preferences. Automatically extracts entities from message content."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["message", "fact", "preference"],
                    "description": "Type of memory to store",
                },
                "content": {
                    "type": "string",
                    "description": "The content to store (message text, preference text, or fact object)",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for message storage",
                },
                "role": {
                    "type": "string",
                    "enum": ["user", "assistant", "system"],
                    "description": "Message role (required for type=message)",
                    "default": "user",
                },
                "category": {
                    "type": "string",
                    "description": "Preference category (required for type=preference)",
                },
                "subject": {
                    "type": "string",
                    "description": "Fact subject (required for type=fact)",
                },
                "predicate": {
                    "type": "string",
                    "description": "Fact predicate/relationship (required for type=fact)",
                },
                "object": {
                    "type": "string",
                    "description": "Fact object (required for type=fact)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata to attach to the memory",
                },
            },
            "required": ["type", "content"],
        },
    },
    {
        "name": "entity_lookup",
        "description": (
            "Look up an entity in the knowledge graph and optionally retrieve "
            "its relationships and neighboring entities via graph traversal."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the entity to look up",
                },
                "type": {
                    "type": "string",
                    "enum": ["PERSON", "ORGANIZATION", "LOCATION", "EVENT", "OBJECT"],
                    "description": "Optional entity type filter",
                },
                "include_neighbors": {
                    "type": "boolean",
                    "description": "Whether to include related entities",
                    "default": True,
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum relationship hops for neighbor traversal",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 3,
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "conversation_history",
        "description": (
            "Retrieve conversation history for a session. Returns messages in "
            "chronological order with role, content, and metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID to retrieve conversation for",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to return",
                    "default": 50,
                },
                "before": {
                    "type": "string",
                    "description": "Return messages before this timestamp (ISO format)",
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Whether to include message metadata",
                    "default": True,
                },
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "graph_query",
        "description": (
            "Execute a read-only Cypher query against the knowledge graph. "
            "Only SELECT/MATCH queries are allowed for safety."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The Cypher query to execute (read-only)",
                },
                "parameters": {
                    "type": "object",
                    "description": "Optional query parameters",
                    "default": {},
                },
            },
            "required": ["query"],
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get the list of MCP tool definitions.

    Returns:
        List of tool definitions in MCP format.
    """
    return MEMORY_TOOLS.copy()


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a specific tool definition by name.

    Args:
        name: The tool name.

    Returns:
        Tool definition dict or None if not found.
    """
    for tool in MEMORY_TOOLS:
        if tool["name"] == name:
            return tool
    return None
