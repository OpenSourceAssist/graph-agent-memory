"""Observability module for Neo4j Agent Memory.

Provides tracing and metrics support via OpenTelemetry and Opik.

Usage:
    from neo4j_agent_memory.observability import get_tracer, TracingProvider

    # Auto-detect available provider
    tracer = get_tracer()

    # Or specify provider explicitly
    tracer = get_tracer(provider="opik")
    tracer = get_tracer(provider="opentelemetry")

    # Use decorator for tracing
    @tracer.trace("extract_entities")
    async def extract(text: str):
        ...

    # Or use context manager
    async with tracer.span("extraction") as span:
        span.set_attribute("text_length", len(text))
        result = await extract(text)
"""

from neo4j_agent_memory.observability.base import (
    NoOpTracer,
    Span,
    Tracer,
    TracingProvider,
    get_tracer,
    is_opentelemetry_available,
    is_opik_available,
)

__all__ = [
    "Tracer",
    "Span",
    "TracingProvider",
    "NoOpTracer",
    "get_tracer",
    "is_opentelemetry_available",
    "is_opik_available",
]
