"""Chat models for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ToolCall(BaseModel):
    """Record of a tool call made by an agent."""

    tool_name: str = Field(..., description="Name of the tool called")
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = Field(None, description="Tool result")
    agent: str | None = Field(None, description="Agent that made the call")
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: int | None = Field(None)


class AgentResponse(BaseModel):
    """Response from a specific agent."""

    agent_name: str = Field(..., description="Name of the agent")
    content: str = Field(..., description="Agent response content")
    tool_calls: list[ToolCall] = Field(default_factory=list)
    delegated_to: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatMessage(BaseModel):
    """A single chat message."""

    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)

    # Agent-specific fields
    agent_responses: list[AgentResponse] = Field(default_factory=list)
    thinking: str | None = Field(None, description="Agent reasoning (if visible)")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User message")
    session_id: str | None = Field(None, description="Session ID for continuity")
    customer_id: str | None = Field(None, description="Customer context")
    investigation_id: str | None = Field(None, description="Investigation context")
    stream: bool = Field(default=False, description="Whether to stream response")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    session_id: str = Field(..., description="Session identifier")
    message: ChatMessage = Field(..., description="Assistant response")

    # Agent activity
    agents_consulted: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)

    # Context
    customer_id: str | None = Field(None)
    investigation_id: str | None = Field(None)

    # Performance
    response_time_ms: int | None = Field(None)


class ConversationHistory(BaseModel):
    """Conversation history response."""

    session_id: str
    messages: list[ChatMessage]
    customer_id: str | None = None
    investigation_id: str | None = None
    created_at: datetime | None = None
    last_message_at: datetime | None = None


class SearchRequest(BaseModel):
    """Request model for memory search."""

    query: str = Field(..., description="Search query")
    session_id: str | None = Field(None, description="Limit to session")
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0, le=1)


class SearchResult(BaseModel):
    """Individual search result."""

    content: str
    type: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response model for memory search."""

    query: str
    results: list[SearchResult]
    total: int
