"""Sentence-Transformers embedding adapter for the Provider Protocol.

Wraps the existing
:class:`~neo4j_agent_memory.embeddings.sentence_transformers.SentenceTransformerEmbedder`
so we get its tested batch logic and lazy model load for free.

Implements :class:`~neo4j_agent_memory.llm.protocol.EmbeddingProvider`.

Install with::

    pip install 'neo4j-agent-memory[sentence-transformers]'

Notes:
    * For known HuggingFace model IDs (``BAAI/bge-*``, ``sentence-transformers/all-*``,
      etc.) the :attr:`dimensions` is auto-populated from the defaults table
      without loading the model.
    * For unknown model IDs, pass ``dimensions=`` explicitly. This guarantees
      :attr:`dimensions` is always valid before vector index setup.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from neo4j_agent_memory.llm.defaults import lookup_embedding_dimensions

if TYPE_CHECKING:
    from collections.abc import Sequence

    from neo4j_agent_memory.embeddings.sentence_transformers import (
        SentenceTransformerEmbedder,
    )


logger = logging.getLogger(__name__)


def _auto_device() -> str:
    """Pick the best available torch device, falling back to CPU.

    Best-effort heuristic: returns ``'cuda'`` if PyTorch reports CUDA is
    available, ``'mps'`` on Apple Silicon when MPS is available, otherwise
    ``'cpu'``. Adapter constructor explicitly accepts a ``device=`` override
    when this heuristic gets it wrong.
    """
    try:
        import torch
    except ImportError:
        return "cpu"
    try:
        if torch.cuda.is_available():
            return "cuda"
        if (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
            and torch.backends.mps.is_built()
        ):
            return "mps"
    except Exception:  # pragma: no cover - defensive
        pass
    return "cpu"


class SentenceTransformersProvider:
    """Local sentence-transformers embedding provider.

    Recommended for cost-sensitive and airgapped deployments. Runs entirely
    on the local machine; no network access is required after the model
    is downloaded.

    Example::

        from neo4j_agent_memory.llm.adapters.sentence_transformers import (
            SentenceTransformersProvider,
        )

        embedder = SentenceTransformersProvider(
            "BAAI/bge-small-en-v1.5",
            device="cuda",  # or "mps", "cpu", or None to auto-detect
        )
        vectors = await embedder.embed(["hello world"])
    """

    def __init__(
        self,
        model: str = "BAAI/bge-small-en-v1.5",
        *,
        device: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.model = model
        self._device = device if device is not None else _auto_device()
        self._underlying: SentenceTransformerEmbedder | None = None

        # Best-effort dimensions resolution before model load.
        # Order: explicit > defaults table > require explicit for unknown models.
        if dimensions is not None:
            self.dimensions = dimensions
        else:
            known = lookup_embedding_dimensions(model)
            if known is not None:
                self.dimensions = known
            else:
                raise ValueError(
                    "Unknown sentence-transformers model dimensions for "
                    f"{model!r}. Pass dimensions=<positive-int> explicitly."
                )

    def _ensure_underlying(self) -> SentenceTransformerEmbedder:
        if self._underlying is None:
            try:
                from neo4j_agent_memory.embeddings.sentence_transformers import (
                    SentenceTransformerEmbedder,
                )
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers package not installed. "
                    "Install with: pip install 'neo4j-agent-memory[sentence-transformers]'"
                ) from exc
            self._underlying = SentenceTransformerEmbedder(
                model_name=self.model,
                device=self._device,
            )
        return self._underlying

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        underlying = self._ensure_underlying()
        # Use the wrapped class's batch logic (already async-safe).
        return await underlying.embed_batch(list(texts))

    async def embed_one(self, text: str) -> list[float]:
        underlying = self._ensure_underlying()
        return await underlying.embed(text)


__all__ = [
    "SentenceTransformersProvider",
]
