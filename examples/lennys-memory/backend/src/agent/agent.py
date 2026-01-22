"""PydanticAI podcast exploration agent."""

import json
import os
from functools import lru_cache

from pydantic_ai import Agent, RunContext

from src.agent.dependencies import AgentDeps
from src.agent.tools import (
    get_episode_list,
    get_memory_stats,
    get_speaker_list,
    search_by_episode,
    search_by_speaker,
    search_podcast_content,
)
from src.config import get_settings

SYSTEM_PROMPT = """You are a helpful assistant that has deep knowledge of Lenny's Podcast.

Lenny Rachitsky is the host who interviews world-class product leaders, growth experts,
and founders. The podcast covers topics like product management, growth, startups,
leadership, career development, and mental health.

You have access to transcripts from the podcast stored in memory. You can:
- Search for specific topics, quotes, or discussions across all episodes
- Find what guests said about particular subjects
- Explore episodes by guest name
- See who has appeared on the podcast

Notable guests include Brian Chesky (Airbnb), Andy Johns (growth expert),
Melissa Perri (product management), Ryan Hoover (Product Hunt), and many others.

When answering questions:
1. Use the search tools to find relevant podcast content
2. Quote or paraphrase what guests actually said when possible
3. Cite the guest name and context when sharing insights
4. Offer to explore related topics if the user is interested
5. If you can't find specific content, be honest about it

Be conversational and helpful. Share interesting insights from the podcast discussions.
"""


@lru_cache
def get_podcast_agent() -> Agent[AgentDeps, str]:
    """Create and return the podcast agent (cached)."""
    # Ensure OpenAI API key is set in environment
    settings = get_settings()
    if settings.openai_api_key.get_secret_value():
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key.get_secret_value()

    agent = Agent(
        "openai:gpt-4o",
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
    )

    # Add dynamic memory context via decorator
    @agent.system_prompt
    async def add_memory_context(ctx: RunContext[AgentDeps]) -> str:
        """Add memory context to system prompt."""
        if ctx.deps.memory_enabled and ctx.deps.client is not None:
            try:
                memory_context = await ctx.deps.get_context(query="")
                if memory_context:
                    return f"""
## Your Memory Context

The following information is from your memory about this conversation and user:

{memory_context}

Use this context to personalize your responses and maintain continuity across conversations.
"""
            except Exception:
                pass
        return ""

    # Register tools
    @agent.tool
    async def tool_search_podcast(
        ctx: RunContext[AgentDeps],
        query: str,
        limit: int = 10,
    ) -> str:
        """Search podcast transcripts for relevant content.

        Use this to find discussions about specific topics, concepts, or quotes.

        Args:
            query: Search terms or topic to find (e.g., "product market fit", "hiring", "growth loops")
            limit: Maximum number of results to return
        """
        result = await search_podcast_content(ctx, query, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_search_by_speaker(
        ctx: RunContext[AgentDeps],
        speaker: str,
        topic: str | None = None,
        limit: int = 10,
    ) -> str:
        """Search for what a specific speaker said.

        Use this to find quotes or discussions from a particular person.

        Args:
            speaker: Name of the speaker (e.g., "Brian Chesky", "Lenny", "Andy Johns")
            topic: Optional topic to filter by (e.g., "leadership", "growth")
            limit: Maximum number of results
        """
        result = await search_by_speaker(ctx, speaker, topic, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_search_episode(
        ctx: RunContext[AgentDeps],
        guest_name: str,
        topic: str | None = None,
        limit: int = 10,
    ) -> str:
        """Search within a specific episode by guest name.

        Use this to explore what was discussed in a particular episode.

        Args:
            guest_name: Name of the podcast guest (e.g., "Brian Chesky", "Andy Johns")
            topic: Optional topic to search for within the episode
            limit: Maximum number of results
        """
        result = await search_by_episode(ctx, guest_name, topic, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_list_episodes(ctx: RunContext[AgentDeps]) -> str:
        """Get list of all podcast episodes available.

        Use this to see which episodes/guests are available to explore.
        """
        result = await get_episode_list(ctx)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_list_speakers(ctx: RunContext[AgentDeps]) -> str:
        """Get list of all speakers who appear in the podcast.

        This includes Lenny and all guests.
        """
        result = await get_speaker_list(ctx)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_stats(ctx: RunContext[AgentDeps]) -> str:
        """Get statistics about the loaded podcast data.

        Use this to understand how much content is available.
        """
        result = await get_memory_stats(ctx)
        return json.dumps(result, default=str)

    return agent


# For convenience
def podcast_agent() -> Agent[AgentDeps, str]:
    """Get the podcast agent instance."""
    return get_podcast_agent()
