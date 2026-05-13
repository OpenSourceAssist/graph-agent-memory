"""Optional Instructor adapter for the Provider Protocol.

Thin wrapper around the `Instructor library <https://python.useinstructor.com/>`_
for users who already use Instructor in their stack and want to plug it
into neo4j-agent-memory's extraction pipeline.

This is intentionally a Silver-tier-only adapter: it implements
:class:`~neo4j_agent_memory.llm.protocol.StructuredExtractor` but not
:class:`~neo4j_agent_memory.llm.protocol.LLMProvider`. Plain chat
completions are better served by the native or LiteLLM adapter — what
Instructor uniquely offers is its structured-output quality.

Install with::

    pip install 'neo4j-agent-memory[instructor]'
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Sequence

    from neo4j_agent_memory.llm.types import ChatMessage


logger = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)


class InstructorProvider:
    """Structured-output provider backed by Instructor.

    Implements :class:`~neo4j_agent_memory.llm.protocol.StructuredExtractor`
    only. ``isinstance(provider, LLMProvider)`` returns False — by design.

    Example::

        from neo4j_agent_memory.llm.adapters.instructor import InstructorProvider

        provider = InstructorProvider("openai/gpt-4o-mini")
        result = await provider.complete_structured(messages, ResponseModel)
    """

    def __init__(
        self,
        model: str,
        *,
        async_client: bool = True,
        **provider_kwargs: Any,
    ) -> None:
        try:
            import instructor
        except ImportError as exc:
            raise ImportError(
                "Instructor not installed. "
                "Install with: pip install 'neo4j-agent-memory[instructor]'"
            ) from exc
        self.model = model
        # ``instructor.from_provider`` resolves provider strings of the same
        # ``"provider/model"`` shape we use, so the integration is seamless.
        self._client = instructor.from_provider(model, async_client=async_client, **provider_kwargs)

    async def complete_structured(
        self,
        messages: Sequence[ChatMessage],
        response_model: type[T],
        *,
        temperature: float = 0.0,
        max_retries: int = 2,
        timeout: float | None = None,
    ) -> T:
        kwargs: dict[str, Any] = {
            "response_model": response_model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
            "max_retries": max_retries,
        }
        if timeout is not None:
            kwargs["timeout"] = timeout
        return await self._client.create(**kwargs)


__all__ = [
    "InstructorProvider",
]
