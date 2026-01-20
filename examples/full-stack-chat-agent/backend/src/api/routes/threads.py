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
async def list_threads() -> list[ThreadSummary]:
    """List all conversation threads."""
    summaries = []
    memory = get_memory_client()

    for thread_id, thread_data in _threads.items():
        # Get message count from episodic memory
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
    return summaries


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
                            id=msg.id,
                            role=msg.role.value,
                            content=msg.content,
                            timestamp=msg.timestamp,
                            tool_calls=[],  # Tool calls would need separate tracking
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

    # Note: Episodic memory messages would need a delete method
    # For now, we just delete the thread reference

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
