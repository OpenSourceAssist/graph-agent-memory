"""NAMS backend aggregator — composition root for the HTTP-backed impls.

A :class:`NamsBackend` owns one :class:`HttpTransport` and the three
memory-layer implementations that share it. :class:`MemoryClient` builds
one of these in :meth:`connect` when ``settings.backend == "nams"``
(Phase 5 wiring).

Decoupling rationale: keeping construction here (not in
:class:`MemoryClient`) means Phase 5 only needs to call
``NamsBackend.from_config(settings.nams)`` and bind the accessors — the
top-level client doesn't need to know about HTTP details.

The Phase 4 follow-up adds :attr:`query` (``NamsCypherQuery``) to this
class.
"""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

from neo4j_agent_memory.config.settings import NamsConfig
from neo4j_agent_memory.nams.auth import AuthProvider, StaticApiKeyAuth
from neo4j_agent_memory.nams.long_term import NamsLongTermMemory
from neo4j_agent_memory.nams.query import NamsCypherQuery
from neo4j_agent_memory.nams.reasoning import NamsReasoningMemory
from neo4j_agent_memory.nams.short_term import NamsShortTermMemory
from neo4j_agent_memory.nams.transport import HttpTransport

if TYPE_CHECKING:
    from neo4j_agent_memory.observability.base import Tracer


class NamsBackend:
    """Holds transport + memory implementations for the NAMS backend.

    Construct via :meth:`from_config` (the canonical path) or directly
    with an existing :class:`HttpTransport`.

    Lifecycle: ``async with NamsBackend.from_config(config) as backend:`` —
    the transport's HTTP session is opened on enter and closed on exit.
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport
        self._short_term = NamsShortTermMemory(transport)
        self._long_term = NamsLongTermMemory(transport)
        self._reasoning = NamsReasoningMemory(transport)
        self._query = NamsCypherQuery(transport)

    # ------------------------------------------------------------------ ctors

    @classmethod
    def from_config(
        cls,
        config: NamsConfig,
        *,
        auth: AuthProvider | None = None,
        tracer: Tracer | None = None,
    ) -> NamsBackend:
        """Build a backend from a :class:`NamsConfig`.

        ``auth`` defaults to :class:`StaticApiKeyAuth` if not provided —
        the canonical static-API-key path. Pass a custom
        :class:`AuthProvider` for OAuth/refresh-token flows.
        """
        if auth is None:
            auth = StaticApiKeyAuth.from_config(config)
        transport = HttpTransport.from_config(config, auth=auth, tracer=tracer)
        return cls(transport)

    # -------------------------------------------------------------- lifecycle

    async def __aenter__(self) -> NamsBackend:
        await self._transport.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._transport.__aexit__(exc_type, exc, tb)

    async def close(self) -> None:
        """Close the underlying HTTP transport."""
        await self._transport.close()

    # ---------------------------------------------------------------- accessors

    @property
    def transport(self) -> HttpTransport:
        """The shared :class:`HttpTransport` instance."""
        return self._transport

    @property
    def short_term(self) -> NamsShortTermMemory:
        return self._short_term

    @property
    def long_term(self) -> NamsLongTermMemory:
        return self._long_term

    @property
    def reasoning(self) -> NamsReasoningMemory:
        return self._reasoning

    @property
    def query(self) -> NamsCypherQuery:
        """Read-only Cypher accessor (NAMS Platinum ``POST /v1/cypher``)."""
        return self._query

    # ----------------------------------------------------------------- probe

    async def probe(self) -> None:
        """Make one lightweight authenticated request to validate connectivity.

        Used by :meth:`MemoryClient.connect` when
        ``NamsConfig.validate_on_connect=True``. Surfaces
        :class:`AuthenticationError` for 401/403 and
        :class:`TransportError` for network failures *at connect time*,
        before any user-visible request fires.

        We call ``list_conversations(limit=1)`` rather than a dedicated
        ``/health`` endpoint because every NAMS deployment supports it.
        (Older draft impls used ``list_sessions``, but that endpoint
        doesn't exist in the live NAMS spec — sessions are not a
        first-class concept.)
        """
        await self._short_term.list_conversations(limit=1)


__all__ = ["NamsBackend"]
