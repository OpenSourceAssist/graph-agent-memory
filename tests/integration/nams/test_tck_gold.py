"""Live-NAMS integration tests — TCK Gold tier (cross-memory).

Covers SPEC §5 cross-memory features:
* Entity relationships and graph traversal
* Entity provenance
* Tool usage statistics
* Trace ↔ message linking
* Entity sharing across sessions (§5.1.3 / §5.5.1)
"""

from __future__ import annotations

from typing import Any

import pytest

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.memory.long_term import Entity, Relationship

pytestmark = pytest.mark.integration


# =============================================================================
# Relationships
# =============================================================================


@pytest.mark.asyncio
async def test_add_relationship_between_entities(
    nams_client: MemoryClient, unique_name: Any
) -> None:
    """``add_relationship`` succeeds with two existing entity ids."""
    e1_name = unique_name("person")
    e2_name = unique_name("org")

    e1_result = await nams_client.long_term.add_entity(e1_name, "PERSON")
    e2_result = await nams_client.long_term.add_entity(e2_name, "ORGANIZATION")

    e1 = e1_result[0] if isinstance(e1_result, tuple) else e1_result
    e2 = e2_result[0] if isinstance(e2_result, tuple) else e2_result

    # No raise = success. Some NAMS impls may not return a body.
    await nams_client.long_term.add_relationship(
        source_id=e1.id,
        relationship_type="WORKS_AT",
        target_id=e2.id,
        properties={"since": "2023"},
    )


@pytest.mark.asyncio
async def test_get_entity_relationships(nams_client: MemoryClient, unique_name: Any) -> None:
    """``get_entity_relationships`` returns a list of :class:`Relationship`."""
    e1_name = unique_name("p")
    e2_name = unique_name("o")
    e1 = await nams_client.long_term.add_entity(e1_name, "PERSON")
    e2 = await nams_client.long_term.add_entity(e2_name, "ORGANIZATION")
    e1 = e1[0] if isinstance(e1, tuple) else e1
    e2 = e2[0] if isinstance(e2, tuple) else e2

    await nams_client.long_term.add_relationship(
        source_id=e1.id, relationship_type="KNOWS", target_id=e2.id
    )

    rels = await nams_client.long_term.get_entity_relationships(e1.id)
    assert isinstance(rels, list)
    for r in rels:
        assert isinstance(r, Relationship)


@pytest.mark.asyncio
async def test_get_related_entities(nams_client: MemoryClient, unique_name: Any) -> None:
    """``get_related_entities`` returns entities reachable from a starting node."""
    a = await nams_client.long_term.add_entity(unique_name("a"), "PERSON")
    b = await nams_client.long_term.add_entity(unique_name("b"), "PERSON")
    a = a[0] if isinstance(a, tuple) else a
    b = b[0] if isinstance(b, tuple) else b

    await nams_client.long_term.add_relationship(
        source_id=a.id, relationship_type="KNOWS", target_id=b.id
    )

    related = await nams_client.long_term.get_related_entities(a.id, depth=1)
    # Result shape varies — could be list of Entity, or {entities: [...], relationships: [...]}
    assert related is not None
    if isinstance(related, list):
        for e in related:
            assert isinstance(e, Entity)


# =============================================================================
# Entity provenance
# =============================================================================


@pytest.mark.asyncio
async def test_get_entity_provenance_returns_dict(
    nams_client: MemoryClient, unique_name: Any
) -> None:
    """``get_entity_provenance`` returns a dict with provenance fields."""
    name = unique_name("prov")
    entity = await nams_client.long_term.add_entity(name, "PERSON")
    entity = entity[0] if isinstance(entity, tuple) else entity

    prov = await nams_client.long_term.get_entity_provenance(entity.id)
    assert isinstance(prov, dict)
    # Don't assert specific fields — different NAMS deployments may
    # return ``sources``/``extractors``/``messages``/etc. The smoke is
    # that the endpoint returns a parseable dict.


# =============================================================================
# Tool stats
# =============================================================================


@pytest.mark.asyncio
async def test_get_tool_stats_after_recording_calls(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``get_tool_stats`` returns aggregate stats after tool calls are recorded."""
    cleanup_registry.track_session(session_id)

    trace = await nams_client.reasoning.start_trace(session_id, "tool-stats-test")
    step = await nams_client.reasoning.add_step(trace.id, thought="invoke tool")
    await nams_client.reasoning.record_tool_call(
        step.id,
        tool_name="distinctive_tool_for_stats",
        arguments={"q": "test"},
        result={"ok": True},
        status="success",
        duration_ms=10,
    )
    await nams_client.reasoning.complete_trace(trace.id, outcome="ok", success=True)

    stats = await nams_client.reasoning.get_tool_stats()
    # NAMS returns list[ToolStats]; bolt returns dict[str, ToolStats].
    # Either is acceptable per the Protocol's ``Any`` return type.
    assert stats is not None


# =============================================================================
# Trace ↔ message linking
# =============================================================================


@pytest.mark.asyncio
async def test_link_trace_to_message(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """``link_trace_to_message`` succeeds with valid ids (no return body)."""
    cleanup_registry.track_session(session_id)

    msg = await nams_client.short_term.add_message(session_id, "user", "triggering message")
    trace = await nams_client.reasoning.start_trace(session_id, "linked-trace")

    # No raise = success.
    await nams_client.reasoning.link_trace_to_message(trace.id, msg.id)


# =============================================================================
# Entity sharing across sessions (SPEC §5.1.3, §5.5.1)
# =============================================================================


@pytest.mark.asyncio
async def test_entity_visible_across_sessions(
    nams_client: MemoryClient,
    test_run_id: str,
    cleanup_registry: Any,
    unique_name: Any,
) -> None:
    """Entities created during session A are visible from session B (SPEC §5.1.3).

    Conversations are per-session; entities live in the workspace and
    span sessions.
    """
    session_a = f"{test_run_id}-shared-a"
    session_b = f"{test_run_id}-shared-b"
    cleanup_registry.track_session(session_a)
    cleanup_registry.track_session(session_b)
    entity_name = unique_name("shared")

    # Write while "operating in" session A.
    await nams_client.short_term.add_message(session_a, "user", f"I met {entity_name} yesterday.")
    e = await nams_client.long_term.add_entity(entity_name, "PERSON")
    e = e[0] if isinstance(e, tuple) else e

    # Query from session B context.
    found = await nams_client.long_term.get_entity_by_name(entity_name)
    assert found is not None
    assert found.name == entity_name
