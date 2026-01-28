"""Embedding providers for vector representations."""

from neo4j_agent_memory.embeddings.base import Embedder

# Conditionally import providers to avoid requiring all dependencies
try:
    from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder
except ImportError:
    BedrockEmbedder = None  # type: ignore[misc, assignment]

__all__ = [
    "Embedder",
    "BedrockEmbedder",
]
