"""Provider-agnostic exception hierarchy for LLM and embedding calls.

Every adapter translates its underlying SDK's exception types into one of
the classes defined here. This is the contract that makes
``except ProviderRateLimitError`` work identically across providers.

These exceptions are intentionally *separate* from the existing
:class:`~neo4j_agent_memory.core.exceptions.MemoryError` hierarchy. Provider
errors are about LLM/embedding provider calls; memory errors are about
Neo4j storage. ``except ProviderRateLimitError`` should never inadvertently
catch a Neo4j connection failure.
"""

from __future__ import annotations

from typing import Any


class ProviderError(Exception):
    """Base class for all LLM/embedding provider errors.

    Adapters raise subclasses of this to communicate failure modes
    independently of which SDK actually raised the underlying error.
    """


class ProviderAuthError(ProviderError):
    """API key missing, invalid, or expired.

    Maps to: OpenAI ``AuthenticationError``, Anthropic ``AuthenticationError``,
    Bedrock 401 ``ClientError`` (``UnrecognizedClientException``,
    ``InvalidSignatureException``), LiteLLM ``AuthenticationError``.
    """


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded.

    Maps to: OpenAI ``RateLimitError``, Anthropic ``RateLimitError``,
    Bedrock ``ThrottlingException`` ``ClientError``, LiteLLM ``RateLimitError``.

    Attributes:
        retry_after: Seconds to wait before retrying, if the provider
            advised one via a ``Retry-After`` header or equivalent.
    """

    retry_after: float | None

    def __init__(self, *args: Any, retry_after: float | None = None) -> None:
        super().__init__(*args)
        self.retry_after = retry_after


class ProviderTimeoutError(ProviderError):
    """Request exceeded the configured timeout.

    Maps to: OpenAI ``APITimeoutError``, Anthropic ``APITimeoutError``,
    Bedrock ``ReadTimeoutError``, LiteLLM ``Timeout``.
    """


class ProviderInvalidRequestError(ProviderError):
    """Malformed request (unknown model, bad parameters, schema violation, etc.).

    Maps to: OpenAI ``BadRequestError``, Anthropic ``BadRequestError``,
    Bedrock ``ValidationException`` ``ClientError``, LiteLLM ``BadRequestError``.
    """


class ProviderServiceError(ProviderError):
    """Provider returned a 5xx (retriable) server error.

    Maps to: OpenAI ``APIStatusError`` with 5xx, Anthropic ``APIStatusError``
    with 5xx, Bedrock ``InternalServerException``/``ServiceUnavailableException``,
    LiteLLM ``ServiceUnavailableError`` / ``APIConnectionError``.
    """


class StructuredExtractionError(ProviderError):
    """Could not produce a valid structured output after retries.

    Raised by :func:`~neo4j_agent_memory.llm.structured.schema_aligned_extract`
    when the LLM repeatedly fails to produce JSON matching the requested
    schema. Carries every attempt and the corresponding ``ValidationError``
    instances so callers can log/diagnose.

    Attributes:
        last_attempts: Raw text of every attempt the LLM made.
        validation_errors: ``ValidationError`` instances from each failed
            Pydantic validation attempt. May be shorter than
            ``last_attempts`` if some attempts failed at the JSON-parse
            stage rather than the validation stage.
    """

    last_attempts: list[str]
    validation_errors: list[Any]

    def __init__(
        self,
        *args: Any,
        last_attempts: list[str] | None = None,
        validation_errors: list[Any] | None = None,
    ) -> None:
        super().__init__(*args)
        self.last_attempts = last_attempts or []
        self.validation_errors = validation_errors or []


class EmbeddingDimensionMismatchError(ProviderError):
    """A pre-existing Neo4j vector index disagrees with the configured embedder.

    Raised at :meth:`MemoryClient.connect` time when the dimensions reported
    by the active :class:`~neo4j_agent_memory.llm.protocol.EmbeddingProvider`
    do not match the dimensions of the existing vector index(es) in Neo4j.
    This usually means the user changed embedding models without rebuilding
    the indexes.

    Attributes:
        expected_dimensions: What the configured embedder reports.
        actual_dimensions: What the Neo4j index actually has.
        index_name: Name of the offending vector index.
    """

    expected_dimensions: int
    actual_dimensions: int
    index_name: str

    def __init__(
        self,
        message: str,
        *,
        expected_dimensions: int,
        actual_dimensions: int,
        index_name: str,
    ) -> None:
        super().__init__(message)
        self.expected_dimensions = expected_dimensions
        self.actual_dimensions = actual_dimensions
        self.index_name = index_name


__all__ = [
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderInvalidRequestError",
    "ProviderServiceError",
    "StructuredExtractionError",
    "EmbeddingDimensionMismatchError",
]
