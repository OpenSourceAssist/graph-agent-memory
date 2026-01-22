"""Thread management API endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    ChatMessage,
    CreateThreadRequest,
    Thread,
    ThreadSummary,
)
from src.memory.client import get_memory_client

router = APIRouter()

# In-memory thread storage (replace with database in production)
_threads: dict[str, dict] = {}


def _get_thread_or_404(thread_id: str) -> dict:
    """Get thread by ID or raise 404."""
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    return _threads[thread_id]


@router.get("/threads", response_model=list[ThreadSummary])
async def list_threads(
    limit: int = 100,
    offset: int = 0,
) -> list[ThreadSummary]:
    """List all conversation threads.

    Uses the new list_sessions() API from neo4j-agent-memory for efficient
    session listing with metadata directly from Neo4j.
    """
    memory = get_memory_client()
    summaries = []

    if memory:
        try:
            # Use the new list_sessions() API for efficient listing
            sessions = await memory.episodic.list_sessions(
                limit=limit,
                offset=offset,
                order_by="updated_at",
                order_dir="desc",
            )

            for session in sessions:
                # Use session data directly from memory
                summaries.append(
                    ThreadSummary(
                        id=session.session_id,
                        title=session.title or session.first_message_preview or "Untitled",
                        created_at=session.created_at,
                        updated_at=session.updated_at or session.created_at,
                        message_count=session.message_count,
                    )
                )

            return summaries
        except Exception as e:
            # Fallback to in-memory storage if memory client fails
            print(f"Warning: Failed to list sessions from memory: {e}")

    # Fallback: use in-memory thread storage
    for thread_id, thread_data in _threads.items():
        message_count = 0
        if memory:
            try:
                conversation = await memory.episodic.get_conversation(thread_id)
                message_count = len(conversation.messages) if conversation else 0
            except Exception:
                pass

        summaries.append(
            ThreadSummary(
                id=thread_id,
                title=thread_data.get("title", "Untitled"),
                created_at=thread_data.get("created_at", datetime.now(timezone.utc)),
                updated_at=thread_data.get("updated_at", datetime.now(timezone.utc)),
                message_count=message_count,
            )
        )

    # Sort by updated_at descending
    summaries.sort(key=lambda x: x.updated_at, reverse=True)
    return summaries[offset : offset + limit]


@router.post("/threads", response_model=ThreadSummary)
async def create_thread(
    request: CreateThreadRequest,
) -> ThreadSummary:
    """Create a new conversation thread."""
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    thread_data = {
        "id": thread_id,
        "title": request.title or "New Conversation",
        "created_at": now,
        "updated_at": now,
    }

    _threads[thread_id] = thread_data

    return ThreadSummary(
        id=thread_id,
        title=thread_data["title"],
        created_at=now,
        updated_at=now,
        message_count=0,
    )


@router.get("/threads/{thread_id}", response_model=Thread)
async def get_thread(
    thread_id: str,
) -> Thread:
    """Get a thread with its messages."""
    thread_data = _get_thread_or_404(thread_id)
    memory = get_memory_client()

    # Get messages from episodic memory
    messages = []
    if memory:
        try:
            conversation = await memory.episodic.get_conversation(thread_id)
            if conversation and conversation.messages:
                for msg in conversation.messages:
                    messages.append(
                        ChatMessage(
                            id=str(msg.id),
                            role=msg.role.value,
                            content=msg.content,
                            timestamp=msg.created_at,
                            tool_calls=[],
                        )
                    )
        except Exception:
            pass

    return Thread(
        id=thread_id,
        title=thread_data.get("title", "Untitled"),
        created_at=thread_data.get("created_at", datetime.now(timezone.utc)),
        updated_at=thread_data.get("updated_at", datetime.now(timezone.utc)),
        messages=messages,
    )


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
) -> dict:
    """Delete a thread and its messages."""
    _get_thread_or_404(thread_id)

    # Delete from local storage
    del _threads[thread_id]

    return {"status": "deleted", "thread_id": thread_id}


@router.patch("/threads/{thread_id}")
async def update_thread(
    thread_id: str,
    title: str | None = None,
) -> ThreadSummary:
    """Update a thread's title."""
    thread_data = _get_thread_or_404(thread_id)

    if title is not None:
        thread_data["title"] = title

    thread_data["updated_at"] = datetime.now(timezone.utc)

    return ThreadSummary(
        id=thread_id,
        title=thread_data["title"],
        created_at=thread_data["created_at"],
        updated_at=thread_data["updated_at"],
        message_count=0,
    )
