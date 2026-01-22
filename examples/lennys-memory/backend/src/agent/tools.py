"""Podcast search tools for the chat agent."""

from typing import Any

from pydantic_ai import RunContext

from src.agent.dependencies import AgentDeps


async def search_podcast_content(
    ctx: RunContext[AgentDeps],
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search podcast transcripts using semantic search.

    Args:
        ctx: The agent run context.
        query: Search terms or topic to find.
        limit: Maximum number of results to return.

    Returns:
        List of matching transcript segments with speaker, episode, and content.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        messages = await ctx.deps.client.episodic.search_messages(
            query=query,
            limit=limit,
            threshold=0.5,
        )

        return [
            {
                "content": (msg.content[:500] + "..." if len(msg.content) > 500 else msg.content),
                "speaker": msg.metadata.get("speaker", "Unknown"),
                "episode_guest": msg.metadata.get("episode_guest", "Unknown"),
                "timestamp": msg.metadata.get("timestamp", ""),
                "relevance": round(msg.metadata.get("similarity", 0), 3),
            }
            for msg in messages
        ]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


async def search_by_speaker(
    ctx: RunContext[AgentDeps],
    speaker: str,
    topic: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search for what a specific speaker said.

    Args:
        ctx: The agent run context.
        speaker: Name of the speaker (e.g., "Brian Chesky", "Lenny").
        topic: Optional topic to filter by.
        limit: Maximum number of results to return.

    Returns:
        List of transcript segments from the specified speaker.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        # Use the internal Neo4j client to run a custom query
        # This filters by speaker metadata stored in messages
        query = """
        MATCH (c:Conversation)-[:HAS_MESSAGE]->(m:Message)
        WHERE c.session_id STARTS WITH 'lenny-podcast-'
        AND m.metadata IS NOT NULL
        AND m.metadata CONTAINS $speaker_pattern
        """

        params: dict[str, Any] = {"speaker_pattern": f'"speaker": "{speaker}"'}

        if topic:
            query += " AND toLower(m.content) CONTAINS toLower($topic)"
            params["topic"] = topic

        query += """
        RETURN m.content AS content,
               m.metadata AS metadata,
               c.session_id AS session_id
        ORDER BY m.created_at DESC
        LIMIT $limit
        """
        params["limit"] = limit

        results = await ctx.deps.client._client.execute_read(query, params)

        return [
            {
                "content": (
                    r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"]
                ),
                "session_id": r["session_id"],
                "metadata": r["metadata"],
            }
            for r in results
        ]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


async def search_by_episode(
    ctx: RunContext[AgentDeps],
    guest_name: str,
    topic: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search within a specific episode by guest name.

    Args:
        ctx: The agent run context.
        guest_name: Name of the podcast guest.
        topic: Optional topic to search for within the episode.
        limit: Maximum number of results to return.

    Returns:
        List of transcript segments from the specified episode.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        # Convert guest name to session_id format
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", guest_name.lower()).strip("-")
        session_id = f"lenny-podcast-{slug}"

        if topic:
            # Search within episode for specific topic
            messages = await ctx.deps.client.episodic.search_messages(
                query=topic,
                session_id=session_id,
                limit=limit,
            )
        else:
            # Get conversation from episode
            conv = await ctx.deps.client.episodic.get_conversation(
                session_id=session_id,
                limit=limit,
            )
            messages = conv.messages if conv else []

        return [
            {
                "content": (msg.content[:500] + "..." if len(msg.content) > 500 else msg.content),
                "speaker": msg.metadata.get("speaker", "Unknown"),
                "timestamp": msg.metadata.get("timestamp", ""),
            }
            for msg in messages
        ]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


async def get_episode_list(ctx: RunContext[AgentDeps]) -> list[dict[str, Any]]:
    """Get list of all podcast episodes.

    Args:
        ctx: The agent run context.

    Returns:
        List of episodes with guest names and message counts.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        query = """
        MATCH (c:Conversation)
        WHERE c.session_id STARTS WITH 'lenny-podcast-'
        OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
        WITH c, count(m) AS message_count
        RETURN c.session_id AS session_id,
               message_count
        ORDER BY c.session_id
        """

        results = await ctx.deps.client._client.execute_read(query)

        return [
            {
                "guest": r["session_id"].replace("lenny-podcast-", "").replace("-", " ").title(),
                "session_id": r["session_id"],
                "message_count": r["message_count"],
            }
            for r in results
        ]
    except Exception as e:
        return [{"error": f"Query failed: {str(e)}"}]


async def get_speaker_list(ctx: RunContext[AgentDeps]) -> list[dict[str, Any]]:
    """Get list of all unique speakers across episodes.

    Args:
        ctx: The agent run context.

    Returns:
        List of speakers with their appearance counts.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        # Query to extract unique speakers from message metadata
        # Note: This assumes metadata is stored as JSON string
        query = """
        MATCH (c:Conversation)-[:HAS_MESSAGE]->(m:Message)
        WHERE c.session_id STARTS WITH 'lenny-podcast-'
        AND m.metadata IS NOT NULL
        WITH m.metadata AS meta
        WITH meta
        WHERE meta CONTAINS '"speaker":'
        RETURN DISTINCT meta
        LIMIT 500
        """

        results = await ctx.deps.client._client.execute_read(query)

        # Parse speaker names from metadata
        import json

        speakers: dict[str, int] = {}
        for r in results:
            try:
                if isinstance(r["meta"], str):
                    metadata = json.loads(r["meta"])
                else:
                    metadata = r["meta"]
                speaker = metadata.get("speaker", "Unknown")
                speakers[speaker] = speakers.get(speaker, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

        return [
            {"speaker": name, "appearance_count": count}
            for name, count in sorted(speakers.items(), key=lambda x: -x[1])
        ]
    except Exception as e:
        return [{"error": f"Query failed: {str(e)}"}]


async def get_memory_stats(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
    """Get statistics about the loaded podcast data.

    Args:
        ctx: The agent run context.

    Returns:
        Dictionary with counts of episodes, messages, speakers, etc.
    """
    if not ctx.deps.client:
        return {"error": "Memory client not available"}

    try:
        stats = await ctx.deps.client.get_stats()
        return {
            "conversations": stats.get("conversations", 0),
            "messages": stats.get("messages", 0),
            "entities": stats.get("entities", 0),
            "note": "These are podcast transcript segments loaded into memory",
        }
    except Exception as e:
        return {"error": f"Failed to get stats: {str(e)}"}
