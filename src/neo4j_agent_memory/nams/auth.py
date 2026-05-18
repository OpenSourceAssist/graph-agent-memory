"""Authentication providers for the NAMS HTTP transport.

The :class:`AuthProvider` Protocol decouples credential acquisition from
the transport. The shipped :class:`StaticApiKeyAuth` reads a long-lived
API key from :class:`NamsConfig` (which itself supports env fallback via
``MEMORY_API_KEY``). Future OAuth/JWT/refresh providers slot in by
implementing the same Protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from neo4j_agent_memory.config.settings import NamsConfig
from neo4j_agent_memory.core.exceptions import AuthenticationError


@runtime_checkable
class AuthProvider(Protocol):
    """Pluggable auth Protocol.

    The single :meth:`apply` method mutates (and returns) a header dict
    before each NAMS request. Async by design — refresh-token providers
    need it; static providers ignore it.
    """

    async def apply(self, headers: dict[str, str]) -> dict[str, str]:
        """Add auth headers and return the (mutated) dict."""
        ...


class StaticApiKeyAuth:
    """API key auth: sends ``Authorization: Bearer {api_key}``.

    Construct directly or via :meth:`from_config`. The latter is the
    canonical path from :class:`NamsConfig`; it raises
    :class:`AuthenticationError` at startup time if no key was supplied
    (rather than letting NAMS return 401 on the first request).
    """

    __slots__ = ("_api_key",)

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise AuthenticationError(
                "Empty API key. Set MEMORY_API_KEY in the environment or pass "
                "api_key=SecretStr(...) on NamsConfig."
            )
        self._api_key = api_key

    @classmethod
    def from_config(cls, config: NamsConfig) -> StaticApiKeyAuth:
        """Build from :class:`NamsConfig`. Raises if no API key is configured.

        :class:`NamsConfig.api_key` is normally populated either explicitly
        or from ``MEMORY_API_KEY`` env (lifted by the
        ``MemorySettings._resolve_backend`` validator).
        """
        if config.api_key is None:
            raise AuthenticationError(
                "NAMS backend requires an API key. Set MEMORY_API_KEY in the "
                "environment or pass NamsConfig(api_key=SecretStr(...))."
            )
        return cls(config.api_key.get_secret_value())

    async def apply(self, headers: dict[str, str]) -> dict[str, str]:
        headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def __repr__(self) -> str:
        # Never leak the key, even in logs/tracebacks.
        return "StaticApiKeyAuth(api_key=***)"


__all__ = ["AuthProvider", "StaticApiKeyAuth"]
