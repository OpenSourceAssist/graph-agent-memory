"""NAMS API-key management — the ``client.auth`` accessor (hosted only).

Mirrors the TypeScript ``AuthClient``: create / list / reveal / rotate / revoke
``nams_*`` API keys, plus the OAuth refresh-token exchange. API keys are
user-owned; each call is scoped to a workspace via the API key (or the
``X-Workspace-Id`` header). The raw key value is returned only at creation and
via :meth:`reveal_api_key`.

This is distinct from :mod:`neo4j_agent_memory.nams.auth`, which signs outgoing
requests (``StaticApiKeyAuth``); this module *manages* keys over REST::

    GET    /auth/api-keys                 → list (no plaintext)
    POST   /auth/api-keys                 → create (plaintext returned once)
    GET    /auth/api-keys/{id}/reveal      → reveal (owner-only)
    POST   /auth/api-keys/{id}/rotate      → rotate (mint new, revoke old)
    DELETE /auth/api-keys/{id}             → revoke
    POST   /auth/refresh                   → refresh access token (JWT clients)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ApiKey(_Lenient):
    """An API key record. ``key`` (plaintext) is set only on create/reveal."""

    id: str
    label: str | None = None
    scopes: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    created_at: str | None = None
    expires_at: str | None = None
    key: str | None = None


class AccessTokenPair(_Lenient):
    """An access/refresh JWT pair from the OAuth refresh exchange."""

    access_token: str
    refresh_token: str
    expires_in: int | None = None


_SPEC_LIST = EndpointSpec(
    rest_method="GET", rest_path="/auth/api-keys", bridge_method="list_api_keys"
)
_SPEC_CREATE = EndpointSpec(
    rest_method="POST", rest_path="/auth/api-keys", bridge_method="create_api_key"
)
_SPEC_REVEAL = EndpointSpec(
    rest_method="GET",
    rest_path="/auth/api-keys/{key_id}/reveal",
    bridge_method="reveal_api_key",
)
_SPEC_ROTATE = EndpointSpec(
    rest_method="POST",
    rest_path="/auth/api-keys/{key_id}/rotate",
    bridge_method="rotate_api_key",
)
_SPEC_REVOKE = EndpointSpec(
    rest_method="DELETE",
    rest_path="/auth/api-keys/{key_id}",
    bridge_method="revoke_api_key",
)
_SPEC_REFRESH = EndpointSpec(
    rest_method="POST", rest_path="/auth/refresh", bridge_method="refresh_access_token"
)


def _coerce_keys(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("keys") or payload.get("api_keys") or []
    else:
        items = payload or []
    return [k for k in items if isinstance(k, dict)]


class NamsAuth:
    """``client.auth`` — API-key lifecycle for the hosted NAMS backend.

    The raw key value is shown only once (on :meth:`create_api_key`) and again
    via :meth:`reveal_api_key` (owner-only). Store it in a secrets manager;
    never commit it. See xref docs: Authentication & API Keys.
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    async def list_api_keys(self, workspace_id: str) -> list[ApiKey]:
        """List a workspace's API keys (metadata only — no plaintext)."""
        payload = await self._transport.request(
            _SPEC_LIST, params={"workspace_id": workspace_id}
        )
        return [ApiKey.model_validate(k) for k in _coerce_keys(payload)]

    async def create_api_key(
        self,
        label: str,
        *,
        scopes: list[str] | None = None,
        workspace_id: str | None = None,
    ) -> ApiKey:
        """Create a new API key. The plaintext ``.key`` is returned **once**."""
        body: dict[str, Any] = {"label": label}
        if scopes is not None:
            body["scopes"] = scopes
        if workspace_id is not None:
            body["workspace_id"] = workspace_id
        payload = await self._transport.request(_SPEC_CREATE, json=body)
        return ApiKey.model_validate(payload or {})

    async def reveal_api_key(self, key_id: str, workspace_id: str) -> ApiKey:
        """Reveal a stored key's plaintext value (owner-only)."""
        payload = await self._transport.request(
            _SPEC_REVEAL,
            path_params={"key_id": key_id},
            params={"workspace_id": workspace_id},
        )
        return ApiKey.model_validate(payload or {})

    async def rotate_api_key(self, key_id: str) -> ApiKey:
        """Rotate a key: mint a replacement and revoke the old one.

        The new plaintext ``.key`` is returned once.
        """
        payload = await self._transport.request(_SPEC_ROTATE, path_params={"key_id": key_id})
        return ApiKey.model_validate(payload or {})

    async def revoke_api_key(self, key_id: str) -> None:
        """Revoke (delete) an API key. Effective on the next request."""
        await self._transport.request(_SPEC_REVOKE, path_params={"key_id": key_id})

    async def refresh_access_token(self, refresh_token: str) -> AccessTokenPair:
        """Exchange a refresh token for a fresh access/refresh JWT pair."""
        payload = await self._transport.request(
            _SPEC_REFRESH, json={"refresh_token": refresh_token}
        )
        return AccessTokenPair.model_validate(payload or {})


__all__ = ["NamsAuth", "ApiKey", "AccessTokenPair"]
