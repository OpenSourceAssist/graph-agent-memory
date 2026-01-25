"""Podcast search tools for the chat agent.

This module provides tools for:
- Podcast content search (transcripts, speakers, episodes)
- Entity queries (people, organizations, topics)
- Location queries with geospatial features
- User preferences and reasoning memory
"""

import json
import math
import re
from typing import Any

from pydantic_ai import RunContext

from src.agent.dependencies import AgentDeps


def _guest_to_session_id(guest_name: str) -> str:
    """Convert a guest name to a session_id format."""
    slug = re.sub(r"[^a-z0-9]+", guest_name.lower(), "-").strip("-")
    return f"lenny-podcast-{slug}"


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371  # Earth's radius in kilometers
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


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
        messages = await ctx.deps.client.short_term.search_messages(
            query=query,
            limit=limit,
            threshold=0.5,
            metadata_filters={"source": "lenny_podcast"},
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
            messages = await ctx.deps.client.short_term.search_messages(
                query=topic,
                session_id=session_id,
                limit=limit,
            )
        else:
            # Get conversation from episode
            conv = await ctx.deps.client.short_term.get_conversation(
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


# =============================================================================
# Entity Query Tools
# =============================================================================


async def search_entities(
    ctx: RunContext[AgentDeps],
    query: str,
    entity_type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search for entities (people, organizations, topics) mentioned in podcasts.

    Args:
        ctx: The agent run context.
        query: Search term (e.g., "product-market fit", "Y Combinator").
        entity_type: Filter by type - PERSON, ORGANIZATION, LOCATION, EVENT, CONCEPT.
        limit: Maximum number of results to return.

    Returns:
        List of entities with descriptions and mention counts.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        entities = await ctx.deps.client.long_term.search_entities(
            query=query,
            entity_type=entity_type,
            limit=limit,
        )

        return [
            {
                "name": e.name,
                "type": e.type,
                "subtype": e.subtype,
                "description": e.description,
                "wikipedia_url": e.wikipedia_url,
                "enriched": bool(e.enriched_description),
            }
            for e in entities
        ]
    except Exception as e:
        return [{"error": f"Entity search failed: {str(e)}"}]


async def get_entity_context(
    ctx: RunContext[AgentDeps],
    entity_name: str,
) -> dict[str, Any]:
    """Get full context about an entity including enrichment data.

    Args:
        ctx: The agent run context.
        entity_name: Name of entity (e.g., "Brian Chesky", "Airbnb").

    Returns:
        Entity details, Wikipedia summary (if available), and podcast mentions.
    """
    if not ctx.deps.client:
        return {"error": "Memory client not available"}

    try:
        # Get entity by name
        entity = await ctx.deps.client.long_term.get_entity_by_name(entity_name)
        if not entity:
            return {"error": f"Entity '{entity_name}' not found"}

        # Get mentions from the graph (filter to podcast sessions only)
        query = """
        MATCH (e:Entity {name: $name})<-[:MENTIONS]-(m:Message)<-[:HAS_MESSAGE]-(c:Conversation)
        WHERE c.session_id STARTS WITH 'lenny-podcast-'
        RETURN m.content AS content,
               m.metadata AS metadata,
               c.session_id AS session_id
        LIMIT 5
        """
        mentions = await ctx.deps.client._client.execute_read(query, {"name": entity_name})

        mention_list = []
        for m in mentions:
            metadata = m.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}
            mention_list.append(
                {
                    "content": m["content"][:300] + "..."
                    if len(m["content"]) > 300
                    else m["content"],
                    "speaker": metadata.get("speaker", "Unknown"),
                    "episode": m["session_id"]
                    .replace("lenny-podcast-", "")
                    .replace("-", " ")
                    .title(),
                }
            )

        return {
            "name": entity.name,
            "type": entity.type,
            "subtype": entity.subtype,
            "description": entity.description,
            "enriched_description": entity.enriched_description,
            "wikipedia_url": entity.wikipedia_url,
            "mentions": mention_list,
        }
    except Exception as e:
        return {"error": f"Failed to get entity context: {str(e)}"}


async def find_related_entities(
    ctx: RunContext[AgentDeps],
    entity_name: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find entities related to a given entity via the knowledge graph.

    Args:
        ctx: The agent run context.
        entity_name: Starting entity (e.g., "Airbnb").
        limit: Maximum number of related entities to return.

    Returns:
        List of related entities with co-occurrence counts.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        # Find entities that co-occur in the same messages (podcast sessions only)
        query = """
        MATCH (e1:Entity {name: $name})<-[:MENTIONS]-(m:Message)<-[:HAS_MESSAGE]-(c:Conversation)
        WHERE c.session_id STARTS WITH 'lenny-podcast-'
        MATCH (m)-[:MENTIONS]->(e2:Entity)
        WHERE e1 <> e2
        WITH e2, count(m) AS co_occurrences
        ORDER BY co_occurrences DESC
        LIMIT $limit
        RETURN e2.name AS name, e2.type AS type, e2.subtype AS subtype,
               e2.description AS description, co_occurrences
        """
        results = await ctx.deps.client._client.execute_read(
            query, {"name": entity_name, "limit": limit}
        )

        return [
            {
                "name": r["name"],
                "type": r["type"],
                "subtype": r["subtype"],
                "description": r["description"],
                "co_occurrences": r["co_occurrences"],
            }
            for r in results
        ]
    except Exception as e:
        return [{"error": f"Failed to find related entities: {str(e)}"}]


async def get_most_mentioned_entities(
    ctx: RunContext[AgentDeps],
    entity_type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get the most frequently mentioned entities across all podcasts.

    Args:
        ctx: The agent run context.
        entity_type: Filter by PERSON, ORGANIZATION, CONCEPT, LOCATION, etc.
        limit: Number of results (default 10).

    Returns:
        List of top entities with mention counts.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        # Count mentions from podcast sessions only
        query = """
        MATCH (e:Entity)<-[r:MENTIONS]-(m:Message)<-[:HAS_MESSAGE]-(c:Conversation)
        WHERE c.session_id STARTS WITH 'lenny-podcast-'
        AND ($type IS NULL OR e.type = $type)
        WITH e, count(r) AS mentions
        ORDER BY mentions DESC
        LIMIT $limit
        RETURN e.name AS name, e.type AS type, e.subtype AS subtype,
               e.description AS description, e.wikipedia_url AS wikipedia_url,
               mentions
        """
        results = await ctx.deps.client._client.execute_read(
            query, {"type": entity_type, "limit": limit}
        )

        return [
            {
                "name": r["name"],
                "type": r["type"],
                "subtype": r["subtype"],
                "description": r["description"],
                "wikipedia_url": r["wikipedia_url"],
                "mentions": r["mentions"],
            }
            for r in results
        ]
    except Exception as e:
        return [{"error": f"Failed to get top entities: {str(e)}"}]


# =============================================================================
# Location Query Tools (Map View Integration)
# =============================================================================


async def search_locations(
    ctx: RunContext[AgentDeps],
    query: str | None = None,
    episode_guest: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search for locations mentioned in podcasts.

    Args:
        ctx: The agent run context.
        query: Optional search term (e.g., "Silicon Valley", "Europe").
        episode_guest: Optional guest name to filter by episode.
        limit: Maximum number of results to return.

    Returns:
        Locations with coordinates for map visualization.
        The frontend map view can display these with markers, clusters, or heatmap.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        session_id = None
        if episode_guest:
            slug = re.sub(r"[^a-z0-9]+", "-", episode_guest.lower()).strip("-")
            session_id = f"lenny-podcast-{slug}"

        locations = await ctx.deps.client.get_locations(
            session_id=session_id,
            has_coordinates=True,
            limit=limit,
        )

        # If query provided, filter by name match
        if query:
            query_lower = query.lower()
            locations = [loc for loc in locations if query_lower in loc.get("name", "").lower()]

        return [
            {
                "name": loc.get("name"),
                "type": loc.get("type", "LOCATION"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "country": loc.get("country"),
                "description": loc.get("description"),
            }
            for loc in locations
        ]
    except Exception as e:
        return [{"error": f"Location search failed: {str(e)}"}]


async def find_locations_near(
    ctx: RunContext[AgentDeps],
    location_name: str,
    radius_km: float = 500.0,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find other locations mentioned near a given location.

    Args:
        ctx: The agent run context.
        location_name: Reference location (e.g., "San Francisco").
        radius_km: Search radius in kilometers (default 500km).
        limit: Maximum number of results to return.

    Returns:
        Nearby locations with distance information.
        Results can be visualized on the map with the radius overlay.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        # First get the reference location
        ref_locations = await ctx.deps.client.get_locations(has_coordinates=True, limit=500)
        ref_loc = None
        for loc in ref_locations:
            if location_name.lower() in loc.get("name", "").lower():
                ref_loc = loc
                break

        if not ref_loc or ref_loc.get("latitude") is None or ref_loc.get("longitude") is None:
            return [{"error": f"Location '{location_name}' not found with coordinates"}]

        # Use geospatial search
        nearby = await ctx.deps.client.search_locations_near(
            latitude=ref_loc["latitude"],
            longitude=ref_loc["longitude"],
            radius_km=radius_km,
            limit=limit,
        )

        return [
            {
                "name": loc.get("name"),
                "type": loc.get("type", "LOCATION"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "country": loc.get("country"),
                "distance_km": round(
                    _haversine_distance(
                        ref_loc["latitude"],
                        ref_loc["longitude"],
                        loc.get("latitude") or 0,
                        loc.get("longitude") or 0,
                    ),
                    1,
                )
                if loc.get("latitude") and loc.get("longitude")
                else None,
            }
            for loc in nearby
            if loc.get("name", "").lower()
            != ref_loc.get("name", "").lower()  # Exclude reference location
        ]
    except Exception as e:
        return [{"error": f"Nearby location search failed: {str(e)}"}]


async def get_episode_locations(
    ctx: RunContext[AgentDeps],
    episode_guest: str,
) -> list[dict[str, Any]]:
    """Get all locations mentioned in a specific episode.

    Args:
        ctx: The agent run context.
        episode_guest: Guest name (e.g., "Brian Chesky").

    Returns:
        A geographic profile of the episode's content.
        Uses session_id filtering to scope to the conversation.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        slug = re.sub(r"[^a-z0-9]+", "-", episode_guest.lower()).strip("-")
        session_id = f"lenny-podcast-{slug}"

        locations = await ctx.deps.client.get_locations(
            session_id=session_id,
            has_coordinates=True,
            limit=100,
        )

        return [
            {
                "name": loc.get("name"),
                "type": loc.get("type", "LOCATION"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "country": loc.get("country"),
                "description": loc.get("description"),
            }
            for loc in locations
        ]
    except Exception as e:
        return [{"error": f"Failed to get episode locations: {str(e)}"}]


async def find_location_path(
    ctx: RunContext[AgentDeps],
    from_location: str,
    to_location: str,
) -> dict[str, Any]:
    """Find the shortest path between two locations in the knowledge graph.

    Args:
        ctx: The agent run context.
        from_location: Starting location name.
        to_location: Destination location name.

    Returns:
        The graph path showing how locations are connected through
        entities, messages, and conversations. The frontend map can visualize
        this as a polyline overlay connecting the locations.
    """
    if not ctx.deps.client:
        return {"error": "Memory client not available"}

    try:
        query = """
        MATCH (start:Entity {type: 'LOCATION'})
        WHERE toLower(start.name) CONTAINS toLower($from_loc)
        WITH start LIMIT 1
        MATCH (end:Entity {type: 'LOCATION'})
        WHERE toLower(end.name) CONTAINS toLower($to_loc)
        WITH start, end LIMIT 1
        MATCH path = shortestPath((start)-[*..6]-(end))
        RETURN start.name AS from_location,
               start.latitude AS from_lat,
               start.longitude AS from_lon,
               end.name AS to_location,
               end.latitude AS to_lat,
               end.longitude AS to_lon,
               [n IN nodes(path) |
                CASE
                    WHEN n:Entity THEN {type: 'entity', name: n.name, entity_type: n.type}
                    WHEN n:Message THEN {type: 'message', content: left(n.content, 100)}
                    WHEN n:Conversation THEN {type: 'conversation', id: n.session_id}
                    ELSE {type: 'unknown'}
                END
               ] AS path_nodes,
               length(path) AS path_length
        """
        results = await ctx.deps.client._client.execute_read(
            query, {"from_loc": from_location, "to_loc": to_location}
        )

        if not results:
            return {"error": f"No path found between '{from_location}' and '{to_location}'"}

        r = results[0]
        return {
            "from_location": {
                "name": r["from_location"],
                "latitude": r["from_lat"],
                "longitude": r["from_lon"],
            },
            "to_location": {
                "name": r["to_location"],
                "latitude": r["to_lat"],
                "longitude": r["to_lon"],
            },
            "path_length": r["path_length"],
            "path_nodes": r["path_nodes"],
        }
    except Exception as e:
        return {"error": f"Path finding failed: {str(e)}"}


async def get_location_clusters(
    ctx: RunContext[AgentDeps],
    episode_guest: str | None = None,
) -> list[dict[str, Any]]:
    """Analyze geographic clusters of locations mentioned in podcasts.

    Args:
        ctx: The agent run context.
        episode_guest: Optional guest to filter by.

    Returns:
        Location density information useful for understanding
        which geographic regions are most discussed. Works with the
        frontend heatmap visualization.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        session_id = None
        if episode_guest:
            slug = re.sub(r"[^a-z0-9]+", "-", episode_guest.lower()).strip("-")
            session_id = f"lenny-podcast-{slug}"

        locations = await ctx.deps.client.get_locations(
            session_id=session_id,
            has_coordinates=True,
            limit=500,
        )

        # Group by country for cluster analysis
        country_clusters: dict[str, list[dict]] = {}
        for loc in locations:
            country = loc.get("country") or "Unknown"
            if country not in country_clusters:
                country_clusters[country] = []
            country_clusters[country].append(
                {
                    "name": loc.get("name"),
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                }
            )

        return [
            {
                "country": country,
                "location_count": len(locs),
                "locations": locs[:5],  # Top 5 locations per country
                "center_lat": sum(l["latitude"] for l in locs if l["latitude"]) / len(locs)
                if locs
                else None,
                "center_lon": sum(l["longitude"] for l in locs if l["longitude"]) / len(locs)
                if locs
                else None,
            }
            for country, locs in sorted(country_clusters.items(), key=lambda x: -len(x[1]))
        ]
    except Exception as e:
        return [{"error": f"Cluster analysis failed: {str(e)}"}]


async def calculate_location_distances(
    ctx: RunContext[AgentDeps],
    locations: list[str],
) -> list[dict[str, Any]]:
    """Calculate distances between multiple locations.

    Args:
        ctx: The agent run context.
        locations: List of location names to measure between.

    Returns:
        Pairwise distances in kilometers using great-circle calculation.
        Useful for understanding the geographic scope of discussions.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    if len(locations) < 2:
        return [{"error": "At least 2 locations are required"}]

    try:
        # Get all locations with coordinates
        all_locs = await ctx.deps.client.get_locations(has_coordinates=True, limit=500)

        # Find matching locations
        found_locs: list[dict] = []
        for loc_name in locations:
            for loc in all_locs:
                if (
                    loc_name.lower() in loc.get("name", "").lower()
                    and loc.get("latitude")
                    and loc.get("longitude")
                ):
                    found_locs.append(
                        {
                            "name": loc.get("name"),
                            "latitude": loc.get("latitude"),
                            "longitude": loc.get("longitude"),
                        }
                    )
                    break

        if len(found_locs) < 2:
            return [
                {"error": f"Need at least 2 locations with coordinates, found {len(found_locs)}"}
            ]

        # Calculate pairwise distances
        distances = []
        for i in range(len(found_locs)):
            for j in range(i + 1, len(found_locs)):
                loc1 = found_locs[i]
                loc2 = found_locs[j]
                dist = _haversine_distance(
                    loc1["latitude"],
                    loc1["longitude"],
                    loc2["latitude"],
                    loc2["longitude"],
                )
                distances.append(
                    {
                        "from": loc1["name"],
                        "to": loc2["name"],
                        "distance_km": round(dist, 1),
                    }
                )

        return sorted(distances, key=lambda x: x["distance_km"])
    except Exception as e:
        return [{"error": f"Distance calculation failed: {str(e)}"}]


# =============================================================================
# User Preferences and Reasoning Memory Tools
# =============================================================================


async def get_user_preferences(
    ctx: RunContext[AgentDeps],
) -> list[dict[str, Any]]:
    """Get the current user's stored preferences.

    Args:
        ctx: The agent run context.

    Returns:
        Preferences including content interests, format preferences,
        and historical patterns. Use this to personalize responses.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        preferences = await ctx.deps.client.long_term.search_preferences(
            query="",
            limit=20,
        )

        return [
            {
                "category": p.category,
                "preference": p.preference,
                "confidence": p.confidence,
                "source": p.source,
            }
            for p in preferences
        ]
    except Exception as e:
        return [{"error": f"Failed to get preferences: {str(e)}"}]


async def find_similar_past_queries(
    ctx: RunContext[AgentDeps],
    current_query: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find similar queries from past conversations and their successful resolutions.

    Args:
        ctx: The agent run context.
        current_query: The current user query.
        limit: Maximum number of similar traces to return.

    Returns:
        Past reasoning traces that solved similar problems.
        Useful for learning from successful past interactions.
    """
    if not ctx.deps.client:
        return [{"error": "Memory client not available"}]

    try:
        traces = await ctx.deps.client.reasoning.get_similar_traces(
            task=current_query,
            limit=limit,
            success_only=True,
        )

        return [
            {
                "task": t.task,
                "outcome": t.outcome,
                "success": t.success,
                "steps_count": len(t.steps) if t.steps else 0,
            }
            for t in traces
        ]
    except Exception as e:
        return [{"error": f"Failed to find similar traces: {str(e)}"}]
