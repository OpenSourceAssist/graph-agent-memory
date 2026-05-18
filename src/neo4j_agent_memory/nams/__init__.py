"""Hosted NAMS (Neo4j Agent Memory Service) HTTP backend.

This package contains the HTTP transport, auth, and memory-layer
implementations that target NAMS — the hosted REST API at
``https://memory.neo4jlabs.com/v1``. Activated by
``MemorySettings(backend="nams", nams=NamsConfig(api_key=...))``.

Sibling of :mod:`neo4j_agent_memory.graph`, which houses the bolt
(direct Neo4j) transport.

Public surface (v0.4 Phase 2):

* :class:`AuthProvider` — Protocol for pluggable auth.
* :class:`StaticApiKeyAuth` — ships the default ``Authorization: Bearer`` impl.
* :class:`HttpTransport` — the httpx wrapper with retries and error mapping.
* :class:`EndpointSpec` — REST-path + bridge-method declaration used by
  Phase 3 memory implementations.
"""

from neo4j_agent_memory.nams.auth import AuthProvider, StaticApiKeyAuth
from neo4j_agent_memory.nams.client import NamsBackend
from neo4j_agent_memory.nams.endpoints import (
    EndpointSpec,
    TransportMode,
    WireProtocol,
    build_url,
    detect_protocol,
    expand_path,
)
from neo4j_agent_memory.nams.long_term import NamsLongTermMemory
from neo4j_agent_memory.nams.query import NamsCypherQuery
from neo4j_agent_memory.nams.reasoning import NamsReasoningMemory
from neo4j_agent_memory.nams.short_term import NamsShortTermMemory
from neo4j_agent_memory.nams.transport import HttpTransport

__all__ = [
    # Auth
    "AuthProvider",
    "StaticApiKeyAuth",
    # Transport
    "HttpTransport",
    # Endpoints
    "EndpointSpec",
    "TransportMode",
    "WireProtocol",
    "build_url",
    "detect_protocol",
    "expand_path",
    # Memory implementations (v0.4 Phase 3)
    "NamsBackend",
    "NamsShortTermMemory",
    "NamsLongTermMemory",
    "NamsReasoningMemory",
    # Cypher accessor (v0.4 Phase 4)
    "NamsCypherQuery",
]
