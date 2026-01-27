"""Embedding providers for vector representations."""

from neo4j_agent_memory.embeddings.base import BaseEmbedder, Embedder
from neo4j_agent_memory.embeddings.openai import OpenAIEmbedder

__all__ = [
    "BaseEmbedder",
    "Embedder",
    "OpenAIEmbedder",
]


# Lazy imports for optional providers
def __getattr__(name: str):
    if name == "VertexAIEmbedder":
        from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder

        return VertexAIEmbedder
    if name == "SentenceTransformerEmbedder":
        from neo4j_agent_memory.embeddings.sentence_transformers import (
            SentenceTransformerEmbedder,
        )

        return SentenceTransformerEmbedder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
