"""Live-NAMS integration smoke — one happy path through all three memory types.

If this fails, something is fundamentally wrong with the v0.4 client.
The TCK tier suites (``test_tck_bronze.py`` onwards) exercise each method
individually for diagnostic value; this file is the single overall
"does anything work at all" smoke.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from neo4j_agent_memory import MemoryClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_smoke_full_flow(
    nams_client: MemoryClient, session_id: str, cleanup_registry: Any
) -> None:
    """Connect → short-term + long-term + reasoning + cypher → cleanup."""
    cleanup_registry.track_session(session_id)

    # Short-term
    msg = await nams_client.short_term.add_message(session_id, "user", "Smoke test hello")
    assert msg.content == "Smoke test hello"

    conv = await nams_client.short_term.get_conversation(session_id)
    assert len(conv.messages) >= 1

    # Long-term
    entity_name = f"SmokeTest-{uuid.uuid4().hex[:8]}"
    entity = await nams_client.long_term.add_entity(entity_name, "PERSON")
    entity = entity[0] if isinstance(entity, tuple) else entity
    assert entity.name == entity_name

    # Reasoning
    trace = await nams_client.reasoning.start_trace(session_id, "smoke task")
    await nams_client.reasoning.complete_trace(trace.id, outcome="ok", success=True)

    # Cypher
    rows = await nams_client.query.cypher("MATCH (n) RETURN count(n) AS n LIMIT 1")
    assert isinstance(rows, list)
