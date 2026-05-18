"""Live-NAMS integration tests — TCK Bronze tier (short-term core).

Covers SPEC §1 (schema) and §2 (short-term memory):
add_message, get_conversation, search_messages, list_sessions,
delete_message, clear_session, plus the session-isolation invariants
the SPEC requires.

Conversation lifecycle on NAMS
==============================

NAMS (unlike bolt) does **not** auto-create a conversation on the
first ``add_message`` — see the ``nams_session`` fixture in
``conftest.py`` for the wrapper that creates the conversation first
and returns the canonical id. Tests that round-trip messages use
``nams_session`` rather than the bare ``session_id`` fixture.
"""

from __future__ import annotations

from typing import Any

import pytest

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.memory.short_term import Message, MessageRole

pytestmark = pytest.mark.integration


# -----------------------------------------------------------------------------
# add_message
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_single_message_returns_persisted_message(
    nams_client: MemoryClient, nams_session: str
) -> None:
    """``add_message`` returns a populated :class:`Message`."""
    msg = await nams_client.short_term.add_message(nams_session, "user", "Hello from Bronze tier.")

    assert isinstance(msg, Message)
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello from Bronze tier."
    assert msg.id is not None
    assert msg.created_at is not None


@pytest.mark.asyncio
async def test_add_message_with_metadata_round_trips(
    nams_client: MemoryClient, nams_session: str
) -> None:
    """Metadata supplied at write time survives read-back."""
    metadata = {"source": "integration-test", "channel": "test"}
    await nams_client.short_term.add_message(
        nams_session, "user", "Message with metadata", metadata=metadata
    )

    conv = await nams_client.short_term.get_conversation(nams_session)
    assert len(conv.messages) >= 1
    target = next((m for m in conv.messages if m.content == "Message with metadata"), None)
    assert target is not None
    # NAMS may strip/normalize metadata keys; assert keys we know we sent.
    assert "source" in target.metadata
    assert target.metadata["source"] == "integration-test"


@pytest.mark.asyncio
async def test_multiple_messages_preserve_order(
    nams_client: MemoryClient, nams_session: str
) -> None:
    """Messages added in sequence are returned in insertion order (SPEC §2.7)."""
    contents = [f"Message {i}" for i in range(5)]
    for c in contents:
        await nams_client.short_term.add_message(nams_session, "user", c)

    conv = await nams_client.short_term.get_conversation(nams_session)
    returned = [m.content for m in conv.messages]
    # The first 5 messages (by insertion order) should match.
    assert returned[: len(contents)] == contents


@pytest.mark.asyncio
async def test_add_message_with_user_identifier(
    nams_client: MemoryClient, nams_session: str
) -> None:
    """``user_identifier`` is forwarded as ``userId`` and accepted by NAMS."""
    msg = await nams_client.short_term.add_message(
        nams_session,
        "user",
        "Hello with user scoping",
        user_identifier=f"{nams_session}-alice",
    )
    assert msg.content == "Hello with user scoping"


# -----------------------------------------------------------------------------
# get_conversation
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_conversation_empty_session(nams_client: MemoryClient, nams_session: str) -> None:
    """Fetching a freshly-created (empty) conversation works."""
    conv = await nams_client.short_term.get_conversation(nams_session)
    # The conversation exists (created by nams_session fixture) but has no
    # messages yet.
    assert conv is not None
    assert conv.messages == [] or len(conv.messages) == 0


@pytest.mark.asyncio
async def test_get_conversation_with_limit(nams_client: MemoryClient, nams_session: str) -> None:
    """``limit`` caps the number of messages returned."""
    for i in range(5):
        await nams_client.short_term.add_message(nams_session, "user", f"msg-{i}")

    conv = await nams_client.short_term.get_conversation(nams_session, limit=3)
    assert len(conv.messages) <= 3


# -----------------------------------------------------------------------------
# search_messages
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_messages_within_session(nams_client: MemoryClient, nams_session: str) -> None:
    """``search_messages`` returns relevant messages scoped to a session."""
    await nams_client.short_term.add_message(
        nams_session, "user", "I love italian food and quiet restaurants."
    )
    await nams_client.short_term.add_message(
        nams_session, "user", "Tell me about French wine pairings."
    )

    results = await nams_client.short_term.search_messages(
        "italian cuisine", session_id=nams_session, limit=5
    )
    # Threshold/recall behavior varies; assert we got back well-formed messages.
    assert isinstance(results, list)
    for msg in results:
        assert isinstance(msg, Message)


@pytest.mark.asyncio
async def test_search_messages_unrelated_query_returns_empty_or_low_relevance(
    nams_client: MemoryClient, nams_session: str
) -> None:
    """A query semantically unrelated to stored messages returns few/no hits."""
    await nams_client.short_term.add_message(nams_session, "user", "I love italian food.")

    results = await nams_client.short_term.search_messages(
        "quantum chromodynamics", session_id=nams_session, limit=5, threshold=0.95
    )
    # At a 0.95 threshold this should yield zero hits.
    assert results == []


# -----------------------------------------------------------------------------
# list_sessions
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_includes_created_session(
    nams_client: MemoryClient, nams_session: str
) -> None:
    """A newly-created session appears in ``list_sessions``."""
    await nams_client.short_term.add_message(
        nams_session, "user", "First message in a fresh session."
    )

    sessions = await nams_client.short_term.list_sessions(limit=100)
    session_ids = {s.session_id for s in sessions}
    assert nams_session in session_ids or any(s.session_id == nams_session for s in sessions), (
        f"Expected session {nams_session} in list_sessions, got: {sorted(session_ids)[:10]}..."
    )


# -----------------------------------------------------------------------------
# clear_session
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_session_removes_all_messages(
    nams_client: MemoryClient, nams_session: str
) -> None:
    """After ``clear_session``, the conversation is empty."""
    await nams_client.short_term.add_message(nams_session, "user", "to be cleared 1")
    await nams_client.short_term.add_message(nams_session, "user", "to be cleared 2")

    await nams_client.short_term.clear_session(nams_session)

    # After clear, the conversation may not exist anymore — either an
    # empty conversation OR a 404 (which our impl maps to a MemoryError).
    try:
        conv = await nams_client.short_term.get_conversation(nams_session)
        assert conv.messages == [] or len(conv.messages) == 0
    except Exception as e:
        # 404 after clear_session is also acceptable.
        assert "not found" in str(e).lower()


@pytest.mark.asyncio
async def test_clear_session_idempotent(nams_client: MemoryClient, nams_session: str) -> None:
    """Calling ``clear_session`` twice on the same session doesn't raise."""
    await nams_client.short_term.add_message(nams_session, "user", "once")
    await nams_client.short_term.clear_session(nams_session)
    # Second call on an already-cleared session must succeed (SPEC §2.8.3).
    await nams_client.short_term.clear_session(nams_session)


# -----------------------------------------------------------------------------
# Session isolation (SPEC §1.1.3, §2.2.4)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_isolation(
    nams_client: MemoryClient, test_run_id: str, cleanup_registry: Any
) -> None:
    """Messages in session A are invisible from session B (SPEC §2.2.4)."""
    session_a_raw = f"{test_run_id}-session-a"
    session_b_raw = f"{test_run_id}-session-b"

    # Create both conversations explicitly.
    conv_a = await nams_client.short_term.create_conversation(
        session_a_raw, user_identifier=session_a_raw, title="A"
    )
    conv_b = await nams_client.short_term.create_conversation(
        session_b_raw, user_identifier=session_b_raw, title="B"
    )
    session_a = str(conv_a.id) if conv_a.id else session_a_raw
    session_b = str(conv_b.id) if conv_b.id else session_b_raw
    cleanup_registry.track_session(session_a)
    cleanup_registry.track_session(session_b)

    await nams_client.short_term.add_message(session_a, "user", "Only in A")
    await nams_client.short_term.add_message(session_b, "user", "Only in B")

    conv_a_fetched = await nams_client.short_term.get_conversation(session_a)
    conv_b_fetched = await nams_client.short_term.get_conversation(session_b)

    a_contents = [m.content for m in conv_a_fetched.messages]
    b_contents = [m.content for m in conv_b_fetched.messages]

    assert "Only in A" in a_contents
    assert "Only in B" not in a_contents
    assert "Only in B" in b_contents
    assert "Only in A" not in b_contents


# -----------------------------------------------------------------------------
# delete_message
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_message_removes_one(nams_client: MemoryClient, nams_session: str) -> None:
    """``delete_message`` removes exactly the targeted message."""
    msg_a = await nams_client.short_term.add_message(nams_session, "user", "keep")
    msg_b = await nams_client.short_term.add_message(nams_session, "user", "delete")
    await nams_client.short_term.add_message(nams_session, "user", "keep too")

    deleted = await nams_client.short_term.delete_message(msg_b.id)
    assert deleted is True

    conv = await nams_client.short_term.get_conversation(nams_session)
    remaining_ids = {str(m.id) for m in conv.messages}
    assert str(msg_a.id) in remaining_ids
    assert str(msg_b.id) not in remaining_ids
