"""Chat API routes for agent interaction."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
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


@router.post("", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """Chat with the financial advisor agent.

    The supervisor agent will analyze your request and delegate to
    specialized sub-agents (KYC, AML, Relationship, Compliance) as needed.

    Args:
        request: Chat request with message and optional context

    Returns:
        Agent response with session information
    """
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Get services
        memory_service = get_memory_service()
        supervisor = get_supervisor_agent()

        # Store user message in conversation memory
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="user",
            content=request.message,
            metadata={
                "customer_id": request.customer_id,
            },
        )

        # Build prompt with context
        prompt = request.message

        if request.customer_id and request.include_context:
            prompt = f"""Customer Context: {request.customer_id}

User Request: {request.message}

Please analyze this request and coordinate with specialized agents as needed."""

        # Invoke the supervisor agent
        logger.info(f"Processing chat request for session {session_id}")
        result = supervisor(prompt)
        response_text = str(result)

        # Store assistant response
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
            metadata={
                "agent": "supervisor",
            },
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            agent="supervisor",
            metadata={
                "customer_id": request.customer_id,
                "context_included": request.include_context,
            },
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/history/{session_id}", response_model=list[ConversationMessage])
async def get_conversation_history(
    session_id: str,
    limit: int = 50,
) -> list[ConversationMessage]:
    """Get conversation history for a session.

    Args:
        session_id: The session identifier
        limit: Maximum messages to return

    Returns:
        List of conversation messages
    """
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
    """Search conversation history semantically.

    Args:
        request: Search parameters

    Returns:
        Matching conversation excerpts with relevance scores
    """
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
