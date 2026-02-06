"""PydanticAI podcast exploration agent."""

import json
import os
from functools import lru_cache

from pydantic_ai import Agent, RunContext

from src.agent.dependencies import AgentDeps
from src.agent.tools import (
    calculate_location_distances,
    # NEW: Entity management tools
    find_duplicate_entities,
    find_location_path,
    find_locations_near,
    find_related_entities,
    find_similar_past_queries,
    # NEW: Conversation & summary tools
    get_conversation_context,
    get_entity_context,
    get_entity_provenance,
    # Podcast search tools
    get_episode_list,
    get_episode_locations,
    get_episode_summary,
    get_location_clusters,
    get_memory_stats,
    get_most_mentioned_entities,
    get_session_reasoning_history,
    get_speaker_list,
    get_tool_usage_patterns,
    # Preferences and reasoning memory tools
    get_user_preferences,
    # NEW: Enhanced reasoning memory tools
    learn_from_similar_task,
    list_podcast_sessions,
    # NEW: Memory graph search
    memory_graph_search,
    search_by_episode,
    search_by_speaker,
    # Entity query tools
    search_entities,
    # Location query tools
    search_locations,
    search_podcast_content,
    trigger_entity_enrichment,
)
from src.config import get_settings

SYSTEM_PROMPT = """You are a helpful assistant that has deep knowledge of Lenny's Podcast.

Lenny Rachitsky is the host who interviews world-class product leaders, growth experts,
and founders. The podcast covers topics like product management, growth, startups,
leadership, career development, and mental health.

## The Three Memory Types

This system uses three types of memory that work together to provide comprehensive context:

1. **Short-Term Memory** (Conversations)
   - Recent messages in the current chat session
   - Maintains conversation context for follow-up questions
   - Enables multi-turn dialogue with memory of what was discussed

2. **Long-Term Memory** (Knowledge Graph)
   - Entities (people, companies, concepts, locations) extracted from 299 podcast episodes
   - Wikipedia enrichment for notable entities with descriptions and images
   - Relationships between entities discovered through co-occurrence
   - Use for entity lookups, discovering connections, and understanding context

3. **Reasoning Memory** (Tool Traces)
   - Records of past successful queries and the approaches that worked
   - Tool usage statistics showing which tools perform best
   - Enables learning from past interactions to improve future responses

When answering questions, leverage all three memory types for the most comprehensive response.

## CRITICAL: Multi-Step Reasoning & Retry Strategy

**NEVER give up after a single tool call returns no results.** Always try multiple approaches:

### When a Tool Returns No/Few Results:

1. **Try broader search terms**: If "company culture" returns nothing, try "culture", "team", "values", "hiring"
2. **Try different tools**: If `tool_search_by_speaker` fails, try `tool_search_podcast` with similar query
3. **Verify the entity exists**: Use `tool_search_entities` or `tool_get_entity_context` to check spelling/existence
4. **Search the episode directly**: Use `tool_search_episode` with just the guest name (no topic filter)
5. **Use semantic search**: `tool_search_podcast` and `tool_memory_graph_search` use vector embeddings - try rephrasing

### Example: "What did Tobi Lutke say about company culture?"

If `tool_search_by_speaker("Tobi Lutke", "company culture")` returns no results:
1. First, verify the guest exists: `tool_search_entities("Tobi Lutke", "PERSON")` or `tool_list_episodes()`
2. Try broader topic: `tool_search_by_speaker("Tobi Lutke", "culture")` or `tool_search_by_speaker("Tobi Lutke", "team")`
3. Search the episode: `tool_search_episode("Tobi Lutke")` to see what topics ARE discussed
4. Try semantic search: `tool_search_podcast("Tobi Lutke culture values team building")`
5. Explore the graph: `tool_memory_graph_search("company culture leadership")` to find related discussions

**You must try at least 2-3 different approaches before concluding no information exists.**

## Tool Selection Strategy (Priority Order)

### For "What did [Person] say about [Topic]?" questions:

1. **FIRST**: `tool_search_podcast("[Person] [Topic]")` - Best for semantic search across all content
2. **SECOND**: `tool_search_by_speaker(speaker="[Person]", topic="[Topic]")` - Filters by speaker
3. **THIRD**: `tool_search_episode(guest_name="[Person]", topic="[Topic]")` - If they were a guest
4. **FALLBACK**: `tool_search_episode(guest_name="[Person]")` - Browse episode without topic filter
5. **EXPLORE**: `tool_memory_graph_search("[Topic]")` - See topic across all speakers with entity connections

### For "Who is [Person]?" questions:

1. `tool_get_entity_context("[Person]")` - Get Wikipedia-enriched profile
2. `tool_find_related_entities("[Person]")` - See connections
3. `tool_search_entities("[Person]")` - If exact name unknown

### For topic exploration:

1. `tool_search_podcast("[topic]")` - Semantic search across all episodes
2. `tool_memory_graph_search("[topic]")` - See topic with entity graph
3. `tool_get_top_entities(entity_type="CONCEPT")` - See most discussed concepts

## Quick Tool Selection Guide

| User Intent | Primary Tool | Fallback Tools |
|-------------|--------------|----------------|
| "What did X say about Y?" | `tool_search_podcast("X Y")` | `tool_search_by_speaker`, `tool_search_episode` |
| "Who is X?" | `tool_get_entity_context` | `tool_search_entities`, `tool_find_related_entities` |
| "Most mentioned companies" | `tool_get_top_entities(entity_type="ORGANIZATION")` | `tool_search_entities` |
| "What's related to X?" | `tool_find_related_entities` | `tool_memory_graph_search`, `tool_get_entity_context` |
| "Explore [topic]" | `tool_memory_graph_search` | `tool_search_podcast`, `tool_search_entities` |
| "Locations in episode" | `tool_get_episode_locations` | `tool_search_locations` |
| "Compare X and Y" | Multiple `tool_search_podcast` calls | `tool_get_entity_context` for both |

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

## Personalization & Memory
- Access user preferences to tailor responses
- Learn from successful past interactions
- Recall earlier parts of the conversation

## Reasoning & Learning
- Find similar past tasks and learn from successful approaches
- Analyze which tools work best for different query types
- Track reasoning history for complex multi-step tasks

## Data Quality & Provenance
- Check where entity information came from (provenance)
- Find potential duplicate entities in the knowledge graph
- Check enrichment status for entities (Wikipedia data availability)

## Episode Overview
- Get episode summaries with key topics and entities
- List all podcast sessions with metadata
- Browse conversation history

Notable guests include Brian Chesky (Airbnb), Andy Johns (growth expert),
Melissa Perri (product management), Ryan Hoover (Product Hunt), and many others.

## Multi-Step Reasoning & Re-Planning

**You are expected to make MULTIPLE tool calls for most queries.** A single tool call is rarely sufficient.

### After Each Tool Call, Ask Yourself:

1. **Did I get useful results?** If no/few results → try a different tool or broader query
2. **Do I have enough information?** If not → call additional tools to fill gaps
3. **Should I verify this?** For important claims → cross-reference with another tool
4. **Can I enrich this?** After finding content → use entity tools to add context

### Mandatory Retry Pattern:

When a tool returns empty/no results:
```
STEP 1: Try the SAME tool with broader/different terms
STEP 2: Try a DIFFERENT tool (e.g., tool_search_podcast instead of tool_search_by_speaker)
STEP 3: Verify the entity/topic exists (tool_search_entities, tool_list_episodes)
STEP 4: Only after 3+ attempts, explain what you tried and why no results were found
```

### Example Multi-Step Flow:

Query: "What did Tobi Lutke say about company culture?"

```
CALL 1: tool_search_podcast("Tobi Lutke company culture")
        → If no results, DON'T STOP
CALL 2: tool_search_by_speaker("Tobi Lutke", "culture")
        → If no results, DON'T STOP
CALL 3: tool_list_episodes() to verify "Tobi Lutke" is a guest
        → If not found, inform user; If found, continue
CALL 4: tool_search_episode("Tobi Lutke") without topic filter
        → See what topics ARE discussed in that episode
CALL 5: tool_search_podcast("Shopify culture team values")
        → Try searching for their company instead
```

Only after exhausting multiple approaches should you conclude no information exists.

## Fuzzy Matching & Vector Search

All tools support **fuzzy name matching** via vector search. You don't need exact names:
- "Chesky" will find "Brian Chesky"
- "airbnb founder" will find Airbnb-related content
- "growth strategies" will find semantically similar discussions
- Names with special characters work: "Lütke" or "Lutke" both work

**Best practices:**
- Use natural language queries - tools use semantic search, not just keyword matching
- `tool_search_podcast` is the most flexible - it searches ALL content semantically
- For entity lookups, partial names work fine (e.g., "Chesky" instead of "Brian Chesky")
- If exact speaker search fails, try searching the podcast content with their name + topic

## CRITICAL: Always Use Tools & Never Give Up Early

**You MUST use one or more tools for EVERY user message.** Never respond based solely on your general knowledge.

### Tool Usage Requirements:

- For ANY question about podcast content, guests, topics, or insights: Use search tools first
- For questions about people or companies: Use entity tools to get actual data
- For geographic questions: Use location tools
- For general questions about the podcast: Use episode/speaker list tools or stats

### Default Starting Tool:

If unsure which tool to use, **start with `tool_search_podcast`** - it's the most flexible and uses semantic search.

### NEVER Do This:

❌ Call ONE tool, get no results, and say "I couldn't find anything"
❌ Give up after a single failed search
❌ Respond based on general knowledge without trying multiple tools

### ALWAYS Do This:

✅ Try at least 2-3 different tools/queries before concluding no data exists
✅ When one tool fails, try a different tool or broader search terms
✅ Verify entities exist before giving up (use tool_list_episodes, tool_search_entities)
✅ Ground your response in actual tool results, citing what you found

## Response Guidelines

When answering questions:
1. **Call multiple tools** - most questions need 2+ tool calls for a complete answer
2. **If first tool fails, keep trying** - use the retry pattern above
3. Quote or paraphrase what guests actually said when possible
4. Cite the guest name and episode context when sharing insights
5. If after 3+ attempts you truly find nothing, explain what you tried
6. Offer to explore related topics, entities, or locations

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
        """Search podcast transcripts using semantic/vector search.

        Uses AI embeddings to find semantically similar content, not just keyword matches.
        Good for finding discussions about topics even when exact words aren't used.

        Args:
            query: Natural language search (e.g., "how to find product market fit", "scaling teams", "founder mental health")
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
        """Search for what a specific speaker said, with semantic topic search.

        Best results when you provide BOTH speaker AND topic - uses vector search on topic.
        Supports fuzzy speaker matching (e.g., "Chesky" matches "Brian Chesky").

        Args:
            speaker: Speaker name - partial matches work (e.g., "Chesky", "Lenny", "Andy")
            topic: Topic to search for semantically (e.g., "hiring mistakes", "scaling challenges")
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
        """Search for entities using semantic/vector search with fuzzy matching.

        Finds people, companies, concepts, or events even with partial names or synonyms.
        Use this to discover entity names before calling tool_get_entity_context.

        Args:
            query: Search term - can be partial name or concept (e.g., "Chesky", "Y Combinator", "product growth")
            entity_type: Optional filter - PERSON, ORGANIZATION, LOCATION, EVENT, CONCEPT
            limit: Maximum number of results
        """
        result = await search_entities(ctx, query, entity_type, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_entity_context(
        ctx: RunContext[AgentDeps],
        entity_name: str,
    ) -> str:
        """Get detailed context about an entity with Wikipedia enrichment.

        Supports fuzzy name matching - partial names like "Chesky" will find "Brian Chesky".
        Returns enriched data (Wikipedia summary, image, URL) if available, plus podcast mentions.

        Args:
            entity_name: Full or partial entity name (e.g., "Brian Chesky", "Chesky", "Airbnb")
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

    # ==========================================================================
    # Enhanced Reasoning Memory Tools (NEW)
    # ==========================================================================

    @agent.tool
    async def tool_learn_from_similar_task(
        ctx: RunContext[AgentDeps],
        task_description: str,
        limit: int = 1,
    ) -> str:
        """Get full reasoning traces from similar past tasks for few-shot learning.

        Returns complete reasoning steps so you can learn the approach that worked.
        Use this when facing a complex or unfamiliar task.

        Args:
            task_description: Description of the current task
            limit: Number of similar traces to return
        """
        result = await learn_from_similar_task(ctx, task_description, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_tool_patterns(
        ctx: RunContext[AgentDeps],
        tool_name: str | None = None,
        limit: int = 10,
    ) -> str:
        """Analyze tool usage patterns to understand which tools are most effective.

        Returns success rates, average durations, and recommendations.
        Use this to optimize your tool selection strategy.

        Args:
            tool_name: Optional specific tool to analyze
            limit: Maximum number of tools to include
        """
        result = await get_tool_usage_patterns(ctx, tool_name, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_reasoning_history(
        ctx: RunContext[AgentDeps],
        session_id: str | None = None,
        limit: int = 10,
    ) -> str:
        """Get reasoning traces from a session to understand conversation history.

        Use this to see what reasoning approaches were used previously.

        Args:
            session_id: Session ID to query (defaults to current session)
            limit: Maximum number of traces to return
        """
        result = await get_session_reasoning_history(ctx, session_id, limit)
        return json.dumps(result, default=str)

    # ==========================================================================
    # Entity Management Tools (NEW)
    # ==========================================================================

    @agent.tool
    async def tool_find_duplicates(
        ctx: RunContext[AgentDeps],
        entity_type: str | None = None,
        limit: int = 20,
    ) -> str:
        """Find potential duplicate entities that may need merging.

        Useful for data quality analysis and entity resolution.

        Args:
            entity_type: Filter by type (PERSON, ORGANIZATION, etc.)
            limit: Maximum number of duplicate pairs to return
        """
        result = await find_duplicate_entities(ctx, entity_type, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_entity_provenance(
        ctx: RunContext[AgentDeps],
        entity_name: str,
    ) -> str:
        """Get the source/provenance information for an entity.

        Shows which messages the entity was extracted from.
        Use this to understand where information came from.

        Args:
            entity_name: Name of the entity to get provenance for
        """
        result = await get_entity_provenance(ctx, entity_name)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_check_enrichment(
        ctx: RunContext[AgentDeps],
        entity_name: str,
        provider: str = "wikimedia",
    ) -> str:
        """Check enrichment status for an entity or request enrichment.

        Shows if entity has Wikipedia data or needs enrichment.

        Args:
            entity_name: Name of the entity to check
            provider: Enrichment provider ("wikimedia" or "diffbot")
        """
        result = await trigger_entity_enrichment(ctx, entity_name, provider)
        return json.dumps(result, default=str)

    # ==========================================================================
    # Conversation & Summary Tools (NEW)
    # ==========================================================================

    @agent.tool
    async def tool_get_conversation_context(
        ctx: RunContext[AgentDeps],
        limit: int = 10,
    ) -> str:
        """Get recent conversation history for context.

        Use this to recall what was discussed earlier in the conversation.

        Args:
            limit: Maximum number of messages to return
        """
        result = await get_conversation_context(ctx, limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_list_podcast_sessions(
        ctx: RunContext[AgentDeps],
        sort_by: str = "message_count",
        limit: int = 20,
    ) -> str:
        """List available podcast sessions with metadata.

        Shows episodes with message counts and timestamps.

        Args:
            sort_by: Sort field ("message_count", "created_at", "updated_at")
            limit: Maximum number of sessions
        """
        result = await list_podcast_sessions(ctx, sort_by, "desc", limit)
        return json.dumps(result, default=str)

    @agent.tool
    async def tool_get_episode_summary(
        ctx: RunContext[AgentDeps],
        episode_guest: str,
    ) -> str:
        """Get a summary of a podcast episode including key topics and entities.

        Use this to get a quick overview before diving into specific content.

        Args:
            episode_guest: Guest name (e.g., "Brian Chesky")
        """
        result = await get_episode_summary(ctx, episode_guest)
        return json.dumps(result, default=str)

    # ==========================================================================
    # Memory Graph Search Tool (NEW)
    # ==========================================================================

    @agent.tool
    async def tool_memory_graph_search(
        ctx: RunContext[AgentDeps],
        query: str,
        limit: int = 10,
        include_related_entities: bool = True,
        max_related_per_entity: int = 5,
    ) -> str:
        """Search memory using semantic similarity, then explore the knowledge graph.

        This is the most powerful search tool - it combines:
        1. Vector search to find semantically similar podcast segments (more messages)
        2. Graph traversal to find ALL entities mentioned in those segments
        3. Relationship expansion to discover ALL connected entities for each entity found

        Use this when you want to explore a topic comprehensively, seeing both
        what was said AND the entities/concepts involved. The result is a rich graph
        visualization showing messages, their mentioned entities, and all related entities.

        Args:
            query: Natural language search (e.g., "challenges of scaling", "product-market fit")
            limit: Number of messages to find (default 10)
            include_related_entities: Whether to expand to related entities (default True)
            max_related_per_entity: Max related entities per found entity (default 5)
        """
        result = await memory_graph_search(
            ctx, query, limit, include_related_entities, max_related_per_entity
        )
        return json.dumps(result, default=str)

    return agent


# For convenience
def podcast_agent() -> Agent[AgentDeps, str]:
    """Get the podcast agent instance."""
    return get_podcast_agent()
