"""MCP prompt definitions for Neo4j Agent Memory.

Defines 3 prompts that provide guided workflows:
- memory_search_guide: Guide for searching across memory types
- entity_analysis: Structured entity analysis workflow
- conversation_summary: Conversation summarization workflow
"""

from __future__ import annotations

from fastmcp.prompts import Message


def register_prompts(mcp) -> None:
    """Register all MCP prompts on the server.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.prompt()
    def memory_search_guide(
        topic: str,
        memory_types: str = "messages,entities,preferences",
    ) -> list[Message]:
        """Guide for searching across memory types.

        Helps construct effective memory searches by suggesting
        which memory types to query and how to interpret results.
        """
        types_list = [t.strip() for t in memory_types.split(",")]
        return [
            Message(
                role="user",
                content=(
                    f"Search my memory for information about: {topic}\n\n"
                    f"Search across these memory types: {', '.join(types_list)}\n\n"
                    "Use the memory_search tool with the query above. "
                    "If the results are insufficient, try:\n"
                    "1. Broadening the query terms\n"
                    "2. Including additional memory types\n"
                    "3. Lowering the similarity threshold\n"
                    "4. Using entity_lookup for specific people/organizations"
                ),
            )
        ]

    @mcp.prompt()
    def entity_analysis(entity_name: str) -> list[Message]:
        """Analyze an entity and its relationships in the knowledge graph.

        Provides a structured approach to understanding an entity's
        connections, context, and significance.
        """
        return [
            Message(
                role="user",
                content=(
                    f"Analyze the entity '{entity_name}' in my knowledge graph.\n\n"
                    "Steps:\n"
                    f"1. Use entity_lookup to find '{entity_name}' with include_neighbors=true\n"
                    "2. For each related entity, note the relationship type and direction\n"
                    "3. Use memory_search to find recent messages mentioning this entity\n"
                    "4. Summarize:\n"
                    "   - Entity type and description\n"
                    "   - Key relationships (who/what is connected)\n"
                    "   - Recent context from conversations\n"
                    "   - Any stored preferences related to this entity"
                ),
            )
        ]

    @mcp.prompt()
    def conversation_summary(session_id: str) -> list[Message]:
        """Summarize a conversation session.

        Retrieves conversation history and guides summarization
        of key topics, decisions, and action items.
        """
        return [
            Message(
                role="user",
                content=(
                    f"Summarize the conversation from session '{session_id}'.\n\n"
                    "Steps:\n"
                    f"1. Use conversation_history to retrieve messages for session '{session_id}'\n"
                    "2. Identify the main topics discussed\n"
                    "3. Note any decisions made or action items\n"
                    "4. Highlight any entities or facts that were mentioned\n"
                    "5. Provide a concise summary with:\n"
                    "   - Key topics\n"
                    "   - Decisions/conclusions\n"
                    "   - Action items\n"
                    "   - Important entities mentioned"
                ),
            )
        ]
