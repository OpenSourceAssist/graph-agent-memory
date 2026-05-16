"""Universal LiteLLM adapter for the Provider Protocol.

LiteLLM is the canonical universal adapter — one optional install
(``[litellm]``) unlocks the long tail of 100+ providers including Azure
OpenAI, Vertex AI Gemini, Cohere, Mistral, Groq, Together, Ollama, vLLM,
OpenRouter, DeepSeek, and many more. Native adapters in this package
exist only for the providers where the native SDK has materially better
capabilities than the LiteLLM normalization (OpenAI strict mode,
Anthropic forced tool use, Bedrock Converse API).

Pinned to ``litellm>=1.50.0,<2.0`` in ``pyproject.toml`` to guard
against upstream regressions. A nightly cassette-refresh job in CI
catches drift before users see it.

Install with::

    pip install 'neo4j-agent-memory[litellm]'
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from neo4j_agent_memory.llm.defaults import lookup_embedding_dimensions
from neo4j_agent_memory.llm.errors import (
    ProviderAuthError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderServiceError,
    ProviderTimeoutError,
)
from neo4j_agent_memory.llm.structured import schema_aligned_extract
from neo4j_agent_memory.llm.types import ChatMessage, Completion, Usage

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)


def _ensure_litellm() -> Any:
    """Import :mod:`litellm` lazily, raising a helpful error if missing."""
    try:
        import litellm
    except ImportError as exc:
        raise ImportError(
            "LiteLLM not installed. Install with: pip install 'neo4j-agent-memory[litellm]'"
        ) from exc
    return litellm


def _translate_litellm_exception(exc: Exception) -> Exception:
    """Map a :mod:`litellm.exceptions` exception to a :class:`ProviderError`."""
    try:
        from litellm.exceptions import (
            APIConnectionError,
            AuthenticationError,
            BadRequestError,
            RateLimitError,
            ServiceUnavailableError,
            Timeout,
        )
    except ImportError:
        return exc

    if isinstance(exc, AuthenticationError):
        return ProviderAuthError(str(exc))
    if isinstance(exc, RateLimitError):
        retry_after: float | None = None
        value = getattr(exc, "retry_after", None)
        if value is not None:
            try:
                retry_after = float(value)
            except (TypeError, ValueError):
                retry_after = None
        return ProviderRateLimitError(str(exc), retry_after=retry_after)
    if isinstance(exc, Timeout):
        return ProviderTimeoutError(str(exc))
    if isinstance(exc, BadRequestError):
        return ProviderInvalidRequestError(str(exc))
    if isinstance(exc, (ServiceUnavailableError, APIConnectionError)):
        return ProviderServiceError(str(exc))
    return exc


def _translate_usage(usage: Any) -> Usage | None:
    if usage is None:
        return None
    if isinstance(usage, dict):
        prompt = usage.get("prompt_tokens", 0) or 0
        completion = usage.get("completion_tokens", 0) or 0
        total = usage.get("total_tokens", 0) or 0
    else:
        prompt = getattr(usage, "prompt_tokens", 0) or 0
        completion = getattr(usage, "completion_tokens", 0) or 0
        total = getattr(usage, "total_tokens", 0) or (prompt + completion)
    return Usage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


class LiteLLMProvider:
    """Universal LLM provider routed through LiteLLM.

    Implements both :class:`~neo4j_agent_memory.llm.protocol.LLMProvider`
    and :class:`~neo4j_agent_memory.llm.protocol.StructuredExtractor`.

    Examples::

        # OpenAI-compatible endpoint (Ollama)
        provider = LiteLLMProvider(
            "ollama/llama3.2",
            api_base="http://localhost:11434",
            api_key="not-needed",
        )

        # Azure OpenAI
        provider = LiteLLMProvider(
            "azure/my-deployment",
            api_key="...",
            api_base="https://my.openai.azure.com",
            api_version="2024-02-15-preview",
        )

        # Vertex AI Gemini
        provider = LiteLLMProvider(
            "vertex_ai/gemini-1.5-pro-002",
            vertex_project="my-gcp-project",
            vertex_location="us-central1",
        )

    Notes:
        * ``complete_structured()`` delegates to
          :func:`schema_aligned_extract` because LiteLLM does not have a
          single structured-output mode that works across all providers.
        * Pass any provider-specific keyword arguments to the constructor
          and they will be forwarded to every ``acompletion`` call. See
          the LiteLLM docs for provider-specific kwargs.
    """

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
        aws_region: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        return_raw: bool = False,
        **default_kwargs: Any,
    ) -> None:
        self.model = model
        self._return_raw = return_raw

        # Build the kwargs we pass to every acompletion() call. LiteLLM
        # uses ``aws_region_name`` not ``aws_region``, so we translate.
        call_kwargs: dict[str, Any] = {
            "timeout": timeout,
            "num_retries": max_retries,
        }
        if api_key is not None:
            call_kwargs["api_key"] = api_key
        if api_base is not None:
            call_kwargs["api_base"] = api_base
        if aws_region is not None:
            call_kwargs["aws_region_name"] = aws_region
        # Filter out None values from default_kwargs so adapters can pass
        # ``something=None`` without polluting the call.
        for key, value in default_kwargs.items():
            if value is not None:
                call_kwargs[key] = value
        self._call_kwargs = call_kwargs

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop: Sequence[str] | None = None,
        timeout: float | None = None,
    ) -> Completion:
        litellm = _ensure_litellm()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
            **self._call_kwargs,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if stop is not None:
            kwargs["stop"] = list(stop)
        if timeout is not None:
            kwargs["timeout"] = timeout

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as exc:
            translated = _translate_litellm_exception(exc)
            if translated is exc:
                raise
            raise translated from exc

        choice = response.choices[0]
        message = choice.message
        content = getattr(message, "content", None) or ""
        finish_reason = getattr(choice, "finish_reason", None)

        # ``response.model_dump`` exists for LiteLLM's ModelResponse objects
        raw: dict[str, Any] | None = None
        if self._return_raw:
            try:
                raw = response.model_dump()
            except AttributeError:
                # Fallback for older LiteLLM versions or dict-shaped responses
                raw = dict(response) if hasattr(response, "items") else None

        return Completion(
            content=content,
            model=getattr(response, "model", self.model),
            usage=_translate_usage(getattr(response, "usage", None)),
            finish_reason=finish_reason,
            raw=raw,
        )

    async def complete_structured(
        self,
        messages: Sequence[ChatMessage],
        response_model: type[T],
        *,
        temperature: float = 0.0,
        max_retries: int = 2,
        timeout: float | None = None,
    ) -> T:
        # LiteLLM normalizes ``response_format={"type": "json_object"}``
        # across providers that support it, but the structured-output
        # quality varies wildly. SAP is the safe path.
        return await schema_aligned_extract(
            self,
            messages,
            response_model,
            temperature=temperature,
            max_retries=max_retries,
            timeout=timeout,
        )


class LiteLLMEmbeddingProvider:
    """Universal embedding provider routed through LiteLLM.

    Auto-populates :attr:`dimensions` from the defaults table for known
    models. For unknown models, pass ``dimensions=N`` explicitly.

    Implements :class:`~neo4j_agent_memory.llm.protocol.EmbeddingProvider`.
    """

    def __init__(
        self,
        model: str,
        *,
        dimensions: int | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        aws_region: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        batch_size: int = 100,
        **default_kwargs: Any,
    ) -> None:
        self.model = model
        if dimensions is not None:
            self.dimensions = dimensions
        else:
            known = lookup_embedding_dimensions(model)
            if known is None:
                raise ValueError(
                    f"Could not determine dimensions for embedding model {model!r}. "
                    f"Pass dimensions=N explicitly or use a model in the defaults table "
                    f"(see neo4j_agent_memory.llm.defaults.EMBEDDING_DIMENSIONS)."
                )
            self.dimensions = known
        self._batch_size = batch_size

        call_kwargs: dict[str, Any] = {
            "timeout": timeout,
            "num_retries": max_retries,
        }
        if api_key is not None:
            call_kwargs["api_key"] = api_key
        if api_base is not None:
            call_kwargs["api_base"] = api_base
        if aws_region is not None:
            call_kwargs["aws_region_name"] = aws_region
        for key, value in default_kwargs.items():
            if value is not None:
                call_kwargs[key] = value
        self._call_kwargs = call_kwargs

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        litellm = _ensure_litellm()
        texts_list = list(texts)
        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts_list), self._batch_size):
            batch = texts_list[start : start + self._batch_size]
            try:
                response = await litellm.aembedding(
                    model=self.model, input=batch, **self._call_kwargs
                )
            except Exception as exc:
                translated = _translate_litellm_exception(exc)
                if translated is exc:
                    raise
                raise translated from exc
            # LiteLLM returns an ``EmbeddingResponse`` with ``.data`` list
            # of {"embedding": [...], "index": N}
            data = response.data if hasattr(response, "data") else response.get("data", [])
            sorted_data = sorted(
                data,
                key=lambda d: d.get("index", 0) if isinstance(d, dict) else d.index,
            )
            for item in sorted_data:
                vec = item["embedding"] if isinstance(item, dict) else item.embedding
                all_embeddings.append(vec)
        return all_embeddings

    async def embed_one(self, text: str) -> list[float]:
        vectors = await self.embed([text])
        return vectors[0]


__all__ = [
    "LiteLLMProvider",
    "LiteLLMEmbeddingProvider",
]
