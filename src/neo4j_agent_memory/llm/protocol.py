"""The Provider Protocol — canonical abstraction for LLM/embedding providers.

This module defines three :class:`typing.Protocol` classes that adapters
implement. They are the contract the agent-memory-tck Bronze and Silver
tiers certify against.

* :class:`LLMProvider` — Bronze tier. Plain chat completions.
* :class:`StructuredExtractor` — Silver tier. Validated Pydantic outputs.
* :class:`EmbeddingProvider` — Bronze tier. Text embeddings backing
  Neo4j vector indexes.

All three are :data:`@runtime_checkable` so the deprecation shim and
diagnostic logging can use :func:`isinstance` checks. Note that at runtime
``@runtime_checkable`` validates method *presence*, not method signatures
— full behavioral conformance is verified by the TCK's behavioral test
harness (``tests/unit/llm/test_adapter_contract.py``).

The module imports only :mod:`typing` and types from :mod:`neo4j_agent_memory.llm.types`.
No SDK imports. This is what makes :mod:`neo4j_agent_memory.llm` importable
in the bare core install.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

from neo4j_agent_memory.llm.types import ChatMessage, Completion

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic import BaseModel


T = TypeVar("T", bound="BaseModel")


@runtime_checkable
class LLMProvider(Protocol):
    """Provider for chat completions (Bronze TCK tier).

    The minimum contract for talking to an LLM. Adapters implementing only
    this Protocol (without :class:`StructuredExtractor`) can still serve
    short-term summarization and free-form extraction via natural-language
    prompts.

    Implementations MUST:

    * Be safe to call concurrently — no shared mutable state.
    * Translate provider-specific errors to
      :class:`~neo4j_agent_memory.llm.errors.ProviderError` subclasses.
    * Honor ``temperature=0.0`` as deterministic when the provider supports it.

    Attributes:
        model: Canonical ``"provider/model"`` identifier (e.g.
            ``"anthropic/claude-3-5-sonnet-latest"``). Adapters that accept
            bare model names (``"gpt-4o"``) should normalize to include
            the provider prefix.
    """

    model: str

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop: Sequence[str] | None = None,
        timeout: float | None = None,
    ) -> Completion:
        """Run a chat completion.

        Args:
            messages: Conversation messages, in order. Adapters may extract
                a ``role='system'`` message into a top-level system parameter
                if the underlying provider requires that (Anthropic).
            temperature: Sampling temperature (0.0 = deterministic).
            max_tokens: Maximum completion tokens to generate. Some providers
                (Anthropic) require this; adapters should default to a
                sensible value (4096) if the caller omits it.
            stop: Optional stop sequences. Adapters may ignore if the provider
                does not support stop sequences.
            timeout: Per-call timeout override, in seconds.

        Returns:
            A :class:`Completion` containing the assistant's response text
            and metadata.

        Raises:
            ProviderAuthError: API key invalid/expired.
            ProviderRateLimitError: Rate limited.
            ProviderTimeoutError: Timed out.
            ProviderInvalidRequestError: Malformed request.
            ProviderServiceError: Provider returned a retriable 5xx.
        """
        ...


@runtime_checkable
class StructuredExtractor(Protocol):
    """Provider for structured Pydantic outputs (Silver TCK tier).

    Adapters implementing this Protocol get to participate in the
    entity-extraction LLM fallback path with strongly-typed outputs.
    Splitting this from :class:`LLMProvider` lets thin adapters (or
    experimental local-model adapters) participate at Bronze without
    committing to structured outputs.

    Implementations MUST:

    * Use the most reliable structured-output mode the underlying provider
      supports — strict JSON schema (OpenAI), forced tool use (Anthropic),
      response_format (LiteLLM), etc.
    * Retry on Pydantic ``ValidationError`` up to ``max_retries`` times,
      passing the validation error back as feedback in the next attempt.
    * Raise :class:`~neo4j_agent_memory.llm.errors.StructuredExtractionError`
      with all attempts after exhausting retries.

    The default implementation in
    :func:`~neo4j_agent_memory.llm.structured.schema_aligned_extract`
    provides a generic SAP-style retry loop that adapters can delegate to
    if their underlying provider has no native structured-output mode.
    """

    async def complete_structured(
        self,
        messages: Sequence[ChatMessage],
        response_model: type[T],
        *,
        temperature: float = 0.0,
        max_retries: int = 2,
        timeout: float | None = None,
    ) -> T:
        """Return a validated instance of ``response_model``.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model class describing the expected
                output shape.
            temperature: Sampling temperature.
            max_retries: Maximum retry attempts after the initial attempt.
                Default 2 → 3 total attempts.
            timeout: Per-call timeout override.

        Returns:
            A validated instance of ``response_model``.

        Raises:
            StructuredExtractionError: All retry attempts failed.
            (also all the :class:`LLMProvider` errors)
        """
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Provider for text embeddings (Bronze TCK tier).

    Embeddings back Neo4j vector indexes on messages, entities,
    preferences, facts, and reasoning traces. The contract:

    * :attr:`model` and :attr:`dimensions` are required at construction.
      :attr:`dimensions` is what Neo4j vector indexes are sized for; a
      mismatch between an existing index and this value at
      :meth:`MemoryClient.connect` time raises
      :class:`~neo4j_agent_memory.llm.errors.EmbeddingDimensionMismatchError`.
    * :meth:`embed` accepts a batch and returns vectors in the same order.
    * Every returned vector has length :attr:`dimensions`.

    Attributes:
        model: Canonical model identifier.
        dimensions: Vector dimensionality. Adapters auto-populate this
            from :data:`~neo4j_agent_memory.llm.defaults.EMBEDDING_DIMENSIONS`
            for known models; for unknown models the user must pass an
            explicit ``dimensions=N`` to the adapter constructor.
    """

    model: str
    dimensions: int

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Args:
            texts: Texts to embed. May be empty (returns ``[]``).

        Returns:
            A list of vectors in the same order as the input. Every vector
            has length :attr:`dimensions`.
        """
        ...

    async def embed_one(self, text: str) -> list[float]:
        """Embed a single text (convenience for hot-path queries).

        Equivalent to ``(await self.embed([text]))[0]`` but adapters may
        optimize.

        Args:
            text: Text to embed.

        Returns:
            A single vector of length :attr:`dimensions`.
        """
        ...


__all__ = [
    "LLMProvider",
    "StructuredExtractor",
    "EmbeddingProvider",
]
