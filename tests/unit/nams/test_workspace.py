"""Unit tests for NAMS workspace addressing (X-Workspace-Id).

Covers the A.1 surface:

* ``NamsConfig.workspace_id`` → ``X-Workspace-Id`` header on every request.
* Header resolution precedence: an explicit ``headers`` entry wins over
  ``workspace_id``.
* No header sent when neither is configured (the production / key-encoded
  path).
* ``MEMORY_WORKSPACE_ID`` env alias is lifted into ``nams.workspace_id`` by
  ``MemorySettings`` (gap-fill only — explicit config wins).
"""

from __future__ import annotations

import httpx
import pytest
import respx
from pydantic import SecretStr

from neo4j_agent_memory import MemorySettings
from neo4j_agent_memory.config.settings import NamsConfig
from neo4j_agent_memory.nams import EndpointSpec, HttpTransport, StaticApiKeyAuth

REST_ENDPOINT = "https://memory.test/v1"
PING_SPEC = EndpointSpec(rest_method="GET", rest_path="/ping", bridge_method="ping")
WS = "ws-1234"


def _transport(config: NamsConfig) -> HttpTransport:
    return HttpTransport.from_config(config, auth=StaticApiKeyAuth.from_config(config))


async def _captured_request(config: NamsConfig) -> httpx.Request:
    """Fire one request through the transport and return the sent httpx.Request."""
    with respx.mock:
        route = respx.get(f"{REST_ENDPOINT}/ping").respond(200, json={})
        async with _transport(config) as t:
            await t.request(PING_SPEC)
        return route.calls.last.request


@pytest.mark.asyncio
async def test_workspace_id_sets_header() -> None:
    config = NamsConfig(
        endpoint=REST_ENDPOINT, api_key=SecretStr("k"), workspace_id=WS,
        validate_on_connect=False,
    )
    req = await _captured_request(config)
    assert req.headers["X-Workspace-Id"] == WS


@pytest.mark.asyncio
async def test_no_workspace_no_header() -> None:
    config = NamsConfig(endpoint=REST_ENDPOINT, api_key=SecretStr("k"), validate_on_connect=False)
    req = await _captured_request(config)
    assert "X-Workspace-Id" not in req.headers


@pytest.mark.asyncio
async def test_explicit_header_overrides_workspace_id() -> None:
    config = NamsConfig(
        endpoint=REST_ENDPOINT, api_key=SecretStr("k"),
        workspace_id=WS, headers={"X-Workspace-Id": "explicit-override"},
        validate_on_connect=False,
    )
    req = await _captured_request(config)
    assert req.headers["X-Workspace-Id"] == "explicit-override"


def test_env_workspace_lifted_into_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_API_KEY", "nams_envkey")
    monkeypatch.setenv("MEMORY_WORKSPACE_ID", WS)
    monkeypatch.delenv("MEMORY_ENDPOINT", raising=False)
    settings = MemorySettings()
    assert settings.backend == "nams"
    assert settings.nams.workspace_id == WS


def test_explicit_config_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_API_KEY", "nams_envkey")
    monkeypatch.setenv("MEMORY_WORKSPACE_ID", "env-ws")
    settings = MemorySettings(
        backend="nams",
        nams=NamsConfig(api_key=SecretStr("k"), workspace_id="explicit-ws"),
    )
    assert settings.nams.workspace_id == "explicit-ws"
