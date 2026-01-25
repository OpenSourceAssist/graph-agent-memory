"""PydanticAI podcast exploration agent."""

import json
import os
from functools import lru_cache

from pydantic_ai import Agent, RunContext

from src.agent.dependencies import AgentDeps
from src.agent.tools import (
    calculate_location_distances,
    find_location_path,
    find_locations_near,
    find_related_entities,
    find_similar_past_queries,
    get_entity_context,
    # Podcast search tools
    get_episode_list,
    get_episode_locations,
    get_location_clusters,
    get_memory_stats,
    get_most_mentioned_entities,
    get_speaker_list,
    # Preferences and reasoning memory tools
    get_user_preferences,
    search_by_episode,
    search_by_speaker,
    # Entity query tools
    search_entities,
    # Location query tools
    search_locations,
    search_podcast_content,
)
from src.config import get_settings

SYSTEM_PROMPT = """You are a helpful assistant that has deep knowledge of Lenny's Podcast.

Lenny Rachitsky is the host who interviews world-class product leaders, growth experts,
and founders. The podcast covers topics like product management, growth, startups,
leadership, career development, and mental health.

You have access to transcripts from the podcast stored in memory. You can:

## Podcast Content Search
- Search for specific topics, quotes, or discussions across all episodes
- Find what guests said about particular subjects
- Explore episodes by guest name
- See who has appeared on the podcast

## Entity Knowledge Graph
- Search for people, companies, and concepts mentioned in podcasts
- Get detailed context about entities including Wikipedia enrichment
- Find related entities that are frequently mentioned together
- See the most discussed topics and influential figures

## Geographic Analysis (Map View)
- Search for locations mentioned in podcasts
- Find nearby locations discussed together
- Get geographic profiles of specific episodes
- Find how locations are connected through the knowledge graph
- Analyze location clusters to understand geographic focus
- Calculate distances between mentioned locations

## Personalization
- Access user preferences to tailor responses
- Learn from successful past interactions

Notable guests include Brian Chesky (Airbnb), Andy Johns (growth expert),
Melissa Perri (product management), Ryan Hoover (Product Hunt), and many others.

## Multi-Step Reasoning

For complex questions, you should:
1. **Plan first**: Break down the question into steps and identify which tools to use
2. **Execute step by step**: Call tools one at a time, using results to inform next steps
3. **Synthesize**: Combine information from multiple tool calls into a coherent answer

For example, if asked "Compare what Brian Chesky and Andy Johns said about growth":
- First, search for Brian Chesky's comments on growth
- Then, search for Andy Johns' comments on growth
- Finally, synthesize and compare their perspectives

You can call multiple tools in sequence to gather comprehensive information.

## CRITICAL: Always Use Tools

**You MUST use one or more tools for EVERY user message.** Never respond based solely on your general knowledge.

- For ANY question about podcast content, guests, topics, or insights: Use search tools first
- For questions about people or companies: Use entity tools to get actual data
- For geographic questions: Use location tools
- For general questions about the podcast: Use episode/speaker list tools or stats
- Even for simple greetings or clarifications: Use a tool like get_stats or list_episodes to provide relevant context

If you're unsure which tool to use, start with `tool_search_podcast` with relevant keywords.

Your responses should be grounded in actual tool results, not general knowledge about the topics.

## Response Guidelines

When answering questions:
1. **ALWAYS call at least one tool before responding** - this is mandatory
2. Use the search tools to find relevant podcast content
3. Use entity tools to provide richer context about people, companies, and topics
4. Use location tools when discussing geographic aspects or market regions
5. Quote or paraphrase what guests actually said when possible
6. Cite the guest name and context when sharing insights
7. Offer to explore related topics, entities, or locations if the user is interested
8. If tools return no results, be honest about it but still base your response on the tool output

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
        """Add memory context to system prompt including preferences and similar traces."""
        if not ctx.deps.memory_enabled or ctx.deps.client is None:
            return ""

        context_parts = []

        try:
            # Get general memory context
            memory_context = await ctx.deps.get_context(query="")
            if memory_context:
                context_parts.append(f"""## Conversation Memory

The following information is from your memory about this conversation and user:

{memory_context}""")
        except Exception:
            pass

        try:
            # Get user preferences
            preferences = await ctx.deps.client.long_term.search_preferences("", limit=10)
            if preferences:
                pref_list = [f"- {p.category}: {p.preference}" for p in preferences]
                context_parts.append(f"""## User Preferences

The user has expressed these preferences:
{chr(10).join(pref_list)}

Tailor your responses to match these preferences where relevant.""")
        except Exception:
            pass

        try:
            # Get similar past traces if there's a current query
            if ctx.deps.current_query:
                similar_traces = await ctx.deps.client.reasoning.get_similar_traces(
                    task=ctx.deps.current_query,
                    limit=2,
                    success_only=True,
                )
                if similar_traces:
                    trace_items = [
                        f"- Query: {t.task}, Outcome: {t.outcome}" for t in similar_traces
                    ]
                    context_parts.append(f"""## Relevant Past Interactions

You've successfully handled similar queries before. Consider these approaches:
{chr(10).join(trace_items)}""")
        except Exception:
            pass

        if context_parts:
            return "\n\n".join(context_parts)
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

    # ==========================================================================
    # Entity Query Tools
    # ==========================================================================

    @agent.tool
    async def tool_search_entities(
        ctx: RunContext[AgentDeps],
        query: str,
        entity_type: str | None = None,
        limit: int = 10,
    ) -> str:
        """Search for entities (people, organizations, topics) mentioned in podcasts.

        Use this to find specific people, companies, concepts, or events discussed.

        Args:
            query: Search term (e.g., "product-market fit", "Y Combinator", "growth")
            entity_type: Filter by type - PERSON, ORGANIZATION, LOCATION, EVENT, CONCEPT
            limit: Maximum number of results
        """
        result = await search_entities(ctx, query, entity_type, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_entity_context(
        ctx: RunContext[AgentDeps],
        entity_name: str,
    ) -> str:
        """Get detailed context about a specific entity.

        Use this to get comprehensive information including Wikipedia data and podcast mentions.

        Args:
            entity_name: Name of the entity (e.g., "Brian Chesky", "Airbnb")
        """
        result = await get_entity_context(ctx, entity_name)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_find_related_entities(
        ctx: RunContext[AgentDeps],
        entity_name: str,
        limit: int = 10,
    ) -> str:
        """Find entities related to a given entity through co-occurrence.

        Use this to explore connections between people, companies, and concepts.

        Args:
            entity_name: Starting entity (e.g., "Airbnb", "growth")
            limit: Maximum number of related entities
        """
        result = await find_related_entities(ctx, entity_name, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_top_entities(
        ctx: RunContext[AgentDeps],
        entity_type: str | None = None,
        limit: int = 10,
    ) -> str:
        """Get the most frequently mentioned entities across all podcasts.

        Use this to discover key themes, influential figures, or important companies.

        Args:
            entity_type: Filter by PERSON, ORGANIZATION, CONCEPT, LOCATION, etc.
            limit: Number of results (default 10)
        """
        result = await get_most_mentioned_entities(ctx, entity_type, limit)
        return json.dumps(result, default=str)

    # ==========================================================================
    # Location Query Tools (Map View Integration)
    # ==========================================================================

    @agent.tool
    async def tool_search_locations(
        ctx: RunContext[AgentDeps],
        query: str | None = None,
        episode_guest: str | None = None,
        limit: int = 20,
    ) -> str:
        """Search for locations mentioned in podcasts.

        Returns locations with coordinates for map visualization.
        The frontend can display these with markers, clusters, or heatmap.

        Args:
            query: Optional search term (e.g., "Silicon Valley", "Europe")
            episode_guest: Optional guest name to filter by episode
            limit: Maximum number of results
        """
        result = await search_locations(ctx, query, episode_guest, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_find_locations_near(
        ctx: RunContext[AgentDeps],
        location_name: str,
        radius_km: float = 500.0,
        limit: int = 20,
    ) -> str:
        """Find other locations mentioned near a given location.

        Useful for understanding geographic context of discussions.
        Results can be visualized on the map with a radius overlay.

        Args:
            location_name: Reference location (e.g., "San Francisco")
            radius_km: Search radius in kilometers (default 500km)
            limit: Maximum number of results
        """
        result = await find_locations_near(ctx, location_name, radius_km, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_episode_locations(
        ctx: RunContext[AgentDeps],
        episode_guest: str,
    ) -> str:
        """Get all locations mentioned in a specific episode.

        Returns a geographic profile of the episode's content.

        Args:
            episode_guest: Guest name (e.g., "Brian Chesky")
        """
        result = await get_episode_locations(ctx, episode_guest)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_find_location_path(
        ctx: RunContext[AgentDeps],
        from_location: str,
        to_location: str,
    ) -> str:
        """Find the shortest path between two locations in the knowledge graph.

        Shows how locations are connected through entities, messages, and conversations.
        The frontend can visualize this as a path overlay on the map.

        Args:
            from_location: Starting location name
            to_location: Destination location name
        """
        result = await find_location_path(ctx, from_location, to_location)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_location_clusters(
        ctx: RunContext[AgentDeps],
        episode_guest: str | None = None,
    ) -> str:
        """Analyze geographic clusters of locations mentioned in podcasts.

        Returns location density by country/region, useful for understanding
        which geographic areas are most discussed. Works with the heatmap view.

        Args:
            episode_guest: Optional guest to filter by
        """
        result = await get_location_clusters(ctx, episode_guest)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_calculate_distances(
        ctx: RunContext[AgentDeps],
        locations: list[str],
    ) -> str:
        """Calculate distances between multiple locations.

        Returns pairwise distances in kilometers using great-circle calculation.
        Useful for understanding the geographic scope of discussions.

        Args:
            locations: List of location names to measure between (e.g., ["San Francisco", "New York", "London"])
        """
        result = await calculate_location_distances(ctx, locations)
        return json.dumps(result, default=str)

    # ==========================================================================
    # Preferences and Reasoning Memory Tools
    # ==========================================================================

    @agent.tool
    async def tool_get_user_preferences(ctx: RunContext[AgentDeps]) -> str:
        """Get the current user's stored preferences.

        Use this to understand user interests and personalize responses.
        Returns preferences about content interests, format preferences, etc.
        """
        result = await get_user_preferences(ctx)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_find_similar_queries(
        ctx: RunContext[AgentDeps],
        current_query: str,
        limit: int = 3,
    ) -> str:
        """Find similar queries from past conversations and their outcomes.

        Use this to learn from successful past interactions.

        Args:
            current_query: The current user query
            limit: Maximum number of similar traces to return
        """
        result = await find_similar_past_queries(ctx, current_query, limit)
        return json.dumps(result, default=str)

    return agent


# For convenience
def podcast_agent() -> Agent[AgentDeps, str]:
    """Get the podcast agent instance."""
    return get_podcast_agent()
