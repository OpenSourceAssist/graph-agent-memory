"""Pluggable LLM and embedding providers.

This package contains the Provider Protocol that lets neo4j-agent-memory
talk to any LLM or embedding model. The design rationale is in the
``Pluggable LLM and Embedding Providers`` PRD and in the explanation
doc :doc:`/explanation/why-provider-protocol`.

Quick reference::

    from neo4j_agent_memory.llm import (
        # Protocols
        LLMProvider,
        StructuredExtractor,
        EmbeddingProvider,
        # Types
        ChatMessage,
        Completion,
        Usage,
        # Errors
        ProviderError,
        ProviderAuthError,
        ProviderRateLimitError,
        ProviderTimeoutError,
        ProviderInvalidRequestError,
        ProviderServiceError,
        StructuredExtractionError,
        EmbeddingDimensionMismatchError,
        # Factory
        from_provider,
        # Helpers
        schema_aligned_extract,
    )

Adapters are imported lazily from
:mod:`neo4j_agent_memory.llm.adapters` to keep the bare-core install
import-time-free. Use :func:`from_provider` for the string-shorthand
factory, or import an adapter class directly when you want full control.
"""

from neo4j_agent_memory.llm.errors import (
    EmbeddingDimensionMismatchError,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderServiceError,
    ProviderTimeoutError,
    StructuredExtractionError,
)
from neo4j_agent_memory.llm.factory import from_provider
from neo4j_agent_memory.llm.protocol import (
    EmbeddingProvider,
    LLMProvider,
    StructuredExtractor,
)
from neo4j_agent_memory.llm.structured import schema_aligned_extract
from neo4j_agent_memory.llm.types import ChatMessage, Completion, Usage

__all__ = [
    # Protocols
    "LLMProvider",
    "StructuredExtractor",
    "EmbeddingProvider",
    # Types
    "ChatMessage",
    "Completion",
    "Usage",
    # Errors
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderInvalidRequestError",
    "ProviderServiceError",
    "StructuredExtractionError",
    "EmbeddingDimensionMismatchError",
    # Factory
    "from_provider",
    # Helpers
    "schema_aligned_extract",
]
