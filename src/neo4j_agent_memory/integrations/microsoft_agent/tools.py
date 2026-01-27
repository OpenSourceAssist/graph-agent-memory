"""Microsoft Agent Framework memory tools.

Provides function tool definitions for memory operations that can be
used with Microsoft Agent Framework agents.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .memory import Neo4jMicrosoftMemory

logger = logging.getLogger(__name__)

try:
    from .gds import GDSAlgorithm

    def create_memory_tools(
        memory: Neo4jMicrosoftMemory,
        include_gds_tools: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Create Microsoft Agent Framework tool definitions for memory operations.

        These tools allow the agent to interact with the memory system
        using function calling.

        .. note::
            Tool format follows Microsoft Agent Framework conventions.
            May need updates for GA release.

        Args:
            memory: The Neo4jMicrosoftMemory instance.
            include_gds_tools: Whether to include GDS algorithm tools.

        Returns:
            List of tool definitions in Agent Framework format.

        Example:
            from neo4j_agent_memory.integrations.microsoft_agent import (
                Neo4jMicrosoftMemory,
                create_memory_tools,
            )

            memory = Neo4jMicrosoftMemory.from_memory_client(client, "session-123")
            tools = create_memory_tools(memory)

            # Use with ChatAgent
            agent = ChatAgent(
                chat_client=chat_client,
                tools=tools,
            )
        """
        tools = [
            # Search across all memory types
            {
                "type": "function",
                "function": {
                    "name": "search_memory",
                    "description": (
                        "Search the user's memory for relevant information including "
                        "past conversations, known facts, preferences, and entities. "
                        "Use this to recall information about the user or past interactions."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query describing what information to find",
                            },
                            "memory_types": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["messages", "entities", "preferences"],
                                },
                                "description": "Which memory types to search (default: all)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results per memory type",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            # Save user preference
            {
                "type": "function",
                "function": {
                    "name": "remember_preference",
                    "description": (
                        "Save a user preference for future reference. "
                        "Use this when the user explicitly states a preference or "
                        "when you infer a strong preference from the conversation."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": (
                                    "Category of preference (e.g., 'shopping', 'style', "
                                    "'brand', 'budget', 'size', 'color')"
                                ),
                            },
                            "preference": {
                                "type": "string",
                                "description": "The preference statement to remember",
                            },
                            "context": {
                                "type": "string",
                                "description": "Optional context for when this preference applies",
                            },
                        },
                        "required": ["category", "preference"],
                    },
                },
            },
            # Recall preferences
            {
                "type": "function",
                "function": {
                    "name": "recall_preferences",
                    "description": (
                        "Recall user preferences related to a topic or category. "
                        "Use this before making recommendations or suggestions."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Topic to find preferences for",
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional category filter",
                            },
                        },
                        "required": ["topic"],
                    },
                },
            },
            # Search knowledge graph
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge",
                    "description": (
                        "Search the knowledge graph for entities (products, brands, "
                        "categories, people, places) and their relationships. "
                        "Use this to find factual information."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for entities",
                            },
                            "entity_type": {
                                "type": "string",
                                "description": "Optional filter by entity type",
                                "enum": [
                                    "PERSON",
                                    "LOCATION",
                                    "ORGANIZATION",
                                    "EVENT",
                                    "OBJECT",
                                ],
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum entities to return",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            # Save fact
            {
                "type": "function",
                "function": {
                    "name": "remember_fact",
                    "description": (
                        "Save a factual statement for future reference. "
                        "Use this for important facts that should be remembered long-term."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Subject of the fact (e.g., 'user', 'John')",
                            },
                            "predicate": {
                                "type": "string",
                                "description": "Relationship (e.g., 'prefers', 'bought', 'lives in')",
                            },
                            "object": {
                                "type": "string",
                                "description": "Object of the fact",
                            },
                        },
                        "required": ["subject", "predicate", "object"],
                    },
                },
            },
            # Get similar past tasks
            {
                "type": "function",
                "function": {
                    "name": "find_similar_tasks",
                    "description": (
                        "Find similar tasks from past interactions to learn from "
                        "previous successes or failures. Useful for complex multi-step tasks."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "Description of the current task",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum traces to return",
                                "default": 3,
                            },
                        },
                        "required": ["task_description"],
                    },
                },
            },
        ]

        # Add GDS tools if enabled
        if include_gds_tools and memory.gds:
            gds_config = memory.gds.config
            tools_to_expose = gds_config.expose_as_tools if gds_config else []

            if GDSAlgorithm.SHORTEST_PATH in tools_to_expose or not tools_to_expose:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": "find_connection_path",
                            "description": (
                                "Find how two entities are connected in the knowledge graph. "
                                "Useful for understanding relationships between products, "
                                "brands, or concepts."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "source": {
                                        "type": "string",
                                        "description": "Name of the starting entity",
                                    },
                                    "target": {
                                        "type": "string",
                                        "description": "Name of the destination entity",
                                    },
                                },
                                "required": ["source", "target"],
                            },
                        },
                    }
                )

            if GDSAlgorithm.NODE_SIMILARITY in tools_to_expose or not tools_to_expose:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": "find_similar_items",
                            "description": (
                                "Find items similar to a given entity based on their "
                                "relationships. Useful for product recommendations."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "entity_name": {
                                        "type": "string",
                                        "description": "Name of the entity to find similar items for",
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Maximum similar items to return",
                                        "default": 5,
                                    },
                                },
                                "required": ["entity_name"],
                            },
                        },
                    }
                )

            if GDSAlgorithm.PAGERANK in tools_to_expose:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": "find_important_entities",
                            "description": (
                                "Find the most important/popular entities in a topic area. "
                                "Uses graph algorithms to identify key items."
                            ),
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "topic": {
                                        "type": "string",
                                        "description": "Topic to find important entities for",
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Maximum entities to return",
                                        "default": 10,
                                    },
                                },
                                "required": ["topic"],
                            },
                        },
                    }
                )

        return tools

    async def execute_memory_tool(
        memory: Neo4jMicrosoftMemory,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """
        Execute a memory tool and return JSON result.

        Args:
            memory: The Neo4jMicrosoftMemory instance.
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            JSON string with tool results.

        Example:
            result = await execute_memory_tool(
                memory,
                "search_memory",
                {"query": "user preferences for shoes", "limit": 5}
            )
            data = json.loads(result)
        """
        try:
            if tool_name == "search_memory":
                query = arguments["query"]
                memory_types = arguments.get(
                    "memory_types", ["messages", "entities", "preferences"]
                )
                limit = arguments.get("limit", 5)

                results = await memory.search_memory(
                    query=query,
                    include_messages="messages" in memory_types,
                    include_entities="entities" in memory_types,
                    include_preferences="preferences" in memory_types,
                    limit=limit,
                )
                return json.dumps({"results": results})

            elif tool_name == "remember_preference":
                await memory.add_preference(
                    category=arguments["category"],
                    preference=arguments["preference"],
                    context=arguments.get("context"),
                )
                return json.dumps(
                    {
                        "status": "saved",
                        "category": arguments["category"],
                        "preference": arguments["preference"],
                    }
                )

            elif tool_name == "recall_preferences":
                prefs = await memory._client.long_term.search_preferences(
                    query=arguments["topic"],
                    category=arguments.get("category"),
                    limit=10,
                )
                return json.dumps(
                    {
                        "preferences": [
                            {
                                "category": p.category,
                                "preference": p.preference,
                                "context": p.context,
                            }
                            for p in prefs
                        ]
                    }
                )

            elif tool_name == "search_knowledge":
                query = arguments["query"]
                entity_type = arguments.get("entity_type")
                limit = arguments.get("limit", 5)

                entity_types = [entity_type] if entity_type else None
                entities = await memory._client.long_term.search_entities(
                    query=query,
                    entity_types=entity_types,
                    limit=limit,
                )
                return json.dumps(
                    {
                        "entities": [
                            {
                                "name": e.display_name,
                                "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                                "description": e.description,
                            }
                            for e in entities
                        ]
                    }
                )

            elif tool_name == "remember_fact":
                await memory.add_fact(
                    subject=arguments["subject"],
                    predicate=arguments["predicate"],
                    obj=arguments["object"],
                )
                return json.dumps(
                    {
                        "status": "saved",
                        "fact": f"{arguments['subject']} {arguments['predicate']} {arguments['object']}",
                    }
                )

            elif tool_name == "find_similar_tasks":
                traces = await memory.get_similar_traces(
                    task=arguments["task_description"],
                    limit=arguments.get("limit", 3),
                )
                return json.dumps(
                    {
                        "similar_tasks": [
                            {
                                "task": t.task,
                                "outcome": t.outcome,
                                "success": t.success,
                            }
                            for t in traces
                        ]
                    }
                )

            elif tool_name == "find_connection_path":
                path = await memory.find_entity_path(
                    source=arguments["source"],
                    target=arguments["target"],
                )
                if path:
                    return json.dumps({"path": path})
                else:
                    return json.dumps({"path": None, "message": "No connection found"})

            elif tool_name == "find_similar_items":
                similar = await memory.find_similar_entities(
                    entity=arguments["entity_name"],
                    limit=arguments.get("limit", 5),
                )
                return json.dumps({"similar_items": similar})

            elif tool_name == "find_important_entities":
                # Search entities related to topic first
                entities = await memory._client.long_term.search_entities(
                    query=arguments["topic"],
                    limit=50,  # Get more to rank
                )
                if entities and memory.gds:
                    entity_ids = [str(e.id) for e in entities]
                    important = await memory.gds.get_central_entities(
                        entity_ids=entity_ids,
                        limit=arguments.get("limit", 10),
                    )
                    return json.dumps({"important_entities": important})
                else:
                    # Return search results as-is
                    return json.dumps(
                        {
                            "important_entities": [
                                {
                                    "name": e.display_name,
                                    "type": e.type.value
                                    if hasattr(e.type, "value")
                                    else str(e.type),
                                    "description": e.description,
                                }
                                for e in entities[: arguments.get("limit", 10)]
                            ]
                        }
                    )

            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return json.dumps({"error": str(e)})


except ImportError:
    # Microsoft Agent Framework not installed
    pass
