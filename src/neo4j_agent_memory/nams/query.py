"""NAMS implementation of :class:`CypherQueryProtocol`.

Forwards read-only Cypher to the Platinum ``POST /v1/cypher`` endpoint
(bridge: ``POST /cypher``). Read-only validation happens client-side via
:func:`is_read_only_query` — same validator the bolt impl and the MCP
``graph_query`` tool use, so behavior is consistent across backends.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from neo4j_agent_memory.core.query import is_read_only_query
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


_SPEC_CYPHER = EndpointSpec(
    rest_method="POST",
    rest_path="/cypher",
    bridge_method="cypher",
)


class NamsCypherQuery:
    """NAMS implementation of :class:`CypherQueryProtocol`.

    Validates read-only client-side, then sends ``{"query": ..., "params":
    ...}`` to the NAMS cypher endpoint. The server enforces read-only
    server-side as a second line of defense — but rejecting writes
    locally avoids round-tripping a query NAMS would reject anyway.
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
        body = {"query": query, "params": params or {}}
        payload = await self._transport.request(_SPEC_CYPHER, json=body)
        # NAMS returns either a list of rows directly, or ``{"rows": [...]}`` —
        # accept both.
        if isinstance(payload, list):
            return [dict(row) for row in payload]
        if isinstance(payload, dict) and "rows" in payload:
            return [dict(row) for row in payload["rows"]]
        return []


__all__ = ["NamsCypherQuery"]
