"""Chat API routes for interacting with the financial advisor agents."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from neo4j_agent_memory import ToolCallStatus

from ...agents.supervisor import get_supervisor_agent
from ...models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationHistory,
    MessageRole,
    SearchRequest,
    SearchResponse,
    SearchResult,
    ToolCall,
)
from ...services.memory_service import (
    FinancialMemoryService,
    get_initialized_memory_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Demo-only: in-memory session service. Use a persistent store for production.
session_service = InMemorySessionService()


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


def _truncate_result(result: Any, max_len: int = 500) -> str | None:
    """Truncate tool results for SSE transmission, always returning a string."""
    if result is None:
        return None
    if isinstance(result, (dict, list)):
        s = json.dumps(result, default=str)
    else:
        s = str(result)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    raw_request: Request,
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
):
    """Stream agent events via Server-Sent Events.

    Streams real-time events as agents process the request, including:
    - agent_start/agent_complete: Agent lifecycle
    - agent_delegate: Supervisor delegating to sub-agents
    - tool_call/tool_result: Tool invocations and results
    - memory_access: Neo4j memory reads/writes
    - thinking: Agent reasoning text
    - response: Final response text
    - trace_saved: Reasoning trace persisted to Neo4j
    - done: Stream complete
    """
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    neo4j_service = getattr(raw_request.app.state, "neo4j_service", None)
    supervisor = get_supervisor_agent(memory_service, neo4j_service=neo4j_service)

    # Create or get session
    # Demo-only: hardcoded user_id. Use authenticated user identity in production.
    session = await session_service.get_session(
        app_name="financial_advisor",
        user_id="user",
        session_id=session_id,
    )
    if session is None:
        session = await session_service.create_session(
            app_name="financial_advisor",
            user_id="user",
            session_id=session_id,
        )

    # Build context message
    context_parts = []
    if request.customer_id:
        context_parts.append(f"Customer context: {request.customer_id}")
    if request.investigation_id:
        context_parts.append(f"Investigation context: {request.investigation_id}")

    user_message = request.message
    if context_parts:
        user_message = f"{' | '.join(context_parts)}\n\n{request.message}"

    runner = Runner(
        agent=supervisor,
        app_name="financial_advisor",
        session_service=session_service,
    )

    async def event_generator():
        response_text = ""
        agents_consulted: set[str] = set()
        current_agent: str | None = None
        tool_call_count = 0
        step_count = 0

        # Reasoning trace state — record after stream completes
        trace_events: list[dict[str, Any]] = []

        # Cache function call args so we can pair them with responses
        pending_calls: dict[str, dict[str, Any]] = {}

        try:
            async for event in runner.run_async(
                user_id="user",
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text=user_message)],
                ),
            ):
                ts = time.time()

                # --- Detect agent transitions via event.author ---
                author = event.author if event.author != "user" else None
                if author and author != current_agent:
                    # Complete previous agent
                    if current_agent:
                        yield _sse_event(
                            "agent_complete",
                            {
                                "agent": current_agent,
                                "timestamp": ts,
                            },
                        )
                        trace_events.append(
                            {
                                "type": "agent_complete",
                                "agent": current_agent,
                            }
                        )

                    # Emit delegation event from supervisor
                    if current_agent:
                        yield _sse_event(
                            "agent_delegate",
                            {
                                "from": current_agent,
                                "to": author,
                                "timestamp": ts,
                            },
                        )

                    current_agent = author
                    agents_consulted.add(current_agent)
                    step_count += 1
                    yield _sse_event(
                        "agent_start",
                        {
                            "agent": current_agent,
                            "timestamp": ts,
                        },
                    )
                    trace_events.append(
                        {
                            "type": "agent_start",
                            "agent": current_agent,
                        }
                    )

                # --- Detect transfer_to_agent in actions ---
                if event.actions and event.actions.transfer_to_agent:
                    yield _sse_event(
                        "agent_delegate",
                        {
                            "from": current_agent or "supervisor",
                            "to": event.actions.transfer_to_agent,
                            "timestamp": ts,
                        },
                    )

                # --- Extract function calls ---
                # ADK internal transfer functions to skip
                _internal_fns = {"transfer_to_agent", "transfer"}

                for fc in event.get_function_calls():
                    fc_name = fc.name
                    if fc_name in _internal_fns:
                        continue
                    fc_args = dict(fc.args) if fc.args else {}
                    pending_calls[fc_name] = fc_args

                    # Detect memory tool calls
                    is_memory_search = any(kw in fc_name for kw in ("search", "context", "history"))
                    is_memory_store = any(kw in fc_name for kw in ("store", "finding", "record"))

                    if is_memory_search:
                        yield _sse_event(
                            "memory_access",
                            {
                                "agent": current_agent,
                                "operation": "search",
                                "tool": fc_name,
                                "query": fc_args.get("query", ""),
                                "timestamp": ts,
                            },
                        )
                    elif is_memory_store:
                        yield _sse_event(
                            "memory_access",
                            {
                                "agent": current_agent,
                                "operation": "store",
                                "tool": fc_name,
                                "timestamp": ts,
                            },
                        )

                    yield _sse_event(
                        "tool_call",
                        {
                            "agent": current_agent,
                            "tool": fc_name,
                            "args": fc_args,
                            "timestamp": ts,
                        },
                    )
                    trace_events.append(
                        {
                            "type": "tool_call",
                            "agent": current_agent,
                            "tool": fc_name,
                            "args": fc_args,
                        }
                    )

                # --- Extract function responses ---
                for fr in event.get_function_responses():
                    if fr.name in _internal_fns:
                        continue
                    tool_call_count += 1
                    fr_args = pending_calls.pop(fr.name, {})
                    yield _sse_event(
                        "tool_result",
                        {
                            "agent": current_agent,
                            "tool": fr.name,
                            "result": _truncate_result(fr.response),
                            "timestamp": ts,
                        },
                    )
                    trace_events.append(
                        {
                            "type": "tool_result",
                            "agent": current_agent,
                            "tool": fr.name,
                            "args": fr_args,
                            "result": fr.response,
                        }
                    )

                # --- Extract text content ---
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            # Only emit thinking for non-final text from sub-agents
                            if not event.is_final_response():
                                yield _sse_event(
                                    "thinking",
                                    {
                                        "agent": current_agent,
                                        "thought": part.text[:300],
                                        "timestamp": ts,
                                    },
                                )
                            response_text += part.text

            # Complete last agent
            if current_agent:
                yield _sse_event(
                    "agent_complete",
                    {
                        "agent": current_agent,
                        "timestamp": time.time(),
                    },
                )

            if not response_text:
                response_text = "Investigation complete."

            # --- Emit final response ---
            yield _sse_event(
                "response",
                {
                    "content": response_text,
                    "session_id": session_id,
                },
            )

            # --- Store conversation in memory (triggers entity extraction) ---
            try:
                await memory_service.add_session(
                    session_id=session_id,
                    messages=[
                        {"role": "user", "content": request.message},
                        {"role": "assistant", "content": response_text},
                    ],
                )
                logger.info("Session stored with entity extraction for %s", session_id)
            except Exception as e:
                logger.warning("Failed to store session: %s", e)

            # --- Save reasoning trace to Neo4j ---
            trace_id = None
            try:
                reasoning = memory_service.client.reasoning
                trace = await reasoning.start_trace(
                    session_id=session_id,
                    task=request.message,
                    generate_embedding=False,
                )
                trace_id = trace.id

                # Group trace events by agent
                current_step = None
                current_step_agent = None
                for te in trace_events:
                    if te["type"] == "agent_start":
                        current_step = await reasoning.add_step(
                            trace_id=trace.id,
                            thought=f"Agent {te['agent']} activated",
                            action=f"Processing as {te['agent']}",
                            generate_embedding=False,
                        )
                        current_step_agent = te["agent"]
                    elif te["type"] == "tool_result" and current_step:
                        await reasoning.record_tool_call(
                            step_id=current_step.id,
                            tool_name=te["tool"],
                            arguments=te.get("args", {}),
                            result=te.get("result"),
                            status=ToolCallStatus.SUCCESS,
                        )

                await reasoning.complete_trace(
                    trace_id=trace.id,
                    outcome=response_text[:500],
                    success=True,
                )

                yield _sse_event(
                    "trace_saved",
                    {
                        "trace_id": str(trace_id),
                        "step_count": step_count,
                        "tool_call_count": tool_call_count,
                    },
                )
                logger.info(
                    "Reasoning trace saved: %s (%d steps, %d tool calls)",
                    trace_id,
                    step_count,
                    tool_call_count,
                )
            except Exception as e:
                logger.warning("Failed to save reasoning trace: %s", e)

            # --- Done ---
            total_duration = int((time.time() - start_time) * 1000)
            yield _sse_event(
                "done",
                {
                    "session_id": session_id,
                    "agents_consulted": sorted(agents_consulted),
                    "tool_call_count": tool_call_count,
                    "total_duration_ms": total_duration,
                    "trace_id": str(trace_id) if trace_id else None,
                },
            )

        except Exception as e:
            logger.error("Stream error: %s", e, exc_info=True)
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    raw_request: Request,
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> ChatResponse:
    """Send a message to the financial advisor and get a response.

    The supervisor agent will analyze the request and delegate to
    specialized agents (KYC, AML, Relationship, Compliance) as needed.
    """
    start_time = time.time()

    # Generate or use existing session ID
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Get neo4j_service from app state (set during startup)
        neo4j_service = getattr(raw_request.app.state, "neo4j_service", None)

        # Get the supervisor agent (passes neo4j_service to tool bindings)
        supervisor = get_supervisor_agent(memory_service, neo4j_service=neo4j_service)

        # Create or get session
        session = await session_service.get_session(
            app_name="financial_advisor",
            user_id="user",
            session_id=session_id,
        )
        if session is None:
            session = await session_service.create_session(
                app_name="financial_advisor",
                user_id="user",
                session_id=session_id,
            )

        # Build context message
        context_parts = []
        if request.customer_id:
            context_parts.append(f"Customer context: {request.customer_id}")
        if request.investigation_id:
            context_parts.append(f"Investigation context: {request.investigation_id}")

        user_message = request.message
        if context_parts:
            user_message = f"{' | '.join(context_parts)}\n\n{request.message}"

        # Create runner and execute
        runner = Runner(
            agent=supervisor,
            app_name="financial_advisor",
            session_service=session_service,
        )

        # Run the agent (run_async returns an async generator of events)
        response_text = ""
        tool_calls = []
        agents_consulted = set()

        async for event in runner.run_async(
            user_id="user",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            ),
        ):
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text
            if hasattr(event, "tool_calls") and event.tool_calls:
                for tc in event.tool_calls:
                    tool_calls.append(
                        ToolCall(
                            tool_name=tc.name,
                            arguments=tc.args or {},
                            agent=getattr(event, "agent_name", None),
                        )
                    )
            if hasattr(event, "agent_name"):
                agents_consulted.add(event.agent_name)

        if not response_text:
            response_text = "Investigation complete."

        # Store the conversation in memory
        await memory_service.add_session(
            session_id=session_id,
            messages=[
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": response_text},
            ],
        )

        response_time = int((time.time() - start_time) * 1000)

        return ChatResponse(
            session_id=session_id,
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=response_text,
            ),
            agents_consulted=list(agents_consulted),
            tool_calls=tool_calls,
            customer_id=request.customer_id,
            investigation_id=request.investigation_id,
            response_time_ms=response_time,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> ConversationHistory:
    """Get conversation history for a session."""
    try:
        entries = await memory_service.get_conversation_history(session_id, limit)

        messages = [
            ChatMessage(
                role=MessageRole(entry.metadata.get("role", "assistant"))
                if entry.metadata
                else MessageRole.ASSISTANT,
                content=entry.content,
            )
            for entry in entries
        ]

        return ConversationHistory(
            session_id=session_id,
            messages=messages,
        )

    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_memory(
    request: SearchRequest,
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> SearchResponse:
    """Search the context graph for relevant information."""
    try:
        results = await memory_service.search_context(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
        )

        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    content=r["content"],
                    type=r["type"],
                    score=r.get("score"),
                    metadata=r.get("metadata", {}),
                )
                for r in results
            ],
            total=len(results),
        )

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> dict[str, str]:
    """Clear a conversation session."""
    try:
        await memory_service.clear_session(session_id)
        return {"status": "cleared", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error clearing session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
