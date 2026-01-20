"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# Chat schemas
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    thread_id: str = Field(..., description="The conversation thread ID")
    message: str = Field(..., description="The user's message")
    memory_enabled: bool = Field(default=True, description="Whether to use memory")


class ToolCallInfo(BaseModel):
    """Information about a tool call."""

    id: str
    name: str
    args: dict[str, Any]
    result: Any | None = None
    status: str = "pending"
    duration_ms: float | None = None


class ChatMessage(BaseModel):
    """A chat message."""

    id: str
    role: str
    content: str
    timestamp: datetime
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)


# Thread schemas
class CreateThreadRequest(BaseModel):
    """Request model for creating a thread."""

    title: str | None = Field(default=None, description="Optional thread title")


class ThreadSummary(BaseModel):
    """Summary of a conversation thread."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class Thread(BaseModel):
    """Full thread with messages."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = Field(default_factory=list)


# Preference schemas
class PreferenceRequest(BaseModel):
    """Request model for adding a preference."""

    category: str = Field(..., description="Preference category")
    preference: str = Field(..., description="The preference value")
    context: str | None = Field(default=None, description="Optional context")


class Preference(BaseModel):
    """A user preference."""

    id: str
    category: str
    preference: str
    context: str | None = None
    confidence: float = 1.0
    created_at: datetime | None = None


# Entity schemas
class Entity(BaseModel):
    """An extracted entity."""

    id: str
    name: str
    type: str
    subtype: str | None = None
    description: str | None = None


# Memory context schemas
class RecentMessage(BaseModel):
    """A recent message from episodic memory."""

    id: str
    role: str
    content: str
    created_at: str | None = None


class MemoryContext(BaseModel):
    """Memory context for display."""

    preferences: list[Preference] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)
    recent_messages: list[RecentMessage] = Field(default_factory=list)


# Graph visualization schemas
class GraphNode(BaseModel):
    """A node in the memory graph."""

    id: str
    labels: list[str]
    properties: dict[str, Any]


class GraphRelationship(BaseModel):
    """A relationship in the memory graph."""

    id: str
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    type: str
    properties: dict[str, Any]

    class Config:
        populate_by_name = True


class MemoryGraph(BaseModel):
    """The complete memory graph for visualization."""

    nodes: list[GraphNode] = Field(default_factory=list)
    relationships: list[GraphRelationship] = Field(default_factory=list)


# SSE event types
class SSETokenEvent(BaseModel):
    """SSE event for streaming tokens."""

    type: str = "token"
    content: str


class SSEToolCallEvent(BaseModel):
    """SSE event for tool call start."""

    type: str = "tool_call"
    id: str
    name: str
    args: dict[str, Any]


class SSEToolResultEvent(BaseModel):
    """SSE event for tool call result."""

    type: str = "tool_result"
    id: str
    name: str
    result: Any
    duration_ms: float


class SSEDoneEvent(BaseModel):
    """SSE event for completion."""

    type: str = "done"
    message_id: str
    trace_id: str | None = None


class SSEErrorEvent(BaseModel):
    """SSE event for errors."""

    type: str = "error"
    message: str
