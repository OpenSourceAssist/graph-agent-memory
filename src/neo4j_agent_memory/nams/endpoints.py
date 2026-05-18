"""Wire-protocol detection and URL construction for the NAMS transport.

Two protocols are supported and auto-selected from the endpoint shape:

* **REST** — endpoint contains ``/v\\d+`` (e.g. ``/v1``). Each method
  maps to a versioned REST route like ``POST /v1/conversations/{id}/messages``.
* **TCK bridge** — anything else. Each method maps to a snake-case
  POST: ``POST /add_message``. Used by the conformance reference
  implementation.

The detection regex matches the hosted service URL
(``https://memory.neo4jlabs.com/v1``) and reasonable on-prem variants
(``http://localhost:8000/v1``). The user may force a protocol via
``NamsConfig.transport_mode={"rest", "bridge"}``.

Phase 3 memory implementations declare an :class:`EndpointSpec` per
Protocol method (e.g. ``add_message`` ↔
``EndpointSpec("POST", "/conversations/{session_id}/messages", "add_message")``)
and call :func:`resolve` to get the (method, url) pair for the active
protocol.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

WireProtocol = Literal["rest", "bridge"]
TransportMode = Literal["auto", "rest", "bridge"]

# Matches `/v<digits>` followed by `/` or end-of-string.
# Catches ``/v1``, ``/v1/``, ``/v2/foo``; rejects ``/version`` and bare paths.
_REST_RE = re.compile(r"/v\d+(/|$)")


def detect_protocol(endpoint: str, mode: TransportMode = "auto") -> WireProtocol:
    """Return the wire protocol to use for ``endpoint``.

    When ``mode != "auto"``, returns the explicit override. Otherwise
    inspects the endpoint for a ``/v<N>`` segment.
    """
    if mode != "auto":
        return mode
    return "rest" if _REST_RE.search(endpoint) else "bridge"


def build_url(
    endpoint: str, *, rest_path: str | None, bridge_method: str, protocol: WireProtocol
) -> str:
    """Construct a full URL for the chosen protocol.

    * ``rest_path`` is a path beginning with ``/`` (e.g. ``/conversations``);
      required when ``protocol == "rest"``.
    * ``bridge_method`` is a snake-case method name without leading slash
      (e.g. ``add_message``); always required.
    """
    base = endpoint.rstrip("/")
    if protocol == "rest":
        if rest_path is None:
            raise ValueError(
                f"REST protocol selected but no rest_path provided for "
                f"bridge_method={bridge_method!r}. Phase 3 memory impls "
                "must declare both."
            )
        if not rest_path.startswith("/"):
            raise ValueError(f"rest_path must begin with '/'; got {rest_path!r}.")
        return base + rest_path
    # bridge
    if "/" in bridge_method:
        raise ValueError(f"bridge_method must not contain '/'; got {bridge_method!r}.")
    return f"{base}/{bridge_method}"


def expand_path(path_template: str, **params: object) -> str:
    """Substitute ``{name}`` placeholders in a REST path template.

    Keys not present in ``path_template`` are ignored (callers usually
    pass a superset). Missing placeholders raise :class:`KeyError`.

    >>> expand_path("/conversations/{session_id}/messages", session_id="abc")
    '/conversations/abc/messages'
    """
    if "{" not in path_template:
        return path_template
    # str.format raises KeyError on missing keys, which is what we want.
    return path_template.format(**params)


@dataclass(frozen=True)
class EndpointSpec:
    """Specification for one Protocol-method ↔ wire-route mapping.

    Phase 3 memory implementations build a registry of these. The
    transport layer takes (spec, params) and dispatches to the right
    URL/HTTP method based on the active protocol.

    Attributes:
        rest_method: HTTP method for REST mode (GET/POST/DELETE/PUT/PATCH).
        rest_path: REST path template with ``{name}`` placeholders.
            ``None`` if a method is bridge-only.
        bridge_method: Snake-case method name for the TCK bridge protocol.
            Always required.
    """

    rest_method: Literal["GET", "POST", "DELETE", "PUT", "PATCH"]
    rest_path: str | None
    bridge_method: str

    def resolve(
        self,
        endpoint: str,
        protocol: WireProtocol,
        path_params: dict[str, object] | None = None,
    ) -> tuple[str, str]:
        """Return the (HTTP method, full URL) tuple for the active protocol.

        For bridge mode, HTTP method is always ``POST``.
        """
        if protocol == "rest":
            if self.rest_path is None:
                raise ValueError(
                    f"Method {self.bridge_method!r} is bridge-only — no REST mapping. "
                    "Set NamsConfig.transport_mode='bridge' to use this method, "
                    "or point the endpoint at a bridge-style URL."
                )
            expanded = expand_path(self.rest_path, **(path_params or {}))
            url = build_url(
                endpoint,
                rest_path=expanded,
                bridge_method=self.bridge_method,
                protocol="rest",
            )
            return (self.rest_method, url)
        # bridge: always POST
        url = build_url(
            endpoint,
            rest_path=None,
            bridge_method=self.bridge_method,
            protocol="bridge",
        )
        return ("POST", url)


__all__ = [
    "WireProtocol",
    "TransportMode",
    "EndpointSpec",
    "detect_protocol",
    "build_url",
    "expand_path",
]
