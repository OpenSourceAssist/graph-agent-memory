"""Tests for nams/reasoning.py — NamsReasoningMemory.

Endpoint shapes verified against the live NAMS OpenAPI spec.

NAMS has no Trace entity. The Protocol's start_trace/complete_trace
are synthesized client-side via an in-memory cache; add_step and
record_tool_call make real HTTP calls.
"""

from __future__ import annotations

import json

import pytest
import respx

from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.core.protocols import ReasoningProtocol
from neo4j_agent_memory.memory.reasoning import (
    ReasoningStep,
    ReasoningTrace,
    ToolCall,
)
from neo4j_agent_memory.nams import HttpTransport, NamsReasoningMemory, StaticApiKeyAuth


@pytest.fixture
async def transport(nams_config):
    auth = StaticApiKeyAuth.from_config(nams_config)
    t = HttpTransport.from_config(nams_config, auth=auth)
    async with t:
        yield t


@pytest.fixture
def reasoning(transport) -> NamsReasoningMemory:
    return NamsReasoningMemory(transport)


# NAMS step response shape (camelCase, NAMS-side field names).
SAMPLE_STEP = {
    "id": "00000000-0000-0000-0000-00000000aaaa",
    "conversationId": "cid",
    "reasoning": "thinking about it",
    "actionTaken": "search",
    "result": "found 3 results",
    "createdAt": "2026-05-17T12:00:00Z",
}

SAMPLE_TOOL_CALL = {
    "id": "00000000-0000-0000-0000-00000000bbbb",
    "stepId": "00000000-0000-0000-0000-00000000aaaa",
    "toolName": "search",
    "status": "success",
    "input": '{"q": "italian"}',
    "output": '["r1"]',
    "durationMs": 42,
    "createdAt": "2026-05-17T12:00:00Z",
}


class TestProtocolConformance:
    def test_satisfies_reasoning_protocol(self, reasoning):
        assert isinstance(reasoning, ReasoningProtocol)


class TestStartTrace:
    """start_trace is client-side only — no HTTP."""

    async def test_returns_trace_with_uuid(self, reasoning):
        trace = await reasoning.start_trace("cid", "find restaurants")
        assert isinstance(trace, ReasoningTrace)
        assert trace.task == "find restaurants"
        assert trace.session_id == "cid"
        # Trace_id is cached client-side.
        assert str(trace.id) in reasoning._traces

    async def test_no_http_called(self, reasoning):
        with respx.mock(assert_all_called=False) as router:
            await reasoning.start_trace("cid", "task")
            assert len(router.calls) == 0


class TestAddStep:
    @respx.mock
    async def test_maps_field_names(self, reasoning):
        trace = await reasoning.start_trace("cid", "task")
        route = respx.post("https://memory.test/v1/reasoning/steps").respond(201, json=SAMPLE_STEP)
        step = await reasoning.add_step(
            trace.id,
            thought="thinking",
            action="search",
            observation="results",
        )
        assert isinstance(step, ReasoningStep)
        body = json.loads(route.calls[0].request.content)
        assert body == {
            "conversationId": "cid",
            "reasoning": "thinking",
            "actionTaken": "search",
            "result": "results",
        }

    @respx.mock
    async def test_partial_step_fields_get_placeholders(self, reasoning):
        """NAMS requires reasoning + actionTaken; we default empties to a space."""
        trace = await reasoning.start_trace("cid", "task")
        route = respx.post("https://memory.test/v1/reasoning/steps").respond(201, json=SAMPLE_STEP)
        await reasoning.add_step(trace.id, thought="just thinking")
        body = json.loads(route.calls[0].request.content)
        assert body["reasoning"] == "just thinking"
        assert body["actionTaken"] == " "

    async def test_unknown_trace_id_raises(self, reasoning):
        with pytest.raises(ValueError, match="Unknown trace_id"):
            await reasoning.add_step("00000000-0000-0000-0000-deadbeefcafe", thought="x")


class TestRecordToolCall:
    @respx.mock
    async def test_maps_args_to_input_string(self, reasoning):
        route = respx.post("https://memory.test/v1/reasoning/tool-calls").respond(
            201, json=SAMPLE_TOOL_CALL
        )
        tc = await reasoning.record_tool_call(
            "00000000-0000-0000-0000-0000000aaaaa",
            "search",
            {"q": "italian"},
            result=["r1"],
            status="success",
            duration_ms=42,
        )
        assert isinstance(tc, ToolCall)
        body = json.loads(route.calls[0].request.content)
        # input + output are JSON-encoded strings; toolName camelCase.
        assert body["toolName"] == "search"
        assert json.loads(body["input"]) == {"q": "italian"}
        assert body["stepId"] == "00000000-0000-0000-0000-0000000aaaaa"
        assert body["status"] == "success"
        assert json.loads(body["output"]) == ["r1"]
        assert body["durationMs"] == 42

    @respx.mock
    async def test_decodes_input_and_output(self, reasoning):
        respx.post("https://memory.test/v1/reasoning/tool-calls").respond(
            201, json=SAMPLE_TOOL_CALL
        )
        tc = await reasoning.record_tool_call(
            "00000000-0000-0000-0000-0000000aaaaa", "search", {"q": "italian"}
        )
        # Response input/output JSON-decoded back into dict/list.
        assert tc.arguments == {"q": "italian"}
        assert tc.result == ["r1"]


class TestCompleteTrace:
    async def test_updates_cache_no_http(self, reasoning):
        trace = await reasoning.start_trace("cid", "task")
        await reasoning.complete_trace(trace.id, outcome="done", success=True)
        cached = reasoning._traces[str(trace.id)]
        assert cached["outcome"] == "done"
        assert cached["success"] is True
        assert cached["completed_at"] is not None

    async def test_unknown_trace_id_is_no_op(self, reasoning):
        # Idempotent for unknown trace_ids.
        await reasoning.complete_trace("00000000-0000-0000-0000-cccccccccccc")


class TestGetTrace:
    async def test_returns_cached_trace(self, reasoning):
        started = await reasoning.start_trace("cid", "task")
        fetched = await reasoning.get_trace(started.id)
        assert fetched is not None
        assert fetched.task == "task"

    async def test_unknown_returns_none(self, reasoning):
        result = await reasoning.get_trace("00000000-0000-0000-0000-aaaaaaaaaaaa")
        assert result is None


class TestGetTraceWithSteps:
    @respx.mock
    async def test_assembles_steps_from_reasoning_trace_endpoint(self, reasoning):
        started = await reasoning.start_trace("cid", "task")
        respx.get("https://memory.test/v1/reasoning/trace/cid").respond(
            200,
            json={
                "conversationId": "cid",
                "steps": [SAMPLE_STEP],
                "toolCalls": [SAMPLE_TOOL_CALL],
            },
        )
        trace = await reasoning.get_trace_with_steps(started.id)
        assert trace is not None
        assert len(trace.steps) == 1
        # Tool calls attached to the matching step.
        assert len(trace.steps[0].tool_calls) == 1

    async def test_unknown_returns_none(self, reasoning):
        result = await reasoning.get_trace_with_steps("00000000-0000-0000-0000-eeeeeeeeeeee")
        assert result is None


class TestGetSessionTraces:
    @respx.mock
    async def test_aggregates_to_single_trace(self, reasoning):
        respx.get("https://memory.test/v1/reasoning/trace/cid").respond(
            200,
            json={
                "conversationId": "cid",
                "steps": [SAMPLE_STEP],
                "toolCalls": [],
            },
        )
        traces = await reasoning.get_session_traces("cid")
        assert len(traces) == 1
        assert traces[0].session_id == "cid"

    @respx.mock
    async def test_empty_returns_empty_list(self, reasoning):
        respx.get("https://memory.test/v1/reasoning/trace/cid").respond(
            200, json={"conversationId": "cid", "steps": [], "toolCalls": []}
        )
        traces = await reasoning.get_session_traces("cid")
        assert traces == []


class TestNotSupportedMethods:
    """search_steps, get_similar_traces, list_traces, get_tool_stats — no NAMS endpoint."""

    async def test_search_steps(self, reasoning):
        with pytest.raises(NotSupportedError):
            await reasoning.search_steps("query")

    async def test_get_similar_traces(self, reasoning):
        with pytest.raises(NotSupportedError):
            await reasoning.get_similar_traces("query")

    async def test_list_traces(self, reasoning):
        with pytest.raises(NotSupportedError):
            await reasoning.list_traces()

    async def test_get_tool_stats(self, reasoning):
        with pytest.raises(NotSupportedError):
            await reasoning.get_tool_stats()


class TestLinkTraceToMessage:
    async def test_no_op(self, reasoning):
        """link_trace_to_message is a no-op on NAMS — steps are already conversation-scoped."""
        result = await reasoning.link_trace_to_message("trace-id", "msg-id")
        assert result is None


class TestGetContext:
    async def test_returns_empty_string(self, reasoning):
        result = await reasoning.get_context("anything")
        assert result == ""
