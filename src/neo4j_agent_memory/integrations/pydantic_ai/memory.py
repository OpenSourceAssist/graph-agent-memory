"""Pydantic AI integration for neo4j-agent-memory."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient


@dataclass
class MemoryDependency:
    """
    Pydantic AI dependency for memory access.

    This can be used as the deps_type for a Pydantic AI agent to provide
    memory capabilities.

    Example:
        from pydantic_ai import Agent
        from neo4j_agent_memory import MemoryClient, MemorySettings
        from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency

        agent = Agent(
            'openai:gpt-4o',
            deps_type=MemoryDependency,
            system_prompt=dynamic_system_prompt,
        )

        async def dynamic_system_prompt(ctx: RunContext[MemoryDependency]) -> str:
            memory = ctx.deps
            context = await memory.get_context(ctx.messages[-1].content)
            return f"You are a helpful assistant.\\n\\nContext:\\n{context}"

        async with MemoryClient(settings) as client:
            deps = MemoryDependency(client=client, session_id="user-123")
            result = await agent.run("Find me a restaurant", deps=deps)
    """

    client: "MemoryClient"
    session_id: str

    async def get_context(self, query: str) -> str:
        """
        Get combined context from all memory types.

        Args:
            query: Query to find relevant context

        Returns:
            Formatted context string for LLM prompts
        """
        return await self.client.get_context(query, session_id=self.session_id)

    async def save_interaction(
        self,
        user_message: str,
        assistant_message: str,
        *,
        extract_entities: bool = True,
    ) -> None:
        """
        Save an interaction to memory.

        Args:
            user_message: The user's message
            assistant_message: The assistant's response
            extract_entities: Whether to extract entities from messages
        """
        await self.client.episodic.add_message(
            self.session_id,
            "user",
            user_message,
            extract_entities=extract_entities,
        )
        await self.client.episodic.add_message(
            self.session_id,
            "assistant",
            assistant_message,
            extract_entities=extract_entities,
        )

    async def add_preference(
        self,
        category: str,
        preference: str,
        context: str | None = None,
    ) -> None:
        """
        Add a user preference.

        Args:
            category: Preference category
            preference: The preference statement
            context: When/where preference applies
        """
        await self.client.semantic.add_preference(category, preference, context=context)

    async def search_preferences(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant preferences.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of preference dictionaries
        """
        prefs = await self.client.semantic.search_preferences(query, limit=limit)
        return [
            {
                "category": p.category,
                "preference": p.preference,
                "context": p.context,
                "confidence": p.confidence,
            }
            for p in prefs
        ]


def create_memory_tools(memory: "MemoryClient") -> list[Callable]:
    """
    Create Pydantic AI tools for memory operations.

    Returns tools that can be registered with a Pydantic AI agent for:
    - search_memory: Search across all memory types
    - save_preference: Save a user preference
    - recall_preferences: Get user preferences for a topic

    Example:
        from pydantic_ai import Agent
        from neo4j_agent_memory.integrations.pydantic_ai import create_memory_tools

        async with MemoryClient(settings) as client:
            tools = create_memory_tools(client)
            agent = Agent('openai:gpt-4o', tools=tools)
    """

    async def search_memory(
        query: str,
        memory_types: list[str] | None = None,
    ) -> str:
        """
        Search the agent's memory for relevant information.

        Args:
            query: Search query
            memory_types: Types to search (episodic, semantic, procedural)

        Returns:
            Relevant memories as formatted text
        """
        results = []
        types = memory_types or ["episodic", "semantic", "procedural"]

        if "episodic" in types:
            messages = await memory.episodic.search_messages(query, limit=5)
            for msg in messages:
                results.append(f"[{msg.role.value}] {msg.content}")

        if "semantic" in types:
            entities = await memory.semantic.search_entities(query, limit=5)
            for entity in entities:
                desc = f": {entity.description}" if entity.description else ""
                results.append(f"[{entity.type.value}] {entity.display_name}{desc}")

            prefs = await memory.semantic.search_preferences(query, limit=5)
            for pref in prefs:
                results.append(f"[PREFERENCE:{pref.category}] {pref.preference}")

        if "procedural" in types:
            traces = await memory.procedural.get_similar_traces(query, limit=3)
            for trace in traces:
                status = "succeeded" if trace.success else "failed"
                results.append(f"[TASK] {trace.task} - {status}")

        return "\n".join(results) if results else "No relevant memories found."

    async def save_preference(
        category: str,
        preference: str,
        context: str | None = None,
    ) -> str:
        """
        Save a user preference to memory.

        Args:
            category: Preference category (food, music, etc.)
            preference: The preference statement
            context: When/where it applies

        Returns:
            Confirmation message
        """
        await memory.semantic.add_preference(category, preference, context=context)
        return f"Saved preference: {preference} (category: {category})"

    async def recall_preferences(topic: str) -> str:
        """
        Recall user preferences related to a topic.

        Args:
            topic: Topic to search for

        Returns:
            Relevant preferences as formatted text
        """
        prefs = await memory.semantic.search_preferences(topic, limit=10)
        if not prefs:
            return "No preferences found for this topic."
        return "\n".join([f"- [{p.category}] {p.preference}" for p in prefs])

    return [search_memory, save_preference, recall_preferences]
