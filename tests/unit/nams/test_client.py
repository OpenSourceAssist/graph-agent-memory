"""Tests for nams/client.py — NamsBackend aggregator."""

from __future__ import annotations

import pytest
import respx
from pydantic import SecretStr

from neo4j_agent_memory.config.settings import NamsConfig
from neo4j_agent_memory.core.exceptions import AuthenticationError, TransportError
from neo4j_agent_memory.nams import (
    NamsBackend,
    NamsLongTermMemory,
    NamsReasoningMemory,
    NamsShortTermMemory,
    StaticApiKeyAuth,
)

# -----------------------------------------------------------------------------
# Construction
# -----------------------------------------------------------------------------


class TestFromConfig:
    def test_default_auth(self, nams_config):
        """`from_config` defaults to StaticApiKeyAuth."""
        backend = NamsBackend.from_config(nams_config)
        assert isinstance(backend.short_term, NamsShortTermMemory)
        assert isinstance(backend.long_term, NamsLongTermMemory)
        assert isinstance(backend.reasoning, NamsReasoningMemory)

    def test_custom_auth(self, nams_config):
        auth = StaticApiKeyAuth("override_key")
        backend = NamsBackend.from_config(nams_config, auth=auth)
        # Hard to verify auth identity without exposing it — just ensure no raise.
        assert backend.short_term is not None

    def test_requires_api_key(self):
        config = NamsConfig()  # no api_key
        with pytest.raises(AuthenticationError, match="API key"):
            NamsBackend.from_config(config)


# -----------------------------------------------------------------------------
# Lifecycle
# -----------------------------------------------------------------------------


class TestLifecycle:
    async def test_context_manager(self, nams_config):
        async with NamsBackend.from_config(nams_config) as backend:
            assert backend.transport.is_open
        assert not backend.transport.is_open

    async def test_close_idempotent(self, nams_config):
        backend = NamsBackend.from_config(nams_config)
        async with backend:
            pass
        await backend.close()  # second close ok


# -----------------------------------------------------------------------------
# Accessors are shared transport
# -----------------------------------------------------------------------------


class TestSharedTransport:
    def test_all_three_share_transport(self, nams_config):
        backend = NamsBackend.from_config(nams_config)
        # Each memory impl holds the same transport instance.
        st_transport = backend.short_term._transport
        lt_transport = backend.long_term._transport
        rm_transport = backend.reasoning._transport
        assert st_transport is lt_transport
        assert lt_transport is rm_transport
        assert st_transport is backend.transport


# -----------------------------------------------------------------------------
# Probe
# -----------------------------------------------------------------------------


class TestProbe:
    @respx.mock
    async def test_probe_succeeds_on_200(self, nams_config):
        respx.get("https://memory.test/v1/sessions").respond(200, json=[])
        async with NamsBackend.from_config(nams_config) as backend:
            await backend.probe()  # no raise

    @respx.mock
    async def test_probe_raises_on_401(self, nams_config):
        respx.get("https://memory.test/v1/sessions").respond(401, json={"error": "invalid key"})
        async with NamsBackend.from_config(nams_config) as backend:
            with pytest.raises(AuthenticationError):
                await backend.probe()

    @respx.mock
    async def test_probe_raises_on_403(self, nams_config):
        respx.get("https://memory.test/v1/sessions").respond(403, json={"error": "forbidden"})
        async with NamsBackend.from_config(nams_config) as backend:
            with pytest.raises(AuthenticationError):
                await backend.probe()

    @respx.mock
    async def test_probe_raises_on_network_failure(self, nams_config):
        import httpx

        respx.get("https://memory.test/v1/sessions").mock(
            side_effect=httpx.ConnectError("net down")
        )
        async with NamsBackend.from_config(nams_config) as backend:
            with pytest.raises(TransportError):
                await backend.probe()

    @respx.mock
    async def test_probe_uses_limit_1(self, nams_config):
        route = respx.get("https://memory.test/v1/sessions").respond(200, json=[])
        async with NamsBackend.from_config(nams_config) as backend:
            await backend.probe()
        assert route.calls[0].request.url.params["limit"] == "1"


# -----------------------------------------------------------------------------
# Bridge mode
# -----------------------------------------------------------------------------


class TestBridgeMode:
    @respx.mock
    async def test_probe_in_bridge_mode(self, bridge_config):
        route = respx.post("https://memory.test/list_sessions").respond(200, json=[])
        async with NamsBackend.from_config(bridge_config) as backend:
            await backend.probe()
        assert route.called


# -----------------------------------------------------------------------------
# End-to-end smoke (sanity check that all three layers are wired)
# -----------------------------------------------------------------------------


class TestSmokeEnd2End:
    @respx.mock
    async def test_all_three_layers_reach_their_endpoints(self, nams_config):
        respx.post("https://memory.test/v1/conversations/s1/messages").respond(
            200,
            json={
                "id": "00000000-0000-0000-0000-000000000001",
                "role": "user",
                "content": "hi",
                "created_at": "2026-05-17T12:00:00Z",
                "metadata": {},
            },
        )
        respx.post("https://memory.test/v1/entities").respond(
            200,
            json={
                "id": "00000000-0000-0000-0000-000000000002",
                "name": "Alice",
                "type": "PERSON",
                "created_at": "2026-05-17T12:00:00Z",
                "metadata": {},
                "aliases": [],
                "attributes": {},
                "confidence": 1.0,
            },
        )
        respx.post("https://memory.test/v1/traces").respond(
            200,
            json={
                "id": "00000000-0000-0000-0000-000000000003",
                "session_id": "s1",
                "task": "task",
                "steps": [],
                "started_at": "2026-05-17T12:00:00Z",
                "created_at": "2026-05-17T12:00:00Z",
                "metadata": {},
            },
        )

        async with NamsBackend.from_config(nams_config) as backend:
            msg = await backend.short_term.add_message("s1", "user", "hi")
            entity = await backend.long_term.add_entity("Alice", "PERSON")
            trace = await backend.reasoning.start_trace("s1", "task")

        assert msg.content == "hi"
        assert entity.name == "Alice"
        assert trace.task == "task"


# Avoid unused-imports warning for the fixture-injected SecretStr.
_ = SecretStr
