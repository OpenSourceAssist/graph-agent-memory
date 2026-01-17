"""Base embedder protocol and utilities."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Protocol for embedding providers."""

    @property
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        ...

    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            Embedding vector as list of floats
        """
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        ...


class BaseEmbedder(ABC):
    """Abstract base class for embedder implementations."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Default implementation calls embed() for each text.
        Subclasses should override for better performance.
        """
        return [await self.embed(text) for text in texts]
