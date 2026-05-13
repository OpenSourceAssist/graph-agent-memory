"""Tests for the WP-SHORT-TERM additions.

Verifies the module-level :func:`_llm_summarizer` helper and that
:meth:`ShortTermMemory.get_conversation_summary` uses
``default_llm_provider`` when no explicit ``summarizer`` is passed.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from neo4j_agent_memory.llm.types import ChatMessage, Completion
from neo4j_agent_memory.memory.short_term import _llm_summarizer


class _RecordingProvider:
    model = "fake/test-model"

    def __init__(self, response: str = "summary text") -> None:
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


async def test_llm_summarizer_calls_provider_with_transcript():
    provider = _RecordingProvider(response="Concise summary.")
    summarizer = _llm_summarizer(provider, max_tokens=200, temperature=0.0)
    result = await summarizer("USER: hi\nASSISTANT: hello")
    assert result == "Concise summary."
    # One call, with a system message and a user message containing the transcript.
    assert len(provider.calls) == 1
    roles = [m.role for m in provider.calls[0]]
    assert "system" in roles and "user" in roles
    user_message = next(m for m in provider.calls[0] if m.role == "user")
    assert "USER: hi" in user_message.content


async def test_short_term_summary_uses_default_llm_provider_when_no_summarizer(
    monkeypatch,
):
    """Walks ShortTermMemory.get_conversation_summary's auto-summarizer path.

    We stub out the Neo4j client's ``execute_read`` so the method does not
    try to talk to a real database; only the summarizer code path matters
    for this test.
    """
    from datetime import datetime, timezone

    from neo4j_agent_memory.memory.short_term import (
        Conversation,
        Message,
        MessageRole,
        ShortTermMemory,
    )

    provider = _RecordingProvider(response="LLM-driven summary.")

    # Stand in for the real Neo4jClient — ShortTermMemory only touches
    # ``execute_read`` from ``get_conversation_summary``.
    class _ClientStub:
        async def execute_read(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
            return []  # No entities returned.

    client_stub = _ClientStub()
    short_term = ShortTermMemory(
        client_stub,  # type: ignore[arg-type]
        embedder=None,
        extractor=None,
        default_llm_provider=provider,
    )

    # Stub out get_conversation so the test does not require a real graph.
    async def fake_get_conversation(session_id: str, *args: Any, **kwargs: Any) -> Conversation:
        now = datetime.now(tz=timezone.utc)
        return Conversation(
            session_id=session_id,
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="hello world",
                    created_at=now,
                ),
                Message(
                    role=MessageRole.ASSISTANT,
                    content="hi back",
                    created_at=now,
                ),
            ],
            created_at=now,
        )

    monkeypatch.setattr(short_term, "get_conversation", fake_get_conversation)

    summary = await short_term.get_conversation_summary("s1")
    assert summary.summary == "LLM-driven summary."
    # The provider should have been called exactly once.
    assert len(provider.calls) == 1


async def test_short_term_summary_falls_back_to_basic_without_provider(monkeypatch):
    """No default_llm_provider, no explicit summarizer → basic keyword summary."""
    from datetime import datetime, timezone

    from neo4j_agent_memory.memory.short_term import (
        Conversation,
        Message,
        MessageRole,
        ShortTermMemory,
    )

    class _ClientStub:
        async def execute_read(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
            return []

    short_term = ShortTermMemory(
        _ClientStub(),  # type: ignore[arg-type]
        embedder=None,
        extractor=None,
        default_llm_provider=None,
    )

    async def fake_get_conversation(session_id: str, *args: Any, **kwargs: Any) -> Conversation:
        now = datetime.now(tz=timezone.utc)
        return Conversation(
            session_id=session_id,
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="kickoff message",
                    created_at=now,
                ),
            ],
            created_at=now,
        )

    monkeypatch.setattr(short_term, "get_conversation", fake_get_conversation)

    summary = await short_term.get_conversation_summary("s2")
    # Basic summarizer mentions message count.
    assert "1 messages" in summary.summary or "messages" in summary.summary


async def test_short_term_summary_explicit_summarizer_wins_over_default(monkeypatch):
    """User-supplied summarizer takes precedence over default_llm_provider."""
    from datetime import datetime, timezone

    from neo4j_agent_memory.memory.short_term import (
        Conversation,
        Message,
        MessageRole,
        ShortTermMemory,
    )

    default_provider = _RecordingProvider(response="DEFAULT")
    # The custom summarizer should be used instead of the default LLM.
    captured: dict[str, str] = {}

    async def custom(text: str) -> str:
        captured["transcript"] = text
        return "CUSTOM"

    class _ClientStub:
        async def execute_read(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
            return []

    short_term = ShortTermMemory(
        _ClientStub(),  # type: ignore[arg-type]
        embedder=None,
        extractor=None,
        default_llm_provider=default_provider,
    )

    async def fake_get_conversation(session_id: str, *args: Any, **kwargs: Any) -> Conversation:
        now = datetime.now(tz=timezone.utc)
        return Conversation(
            session_id=session_id,
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="ping",
                    created_at=now,
                ),
            ],
            created_at=now,
        )

    monkeypatch.setattr(short_term, "get_conversation", fake_get_conversation)

    summary = await short_term.get_conversation_summary("s3", summarizer=custom)
    assert summary.summary == "CUSTOM"
    assert "ping" in captured["transcript"]
    # The default provider must not be invoked when an explicit summarizer
    # is supplied.
    assert default_provider.calls == []
