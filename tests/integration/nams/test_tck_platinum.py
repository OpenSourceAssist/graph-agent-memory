"""Live-NAMS integration tests — TCK Platinum tier (hosted-only operations).

Covers Volume 5 of the SPEC — operations that exist only on the hosted
NAMS service (no bolt equivalent):

* Conversation lifecycle (``create_conversation``, ``list_conversations``)
* ``bulk_add_messages``
* Observations / reflections (``get_observations``, ``get_reflections``)
* Entity feedback + history (``set_entity_feedback``, ``get_entity_history``)
* Read-only Cypher console (``client.query.cypher``)
"""

from __future__ import annotations

from typing import Any

import pytest

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.memory.short_term import Conversation, Message

pytestmark = pytest.mark.integration


# =============================================================================
# Conversation lifecycle
# =============================================================================


@pytest.mark.asyncio
async def test_create_conversation(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``create_conversation`` returns a :class:`Conversation`."""
    cleanup_registry.track_session(session_id)

    conv = await nams_client.short_term.create_conversation(
        session_id, title="Integration test conversation"
    )
    assert isinstance(conv, Conversation)
    assert conv.session_id == session_id


@pytest.mark.asyncio
async def test_list_conversations(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``list_conversations`` includes a freshly created conversation."""
    cleanup_registry.track_session(session_id)

    await nams_client.short_term.create_conversation(session_id, title="listme")

    convs = await nams_client.short_term.list_conversations(limit=100)
    assert isinstance(convs, list)
    session_ids = {c.session_id for c in convs}
    assert session_id in session_ids


# =============================================================================
# bulk_add_messages
# =============================================================================


@pytest.mark.asyncio
async def test_bulk_add_messages(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``bulk_add_messages`` inserts multiple messages in one round-trip."""
    cleanup_registry.track_session(session_id)

    batch = [
        {"role": "user", "content": "bulk msg 1"},
        {"role": "assistant", "content": "bulk msg 2"},
        {"role": "user", "content": "bulk msg 3"},
    ]
    results = await nams_client.short_term.bulk_add_messages(session_id, batch)
    assert isinstance(results, list)
    assert len(results) == 3
    for m in results:
        assert isinstance(m, Message)

    # Verify they persisted.
    conv = await nams_client.short_term.get_conversation(session_id)
    contents = [m.content for m in conv.messages]
    assert "bulk msg 1" in contents
    assert "bulk msg 3" in contents


# =============================================================================
# Observations + reflections
# =============================================================================


@pytest.mark.asyncio
async def test_get_observations_returns_list(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``get_observations`` returns a list (possibly empty for a new session)."""
    cleanup_registry.track_session(session_id)
    await nams_client.short_term.add_message(
        session_id, "user", "Going to Paris next week for a wedding."
    )

    observations = await nams_client.short_term.get_observations(session_id, limit=20)
    assert isinstance(observations, list)
    # Don't assert content — observations may be async-generated.


@pytest.mark.asyncio
async def test_get_reflections_returns_list(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``get_reflections`` returns a list (possibly empty for a new session)."""
    cleanup_registry.track_session(session_id)
    await nams_client.short_term.add_message(
        session_id, "user", "I prefer ethical sourcing for everything I buy."
    )

    reflections = await nams_client.short_term.get_reflections(session_id, limit=10)
    assert isinstance(reflections, list)


# =============================================================================
# Entity feedback + history
# =============================================================================


@pytest.mark.asyncio
async def test_set_entity_feedback(nams_client: MemoryClient, unique_name: Any) -> None:
    """``set_entity_feedback`` succeeds without raising for valid input."""
    name = unique_name("feedback-target")
    entity = await nams_client.long_term.add_entity(name, "PERSON")
    entity = entity[0] if isinstance(entity, tuple) else entity

    # No raise = success — Platinum method on NAMS.
    await nams_client.long_term.set_entity_feedback(
        entity.id, "positive", user_identifier="test-user"
    )


@pytest.mark.asyncio
async def test_get_entity_history(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any, unique_name: Any
) -> None:
    """``get_entity_history`` returns a list (possibly empty for a new entity)."""
    cleanup_registry.track_session(session_id)
    name = unique_name("history-target")
    entity = await nams_client.long_term.add_entity(name, "PERSON")
    entity = entity[0] if isinstance(entity, tuple) else entity
    # Mention the entity in a message — should bump history.
    await nams_client.short_term.add_message(session_id, "user", f"Let me tell you about {name}.")

    history = await nams_client.long_term.get_entity_history(entity.id, limit=20)
    assert isinstance(history, list)


# =============================================================================
# Cypher query
# =============================================================================


@pytest.mark.asyncio
async def test_cypher_basic_read(nams_client: MemoryClient) -> None:
    """``client.query.cypher`` runs a basic read query."""
    rows = await nams_client.query.cypher("MATCH (n) RETURN count(n) AS total LIMIT 1")
    assert isinstance(rows, list)
    # Single-row aggregation should yield one row.
    if rows:
        assert "total" in rows[0]


@pytest.mark.asyncio
async def test_cypher_with_params(nams_client: MemoryClient, unique_name: Any) -> None:
    """``client.query.cypher`` correctly substitutes parameters."""
    name = unique_name("cyparams")
    await nams_client.long_term.add_entity(name, "PERSON")

    rows = await nams_client.query.cypher(
        "MATCH (e:Entity {name: $name}) RETURN e.name AS name LIMIT 1",
        {"name": name},
    )
    assert isinstance(rows, list)
    if rows:
        assert rows[0]["name"] == name


@pytest.mark.asyncio
async def test_cypher_rejects_writes_client_side(nams_client: MemoryClient) -> None:
    """Write Cypher is rejected client-side without any HTTP round-trip."""
    with pytest.raises(ValueError, match="read-only"):
        await nams_client.query.cypher("CREATE (n:Test) RETURN n")

    with pytest.raises(ValueError, match="read-only"):
        await nams_client.query.cypher("MATCH (n) DELETE n")

    with pytest.raises(ValueError, match="read-only"):
        await nams_client.query.cypher("MATCH (n) SET n.x = 1")
