"""OTel-style span attributes for NAMS HTTP requests.

Thin convention layer over :class:`observability.Tracer`. Centralizes
attribute names so all NAMS spans share the same schema. When the
configured tracer is a :class:`NoOpTracer`, every call here is a no-op
with negligible overhead.

Attribute keys follow OpenTelemetry's HTTP semantic conventions where
possible (``http.method``, ``http.url``, ``http.status_code``) plus
NAMS-specific keys (``nams.method``, ``nams.protocol``,
``nams.retry_count``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j_agent_memory.observability.base import Span

# Span name used for every NAMS HTTP request. Sub-attributes carry the detail.
SPAN_NAME = "nams.http.request"

# Attribute keys
ATTR_HTTP_METHOD = "http.method"
ATTR_HTTP_URL = "http.url"
ATTR_HTTP_STATUS_CODE = "http.status_code"
ATTR_NAMS_METHOD = "nams.method"
ATTR_NAMS_PROTOCOL = "nams.protocol"
ATTR_NAMS_RETRY_COUNT = "nams.retry_count"
ATTR_NAMS_ENDPOINT = "nams.endpoint"


def set_request_attributes(
    span: Span,
    *,
    http_method: str,
    url: str,
    nams_method: str,
    protocol: str,
) -> None:
    """Populate request-side span attributes (called before the HTTP call)."""
    span.set_attribute(ATTR_HTTP_METHOD, http_method)
    span.set_attribute(ATTR_HTTP_URL, url)
    span.set_attribute(ATTR_NAMS_METHOD, nams_method)
    span.set_attribute(ATTR_NAMS_PROTOCOL, protocol)


def set_response_attributes(
    span: Span,
    *,
    status_code: int,
    retry_count: int = 0,
) -> None:
    """Populate response-side span attributes (called after the HTTP call)."""
    span.set_attribute(ATTR_HTTP_STATUS_CODE, status_code)
    if retry_count > 0:
        span.set_attribute(ATTR_NAMS_RETRY_COUNT, retry_count)


__all__ = [
    "SPAN_NAME",
    "ATTR_HTTP_METHOD",
    "ATTR_HTTP_URL",
    "ATTR_HTTP_STATUS_CODE",
    "ATTR_NAMS_METHOD",
    "ATTR_NAMS_PROTOCOL",
    "ATTR_NAMS_RETRY_COUNT",
    "ATTR_NAMS_ENDPOINT",
    "set_request_attributes",
    "set_response_attributes",
]
