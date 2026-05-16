"""Tests for the LLM-aware MemoryObserver (WP-OBSERVER).

Exercises the new ``llm_provider`` parameter on
:class:`~neo4j_agent_memory.mcp._observer.MemoryObserver` without
requiring an MCP/FastMCP install. Builds a fake client + a canned LLM
provider and walks the observer through the threshold trigger.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from neo4j_agent_memory.llm.types import ChatMessage, Completion

pytest.importorskip("fastmcp", reason="MemoryObserver lives in the mcp package")

from neo4j_agent_memory.mcp._observer import MemoryObserver  # noqa: E402


@dataclass
class _FakeMessage:
    role: str
    content: str


class _FakeShortTerm:
    def __init__(self, messages: list[_FakeMessage]) -> None:
        self._messages = messages

    async def get_conversation(self, *, session_id: str, limit: int = 100) -> Any:
        return type("Conv", (), {"messages": self._messages})


class _FakeClient:
    def __init__(self, messages: list[_FakeMessage]) -> None:
        self.short_term = _FakeShortTerm(messages)


class _RecordingProvider:
    """LLMProvider double that records the prompt and returns a canned summary."""

    model = "fake/test-model"

    def __init__(self, response: str = "Compressed summary.") -> None:
        self._response = response
        self.calls: list[Sequence[ChatMessage]] = []

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop: Sequence[str] | None = None,
        timeout: float | None = None,
    ) -> Completion:
        self.calls.append(list(messages))
        return Completion(content=self._response, model=self.model)


async def _push_until_threshold(observer: MemoryObserver, session_id: str) -> None:
    """Push enough chars + messages to trip both the token and message-count gates."""
    # threshold is set to 200 tokens (~800 chars). Recent window default is 20.
    # Push 25 user messages of ~50 chars to comfortably exceed both gates.
    for i in range(25):
        await observer.on_message_stored(
            session_id,
            f"user message {i} contains Subject Capitalized for entity hints",
            message_id=f"m{i}",
            role="user",
        )


async def test_observer_uses_llm_provider_for_reflection():
    messages = [_FakeMessage(role="user", content=f"history line {i}") for i in range(40)]
    client = _FakeClient(messages)
    provider = _RecordingProvider(response="LLM compressed: focus on entities.")
    observer = MemoryObserver(
        client,  # type: ignore[arg-type]
        threshold_tokens=200,
        recent_message_window=20,
        llm_provider=provider,
    )

    await _push_until_threshold(observer, "s1")

    # The observer should have called the LLM exactly once (the threshold trip).
    assert len(provider.calls) == 1
    # The summarization prompt should mention the transcript.
    user_prompts = [m for m in provider.calls[0] if m.role == "user"]
    assert user_prompts and "history line" in user_prompts[0].content
    # And the resulting reflection should incorporate the LLM output.
    obs = await observer.get_observations("s1")
    assert obs["reflections"]
    assert "LLM compressed" in obs["reflections"][0]


async def test_observer_falls_back_to_keywords_without_provider():
    messages = [_FakeMessage(role="user", content=f"Acme Corp meeting line {i}") for i in range(40)]
    client = _FakeClient(messages)
    observer = MemoryObserver(
        client,  # type: ignore[arg-type]
        threshold_tokens=200,
        recent_message_window=20,
        llm_provider=None,
    )

    await _push_until_threshold(observer, "s2")

    obs = await observer.get_observations("s2")
    # Keyword-fallback reflections include "Session summary" prefix and
    # the capitalized entity phrase.
    assert obs["reflections"]
    assert "Session summary" in obs["reflections"][0]


class _BrokenProvider:
    model = "fake/broken"

    async def complete(self, *args: Any, **kwargs: Any) -> Completion:
        raise RuntimeError("simulated provider outage")


async def test_observer_falls_back_to_keywords_on_provider_error():
    messages = [_FakeMessage(role="user", content=f"Project Alpha note {i}") for i in range(40)]
    client = _FakeClient(messages)
    observer = MemoryObserver(
        client,  # type: ignore[arg-type]
        threshold_tokens=200,
        recent_message_window=20,
        llm_provider=_BrokenProvider(),
    )

    await _push_until_threshold(observer, "s3")

    obs = await observer.get_observations("s3")
    # Provider errors must not break the message-store path; the observer
    # falls through to the keyword summarizer.
    assert obs["reflections"]
    assert "Session summary" in obs["reflections"][0]
