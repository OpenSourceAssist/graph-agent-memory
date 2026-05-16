"""Reusable adapter contract harness.

This module is both:

1. A library of ``run_*_contract`` helpers that adapter test files import
   to exercise the canonical Protocol contract.
2. A self-test that runs the harness against the in-memory ``CannedProvider``
   doubles. If the harness passes against the canned providers, it is in a
   shape that can be reused against real adapters.

Adapter-specific tests (e.g. ``test_openai_adapter.py`` against recorded
VCR cassettes) live in sibling files and import the helpers below. Those
files are not included in this PR — they require API keys / cassettes to
be set up — but the harness is the single source of truth they will share.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest
from pydantic import BaseModel

from neo4j_agent_memory.llm import (
    ChatMessage,
    Completion,
    EmbeddingProvider,
    LLMProvider,
    StructuredExtractor,
)

from ._mocks import CannedEmbeddingProvider, CannedLLMProvider, SimplePayload

# ---------------------------------------------------------------------------
# Reusable contract helpers
# ---------------------------------------------------------------------------


async def run_llm_contract(provider: Any, *, sample_prompt: str = "say hi") -> None:
    """Assert ``provider`` satisfies the :class:`LLMProvider` contract.

    Behavioral checks:

    * Implements the Protocol (structural ``isinstance``).
    * Carries a non-empty :attr:`model` attribute.
    * :meth:`complete` returns a :class:`Completion` with non-empty content
      and a model string.
    * :meth:`complete` is safe to call concurrently — calling 5 times via
      :func:`asyncio.gather` must not crash.
    """
    assert isinstance(provider, LLMProvider), (
        f"{type(provider).__name__} does not satisfy the LLMProvider Protocol"
    )
    assert isinstance(provider.model, str) and provider.model

    messages = [ChatMessage(role="user", content=sample_prompt)]
    completion = await provider.complete(messages, temperature=0.0)
    assert isinstance(completion, Completion)
    assert completion.content
    assert completion.model

    # Concurrent safety — five parallel calls
    results = await asyncio.gather(*(provider.complete(messages) for _ in range(5)))
    assert all(isinstance(r, Completion) for r in results)


async def run_structured_contract(
    provider: Any,
    *,
    response_model: type[BaseModel] = SimplePayload,
    sample_prompt: str = "Return name=Alice age=30 as JSON.",
) -> None:
    """Assert ``provider`` satisfies :class:`StructuredExtractor`.

    Calls :meth:`complete_structured` and verifies a validated instance is
    returned. Adapters that delegate to
    :func:`schema_aligned_extract` are also exercised by this — the result
    type matters, not the path.
    """
    assert isinstance(provider, StructuredExtractor), (
        f"{type(provider).__name__} does not satisfy the StructuredExtractor Protocol"
    )
    messages = [ChatMessage(role="user", content=sample_prompt)]
    result = await provider.complete_structured(messages, response_model)
    assert isinstance(result, response_model)


async def run_embedding_contract(provider: Any) -> None:
    """Assert ``provider`` satisfies :class:`EmbeddingProvider`.

    * Implements the Protocol.
    * Has a positive ``dimensions`` attribute.
    * :meth:`embed` of one text returns one vector of the right length.
    * :meth:`embed` of an empty list returns ``[]``.
    * :meth:`embed_one` returns a single vector of the right length.
    """
    assert isinstance(provider, EmbeddingProvider), (
        f"{type(provider).__name__} does not satisfy the EmbeddingProvider Protocol"
    )
    assert isinstance(provider.dimensions, int) and provider.dimensions > 0
    assert isinstance(provider.model, str) and provider.model

    vectors = await provider.embed(["one text"])
    assert len(vectors) == 1
    assert len(vectors[0]) == provider.dimensions

    # Empty input yields empty output.
    assert await provider.embed([]) == []

    single = await provider.embed_one("single")
    assert len(single) == provider.dimensions


# ---------------------------------------------------------------------------
# Self-tests — verify the harness itself works against the canned doubles
# ---------------------------------------------------------------------------


async def test_canned_llm_provider_passes_llm_contract():
    # Provider needs as many responses as the harness will request:
    # 1 for the primary call + 5 for the concurrency check = 6 total.
    provider = CannedLLMProvider(responses=["hi"] * 6)
    await run_llm_contract(provider)


async def test_canned_llm_provider_does_not_pass_structured_contract():
    # CannedLLMProvider has no complete_structured(); the harness must
    # fail the protocol check rather than silently appearing to work.
    provider = CannedLLMProvider(responses=["{}"] * 4)
    with pytest.raises(AssertionError):
        await run_structured_contract(provider)


async def test_canned_embedding_provider_passes_embedding_contract():
    embedder = CannedEmbeddingProvider(dimensions=4)
    await run_embedding_contract(embedder)


# ---------------------------------------------------------------------------
# Static checks on real adapter classes (no SDK calls)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_path,class_name",
    [
        ("neo4j_agent_memory.llm.adapters.openai", "OpenAIProvider"),
        ("neo4j_agent_memory.llm.adapters.openai", "OpenAIEmbeddingProvider"),
        ("neo4j_agent_memory.llm.adapters.anthropic", "AnthropicProvider"),
        ("neo4j_agent_memory.llm.adapters.bedrock", "BedrockProvider"),
        ("neo4j_agent_memory.llm.adapters.bedrock", "BedrockEmbeddingProvider"),
        ("neo4j_agent_memory.llm.adapters.litellm", "LiteLLMProvider"),
        ("neo4j_agent_memory.llm.adapters.litellm", "LiteLLMEmbeddingProvider"),
        (
            "neo4j_agent_memory.llm.adapters.sentence_transformers",
            "SentenceTransformersProvider",
        ),
        ("neo4j_agent_memory.llm.adapters.vertex_ai", "VertexAIEmbeddingProvider"),
        ("neo4j_agent_memory.llm.adapters.instructor", "InstructorProvider"),
    ],
)
def test_adapter_class_exists_and_is_a_class(module_path: str, class_name: str):
    """Every adapter advertised in the docs must be importable.

    This is a low-cost catch for accidental rename / removal regressions.
    The adapter modules are allowed to import their SDKs lazily (inside
    methods), so importing the module itself should succeed even without
    the underlying extra installed.
    """
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    assert inspect.isclass(cls), f"{class_name} should be a class"
