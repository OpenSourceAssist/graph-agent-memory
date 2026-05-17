"""NAMS implementation of :class:`ReasoningProtocol`.

Endpoint mappings inferred from plan §G. Bolt-only methods
(``on_tool_call_recorded`` hook, ``migrate_tool_stats``) are NOT on this
class. The streaming :class:`StreamingTraceRecorder` from
``memory.reasoning`` works against any object that exposes
``add_step``/``record_tool_call``/``complete_trace`` (which we do), so
streaming flows work transparently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from neo4j_agent_memory.memory.reasoning import (
    ReasoningStep,
    ReasoningTrace,
    ToolCall,
    ToolStats,
)
from neo4j_agent_memory.nams._serialization import payload_to_model
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


# -----------------------------------------------------------------------------
# Endpoint registry
# -----------------------------------------------------------------------------

_SPEC_START_TRACE = EndpointSpec(
    rest_method="POST", rest_path="/traces", bridge_method="start_trace"
)
_SPEC_ADD_STEP = EndpointSpec(
    rest_method="POST",
    rest_path="/traces/{trace_id}/steps",
    bridge_method="add_step",
)
_SPEC_RECORD_TOOL_CALL = EndpointSpec(
    rest_method="POST",
    rest_path="/steps/{step_id}/tool-calls",
    bridge_method="record_tool_call",
)
# TODO(nams-spec): verify ``:complete`` verb suffix.
_SPEC_COMPLETE_TRACE = EndpointSpec(
    rest_method="POST",
    rest_path="/traces/{trace_id}:complete",
    bridge_method="complete_trace",
)
_SPEC_SEARCH_STEPS = EndpointSpec(
    rest_method="POST", rest_path="/steps/search", bridge_method="search_steps"
)
_SPEC_GET_SIMILAR_TRACES = EndpointSpec(
    rest_method="POST",
    rest_path="/traces/similar",
    bridge_method="get_similar_traces",
)
_SPEC_GET_TRACE = EndpointSpec(
    rest_method="GET", rest_path="/traces/{trace_id}", bridge_method="get_trace"
)
_SPEC_GET_TRACE_WITH_STEPS = EndpointSpec(
    rest_method="GET",
    rest_path="/traces/{trace_id}",
    bridge_method="get_trace_with_steps",
)
_SPEC_GET_SESSION_TRACES = EndpointSpec(
    rest_method="GET", rest_path="/traces", bridge_method="get_session_traces"
)
_SPEC_LIST_TRACES = EndpointSpec(
    rest_method="GET", rest_path="/traces", bridge_method="list_traces"
)
_SPEC_GET_TOOL_STATS = EndpointSpec(
    rest_method="GET", rest_path="/tools/stats", bridge_method="get_tool_stats"
)
# TODO(nams-spec): verify trace↔message linking shape.
_SPEC_LINK_TRACE_TO_MESSAGE = EndpointSpec(
    rest_method="POST",
    rest_path="/traces/{trace_id}/messages/{message_id}",
    bridge_method="link_trace_to_message",
)
# TODO(nams-spec): verify reasoning get_context shape vs short/long-term.
_SPEC_GET_CONTEXT = EndpointSpec(
    rest_method="POST",
    rest_path="/reasoning/context",
    bridge_method="get_context",
)


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _to_str(value: UUID | str) -> str:
    return str(value)


class NamsReasoningMemory:
    """Reasoning memory backed by the NAMS HTTP service."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------ Bronze

    async def start_trace(
        self,
        session_id: str,
        task: str,
        **kwargs: Any,
    ) -> ReasoningTrace:
        """Begin recording a reasoning trace."""
        body = _drop_none(
            {
                "session_id": session_id,
                "task": task,
                "metadata": kwargs.get("metadata"),
                "triggered_by_message_id": (
                    _to_str(kwargs["triggered_by_message_id"])
                    if kwargs.get("triggered_by_message_id") is not None
                    else None
                ),
                "userId": kwargs.get("user_identifier"),
            }
        )
        payload = await self._transport.request(_SPEC_START_TRACE, json=body)
        return payload_to_model(payload, ReasoningTrace)

    async def add_step(
        self,
        trace_id: UUID | str,
        **kwargs: Any,
    ) -> ReasoningStep:
        """Append a step to a trace.

        Accepts ``thought``, ``action``, ``observation``, ``metadata`` —
        any subset can be ``None``. The Protocol's positional ``content``
        argument from bolt is not directly used here; bolt's ``add_step``
        is also keyword-only after ``trace_id``.
        """
        body = _drop_none(
            {
                "thought": kwargs.get("thought"),
                "action": kwargs.get("action"),
                "observation": kwargs.get("observation"),
                "metadata": kwargs.get("metadata"),
            }
        )
        payload = await self._transport.request(
            _SPEC_ADD_STEP,
            path_params={"trace_id": _to_str(trace_id)},
            json=body,
        )
        return payload_to_model(payload, ReasoningStep)

    async def record_tool_call(
        self,
        step_id: UUID | str,
        tool_name: str,
        arguments: dict[str, Any],
        **kwargs: Any,
    ) -> ToolCall:
        """Record a tool invocation tied to a reasoning step."""
        body = _drop_none(
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": kwargs.get("result"),
                "status": kwargs.get("status"),
                "duration_ms": kwargs.get("duration_ms"),
                "error": kwargs.get("error"),
            }
        )
        payload = await self._transport.request(
            _SPEC_RECORD_TOOL_CALL,
            path_params={"step_id": _to_str(step_id)},
            json=body,
        )
        return payload_to_model(payload, ToolCall)

    async def complete_trace(
        self,
        trace_id: UUID | str,
        **kwargs: Any,
    ) -> None:
        """Finalize a trace with an outcome and success flag."""
        body = _drop_none(
            {
                "outcome": kwargs.get("outcome"),
                "success": kwargs.get("success"),
            }
        )
        await self._transport.request(
            _SPEC_COMPLETE_TRACE,
            path_params={"trace_id": _to_str(trace_id)},
            json=body or None,
        )

    # ------------------------------------------------------------------ Silver

    async def search_steps(self, query: str, **kwargs: Any) -> list[ReasoningStep]:
        """Vector/keyword search across reasoning steps."""
        body = _drop_none(
            {
                "query": query,
                "session_id": kwargs.get("session_id"),
                "limit": kwargs.get("limit"),
                "threshold": kwargs.get("threshold"),
            }
        )
        payload = await self._transport.request(_SPEC_SEARCH_STEPS, json=body)
        return [payload_to_model(item, ReasoningStep) for item in (payload or [])]

    async def get_similar_traces(
        self,
        query: str,
        **kwargs: Any,
    ) -> list[ReasoningTrace]:
        """Find traces with similar task descriptions."""
        body = _drop_none(
            {
                "query": query,
                "session_id": kwargs.get("session_id"),
                "limit": kwargs.get("limit"),
                "threshold": kwargs.get("threshold"),
                "success_only": kwargs.get("success_only"),
            }
        )
        payload = await self._transport.request(_SPEC_GET_SIMILAR_TRACES, json=body)
        return [payload_to_model(item, ReasoningTrace) for item in (payload or [])]

    async def get_trace(self, trace_id: UUID | str) -> ReasoningTrace | None:
        """Fetch a single trace (header only)."""
        from neo4j_agent_memory.core.exceptions import MemoryError as _ME

        try:
            payload = await self._transport.request(
                _SPEC_GET_TRACE,
                path_params={"trace_id": _to_str(trace_id)},
            )
        except _ME as e:
            if "not found" in str(e).lower():
                return None
            raise
        if payload is None:
            return None
        return payload_to_model(payload, ReasoningTrace)

    async def get_trace_with_steps(
        self,
        trace_id: UUID | str,
    ) -> ReasoningTrace | None:
        """Fetch a trace with its full step + tool-call chain."""
        from neo4j_agent_memory.core.exceptions import MemoryError as _ME

        try:
            payload = await self._transport.request(
                _SPEC_GET_TRACE_WITH_STEPS,
                path_params={"trace_id": _to_str(trace_id)},
                params={"include": "steps"},
            )
        except _ME as e:
            if "not found" in str(e).lower():
                return None
            raise
        if payload is None:
            return None
        return payload_to_model(payload, ReasoningTrace)

    async def get_session_traces(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> list[ReasoningTrace]:
        """List traces for a session."""
        params = _drop_none(
            {
                "session_id": session_id,
                "limit": kwargs.get("limit"),
                "offset": kwargs.get("offset"),
                "success_only": kwargs.get("success_only"),
            }
        )
        payload = await self._transport.request(
            _SPEC_GET_SESSION_TRACES, params=params or None
        )
        return [payload_to_model(item, ReasoningTrace) for item in (payload or [])]

    async def list_traces(self, **kwargs: Any) -> list[ReasoningTrace]:
        """List traces globally (paginated)."""
        params = _drop_none(
            {
                "limit": kwargs.get("limit"),
                "offset": kwargs.get("offset"),
            }
        )
        payload = await self._transport.request(
            _SPEC_LIST_TRACES, params=params or None
        )
        return [payload_to_model(item, ReasoningTrace) for item in (payload or [])]

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """Return assembled context text from reasoning memory."""
        body = _drop_none(
            {
                "query": query,
                "max_traces": kwargs.get("max_traces") or kwargs.get("max_items"),
                "session_id": kwargs.get("session_id"),
            }
        )
        payload = await self._transport.request(_SPEC_GET_CONTEXT, json=body)
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            return str(payload.get("context") or payload.get("text") or "")
        return ""

    # -------------------------------------------------------------------- Gold

    async def get_tool_stats(self, **kwargs: Any) -> Any:
        """Return aggregate tool-usage stats.

        Returns ``list[ToolStats]``. Bolt returns ``dict[str, ToolStats]``
        — Protocol type is :class:`Any` to permit both shapes; portable
        code should branch.
        """
        params = _drop_none(
            {
                "tool_name": kwargs.get("tool_name"),
                "session_id": kwargs.get("session_id"),
            }
        )
        payload = await self._transport.request(
            _SPEC_GET_TOOL_STATS, params=params or None
        )
        return [payload_to_model(item, ToolStats) for item in (payload or [])]

    async def link_trace_to_message(
        self,
        trace_id: UUID | str,
        message_id: UUID | str,
    ) -> None:
        """Link a reasoning trace to the message that triggered it."""
        await self._transport.request(
            _SPEC_LINK_TRACE_TO_MESSAGE,
            path_params={
                "trace_id": _to_str(trace_id),
                "message_id": _to_str(message_id),
            },
        )


__all__ = ["NamsReasoningMemory"]
