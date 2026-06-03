"""Unit tests for nams/auth_keys.py — the client.auth API-key accessor."""

from __future__ import annotations

import json

import pytest
import respx

from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.nams import HttpTransport, StaticApiKeyAuth
from neo4j_agent_memory.nams._unsupported import _NamsUnsupported
from neo4j_agent_memory.nams.auth_keys import AccessTokenPair, ApiKey, NamsAuth

BASE = "https://memory.test/v1"

KEY = {
    "id": "key_1",
    "label": "ci",
    "scopes": ["memory:read", "memory:write"],
    "workspace_id": "ws_1",
    "created_at": "2026-05-30T00:00:00Z",
}


@pytest.fixture
async def transport(nams_config):
    auth = StaticApiKeyAuth.from_config(nams_config)
    async with HttpTransport.from_config(nams_config, auth=auth) as t:
        yield t


@pytest.fixture
def auth(transport) -> NamsAuth:
    return NamsAuth(transport)


@respx.mock
async def test_list_api_keys_accepts_envelope_and_query(auth):
    route = respx.get(f"{BASE}/auth/api-keys").respond(200, json={"keys": [KEY]})
    keys = await auth.list_api_keys("ws_1")
    assert dict(route.calls.last.request.url.params) == {"workspace_id": "ws_1"}
    assert len(keys) == 1
    assert isinstance(keys[0], ApiKey)
    assert keys[0].scopes == ["memory:read", "memory:write"]
    assert keys[0].key is None  # no plaintext on list


@respx.mock
async def test_list_api_keys_bare_list(auth):
    respx.get(f"{BASE}/auth/api-keys").respond(200, json=[KEY])
    keys = await auth.list_api_keys("ws_1")
    assert keys[0].id == "key_1"


@respx.mock
async def test_create_returns_plaintext_once(auth):
    route = respx.post(f"{BASE}/auth/api-keys").respond(
        201, json={**KEY, "key": "nams_secret_plaintext"}
    )
    key = await auth.create_api_key("ci", scopes=["memory:read"], workspace_id="ws_1")
    body = json.loads(route.calls.last.request.content)
    assert body == {"label": "ci", "scopes": ["memory:read"], "workspace_id": "ws_1"}
    assert key.key == "nams_secret_plaintext"


@respx.mock
async def test_reveal_sends_path_and_query(auth):
    route = respx.get(f"{BASE}/auth/api-keys/key_1/reveal").respond(
        200, json={**KEY, "key": "nams_revealed"}
    )
    key = await auth.reveal_api_key("key_1", "ws_1")
    assert dict(route.calls.last.request.url.params) == {"workspace_id": "ws_1"}
    assert key.key == "nams_revealed"


@respx.mock
async def test_rotate_posts_to_rotate_path(auth):
    route = respx.post(f"{BASE}/auth/api-keys/key_1/rotate").respond(
        200, json={**KEY, "id": "key_2", "key": "nams_rotated"}
    )
    key = await auth.rotate_api_key("key_1")
    assert route.called
    assert key.id == "key_2"
    assert key.key == "nams_rotated"


@respx.mock
async def test_revoke_deletes(auth):
    route = respx.delete(f"{BASE}/auth/api-keys/key_1").respond(204)
    await auth.revoke_api_key("key_1")
    assert route.called


@respx.mock
async def test_refresh_access_token(auth):
    respx.post(f"{BASE}/auth/refresh").respond(
        200, json={"access_token": "a", "refresh_token": "r", "expires_in": 3600}
    )
    pair = await auth.refresh_access_token("old-refresh")
    assert isinstance(pair, AccessTokenPair)
    assert pair.access_token == "a"
    assert pair.expires_in == 3600


async def test_bolt_sentinel_raises():
    sentinel = _NamsUnsupported(
        accessor="auth",
        message="API-key management is a NAMS capability.",
        workaround="dashboard",
    )
    with pytest.raises(NotSupportedError, match="auth"):
        await sentinel.list_api_keys("ws_1")
