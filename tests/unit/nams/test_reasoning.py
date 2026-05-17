"""Tests for nams/reasoning.py — NamsReasoningMemory."""

from __future__ import annotations

import json

import pytest
import respx

from neo4j_agent_memory.core.protocols import ReasoningProtocol
from neo4j_agent_memory.memory.reasoning import (
    ReasoningStep,
    ReasoningTrace,
    ToolCall,
    ToolStats,
)
from neo4j_agent_memory.nams import HttpTransport, NamsReasoningMemory, StaticApiKeyAuth

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
async def transport(nams_config):
    auth = StaticApiKeyAuth.from_config(nams_config)
    t = HttpTransport.from_config(nams_config, auth=auth)
    async with t:
        yield t


@pytest.fixture
def reasoning(transport) -> NamsReasoningMemory:
    return NamsReasoningMemory(transport)


SAMPLE_TRACE = {
    "id": "00000000-0000-0000-0000-000000000001",
    "session_id": "s1",
    "task": "find restaurants",
    "steps": [],
    "started_at": "2026-05-17T12:00:00Z",
    "created_at": "2026-05-17T12:00:00Z",
    "metadata": {},
}

SAMPLE_STEP = {
    "id": "00000000-0000-0000-0000-00000000aaaa",
    "trace_id": "00000000-0000-0000-0000-000000000001",
    "step_number": 1,
    "thought": "searching",
    "tool_calls": [],
    "created_at": "2026-05-17T12:00:00Z",
    "metadata": {},
}

SAMPLE_TOOL_CALL = {
    "id": "00000000-0000-0000-0000-00000000bbbb",
    "tool_name": "search",
    "arguments": {"query": "italian"},
    "status": "success",
    "result": ["restaurant1"],
    "created_at": "2026-05-17T12:00:00Z",
    "metadata": {},
}


# -----------------------------------------------------------------------------
# Protocol conformance
# -----------------------------------------------------------------------------


class TestProtocolConformance:
    def test_satisfies_reasoning_protocol(self, reasoning):
        assert isinstance(reasoning, ReasoningProtocol)


# -----------------------------------------------------------------------------
# Bronze tier
# -----------------------------------------------------------------------------


class TestStartTrace:
    @respx.mock
    async def test_basic(self, reasoning):
        route = respx.post("https://memory.test/v1/traces").respond(200, json=SAMPLE_TRACE)
        trace = await reasoning.start_trace("s1", "find restaurants")
        assert isinstance(trace, ReasoningTrace)
        assert trace.session_id == "s1"
        assert trace.task == "find restaurants"
        body = json.loads(route.calls[0].request.content)
        assert body == {"session_id": "s1", "task": "find restaurants"}

    @respx.mock
    async def test_with_triggered_by_message_id(self, reasoning):
        from uuid import UUID

        route = respx.post("https://memory.test/v1/traces").respond(200, json=SAMPLE_TRACE)
        msg_id = UUID(int=42)
        await reasoning.start_trace(
            "s1",
            "task",
            triggered_by_message_id=msg_id,
            user_identifier="alice",
        )
        body = json.loads(route.calls[0].request.content)
        assert body["triggered_by_message_id"] == str(msg_id)
        assert body["userId"] == "alice"


class TestAddStep:
    @respx.mock
    async def test_basic(self, reasoning):
        route = respx.post(
            "https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001/steps"
        ).respond(200, json=SAMPLE_STEP)
        step = await reasoning.add_step(
            "00000000-0000-0000-0000-000000000001",
            thought="thinking",
            action="search",
            observation="results found",
        )
        assert isinstance(step, ReasoningStep)
        body = json.loads(route.calls[0].request.content)
        assert body == {
            "thought": "thinking",
            "action": "search",
            "observation": "results found",
        }

    @respx.mock
    async def test_partial_step_fields(self, reasoning):
        """Only thought set → other fields omitted from body."""
        respx.post(
            "https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001/steps"
        ).respond(200, json=SAMPLE_STEP)
        await reasoning.add_step("00000000-0000-0000-0000-000000000001", thought="just thinking")


class TestRecordToolCall:
    @respx.mock
    async def test_success(self, reasoning):
        route = respx.post(
            "https://memory.test/v1/steps/00000000-0000-0000-0000-00000000aaaa/tool-calls"
        ).respond(200, json=SAMPLE_TOOL_CALL)
        tc = await reasoning.record_tool_call(
            "00000000-0000-0000-0000-00000000aaaa",
            "search",
            {"query": "italian"},
            result=["r1"],
            status="success",
            duration_ms=42,
        )
        assert isinstance(tc, ToolCall)
        body = json.loads(route.calls[0].request.content)
        assert body == {
            "tool_name": "search",
            "arguments": {"query": "italian"},
            "result": ["r1"],
            "status": "success",
            "duration_ms": 42,
        }

    @respx.mock
    async def test_error(self, reasoning):
        respx.post(
            "https://memory.test/v1/steps/00000000-0000-0000-0000-00000000aaaa/tool-calls"
        ).respond(200, json={**SAMPLE_TOOL_CALL, "status": "error", "error": "boom"})
        tc = await reasoning.record_tool_call(
            "00000000-0000-0000-0000-00000000aaaa",
            "search",
            {},
            status="error",
            error="boom",
        )
        assert tc.error == "boom"


class TestCompleteTrace:
    @respx.mock
    async def test_basic(self, reasoning):
        route = respx.post(
            "https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001:complete"
        ).respond(204)
        await reasoning.complete_trace(
            "00000000-0000-0000-0000-000000000001",
            outcome="found 3 restaurants",
            success=True,
        )
        body = json.loads(route.calls[0].request.content)
        assert body == {"outcome": "found 3 restaurants", "success": True}


# -----------------------------------------------------------------------------
# Silver tier
# -----------------------------------------------------------------------------


class TestSearchSteps:
    @respx.mock
    async def test_basic(self, reasoning):
        respx.post("https://memory.test/v1/steps/search").respond(200, json=[SAMPLE_STEP])
        steps = await reasoning.search_steps("search", session_id="s1", limit=5)
        assert len(steps) == 1
        assert isinstance(steps[0], ReasoningStep)


class TestGetSimilarTraces:
    @respx.mock
    async def test_basic(self, reasoning):
        route = respx.post("https://memory.test/v1/traces/similar").respond(
            200, json=[SAMPLE_TRACE]
        )
        traces = await reasoning.get_similar_traces("find food", limit=3, success_only=True)
        assert len(traces) == 1
        body = json.loads(route.calls[0].request.content)
        assert body["query"] == "find food"
        assert body["limit"] == 3
        assert body["success_only"] is True


class TestGetTrace:
    @respx.mock
    async def test_found(self, reasoning):
        respx.get("https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001").respond(
            200, json=SAMPLE_TRACE
        )
        t = await reasoning.get_trace("00000000-0000-0000-0000-000000000001")
        assert isinstance(t, ReasoningTrace)

    @respx.mock
    async def test_not_found_returns_none(self, reasoning):
        # Intentionally use a bare 404 so we exercise status-based detection.
        respx.get("https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001").respond(404)
        assert await reasoning.get_trace("00000000-0000-0000-0000-000000000001") is None


class TestGetTraceWithSteps:
    @respx.mock
    async def test_found_includes_steps(self, reasoning):
        respx.get("https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001").respond(
            200,
            json={**SAMPLE_TRACE, "steps": [SAMPLE_STEP]},
        )
        t = await reasoning.get_trace_with_steps("00000000-0000-0000-0000-000000000001")
        assert t is not None
        assert len(t.steps) == 1

    @respx.mock
    async def test_not_found_returns_none(self, reasoning):
        # Intentionally use a bare 404 so we exercise status-based detection.
        respx.get("https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001").respond(404)
        result = await reasoning.get_trace_with_steps("00000000-0000-0000-0000-000000000001")
        assert result is None


class TestGetSessionTraces:
    @respx.mock
    async def test_basic(self, reasoning):
        route = respx.get("https://memory.test/v1/traces").respond(200, json=[SAMPLE_TRACE])
        traces = await reasoning.get_session_traces("s1", limit=20)
        assert len(traces) == 1
        assert route.calls[0].request.url.params["session_id"] == "s1"


class TestListTraces:
    @respx.mock
    async def test_basic(self, reasoning):
        respx.get("https://memory.test/v1/traces").respond(200, json=[SAMPLE_TRACE])
        traces = await reasoning.list_traces(limit=50)
        assert len(traces) == 1


class TestGetContext:
    @respx.mock
    async def test_dict_response(self, reasoning):
        route = respx.post("https://memory.test/v1/reasoning/context").respond(
            200, json={"context": "reasoning summary"}
        )
        ctx = await reasoning.get_context("query")
        assert ctx == "reasoning summary"
        assert json.loads(route.calls[0].request.content) == {"query": "query"}

    @respx.mock
    async def test_max_traces_zero_is_preserved(self, reasoning):
        route = respx.post("https://memory.test/v1/reasoning/context").respond(
            200, json={"context": "reasoning summary"}
        )
        await reasoning.get_context("query", max_traces=0, max_items=10)
        assert json.loads(route.calls[0].request.content) == {"query": "query", "max_traces": 0}


# -----------------------------------------------------------------------------
# Gold tier
# -----------------------------------------------------------------------------


class TestGetToolStats:
    @respx.mock
    async def test_returns_list(self, reasoning):
        """NAMS shape: ``list[ToolStats]`` (bolt returns dict)."""
        respx.get("https://memory.test/v1/tools/stats").respond(
            200,
            json=[
                {
                    "name": "search",
                    "total_calls": 10,
                    "successful_calls": 9,
                    "failed_calls": 1,
                    "success_rate": 0.9,
                }
            ],
        )
        stats = await reasoning.get_tool_stats()
        assert isinstance(stats, list)
        assert len(stats) == 1
        assert isinstance(stats[0], ToolStats)
        assert stats[0].name == "search"
        assert stats[0].success_rate == 0.9

    @respx.mock
    async def test_filter_by_tool_name(self, reasoning):
        route = respx.get("https://memory.test/v1/tools/stats").respond(200, json=[])
        await reasoning.get_tool_stats(tool_name="search")
        assert route.calls[0].request.url.params["tool_name"] == "search"


class TestLinkTraceToMessage:
    @respx.mock
    async def test_basic(self, reasoning):
        route = respx.post(
            "https://memory.test/v1/traces/00000000-0000-0000-0000-000000000001/messages/00000000-0000-0000-0000-00000000aaaa"
        ).respond(204)
        await reasoning.link_trace_to_message(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-00000000aaaa",
        )
        assert route.called


# -----------------------------------------------------------------------------
# Bridge protocol routing
# -----------------------------------------------------------------------------


class TestBridgeRouting:
    @respx.mock
    async def test_start_trace_bridge_path(self, bridge_config):
        auth = StaticApiKeyAuth.from_config(bridge_config)
        route = respx.post("https://memory.test/start_trace").respond(200, json=SAMPLE_TRACE)
        async with HttpTransport.from_config(bridge_config, auth=auth) as t:
            r = NamsReasoningMemory(t)
            await r.start_trace("s1", "task")
        assert route.called
