"""News graph tools for the chat agent."""

from datetime import date, datetime
from typing import Any

from pydantic_ai import RunContext

from src.agent.dependencies import AgentDeps


async def _run_query(
    ctx: RunContext[AgentDeps],
    query: str,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a Cypher query against the news graph."""
    if ctx.deps.news_driver is None:
        return [{"error": "News graph driver not configured"}]

    async with ctx.deps.news_driver.session(database=ctx.deps.news_database) as session:
        result = await session.run(query, params or {})
        records = await result.data()
        return records


async def search_news(
    ctx: RunContext[AgentDeps],
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search news articles using text matching on title and abstract.

    Args:
        ctx: The agent run context.
        query: The search query string.
        limit: Maximum number of results to return.

    Returns:
        List of matching articles with title, abstract, and published date.
    """
    # Use CONTAINS for text matching since fulltext index may not exist
    # Split query into words for better matching
    cypher = """
    MATCH (a:Article)
    WHERE toLower(a.title) CONTAINS toLower($query)
       OR toLower(a.abstract) CONTAINS toLower($query)
    RETURN a.title AS title,
           a.abstract AS abstract,
           a.published AS published,
           a.url AS url
    ORDER BY a.published DESC
    LIMIT $limit
    """
    return await _run_query(ctx, cypher, {"query": query, "limit": limit})


async def vector_search_news(
    ctx: RunContext[AgentDeps],
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search news articles using semantic vector similarity.

    Args:
        ctx: The agent run context.
        query: The search query for semantic matching.
        limit: Maximum number of results to return.

    Returns:
        List of semantically similar articles.
    """
    cypher = """
    WITH genai.vector.encode($query, "OpenAI", {
        token: $openai_key,
        model: "text-embedding-ada-002"
    }) AS queryVector
    CALL db.index.vector.queryNodes("article_embeddings", $limit, queryVector)
    YIELD node, score
    RETURN node.title AS title,
           node.abstract AS abstract,
           node.published AS published,
           node.url AS url,
           score
    """
    from src.config import get_settings

    settings = get_settings()
    return await _run_query(
        ctx,
        cypher,
        {
            "query": query,
            "limit": limit,
            "openai_key": settings.openai_api_key.get_secret_value(),
        },
    )


async def get_recent_news(
    ctx: RunContext[AgentDeps],
    limit: int = 10,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Get the most recent news articles.

    Args:
        ctx: The agent run context.
        limit: Maximum number of results to return.
        days: Number of days to look back.

    Returns:
        List of recent articles ordered by publication date.
    """
    cypher = """
    MATCH (a:Article)
    WHERE a.published >= datetime() - duration({days: $days})
    RETURN a.title AS title,
           a.abstract AS abstract,
           a.published AS published,
           a.url AS url
    ORDER BY a.published DESC
    LIMIT $limit
    """
    return await _run_query(ctx, cypher, {"limit": limit, "days": days})


async def get_news_by_topic(
    ctx: RunContext[AgentDeps],
    topic: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get news articles by topic.

    Args:
        ctx: The agent run context.
        topic: The topic to filter by.
        limit: Maximum number of results to return.

    Returns:
        List of articles matching the topic.
    """
    cypher = """
    MATCH (a:Article)-[:HAS_TOPIC]->(t:Topic)
    WHERE toLower(t.name) CONTAINS toLower($topic)
    RETURN a.title AS title,
           a.abstract AS abstract,
           a.published AS published,
           a.url AS url,
           t.name AS topic
    ORDER BY a.published DESC
    LIMIT $limit
    """
    return await _run_query(ctx, cypher, {"topic": topic, "limit": limit})


async def get_topics(ctx: RunContext[AgentDeps]) -> list[dict[str, Any]]:
    """Get all available news topics with article counts.

    Args:
        ctx: The agent run context.

    Returns:
        List of topics with their article counts.
    """
    cypher = """
    MATCH (t:Topic)<-[:HAS_TOPIC]-(a:Article)
    RETURN t.name AS topic, count(a) AS article_count
    ORDER BY article_count DESC
    LIMIT 50
    """
    return await _run_query(ctx, cypher, {})


async def search_news_by_location(
    ctx: RunContext[AgentDeps],
    location: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search news articles by geographic location.

    Args:
        ctx: The agent run context.
        location: The location to search for.
        limit: Maximum number of results to return.

    Returns:
        List of articles related to the location.
    """
    cypher = """
    MATCH (a:Article)-[:ABOUT_GEO]->(g:Geo)
    WHERE toLower(g.name) CONTAINS toLower($location)
    RETURN a.title AS title,
           a.abstract AS abstract,
           a.published AS published,
           a.url AS url,
           g.name AS location
    ORDER BY a.published DESC
    LIMIT $limit
    """
    return await _run_query(ctx, cypher, {"location": location, "limit": limit})


async def search_news_multi_topic(
    ctx: RunContext[AgentDeps],
    topics: list[str],
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search news articles that match any of the given topics or keywords.

    Use this for broad research queries that span multiple subjects.

    Args:
        ctx: The agent run context.
        topics: List of topics/keywords to search for.
        limit: Maximum number of results to return.

    Returns:
        List of articles matching any of the topics.
    """
    # Build a dynamic WHERE clause for multiple topics
    cypher = """
    MATCH (a:Article)
    OPTIONAL MATCH (a)-[:HAS_TOPIC]->(t:Topic)
    OPTIONAL MATCH (a)-[:ABOUT_PERSON]->(p:Person)
    WITH a, collect(DISTINCT t.name) AS topics, collect(DISTINCT p.name) AS people
    WHERE any(topic IN $topics WHERE
        toLower(a.title) CONTAINS toLower(topic) OR
        toLower(a.abstract) CONTAINS toLower(topic) OR
        any(t IN topics WHERE toLower(t) CONTAINS toLower(topic)) OR
        any(person IN people WHERE toLower(person) CONTAINS toLower(topic))
    )
    RETURN DISTINCT a.title AS title,
           a.abstract AS abstract,
           a.published AS published,
           a.url AS url,
           topics,
           people
    ORDER BY a.published DESC
    LIMIT $limit
    """
    return await _run_query(ctx, cypher, {"topics": topics, "limit": limit})


async def search_news_by_date_range(
    ctx: RunContext[AgentDeps],
    start_date: str,
    end_date: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search news articles within a date range.

    Args:
        ctx: The agent run context.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        limit: Maximum number of results to return.

    Returns:
        List of articles published within the date range.
    """
    cypher = """
    MATCH (a:Article)
    WHERE date(a.published) >= date($start_date)
      AND date(a.published) <= date($end_date)
    RETURN a.title AS title,
           a.abstract AS abstract,
           a.published AS published,
           a.url AS url
    ORDER BY a.published DESC
    LIMIT $limit
    """
    return await _run_query(
        ctx, cypher, {"start_date": start_date, "end_date": end_date, "limit": limit}
    )


async def get_database_schema(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
    """Get the news graph database schema.

    Args:
        ctx: The agent run context.

    Returns:
        Dictionary describing the database schema including node labels,
        relationship types, and their properties.
    """
    # Get node labels and their properties
    labels_query = """
    CALL db.labels() YIELD label
    CALL apoc.meta.nodeTypeProperties({labels: [label]}) YIELD nodeLabels, propertyName, propertyTypes
    RETURN label, collect({property: propertyName, types: propertyTypes}) AS properties
    """

    # Get relationship types
    rels_query = """
    CALL db.relationshipTypes() YIELD relationshipType
    RETURN collect(relationshipType) AS relationships
    """

    labels_result = await _run_query(ctx, labels_query, {})
    rels_result = await _run_query(ctx, rels_query, {})

    return {
        "node_labels": labels_result,
        "relationships": rels_result[0]["relationships"] if rels_result else [],
        "description": """
News Graph Schema:
- Article: News articles with title, abstract, published date, url, embedding
- Topic: Categories/topics that articles are about
- Person: People mentioned in articles
- Organization: Companies and organizations mentioned
- Geo: Geographic locations mentioned
- Photo: Images associated with articles

Relationships:
- (Article)-[:HAS_TOPIC]->(Topic)
- (Article)-[:ABOUT_PERSON]->(Person)
- (Article)-[:ABOUT_ORGANIZATION]->(Organization)
- (Article)-[:ABOUT_GEO]->(Geo)
- (Article)-[:HAS_PHOTO]->(Photo)
        """,
    }


async def text2cypher(
    ctx: RunContext[AgentDeps],
    question: str,
) -> dict[str, str]:
    """Generate a Cypher query from a natural language question.

    Uses the LLM to convert a question into a valid Cypher query
    for the news graph database.

    Args:
        ctx: The agent run context.
        question: Natural language question to convert.

    Returns:
        Dictionary with the generated Cypher query.
    """
    schema = await get_database_schema(ctx)

    prompt = f"""Given the following Neo4j graph database schema:
{schema["description"]}

Generate a Cypher query to answer this question: {question}

Return only the Cypher query, no explanation.
The query should be read-only (no CREATE, DELETE, SET, MERGE operations).
"""

    # This is a simplified implementation - in production you might
    # use a separate LLM call or a specialized text-to-cypher model
    return {
        "question": question,
        "generated_query": f"// TODO: Implement text2cypher with LLM\n// Question: {question}",
        "note": "Use execute_cypher to run a specific query instead",
    }


async def execute_cypher(
    ctx: RunContext[AgentDeps],
    query: str,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a read-only Cypher query against the news graph.

    Args:
        ctx: The agent run context.
        query: The Cypher query to execute.
        params: Optional parameters for the query.

    Returns:
        Query results as a list of dictionaries.
    """
    # Validate query is read-only
    query_upper = query.upper()
    write_keywords = ["CREATE", "DELETE", "SET", "MERGE", "REMOVE", "DROP"]
    for keyword in write_keywords:
        if keyword in query_upper:
            return [{"error": f"Write operations not allowed: {keyword} found in query"}]

    return await _run_query(ctx, query, params)
