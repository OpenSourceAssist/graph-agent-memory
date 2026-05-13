"""Provider-agnostic types for LLM and embedding interactions.

These Pydantic models form the boundary between the abstract
:class:`~neo4j_agent_memory.llm.protocol.LLMProvider` Protocol and concrete
adapter implementations. All adapters translate provider-native request/
response shapes to and from these types.

Design choices worth flagging:

* All types are :class:`pydantic.BaseModel` so :class:`MemorySettings`
  serialization round-trips cleanly and IDE autocomplete works without
  ``TYPE_CHECKING`` gymnastics.
* :class:`ChatMessage` is *frozen* — instances are immutable so they can
  be safely shared across coroutines and reused for retries.
* :class:`ChatMessage.content` is ``str`` only. Multimodal content (image,
  audio) is a v0.4+ concern; introducing a ``content: str | list[ContentPart]``
  union later is non-breaking.
* :class:`Completion.raw` carries the provider's native response (as a dict)
  for observability tooling. Adapters set this only when their per-instance
  ``return_raw=True`` flag is on so users do not pay the serialization cost
  by default.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """A single chat message in a conversation with an LLM.

    Mirrors the OpenAI Chat Completions payload shape because that is the
    most widely-supported lingua franca; non-OpenAI adapters translate to
    and from this shape (e.g. Anthropic extracts the ``system`` role into
    a top-level ``system=`` parameter).

    Frozen so the same instance can be reused across retry attempts in
    :func:`~neo4j_agent_memory.llm.structured.schema_aligned_extract`
    without defensive copying.
    """

    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant", "tool"] = Field(
        description="Speaker role for this message."
    )
    content: str = Field(description="Text content of the message.")
    name: str | None = Field(
        default=None,
        description="Optional name attribution; used for tool messages.",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="ID of the tool call this message responds to (only set on role='tool').",
    )


class Usage(BaseModel):
    """Token usage and cost information for a single completion call.

    Adapters populate as many fields as their underlying provider reports.
    Missing fields default to 0 (counts) or ``None`` (cost).
    """

    prompt_tokens: int = Field(default=0, ge=0, description="Tokens consumed by the prompt.")
    completion_tokens: int = Field(default=0, ge=0, description="Tokens generated in the response.")
    total_tokens: int = Field(default=0, ge=0, description="Sum of prompt + completion tokens.")
    cached_tokens: int = Field(
        default=0,
        ge=0,
        description=(
            "Tokens served from provider-side cache. Populated by adapters "
            "for Anthropic prompt caching and OpenAI cached-input pricing."
        ),
    )
    cost_usd: float | None = Field(
        default=None,
        description="Cost of the call in USD, if the adapter computes it.",
    )


class Completion(BaseModel):
    """The result of an LLM chat completion call.

    Adapters construct one of these for every successful response from
    their underlying SDK. Upstream code in neo4j-agent-memory consumes
    only ``content``; ``model``, ``usage``, ``finish_reason``, and ``raw``
    are present for observability and downstream cost accounting.
    """

    content: str = Field(description="Text content of the assistant's response.")
    model: str = Field(
        description=(
            "The model identifier the provider actually used. May differ "
            "from the requested model when providers route between variants."
        )
    )
    usage: Usage | None = Field(
        default=None,
        description="Token usage if the provider reported it.",
    )
    finish_reason: str | None = Field(
        default=None,
        description=(
            "Why the model stopped generating ('stop', 'length', 'tool_calls', "
            "'content_filter', etc.). Provider-specific values pass through."
        ),
    )
    raw: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Provider-native response object, serialized as a dict. Only "
            "populated when the adapter's ``return_raw=True`` flag is set. "
            "Used by observability tooling (OpenInference, Opik) that needs "
            "the full provider response."
        ),
    )


__all__ = [
    "ChatMessage",
    "Usage",
    "Completion",
]
