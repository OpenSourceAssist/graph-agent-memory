"""Native AWS Bedrock adapter for the Provider Protocol.

Uses Bedrock's Converse API for a unified interface across Anthropic,
Amazon Titan, and Meta Llama models hosted on Bedrock. Treated as a
separate adapter from the Anthropic-direct adapter because:

* The auth model is AWS SigV4, not an API key.
* Configuration (``aws_region``, ``aws_profile``) differs substantively.
* Bedrock-hosted Anthropic models have a different model id format
  (``anthropic.claude-3-5-sonnet-20241022-v2:0``).

Implements:

* :class:`BedrockProvider` — :class:`LLMProvider` + :class:`StructuredExtractor`
* :class:`BedrockEmbeddingProvider` — :class:`EmbeddingProvider` (wraps
  :class:`~neo4j_agent_memory.embeddings.bedrock.BedrockEmbedder`)

Install with::

    pip install 'neo4j-agent-memory[bedrock]'
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ValidationError

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

    from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder


logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)


_DEFAULT_MAX_TOKENS = 4096


def _strip_provider_prefix(model: str) -> str:
    if model.startswith("bedrock/"):
        return model[len("bedrock/") :]
    return model


def _is_anthropic_on_bedrock(bare_model: str) -> bool:
    """Whether ``bare_model`` is an Anthropic model on Bedrock.

    Anthropic-on-Bedrock model ids start with ``anthropic.`` or
    ``us.anthropic.`` (inference-profile prefixed).
    """
    return bare_model.startswith("anthropic.") or bare_model.startswith("us.anthropic.")


def _translate_bedrock_exception(exc: Exception) -> Exception:
    """Map a :mod:`botocore.exceptions` exception to a :class:`ProviderError`."""
    try:
        from botocore.exceptions import (
            ClientError,
            ConnectTimeoutError,
            EndpointConnectionError,
            ReadTimeoutError,
        )
    except ImportError:
        return exc

    if isinstance(exc, (ReadTimeoutError, ConnectTimeoutError)):
        return ProviderTimeoutError(str(exc))
    if isinstance(exc, EndpointConnectionError):
        return ProviderServiceError(str(exc))
    if isinstance(exc, ClientError):
        # ClientError has a typed .response dict; getattr appeases type checkers
        # that only see the bare Exception base class.
        response_dict = getattr(exc, "response", {}) or {}
        code = response_dict.get("Error", {}).get("Code", "")
        if code in {
            "UnrecognizedClientException",
            "InvalidSignatureException",
            "AccessDeniedException",
        }:
            return ProviderAuthError(str(exc))
        if code in {"ThrottlingException", "TooManyRequestsException"}:
            return ProviderRateLimitError(str(exc))
        if code in {"ValidationException"}:
            return ProviderInvalidRequestError(str(exc))
        if code in {
            "InternalServerException",
            "ServiceUnavailableException",
            "ModelTimeoutException",
        }:
            return ProviderServiceError(str(exc))
    return exc


def _converse_messages(
    messages: Sequence[ChatMessage],
) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]]]:
    """Split messages into ``(system, messages)`` for the Converse API.

    Bedrock's Converse API expects:
    - ``system=[{"text": "..."}, ...]`` — a list
    - ``messages=[{"role": "user|assistant", "content": [{"text": "..."}]}]``
    """
    system: list[dict[str, Any]] = []
    converse_messages: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "system":
            system.append({"text": msg.content})
            continue
        role = msg.role if msg.role in ("user", "assistant") else "user"
        converse_messages.append({"role": role, "content": [{"text": msg.content}]})
    return (system if system else None), converse_messages


class BedrockProvider:
    """Native Bedrock LLM provider via the Converse API.

    Example::

        provider = BedrockProvider(
            "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
            aws_region="us-west-2",
        )
    """

    def __init__(
        self,
        model: str,
        *,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        timeout: float = 60.0,
        return_raw: bool = False,
        default_max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        bare = _strip_provider_prefix(model)
        self.model = f"bedrock/{bare}"
        self._bare_model = bare
        self._aws_region = aws_region
        self._aws_profile = aws_profile
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._timeout = timeout
        self._return_raw = return_raw
        self._default_max_tokens = default_max_tokens
        self._client: Any | None = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:
                raise ImportError(
                    "boto3 not installed. Install with: pip install 'neo4j-agent-memory[bedrock]'"
                ) from exc
            session_kwargs: dict[str, Any] = {}
            if self._aws_profile:
                session_kwargs["profile_name"] = self._aws_profile
            if self._aws_region:
                session_kwargs["region_name"] = self._aws_region
            session = boto3.Session(**session_kwargs)
            client_kwargs: dict[str, Any] = {
                "config": Config(read_timeout=self._timeout),
            }
            if self._aws_access_key_id:
                client_kwargs["aws_access_key_id"] = self._aws_access_key_id
            if self._aws_secret_access_key:
                client_kwargs["aws_secret_access_key"] = self._aws_secret_access_key
            self._client = session.client("bedrock-runtime", **client_kwargs)
        return self._client

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop: Sequence[str] | None = None,
        timeout: float | None = None,
    ) -> Completion:
        client = self._ensure_client()
        system, conv_messages = _converse_messages(messages)
        inference_config: dict[str, Any] = {
            "temperature": temperature,
            "maxTokens": max_tokens if max_tokens is not None else self._default_max_tokens,
        }
        if stop is not None:
            inference_config["stopSequences"] = list(stop)
        kwargs: dict[str, Any] = {
            "modelId": self._bare_model,
            "messages": conv_messages,
            "inferenceConfig": inference_config,
        }
        if system is not None:
            kwargs["system"] = system

        try:
            # boto3 is sync; run in a thread.
            response = await asyncio.to_thread(client.converse, **kwargs)
        except Exception as exc:
            translated = _translate_bedrock_exception(exc)
            if translated is exc:
                raise
            raise translated from exc

        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        text_parts = [b.get("text", "") for b in content_blocks if "text" in b]
        usage_data = response.get("usage") or {}
        return Completion(
            content="".join(text_parts),
            model=self._bare_model,
            usage=Usage(
                prompt_tokens=usage_data.get("inputTokens", 0) or 0,
                completion_tokens=usage_data.get("outputTokens", 0) or 0,
                total_tokens=usage_data.get("totalTokens", 0) or 0,
            ),
            finish_reason=response.get("stopReason"),
            raw=response if self._return_raw else None,
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
        """Use Converse toolConfig for Anthropic-on-Bedrock; SAP for everything else.

        Only Anthropic models on Bedrock reliably support forced tool use
        through Converse. For Titan and Llama models we delegate to the
        generic SAP retry loop.
        """
        if not _is_anthropic_on_bedrock(self._bare_model):
            return await schema_aligned_extract(
                self,
                messages,
                response_model,
                temperature=temperature,
                max_retries=max_retries,
                timeout=timeout,
            )

        client = self._ensure_client()
        system, conv_messages = _converse_messages(messages)
        schema = response_model.model_json_schema()
        tool_spec = {
            "toolSpec": {
                "name": "submit_extraction",
                "description": (
                    f"Submit a structured extraction matching the {response_model.__name__} schema."
                ),
                "inputSchema": {"json": schema},
            }
        }
        kwargs: dict[str, Any] = {
            "modelId": self._bare_model,
            "messages": conv_messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": self._default_max_tokens,
            },
            "toolConfig": {
                "tools": [tool_spec],
                "toolChoice": {"tool": {"name": "submit_extraction"}},
            },
        }
        if system is not None:
            kwargs["system"] = system

        try:
            response = await asyncio.to_thread(client.converse, **kwargs)
        except Exception as exc:
            translated = _translate_bedrock_exception(exc)
            if translated is exc:
                raise
            raise translated from exc

        content = response.get("output", {}).get("message", {}).get("content", [])
        for block in content:
            if "toolUse" in block:
                tool_input = block["toolUse"].get("input", {})
                try:
                    return response_model.model_validate(tool_input)
                except ValidationError as exc:
                    logger.debug(
                        "Bedrock tool-use response failed validation; falling back to SAP: %s",
                        exc,
                    )
                    break

        return await schema_aligned_extract(
            self,
            messages,
            response_model,
            temperature=temperature,
            max_retries=max_retries,
            timeout=timeout,
        )


class BedrockEmbeddingProvider:
    """Bedrock embedding provider.

    Wraps the existing
    :class:`~neo4j_agent_memory.embeddings.bedrock.BedrockEmbedder` for the
    new Protocol surface.

    Implements :class:`~neo4j_agent_memory.llm.protocol.EmbeddingProvider`.
    """

    def __init__(
        self,
        model: str = "bedrock/amazon.titan-embed-text-v2:0",
        *,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 25,
        normalize: bool = True,
    ) -> None:
        bare = _strip_provider_prefix(model)
        self.model = f"bedrock/{bare}"
        self._bare_model = bare
        self._aws_region = aws_region
        self._aws_profile = aws_profile
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._batch_size = batch_size
        self._normalize = normalize
        self._underlying: BedrockEmbedder | None = None

        if dimensions is not None:
            self.dimensions = dimensions
        else:
            known = lookup_embedding_dimensions(self.model)
            if known is None:
                raise ValueError(
                    f"Could not determine dimensions for Bedrock model {self.model!r}. "
                    f"Pass dimensions=N explicitly or use a model in the defaults table."
                )
            self.dimensions = known

    def _ensure_underlying(self) -> BedrockEmbedder:
        if self._underlying is None:
            try:
                from neo4j_agent_memory.embeddings.bedrock import BedrockEmbedder
            except ImportError as exc:
                raise ImportError(
                    "boto3 not installed. Install with: pip install 'neo4j-agent-memory[bedrock]'"
                ) from exc
            self._underlying = BedrockEmbedder(
                model=self._bare_model,
                region_name=self._aws_region,
                profile_name=self._aws_profile,
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                batch_size=self._batch_size,
                normalize=self._normalize,
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
    "BedrockProvider",
    "BedrockEmbeddingProvider",
]
