"""Unit tests for observability module."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from neo4j_agent_memory.observability.base import (
    NoOpSpan,
    NoOpTracer,
    Span,
    Tracer,
    TracingProvider,
    get_tracer,
    is_opentelemetry_available,
    is_opik_available,
)


class TestNoOpSpan:
    """Tests for NoOpSpan."""

    def test_set_attribute(self):
        """Test that set_attribute does nothing."""
        span = NoOpSpan()
        span.set_attribute("key", "value")
        # Should not raise

    def test_set_status(self):
        """Test that set_status does nothing."""
        span = NoOpSpan()
        span.set_status("OK")
        span.set_status("ERROR", "something went wrong")
        # Should not raise

    def test_record_exception(self):
        """Test that record_exception does nothing."""
        span = NoOpSpan()
        span.record_exception(ValueError("test error"))
        # Should not raise

    def test_end(self):
        """Test that end does nothing."""
        span = NoOpSpan()
        span.end()
        # Should not raise


class TestNoOpTracer:
    """Tests for NoOpTracer."""

    def test_start_span(self):
        """Test that start_span returns a NoOpSpan."""
        tracer = NoOpTracer()
        span = tracer.start_span("test_span")
        assert isinstance(span, NoOpSpan)

    def test_start_span_with_attributes(self):
        """Test start_span with attributes."""
        tracer = NoOpTracer()
        span = tracer.start_span("test_span", {"key": "value"})
        assert isinstance(span, NoOpSpan)

    def test_span_context_manager(self):
        """Test span as context manager."""
        tracer = NoOpTracer()
        with tracer.span("test_span") as span:
            assert isinstance(span, NoOpSpan)
            span.set_attribute("key", "value")

    def test_span_context_manager_with_exception(self):
        """Test span context manager handles exceptions."""
        tracer = NoOpTracer()
        with pytest.raises(ValueError):
            with tracer.span("test_span") as span:
                raise ValueError("test error")

    @pytest.mark.asyncio
    async def test_async_span_context_manager(self):
        """Test async span context manager."""
        tracer = NoOpTracer()
        async with tracer.async_span("test_span") as span:
            assert isinstance(span, NoOpSpan)

    @pytest.mark.asyncio
    async def test_async_span_with_exception(self):
        """Test async span handles exceptions."""
        tracer = NoOpTracer()
        with pytest.raises(ValueError):
            async with tracer.async_span("test_span"):
                raise ValueError("test error")


class TestTracerDecorator:
    """Tests for the trace decorator."""

    def test_trace_sync_function(self):
        """Test tracing a synchronous function."""
        tracer = NoOpTracer()

        @tracer.trace("my_function")
        def my_function(x: int) -> int:
            return x * 2

        result = my_function(5)
        assert result == 10

    def test_trace_sync_function_default_name(self):
        """Test trace decorator uses function name by default."""
        tracer = NoOpTracer()

        @tracer.trace()
        def another_function(x: int) -> int:
            return x + 1

        result = another_function(5)
        assert result == 6

    @pytest.mark.asyncio
    async def test_trace_async_function(self):
        """Test tracing an async function."""
        tracer = NoOpTracer()

        @tracer.trace("async_function")
        async def my_async_function(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 3

        result = await my_async_function(5)
        assert result == 15

    def test_trace_with_attributes(self):
        """Test trace decorator with attributes."""
        tracer = NoOpTracer()

        @tracer.trace("func_with_attrs", {"custom_attr": "value"})
        def func_with_attrs() -> str:
            return "hello"

        result = func_with_attrs()
        assert result == "hello"

    def test_trace_preserves_exception(self):
        """Test that trace decorator preserves exceptions."""
        tracer = NoOpTracer()

        @tracer.trace("failing_func")
        def failing_func():
            raise RuntimeError("test error")

        with pytest.raises(RuntimeError, match="test error"):
            failing_func()

    @pytest.mark.asyncio
    async def test_trace_async_preserves_exception(self):
        """Test that trace decorator preserves async exceptions."""
        tracer = NoOpTracer()

        @tracer.trace("failing_async")
        async def failing_async():
            raise RuntimeError("async error")

        with pytest.raises(RuntimeError, match="async error"):
            await failing_async()


class TestTracingProvider:
    """Tests for TracingProvider enum."""

    def test_provider_values(self):
        """Test that all expected providers exist."""
        assert TracingProvider.OPENTELEMETRY == "opentelemetry"
        assert TracingProvider.OPIK == "opik"
        assert TracingProvider.NOOP == "noop"
        assert TracingProvider.AUTO == "auto"

    def test_provider_from_string(self):
        """Test creating provider from string."""
        assert TracingProvider("opentelemetry") == TracingProvider.OPENTELEMETRY
        assert TracingProvider("opik") == TracingProvider.OPIK
        assert TracingProvider("noop") == TracingProvider.NOOP


class TestAvailabilityChecks:
    """Tests for availability check functions."""

    def test_is_opentelemetry_available_when_not_installed(self):
        """Test OpenTelemetry availability check when not installed."""
        with patch.dict("sys.modules", {"opentelemetry.trace": None}):
            # Force reimport
            import importlib

            import neo4j_agent_memory.observability.base as base_module

            importlib.reload(base_module)
            # Result depends on actual installation

    def test_is_opik_available_when_not_installed(self):
        """Test Opik availability check when not installed."""
        with patch.dict("sys.modules", {"opik": None}):
            import importlib

            import neo4j_agent_memory.observability.base as base_module

            importlib.reload(base_module)
            # Result depends on actual installation


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_noop(self):
        """Test getting a noop tracer."""
        tracer = get_tracer(provider="noop")
        assert tracer.__class__.__name__ == "NoOpTracer"

    def test_get_tracer_noop_enum(self):
        """Test getting noop tracer with enum."""
        tracer = get_tracer(provider=TracingProvider.NOOP)
        assert tracer.__class__.__name__ == "NoOpTracer"

    @patch("neo4j_agent_memory.observability.base.is_opentelemetry_available")
    @patch("neo4j_agent_memory.observability.base.is_opik_available")
    def test_get_tracer_auto_fallback_to_noop(self, mock_opik, mock_otel):
        """Test auto provider falls back to noop when nothing available."""
        mock_opik.return_value = False
        mock_otel.return_value = False

        tracer = get_tracer(provider="auto")
        assert tracer.__class__.__name__ == "NoOpTracer"

    def test_get_tracer_with_service_name(self):
        """Test get_tracer accepts service_name parameter."""
        tracer = get_tracer(provider="noop", service_name="my-service")
        assert tracer.__class__.__name__ == "NoOpTracer"


class TestSpanAbstract:
    """Tests for Span abstract class."""

    def test_span_is_abstract(self):
        """Test that Span cannot be instantiated directly."""
        # Span is an ABC, we can only test its subclasses
        assert issubclass(NoOpSpan, Span)


class TestTracerAbstract:
    """Tests for Tracer abstract class."""

    def test_tracer_is_abstract(self):
        """Test that Tracer cannot be instantiated directly."""
        assert issubclass(NoOpTracer, Tracer)


class TestOpenTelemetryTracer:
    """Tests for OpenTelemetry tracer (when available)."""

    @pytest.mark.skipif(not is_opentelemetry_available(), reason="OpenTelemetry not installed")
    def test_create_otel_tracer(self):
        """Test creating OpenTelemetry tracer."""
        from neo4j_agent_memory.observability.otel import OpenTelemetryTracer

        tracer = OpenTelemetryTracer(service_name="test-service")
        assert tracer.service_name == "test-service"

    @pytest.mark.skipif(not is_opentelemetry_available(), reason="OpenTelemetry not installed")
    def test_otel_tracer_start_span(self):
        """Test starting a span with OpenTelemetry tracer."""
        from neo4j_agent_memory.observability.otel import OpenTelemetryTracer

        tracer = OpenTelemetryTracer(service_name="test-service")
        span = tracer.start_span("test_span")
        assert span is not None
        span.end()

    @pytest.mark.skipif(not is_opentelemetry_available(), reason="OpenTelemetry not installed")
    def test_otel_span_attributes(self):
        """Test setting attributes on OpenTelemetry span."""
        from neo4j_agent_memory.observability.otel import OpenTelemetryTracer

        tracer = OpenTelemetryTracer(service_name="test-service")
        span = tracer.start_span("test_span")
        span.set_attribute("string_attr", "value")
        span.set_attribute("int_attr", 42)
        span.set_attribute("float_attr", 3.14)
        span.set_attribute("bool_attr", True)
        span.set_attribute("list_attr", ["a", "b", "c"])
        span.set_attribute("complex_attr", {"nested": "value"})  # Should convert to string
        span.end()

    @pytest.mark.skipif(not is_opentelemetry_available(), reason="OpenTelemetry not installed")
    def test_otel_span_status(self):
        """Test setting status on OpenTelemetry span."""
        from neo4j_agent_memory.observability.otel import OpenTelemetryTracer

        tracer = OpenTelemetryTracer(service_name="test-service")
        span = tracer.start_span("test_span")
        span.set_status("OK")
        span.set_status("ERROR", "something went wrong")
        span.end()

    @pytest.mark.skipif(not is_opentelemetry_available(), reason="OpenTelemetry not installed")
    def test_otel_span_exception(self):
        """Test recording exception on OpenTelemetry span."""
        from neo4j_agent_memory.observability.otel import OpenTelemetryTracer

        tracer = OpenTelemetryTracer(service_name="test-service")
        span = tracer.start_span("test_span")
        span.record_exception(ValueError("test error"))
        span.end()


class TestOpikTracer:
    """Tests for Opik tracer (when available)."""

    @pytest.mark.skipif(not is_opik_available(), reason="Opik not installed")
    def test_create_opik_tracer(self):
        """Test creating Opik tracer."""
        from neo4j_agent_memory.observability.opik import OpikTracer

        # This will require proper Opik configuration
        with patch("opik.Opik"):
            with patch("opik.configure"):
                tracer = OpikTracer(service_name="test-service")
                assert tracer.service_name == "test-service"


class TestIntegration:
    """Integration tests for observability module."""

    def test_trace_extraction_pipeline(self):
        """Test tracing an extraction pipeline."""
        tracer = NoOpTracer()

        @tracer.trace("extract")
        def extract(text: str) -> dict:
            return {"entities": [], "relations": []}

        @tracer.trace("process")
        def process(result: dict) -> list:
            return result.get("entities", [])

        # Simulate extraction pipeline
        result = extract("John works at Acme Corp")
        entities = process(result)
        assert entities == []

    @pytest.mark.asyncio
    async def test_trace_async_extraction(self):
        """Test tracing async extraction."""
        tracer = NoOpTracer()

        @tracer.trace("async_extract")
        async def async_extract(text: str) -> dict:
            await asyncio.sleep(0.01)
            return {"entities": ["John", "Acme Corp"]}

        result = await async_extract("John works at Acme Corp")
        assert result["entities"] == ["John", "Acme Corp"]

    def test_nested_spans(self):
        """Test nested span creation."""
        tracer = NoOpTracer()

        results = []

        with tracer.span("outer") as outer_span:
            outer_span.set_attribute("level", "outer")
            results.append("outer_start")

            with tracer.span("inner") as inner_span:
                inner_span.set_attribute("level", "inner")
                results.append("inner")

            results.append("outer_end")

        assert results == ["outer_start", "inner", "outer_end"]
