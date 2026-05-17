"""End-to-end NAMS smoke test against a real sandbox or TCK reference impl.

Skips cleanly when neither is reachable.
"""

from __future__ import annotations

import uuid

import pytest

from neo4j_agent_memory import MemoryClient, MemorySettings


@pytest.mark.integration
@pytest.mark.asyncio
async def test_smoke_full_flow(nams_config) -> None:
    """Connect, store short-term + long-term + reasoning, read it back."""
    settings = MemorySettings(backend="nams", nams=nams_config)
    session_id = f"nams-smoke-{uuid.uuid4().hex[:8]}"

    async with MemoryClient(settings) as client:
        # Probe
        await client._nams_backend.probe()  # type: ignore[union-attr]

        # Short-term
        msg = await client.short_term.add_message(session_id, "user", "Hello, NAMS!")
        assert msg.content == "Hello, NAMS!"

        conv = await client.short_term.get_conversation(session_id)
        assert len(conv.messages) >= 1

        # Long-term
        entity = await client.long_term.add_entity(f"SmokeTest-{uuid.uuid4().hex[:6]}", "PERSON")
        assert entity.name.startswith("SmokeTest-")

        # Reasoning
        trace = await client.reasoning.start_trace(session_id, "smoke test task")
        await client.reasoning.complete_trace(trace.id, outcome="ok", success=True)

        # Cleanup
        await client.short_term.clear_session(session_id)
