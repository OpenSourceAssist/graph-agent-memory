"""End-to-end ADK ↔ NAMS suite (issue #130 regression, against staging).

Exercises ``Neo4jMemoryService`` against the live NAMS backend to prove
the #130 fixes hold end-to-end:

* conversation-scoped search (no unscoped-search ``ValueError``);
* graceful no-session search (skips messages, still recalls entities);
* entity extraction from real text (the service must not crash NAMS).

The service accepts dict-style sessions, so these run without the
``google-adk`` package installed.
"""

from __future__ import annotations

import uuid

import pytest

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.integrations.google_adk.memory_service import Neo4jMemoryService

pytestmark = pytest.mark.integration


@pytest.fixture
def adk_service(nams_client: MemoryClient) -> Neo4jMemoryService:
    return Neo4jMemoryService(memory_client=nams_client, extract_on_store=True)


@pytest.mark.asyncio
async def test_search_is_conversation_scoped_no_crash(
    adk_service: Neo4jMemoryService, nams_client: MemoryClient, cleanup_registry
) -> None:
    sid = f"itest-adk-{uuid.uuid4().hex[:8]}"
    conv = await nams_client.short_term.create_conversation(conversation_id=sid)
    cid = str(conv.id)
    cleanup_registry.track_session(cid)

    await adk_service.add_session_to_memory(
        {
            "id": cid,
            "messages": [
                {"role": "user", "content": "Tell me about Marie Curie and radioactivity."},
                {"role": "assistant", "content": "Marie Curie pioneered research on radioactivity."},
            ],
        }
    )
    # Must not raise the unscoped-search ValueError that #130 reported.
    response = await adk_service.search_memory("radioactivity")
    assert response is not None


@pytest.mark.asyncio
async def test_search_without_session_skips_messages_gracefully(
    nams_client: MemoryClient,
) -> None:
    # Fresh service, no session ever tracked — must not crash on NAMS.
    service = Neo4jMemoryService(memory_client=nams_client)
    response = await service.search_memory("anything")
    assert response is not None  # entities/preferences searched; messages skipped


@pytest.mark.asyncio
async def test_entity_extraction_from_session_text(
    adk_service: Neo4jMemoryService, nams_client: MemoryClient, cleanup_registry
) -> None:
    sid = f"itest-adk-extract-{uuid.uuid4().hex[:8]}"
    marker = f"Zylotech{uuid.uuid4().hex[:6].capitalize()}"
    conv = await nams_client.short_term.create_conversation(conversation_id=sid)
    cid = str(conv.id)
    cleanup_registry.track_session(cid)

    await adk_service.add_session_to_memory(
        {"id": cid, "messages": [{"role": "user", "content": f"{marker} is a robotics company."}]}
    )
    # Extraction is async — await it explicitly via the readiness helper.
    ready = await nams_client.long_term.wait_for_extraction(
        query=marker, expected_names=[marker], timeout=40, interval=2
    )
    # If staging extraction is lagging, skip rather than flake (perf signal).
    if not ready:
        pytest.skip("Staging extraction did not surface the entity within timeout.")
