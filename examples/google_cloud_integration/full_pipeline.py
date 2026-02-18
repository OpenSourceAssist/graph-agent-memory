#!/usr/bin/env python3
"""Full Google Cloud Integration Pipeline Demo.

This comprehensive example demonstrates all Google Cloud features
introduced in neo4j-agent-memory v0.0.3:

1. Vertex AI Embeddings - Generate embeddings using Google's models
2. Google ADK Integration - Use Neo4jMemoryService with ADK agents
3. MCP Server - Access memory through Model Context Protocol tools
4. Cloud Run Ready - Configuration for production deployment

Requirements:
    pip install neo4j-agent-memory[google,mcp]
    gcloud auth application-default login
"""

import asyncio
import json
import os
from datetime import datetime

from pydantic import SecretStr


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print()
    print(f"--- {title} ---")
    print()


async def setup_client():
    """Create and return a configured MemoryClient."""
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.config.settings import (
        EmbeddingConfig,
        EmbeddingProvider,
        Neo4jConfig,
    )

    # Determine embedding provider
    use_vertex = os.environ.get("GOOGLE_CLOUD_PROJECT") and os.environ.get(
        "EMBEDDING_PROVIDER", ""
    ).lower() in ("vertex_ai", "vertex", "google")

    if use_vertex:
        embedding_config = EmbeddingConfig(
            provider=EmbeddingProvider.VERTEX_AI,
            model=os.environ.get("EMBEDDING_MODEL", "text-embedding-004"),
            project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("VERTEX_AI_LOCATION", "us-central1"),
        )
        print("Using Vertex AI embeddings")
    else:
        embedding_config = EmbeddingConfig(
            provider=EmbeddingProvider.OPENAI,
            model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        print("Using OpenAI embeddings (set GOOGLE_CLOUD_PROJECT for Vertex AI)")

    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            username=os.environ.get("NEO4J_USER", "neo4j"),
            password=SecretStr(os.environ.get("NEO4J_PASSWORD", "password")),
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        ),
        embedding=embedding_config,
    )

    return MemoryClient(settings)


async def demo_vertex_ai_embeddings(client):
    """Demonstrate Vertex AI embedding generation."""
    print_header("Phase 1: Vertex AI Embeddings")

    # Check if we can use Vertex AI
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("Skipping Vertex AI demo (GOOGLE_CLOUD_PROJECT not set)")
        print("To enable: export GOOGLE_CLOUD_PROJECT=your-project-id")
        return

    from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder

    embedder = VertexAIEmbedder(
        model="text-embedding-004",
        project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("VERTEX_AI_LOCATION", "us-central1"),
    )

    print(f"Model: {embedder._model}")
    print(f"Dimensions: {embedder.dimensions}")
    print(f"Location: {embedder._location}")

    print_subheader("Generating Embeddings")

    texts = [
        "Graph databases store relationships as first-class citizens.",
        "Vector search enables semantic similarity matching.",
        "Agent memory combines multiple storage strategies.",
    ]

    embeddings = await embedder.embed_batch(texts)
    for text, emb in zip(texts, embeddings):
        print(f"  ✓ {text[:45]}... → {len(emb)} dims")

    print()
    print("Vertex AI embeddings ready for use with MemoryClient!")


async def demo_adk_memory_service(client):
    """Demonstrate Google ADK MemoryService integration."""
    print_header("Phase 2: Google ADK MemoryService")

    from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

    memory_service = Neo4jMemoryService(
        memory_client=client,
        user_id="pipeline-demo-user",
        include_entities=True,
        include_preferences=True,
    )

    print("Neo4jMemoryService configured:")
    print(f"  User ID: {memory_service.user_id}")
    print(f"  Entity extraction: enabled")
    print(f"  Preference learning: enabled")

    print_subheader("Storing Conversation Sessions")

    # Create rich conversation with entities and preferences
    session_id = f"pipeline-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    sessions = [
        {
            "id": f"{session_id}-1",
            "messages": [
                {
                    "role": "user",
                    "content": "I'm working with Dr. Sarah Chen on the GraphRAG "
                    "research project at Stanford University.",
                },
                {
                    "role": "assistant",
                    "content": "Interesting! GraphRAG combines graph databases with "
                    "retrieval-augmented generation. How's the project progressing?",
                },
                {
                    "role": "user",
                    "content": "Great! We've published initial results. I prefer "
                    "working in Python and use Neo4j for the knowledge graph.",
                },
            ],
        },
        {
            "id": f"{session_id}-2",
            "messages": [
                {
                    "role": "user",
                    "content": "I have a meeting with the Neo4j team in San Francisco "
                    "next week to discuss the agent memory integration.",
                },
                {
                    "role": "assistant",
                    "content": "That sounds productive! Neo4j's agent memory library "
                    "looks promising for your research.",
                },
            ],
        },
    ]

    for session in sessions:
        await memory_service.add_session_to_memory(session)
        print(f"  ✓ Stored session: {session['id']}")

    print_subheader("Searching Memories")

    queries = [
        ("Dr. Sarah Chen", "Finding person entities"),
        ("GraphRAG research", "Finding project context"),
        ("programming preferences", "Finding user preferences"),
        ("Neo4j meeting", "Finding scheduled events"),
    ]

    for query, description in queries:
        results = await memory_service.search_memories(query=query, limit=2)
        print(f"  Query: '{query}' ({description})")
        for r in results:
            print(f"    [{r.memory_type}] {r.content[:50]}...")
        print()


async def demo_mcp_server(client):
    """Demonstrate MCP server tools."""
    print_header("Phase 3: MCP Server Tools")

    from neo4j_agent_memory.mcp.handlers import MCPHandlers
    from neo4j_agent_memory.mcp.tools import MEMORY_TOOLS

    print(f"MCP Server exposes {len(MEMORY_TOOLS)} tools:")
    for tool in MEMORY_TOOLS:
        print(f"  • {tool['name']}: {tool['description'][:50]}...")
    print()

    handlers = MCPHandlers(client)

    print_subheader("Tool Demonstrations")

    # 1. memory_store
    print("1. memory_store")
    result = await handlers.handle_memory_store(
        type="message",
        content="Remember to review the MCP protocol documentation.",
        session_id="mcp-demo",
        role="user",
    )
    print(f"   Stored: {result['content'][:50]}...")

    # 2. memory_search
    print()
    print("2. memory_search")
    result = await handlers.handle_memory_search(
        query="MCP protocol",
        limit=3,
    )
    print(f"   Found {len(result.get('results', []))} results")

    # 3. conversation_history
    print()
    print("3. conversation_history")
    result = await handlers.handle_conversation_history(
        session_id="mcp-demo",
        limit=5,
    )
    print(f"   Retrieved {len(result.get('messages', []))} messages")

    # 4. graph_query
    print()
    print("4. graph_query")
    result = await handlers.handle_graph_query(
        query="MATCH (n) RETURN labels(n) as type, count(*) as count ORDER BY count DESC LIMIT 5",
    )
    print(f"   Node types: {json.dumps(result.get('results', []), indent=6)}")

    # 5. entity_lookup
    print()
    print("5. entity_lookup")
    result = await handlers.handle_entity_lookup(
        name="Neo4j",
        include_neighbors=True,
        max_hops=1,
    )
    if result.get("entity"):
        print(f"   Found entity: {result['entity'].get('name', 'N/A')}")
    else:
        print("   No entity found (try after storing more data)")


async def demo_production_config():
    """Show production configuration for Cloud Run."""
    print_header("Phase 4: Production Configuration (Cloud Run)")

    print("Cloud Run Deployment Configuration:")
    print()

    dockerfile = """
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install neo4j-agent-memory[google,mcp]
EXPOSE 8080
CMD ["neo4j-memory", "mcp", "serve", "--transport", "sse", "--port", "8080"]
"""
    print("Dockerfile:")
    print("-" * 40)
    print(dockerfile)

    env_config = """
# Required environment variables (use Secret Manager)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_PASSWORD=<from-secret-manager>
GOOGLE_CLOUD_PROJECT=your-project-id

# Optional
EMBEDDING_PROVIDER=vertex_ai
EMBEDDING_MODEL=text-embedding-004
"""
    print("Environment Variables:")
    print("-" * 40)
    print(env_config)

    deploy_cmd = """
# Deploy to Cloud Run
gcloud run deploy neo4j-memory-mcp \\
  --source deploy/cloudrun \\
  --region us-central1 \\
  --set-secrets NEO4J_URI=neo4j-uri:latest \\
  --set-secrets NEO4J_PASSWORD=neo4j-password:latest \\
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID
"""
    print("Deployment Command:")
    print("-" * 40)
    print(deploy_cmd)


async def main():
    """Run the complete Google Cloud integration pipeline."""
    print("\n" + "=" * 70)
    print("  Neo4j Agent Memory - Google Cloud Integration Pipeline")
    print("  Version 0.0.3 Feature Demonstration")
    print("=" * 70)

    print()
    print("This demo showcases all Google Cloud features:")
    print("  • Vertex AI Embeddings (text-embedding-004)")
    print("  • Google ADK MemoryService")
    print("  • MCP Server with 5 tools")
    print("  • Cloud Run deployment configuration")
    print()
    print(f"Timestamp: {datetime.now().isoformat()}")

    try:
        # Setup
        async with await setup_client() as client:
            # Run all demos
            await demo_vertex_ai_embeddings(client)
            await demo_adk_memory_service(client)
            await demo_mcp_server(client)

        # Show production config (no client needed)
        await demo_production_config()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check Neo4j is running: docker ps | grep neo4j")
        print("  2. Verify credentials: NEO4J_URI, NEO4J_PASSWORD")
        print("  3. For Vertex AI: gcloud auth application-default login")
        print("  4. Set project: export GOOGLE_CLOUD_PROJECT=your-project")
        raise

    print_header("Pipeline Complete!")

    print("Summary of features demonstrated:")
    print("  ✓ Vertex AI embeddings with text-embedding-004")
    print("  ✓ ADK MemoryService for session and entity storage")
    print("  ✓ MCP Server tools for memory operations")
    print("  ✓ Cloud Run deployment configuration")
    print()
    print("Next steps:")
    print("  • Explore Neo4j Browser to see the knowledge graph")
    print("  • Start the MCP server: neo4j-memory mcp serve")
    print("  • Deploy to Cloud Run: see deploy/cloudrun/README.md")
    print()


if __name__ == "__main__":
    asyncio.run(main())
