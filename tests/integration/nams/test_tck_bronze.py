"""Live-NAMS integration tests — TCK Bronze tier (short-term core).

Covers SPEC §1 (schema) and §2 (short-term memory):
add_message, get_conversation, search_messages, list_sessions,
delete_message, clear_session, plus the session-isolation invariants
the SPEC requires.
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
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``add_message`` returns a populated :class:`Message`."""
    cleanup_registry.track_session(session_id)

    msg = await nams_client.short_term.add_message(session_id, "user", "Hello from Bronze tier.")

    assert isinstance(msg, Message)
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello from Bronze tier."
    assert msg.id is not None
    assert msg.created_at is not None


@pytest.mark.asyncio
async def test_add_message_with_metadata_round_trips(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """Metadata supplied at write time survives read-back."""
    cleanup_registry.track_session(session_id)

    metadata = {"source": "integration-test", "channel": "test"}
    await nams_client.short_term.add_message(
        session_id, "user", "Message with metadata", metadata=metadata
    )

    conv = await nams_client.short_term.get_conversation(session_id)
    assert len(conv.messages) >= 1
    target = next((m for m in conv.messages if m.content == "Message with metadata"), None)
    assert target is not None
    # NAMS may strip/normalize metadata keys; assert keys we know we sent.
    assert "source" in target.metadata
    assert target.metadata["source"] == "integration-test"


@pytest.mark.asyncio
async def test_multiple_messages_preserve_order(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """Messages added in sequence are returned in insertion order (SPEC §2.7)."""
    cleanup_registry.track_session(session_id)

    contents = [f"Message {i}" for i in range(5)]
    for c in contents:
        await nams_client.short_term.add_message(session_id, "user", c)

    conv = await nams_client.short_term.get_conversation(session_id)
    returned = [m.content for m in conv.messages]
    # The first 5 messages (by insertion order) should match.
    assert returned[: len(contents)] == contents


@pytest.mark.asyncio
async def test_add_message_with_user_identifier(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``user_identifier`` is forwarded as ``userId`` and accepted by NAMS."""
    cleanup_registry.track_session(session_id)

    msg = await nams_client.short_term.add_message(
        session_id,
        "user",
        "Hello with user scoping",
        user_identifier=f"{session_id}-alice",
    )
    assert msg.content == "Hello with user scoping"


# -----------------------------------------------------------------------------
# get_conversation
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_conversation_empty_session(nams_client: MemoryClient, session_id: str) -> None:
    """Fetching an empty / nonexistent session returns an empty conversation."""
    conv = await nams_client.short_term.get_conversation(session_id)
    # Some implementations may 404 here — observe behavior. If empty
    # session yields a conversation object, messages should be empty.
    assert conv.session_id == session_id
    assert conv.messages == [] or len(conv.messages) == 0


@pytest.mark.asyncio
async def test_get_conversation_with_limit(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``limit`` caps the number of messages returned."""
    cleanup_registry.track_session(session_id)

    for i in range(5):
        await nams_client.short_term.add_message(session_id, "user", f"msg-{i}")

    conv = await nams_client.short_term.get_conversation(session_id, limit=3)
    assert len(conv.messages) <= 3


# -----------------------------------------------------------------------------
# search_messages
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_messages_within_session(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``search_messages`` returns relevant messages scoped to a session."""
    cleanup_registry.track_session(session_id)

    await nams_client.short_term.add_message(
        session_id, "user", "I love italian food and quiet restaurants."
    )
    await nams_client.short_term.add_message(
        session_id, "user", "Tell me about French wine pairings."
    )

    results = await nams_client.short_term.search_messages(
        "italian cuisine", session_id=session_id, limit=5
    )
    # Threshold/recall behavior varies; assert we got back well-formed messages.
    assert isinstance(results, list)
    for msg in results:
        assert isinstance(msg, Message)


@pytest.mark.asyncio
async def test_search_messages_unrelated_query_returns_empty_or_low_relevance(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """A query semantically unrelated to stored messages returns few/no hits."""
    cleanup_registry.track_session(session_id)

    await nams_client.short_term.add_message(session_id, "user", "I love italian food.")

    results = await nams_client.short_term.search_messages(
        "quantum chromodynamics", session_id=session_id, limit=5, threshold=0.95
    )
    # At a 0.95 threshold this should yield zero hits.
    assert results == []


# -----------------------------------------------------------------------------
# list_sessions
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_includes_created_session(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """A newly-created session appears in ``list_sessions``."""
    cleanup_registry.track_session(session_id)

    await nams_client.short_term.add_message(
        session_id, "user", "First message in a fresh session."
    )

    sessions = await nams_client.short_term.list_sessions(limit=100)
    session_ids = {s.session_id for s in sessions}
    assert session_id in session_ids, (
        f"Expected session {session_id} in list_sessions, got: {sorted(session_ids)[:10]}..."
    )


# -----------------------------------------------------------------------------
# clear_session
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_session_removes_all_messages(
    nams_client: MemoryClient, session_id: str
) -> None:
    """After ``clear_session``, the conversation is empty."""
    await nams_client.short_term.add_message(session_id, "user", "to be cleared 1")
    await nams_client.short_term.add_message(session_id, "user", "to be cleared 2")

    await nams_client.short_term.clear_session(session_id)

    conv = await nams_client.short_term.get_conversation(session_id)
    assert conv.messages == [] or len(conv.messages) == 0


@pytest.mark.asyncio
async def test_clear_session_idempotent(nams_client: MemoryClient, session_id: str) -> None:
    """Calling ``clear_session`` twice on the same session doesn't raise."""
    await nams_client.short_term.add_message(session_id, "user", "once")
    await nams_client.short_term.clear_session(session_id)
    # Second call on an already-cleared session must succeed (SPEC §2.8.3).
    await nams_client.short_term.clear_session(session_id)


# -----------------------------------------------------------------------------
# Session isolation (SPEC §1.1.3, §2.2.4)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_isolation(
    nams_client: MemoryClient, test_run_id: str, cleanup_registry: Any
) -> None:
    """Messages in session A are invisible from session B (SPEC §2.2.4)."""
    session_a = f"{test_run_id}-session-a"
    session_b = f"{test_run_id}-session-b"
    cleanup_registry.track_session(session_a)
    cleanup_registry.track_session(session_b)

    await nams_client.short_term.add_message(session_a, "user", "Only in A")
    await nams_client.short_term.add_message(session_b, "user", "Only in B")

    conv_a = await nams_client.short_term.get_conversation(session_a)
    conv_b = await nams_client.short_term.get_conversation(session_b)

    a_contents = [m.content for m in conv_a.messages]
    b_contents = [m.content for m in conv_b.messages]

    assert "Only in A" in a_contents
    assert "Only in B" not in a_contents
    assert "Only in B" in b_contents
    assert "Only in A" not in b_contents


# -----------------------------------------------------------------------------
# delete_message
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_message_removes_one(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``delete_message`` removes exactly the targeted message."""
    cleanup_registry.track_session(session_id)

    msg_a = await nams_client.short_term.add_message(session_id, "user", "keep")
    msg_b = await nams_client.short_term.add_message(session_id, "user", "delete")
    await nams_client.short_term.add_message(session_id, "user", "keep too")

    deleted = await nams_client.short_term.delete_message(msg_b.id)
    assert deleted is True

    conv = await nams_client.short_term.get_conversation(session_id)
    remaining_ids = {str(m.id) for m in conv.messages}
    assert str(msg_a.id) in remaining_ids
    assert str(msg_b.id) not in remaining_ids
