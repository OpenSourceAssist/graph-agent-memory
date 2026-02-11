#!/usr/bin/env python3
"""Vertex AI Embeddings Demo.

Demonstrates using Google Vertex AI for generating text embeddings
with Neo4j Agent Memory.

Features demonstrated:
- VertexAIEmbedder initialization
- Single text embedding
- Batch embedding for multiple texts
- Integration with MemoryClient
- Different task types for queries vs documents

Requirements:
    pip install neo4j-agent-memory[vertex-ai]
    gcloud auth application-default login
"""

import asyncio
import os
from datetime import datetime

from pydantic import SecretStr


async def demo_basic_embeddings():
    """Demonstrate basic Vertex AI embedding generation."""
    from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder

    print("=" * 60)
    print("Vertex AI Embeddings - Basic Usage")
    print("=" * 60)
    print()

    # Initialize embedder
    embedder = VertexAIEmbedder(
        model="text-embedding-004",
        project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("VERTEX_AI_LOCATION", "us-central1"),
    )

    print(f"Model: {embedder.model}")
    print(f"Dimensions: {embedder.dimensions}")
    print(f"Task Type: {embedder.task_type}")
    print()

    # Single embedding
    print("1. Single Text Embedding")
    print("-" * 40)
    text = "Neo4j is a graph database that stores and manages connected data."
    embedding = await embedder.embed(text)
    print(f"   Text: {text[:50]}...")
    print(f"   Embedding dimensions: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
    print()

    # Batch embedding
    print("2. Batch Embedding")
    print("-" * 40)
    texts = [
        "Graph databases excel at relationship queries.",
        "Vector search enables semantic similarity matching.",
        "Agent memory combines short-term and long-term storage.",
        "Entity extraction identifies people, places, and organizations.",
        "The Model Context Protocol enables tool-based AI interactions.",
    ]
    embeddings = await embedder.embed_batch(texts)
    print(f"   Processed {len(texts)} texts")
    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        print(f"   [{i + 1}] {text[:40]}... → {len(emb)} dims")
    print()

    # Compare similarities
    print("3. Semantic Similarity")
    print("-" * 40)
    query = "How do graph databases handle relationships?"
    query_embedding = await embedder.embed(query)

    def cosine_similarity(a: list[float], b: list[float]) -> float:
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b)

    print(f"   Query: {query}")
    print()
    similarities = [
        (text, cosine_similarity(query_embedding, emb)) for text, emb in zip(texts, embeddings)
    ]
    similarities.sort(key=lambda x: x[1], reverse=True)
    for text, sim in similarities:
        print(f"   {sim:.4f} - {text[:50]}...")
    print()


async def demo_with_memory_client():
    """Demonstrate Vertex AI embeddings with MemoryClient."""
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.config.settings import (
        EmbeddingConfig,
        EmbeddingProvider,
        Neo4jConfig,
    )

    print("=" * 60)
    print("Vertex AI Embeddings - With MemoryClient")
    print("=" * 60)
    print()

    # Configure with Vertex AI embeddings
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            username=os.environ.get("NEO4J_USER", "neo4j"),
            password=SecretStr(os.environ.get("NEO4J_PASSWORD", "password")),
        ),
        embedding=EmbeddingConfig(
            provider=EmbeddingProvider.VERTEX_AI,
            model="text-embedding-004",
            project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("VERTEX_AI_LOCATION", "us-central1"),
        ),
    )

    print("Configuration:")
    print(f"  Embedding Provider: {settings.embedding.provider}")
    print(f"  Model: {settings.embedding.model}")
    print(f"  Project: {settings.embedding.project_id}")
    print()

    async with MemoryClient(settings) as client:
        print("1. Storing messages with Vertex AI embeddings...")
        print("-" * 40)

        session_id = f"vertex-demo-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Store some messages
        messages = [
            ("user", "Tell me about graph databases and their use cases."),
            (
                "assistant",
                "Graph databases like Neo4j excel at managing connected data. "
                "They're ideal for social networks, recommendation engines, "
                "fraud detection, and knowledge graphs.",
            ),
            ("user", "How does vector search integrate with graphs?"),
            (
                "assistant",
                "Neo4j combines vector indexes with graph traversal. "
                "You can find semantically similar nodes and then explore "
                "their relationships for richer context.",
            ),
        ]

        for role, content in messages:
            await client.short_term.add_message(
                session_id=session_id,
                role=role,
                content=content,
                user_id="demo-user",
            )
            print(f"  [{role}] {content[:50]}...")
        print()

        print("2. Semantic search with Vertex AI embeddings...")
        print("-" * 40)

        queries = [
            "graph database applications",
            "combining vectors and graphs",
            "Neo4j features",
        ]

        for query in queries:
            print(f"\n  Query: '{query}'")
            results = await client.short_term.search_messages(
                query=query,
                session_id=session_id,
                limit=2,
            )
            for msg in results:
                print(f"    → {msg.content[:60]}...")
        print()


async def demo_task_types():
    """Demonstrate different task types for Vertex AI embeddings."""
    from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder

    print("=" * 60)
    print("Vertex AI Embeddings - Task Types")
    print("=" * 60)
    print()

    print("Vertex AI supports different task types for optimized embeddings:")
    print()

    task_types = [
        ("RETRIEVAL_DOCUMENT", "For indexing documents to be searched"),
        ("RETRIEVAL_QUERY", "For search queries"),
        ("SEMANTIC_SIMILARITY", "For comparing text similarity"),
        ("CLASSIFICATION", "For text classification tasks"),
        ("CLUSTERING", "For clustering similar texts"),
    ]

    for task_type, description in task_types:
        print(f"  • {task_type}")
        print(f"    {description}")

    print()
    print("Example: Using different task types for query vs document")
    print("-" * 40)

    # Document embedder
    doc_embedder = VertexAIEmbedder(
        model="text-embedding-004",
        task_type="RETRIEVAL_DOCUMENT",
        project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    )

    # Query embedder
    query_embedder = VertexAIEmbedder(
        model="text-embedding-004",
        task_type="RETRIEVAL_QUERY",
        project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    )

    document = "Neo4j provides native graph storage and processing capabilities."
    query = "What are Neo4j's core features?"

    doc_embedding = await doc_embedder.embed(document)
    query_embedding = await query_embedder.embed(query)

    print(f"  Document ({doc_embedder.task_type}): {len(doc_embedding)} dims")
    print(f"  Query ({query_embedder.task_type}): {len(query_embedding)} dims")
    print()
    print(
        "  Using matched task types can improve retrieval quality for asymmetric search scenarios."
    )
    print()


async def main():
    """Run all Vertex AI embedding demos."""
    print("\n" + "=" * 60)
    print("Neo4j Agent Memory - Vertex AI Embeddings Demo")
    print("=" * 60 + "\n")

    # Check for GCP project
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("Warning: GOOGLE_CLOUD_PROJECT not set.")
        print("Set it with: export GOOGLE_CLOUD_PROJECT=your-project-id")
        print()

    try:
        await demo_basic_embeddings()
        await demo_task_types()

        # Only run memory client demo if Neo4j is configured
        if os.environ.get("NEO4J_URI") or os.environ.get("NEO4J_PASSWORD"):
            await demo_with_memory_client()
        else:
            print("Skipping MemoryClient demo (NEO4J_* not configured)")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure you have:")
        print("  1. Authenticated: gcloud auth application-default login")
        print("  2. Set project: export GOOGLE_CLOUD_PROJECT=your-project-id")
        print("  3. Enabled Vertex AI API in your GCP project")
        raise

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
