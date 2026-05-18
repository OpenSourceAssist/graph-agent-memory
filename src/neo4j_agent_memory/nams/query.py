"""NAMS implementation of :class:`CypherQueryProtocol`.

Forwards read-only Cypher to the NAMS query endpoint
(``POST /v1/query``, verified against the live API spec). Request
shape: ``{"cypher": "<query>", "params": {...}}``. Response shape:
``{"columns": [...], "rows": [...], "stats": {...}}`` — we unwrap and
return only ``rows`` to keep the unified ``CypherQueryProtocol``
contract consistent across backends.

Read-only validation happens client-side via :func:`is_read_only_query`
— same validator the bolt impl and the MCP ``graph_query`` tool use,
so behavior is consistent across backends. The server enforces
read-only server-side as a second line of defense.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from neo4j_agent_memory.core.query import is_read_only_query
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


_SPEC_CYPHER = EndpointSpec(
    rest_method="POST",
    rest_path="/query",
    bridge_method="query",
)


class NamsCypherQuery:
    """NAMS implementation of :class:`CypherQueryProtocol`.

    Validates read-only client-side, then sends
    ``{"cypher": ..., "params": ...}`` to ``POST /v1/query``.
    Returns the ``rows`` array from the response envelope.
    """

    __slots__ = ("_transport",)

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    async def cypher(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read-only Cypher query via NAMS."""
        if not is_read_only_query(query):
            raise ValueError(
                "Only read-only Cypher queries are allowed. "
                "Detected write keywords (CREATE/MERGE/DELETE/SET/...). "
                "Use the appropriate memory-layer method for writes."
            )
        # NAMS field is ``cypher`` (not ``query``) per the verified spec.
        body = {"cypher": query, "params": params or {}}
        payload = await self._transport.request(_SPEC_CYPHER, json=body)
        # Response shape: {"columns": [...], "rows": [...], "stats": {...}}.
        # Older deployments / TCK bridge may return a bare list — accept both.
        if isinstance(payload, dict) and "rows" in payload:
            rows = payload["rows"]
            return [dict(r) for r in rows] if isinstance(rows, list) else []
        if isinstance(payload, list):
            return [dict(r) for r in payload]
        return []


__all__ = ["NamsCypherQuery"]
