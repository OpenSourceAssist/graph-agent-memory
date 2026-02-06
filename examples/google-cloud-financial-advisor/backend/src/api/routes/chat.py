"""Chat API routes for interacting with the financial advisor agents."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

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
from ...services.memory_service import FinancialMemoryService, get_memory_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Session service for ADK
session_service = InMemorySessionService()


async def get_initialized_memory_service() -> FinancialMemoryService:
    """Get the initialized memory service."""
    service = get_memory_service()
    if not service._initialized:
        await service.initialize()
    return service


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
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
        # Get the supervisor agent
        supervisor = get_supervisor_agent(memory_service)

        # Create or get session
        session = session_service.get_session(
            app_name="financial_advisor",
            user_id="user",
            session_id=session_id,
        )
        if session is None:
            session = session_service.create_session(
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

        # Run the agent
        result = await runner.run_async(
            user_id="user",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            ),
        )

        # Extract response content
        response_text = ""
        tool_calls = []
        agents_consulted = set()

        for event in result.events:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text
            if hasattr(event, "tool_calls"):
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

        # If no text response, try to get from final output
        if not response_text and hasattr(result, "output"):
            response_text = (
                str(result.output) if result.output else "Investigation complete."
            )

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
