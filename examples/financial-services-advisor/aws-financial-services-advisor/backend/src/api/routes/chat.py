"""Chat API routes for agent interaction with SSE streaming support."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...agents import get_supervisor_agent
from ...services.memory_service import get_memory_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User message to the agent")
    session_id: str | None = Field(
        default=None, description="Session ID for conversation continuity"
    )
    customer_id: str | None = Field(
        default=None, description="Customer context for the conversation"
    )
    include_context: bool = Field(
        default=True, description="Whether to include graph context"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID for this conversation")
    agent: str = Field(
        default="supervisor", description="Agent that handled the request"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )


class ConversationMessage(BaseModel):
    """Single message in conversation history."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: str | None = Field(default=None, description="Message timestamp")


class SearchRequest(BaseModel):
    """Request model for conversation search."""

    query: str = Field(..., description="Search query")
    session_id: str | None = Field(default=None, description="Limit search to session")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")


def _sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


def _truncate_result(value: Any, max_len: int = 500) -> str:
    """Always return a string representation, truncated."""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, default=str)
    else:
        text = str(value)
    return text[:max_len] + "..." if len(text) > max_len else text


@router.post("/stream")
async def chat_stream(request: ChatRequest, req: Request) -> StreamingResponse:
    """Chat with the financial advisor via SSE streaming.

    Emits real-time events as agents process the request:
    - agent_start / agent_complete: Agent lifecycle
    - tool_call / tool_result: Tool invocations
    - thinking: Intermediate reasoning
    - response: Final response text
    - trace_saved: Reasoning trace persisted
    - done: Stream complete with summary
    """
    session_id = request.session_id or str(uuid.uuid4())
    start_time = time.time()

    async def event_generator():
        memory_service = get_memory_service()
        neo4j_service = getattr(req.app.state, "neo4j_service", None)

        if not neo4j_service:
            yield _sse_event("error", {"message": "Neo4j service not available"})
            return

        # Store user message
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="user",
            content=request.message,
            metadata={"customer_id": request.customer_id},
        )

        # Build prompt
        prompt = request.message
        if request.customer_id and request.include_context:
            prompt = f"Customer Context: {request.customer_id}\n\nUser Request: {request.message}\n\nPlease analyze and coordinate with specialized agents."

        # Emit start event
        yield _sse_event("agent_start", {
            "agent": "supervisor",
            "timestamp": time.time(),
        })

        # Invoke supervisor (synchronous in Strands)
        try:
            supervisor = get_supervisor_agent(neo4j_service)
            result = supervisor(prompt)
            response_text = str(result)
        except Exception as e:
            logger.error(f"Agent error: {e}")
            yield _sse_event("error", {"message": str(e)})
            return

        # Emit completion events
        yield _sse_event("agent_complete", {
            "agent": "supervisor",
            "timestamp": time.time(),
        })

        yield _sse_event("response", {
            "content": response_text,
            "session_id": session_id,
        })

        # Store assistant response
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
            metadata={"agent": "supervisor"},
        )

        # Trigger entity extraction on the conversation
        try:
            await memory_service.add_session(session_id, [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": response_text},
            ], extract_entities=True)
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")

        # Record reasoning trace
        trace_id = None
        try:
            trace_id_str = await memory_service.start_investigation_trace(
                session_id=session_id,
                task=request.message,
            )
            trace_id = trace_id_str

            await memory_service.add_reasoning_step(
                trace_id=trace_id_str,
                agent="supervisor",
                action="process_request",
                reasoning=f"Processed request: {request.message[:200]}",
                result={"response_length": len(response_text)},
            )

            await memory_service.complete_investigation_trace(
                trace_id=trace_id_str,
                conclusion=response_text[:500],
                success=True,
            )

            yield _sse_event("trace_saved", {
                "trace_id": trace_id_str,
                "step_count": 1,
                "tool_call_count": 0,
            })

        except Exception as e:
            logger.warning(f"Could not save reasoning trace: {e}")

        # Done event
        total_duration_ms = int((time.time() - start_time) * 1000)
        yield _sse_event("done", {
            "session_id": session_id,
            "agents_consulted": ["supervisor"],
            "tool_call_count": 0,
            "total_duration_ms": total_duration_ms,
            "trace_id": trace_id,
        })

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
async def chat_with_agent(request: ChatRequest, req: Request) -> ChatResponse:
    """Chat with the financial advisor agent (synchronous)."""
    session_id = request.session_id or str(uuid.uuid4())

    try:
        memory_service = get_memory_service()
        neo4j_service = getattr(req.app.state, "neo4j_service", None)

        if not neo4j_service:
            raise HTTPException(status_code=503, detail="Neo4j service not available")

        supervisor = get_supervisor_agent(neo4j_service)

        # Store user message
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="user",
            content=request.message,
            metadata={"customer_id": request.customer_id},
        )

        # Build prompt
        prompt = request.message
        if request.customer_id and request.include_context:
            prompt = f"Customer Context: {request.customer_id}\n\nUser Request: {request.message}\n\nPlease analyze and coordinate with specialized agents."

        # Invoke supervisor
        logger.info(f"Processing chat request for session {session_id}")
        result = supervisor(prompt)
        response_text = str(result)

        # Store assistant response
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
            metadata={"agent": "supervisor"},
        )

        # Trigger entity extraction
        try:
            await memory_service.add_session(session_id, [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": response_text},
            ], extract_entities=True)
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")

        # Record reasoning trace
        try:
            trace_id = await memory_service.start_investigation_trace(
                session_id=session_id,
                task=request.message,
            )
            await memory_service.add_reasoning_step(
                trace_id=trace_id,
                agent="supervisor",
                action="process_request",
                reasoning=f"Processed: {request.message[:200]}",
            )
            await memory_service.complete_investigation_trace(
                trace_id=trace_id,
                conclusion=response_text[:500],
                success=True,
            )
        except Exception as e:
            logger.warning(f"Could not save reasoning trace: {e}")

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            agent="supervisor",
            metadata={
                "customer_id": request.customer_id,
                "context_included": request.include_context,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/history/{session_id}", response_model=list[ConversationMessage])
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
) -> list[ConversationMessage]:
    """Get conversation history for a session."""
    try:
        memory_service = get_memory_service()
        messages = await memory_service.get_conversation_history(
            session_id=session_id,
            limit=limit,
        )

        return [
            ConversationMessage(
                role=m["role"],
                content=m["content"],
                timestamp=m.get("timestamp"),
            )
            for m in messages
        ]

    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_conversations(request: SearchRequest) -> list[dict[str, Any]]:
    """Search conversation history semantically."""
    try:
        memory_service = get_memory_service()
        results = await memory_service.search_conversations(
            query=request.query,
            session_id=request.session_id,
            limit=request.limit,
        )
        return results

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
