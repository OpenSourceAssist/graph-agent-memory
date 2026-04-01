"""MCP server instructions for Neo4j Agent Memory.

Server instructions are sent during MCP initialization and injected into
the LLM's system context by the host. They teach Claude how to use the
memory tools effectively.
"""

CORE_INSTRUCTIONS = """\
You have access to a persistent graph memory backed by Neo4j.

ALWAYS at conversation start:
  Call memory_get_context to load relevant memories for this session.

DURING conversation:
  When the user shares important facts, preferences, or decisions,
  call memory_store_message to persist them. The server automatically
  extracts entities and detects preferences from message content.

WHEN the user asks what you remember:
  Call memory_search with relevant keywords to find stored memories
  across messages, entities, and preferences.

WHEN the user shares a preference:
  Call memory_add_preference with the appropriate category and
  preference text to store it for future reference.

WHEN you learn about a new entity (person, place, organization, etc.):
  Call memory_add_entity with the entity name and POLE+O type.

WHEN you learn a new fact:
  Call memory_add_fact with subject, predicate, and object to store
  the knowledge triple.

Entity types follow POLE+O: Person, Object, Location, Event, Organization.
Each type supports subtypes for finer classification (e.g., OBJECT:VEHICLE,
LOCATION:ADDRESS).

Relationships use UPPER_SNAKE_CASE (e.g., WORKS_AT, LIVES_IN, FOUNDED).
"""

EXTENDED_INSTRUCTIONS = (
    CORE_INSTRUCTIONS
    + """
FOR complex tasks:
  Call memory_start_trace to begin recording your reasoning process.
  Call memory_record_step for each significant decision or action.
  Call memory_complete_trace when the task is finished.

FOR entity management:
  Use memory_get_entity for detailed entity info with graph relationships.
  Use memory_create_relationship to link entities together.

FOR exploring memory:
  Use memory_get_conversation to retrieve full conversation history.
  Use memory_list_sessions to see available conversation sessions.
  Use memory_export_graph for visualization-ready graph data.

FOR advanced queries:
  Use graph_query to execute read-only Cypher queries against the
  knowledge graph when the other tools don't cover your needs.
"""
)


def get_instructions(profile: str = "extended") -> str:
    """Get server instructions for the given tool profile.

    Args:
        profile: Tool profile name ('core' or 'extended').

    Returns:
        Instructions text to send during MCP initialization.
    """
    if profile == "extended":
        return EXTENDED_INSTRUCTIONS
    return CORE_INSTRUCTIONS
