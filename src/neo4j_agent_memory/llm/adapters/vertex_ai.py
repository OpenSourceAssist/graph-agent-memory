"""Vertex AI embedding adapter for the Provider Protocol.

Wraps the existing
:class:`~neo4j_agent_memory.embeddings.vertex_ai.VertexAIEmbedder`.

Note: Vertex AI as an LLM provider routes through LiteLLM, not a native
adapter. This file provides the *embedding* adapter only. To use Gemini
on Vertex AI as an LLM, use::

    from_provider("vertex_ai/gemini-1.5-pro-002",
                  vertex_project="my-project",
                  vertex_location="us-central1")

which resolves to a :class:`LiteLLMProvider`.

Install with::

    pip install 'neo4j-agent-memory[vertex-ai]'
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from neo4j_agent_memory.llm.defaults import lookup_embedding_dimensions

if TYPE_CHECKING:
    from collections.abc import Sequence

    from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder


logger = logging.getLogger(__name__)


def _strip_provider_prefix(model: str) -> str:
    if model.startswith("vertex_ai/"):
        return model[len("vertex_ai/") :]
    return model


class VertexAIEmbeddingProvider:
    """Vertex AI embedding provider.

    Implements :class:`~neo4j_agent_memory.llm.protocol.EmbeddingProvider`.

    Example::

        from neo4j_agent_memory.llm.adapters.vertex_ai import (
            VertexAIEmbeddingProvider,
        )
        embedder = VertexAIEmbeddingProvider(
            "vertex_ai/text-embedding-004",
            project_id="my-gcp-project",
            location="us-central1",
        )
    """

    def __init__(
        self,
        model: str = "vertex_ai/text-embedding-004",
        *,
        project_id: str | None = None,
        location: str = "us-central1",
        task_type: str = "RETRIEVAL_DOCUMENT",
        dimensions: int | None = None,
        batch_size: int = 250,
    ) -> None:
        bare = _strip_provider_prefix(model)
        self.model = f"vertex_ai/{bare}"
        self._bare_model = bare
        self._project_id = project_id
        self._location = location
        self._task_type = task_type
        self._batch_size = batch_size
        self._underlying: VertexAIEmbedder | None = None

        if dimensions is not None:
            self.dimensions = dimensions
        else:
            known = lookup_embedding_dimensions(self.model)
            if known is None:
                # Vertex AI text models are almost all 768; provide a
                # sensible default rather than refusing.
                logger.warning(
                    "VertexAIEmbeddingProvider: dimensions for %r not in defaults "
                    "table; assuming 768.",
                    self.model,
                )
                self.dimensions = 768
            else:
                self.dimensions = known

    def _ensure_underlying(self) -> VertexAIEmbedder:
        if self._underlying is None:
            try:
                from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder
            except ImportError as exc:
                raise ImportError(
                    "google-cloud-aiplatform not installed. "
                    "Install with: pip install 'neo4j-agent-memory[vertex-ai]'"
                ) from exc
            self._underlying = VertexAIEmbedder(
                model=self._bare_model,
                project_id=self._project_id,
                location=self._location,
                batch_size=self._batch_size,
                task_type=self._task_type,
            )
        return self._underlying

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        underlying = self._ensure_underlying()
        return await underlying.embed_batch(list(texts))

    async def embed_one(self, text: str) -> list[float]:
        underlying = self._ensure_underlying()
        return await underlying.embed(text)


__all__ = [
    "VertexAIEmbeddingProvider",
]
