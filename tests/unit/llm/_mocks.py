"""Shared test doubles for the llm test suite.

The contract test harness and the foundation tests both consume these,
so they live in a private module rather than getting redefined per-file.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from neo4j_agent_memory.llm.types import ChatMessage, Completion, Usage


class CannedLLMProvider:
    """Minimal :class:`LLMProvider` implementation backed by a queue of strings.

    Returns the next queued response on each :meth:`complete` call. Useful
    for exercising :func:`schema_aligned_extract` retry behavior without
    hitting a real model.
    """

    def __init__(self, responses: Sequence[str], *, model: str = "test/canned") -> None:
        self.model = model
        self._responses = list(responses)
        self.calls: list[list[ChatMessage]] = []

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop: Sequence[str] | None = None,
        timeout: float | None = None,
    ) -> Completion:
        # Record what the caller sent so retry tests can assert the
        # validation-feedback message is appended.
        self.calls.append(list(messages))
        if not self._responses:
            raise RuntimeError("CannedLLMProvider exhausted")
        content = self._responses.pop(0)
        return Completion(
            content=content,
            model=self.model,
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


class CannedEmbeddingProvider:
    """Minimal :class:`EmbeddingProvider` returning deterministic test vectors."""

    def __init__(self, *, model: str = "test/canned-embed", dimensions: int = 4) -> None:
        self.model = model
        self.dimensions = dimensions

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        # Each vector is just [i, 0, 0, ...] of length ``dimensions`` so
        # tests can distinguish individual results without caring about
        # actual semantic content.
        return [[float(i), *([0.0] * (self.dimensions - 1))] for i, _ in enumerate(texts)]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


class SimplePayload(BaseModel):
    """Trivial Pydantic model used to exercise structured extraction."""

    name: str
    age: int


__all__ = [
    "CannedLLMProvider",
    "CannedEmbeddingProvider",
    "SimplePayload",
]
