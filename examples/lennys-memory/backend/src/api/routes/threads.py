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
            sessions = await memory.short_term.list_sessions(
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
                conversation = await memory.short_term.get_conversation(thread_id)
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
    """Get a thread with its messages.

    First checks in-memory storage, then falls back to Neo4j sessions
    (e.g., loaded podcast transcripts).
    """
    memory = get_memory_client()
    thread_data = _threads.get(thread_id)

    # If not in local storage, try to get from Neo4j
    if thread_data is None and memory:
        try:
            conversation = await memory.short_term.get_conversation(thread_id)
            if conversation:
                # Create thread_data from Neo4j session
                thread_data = {
                    "id": thread_id,
                    "title": conversation.title or thread_id,
                    "created_at": conversation.created_at or datetime.now(timezone.utc),
                    "updated_at": conversation.updated_at or conversation.created_at or datetime.now(timezone.utc),
                }
        except Exception:
            pass

    if thread_data is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Get messages from short-term memory
    messages = []
    if memory:
        try:
            conversation = await memory.short_term.get_conversation(thread_id)
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
    memory = get_memory_client()

    # Check if thread exists in local storage or Neo4j
    exists_locally = thread_id in _threads
    exists_in_neo4j = False

    if memory:
        try:
            conversation = await memory.short_term.get_conversation(thread_id)
            exists_in_neo4j = conversation is not None
        except Exception:
            pass

    if not exists_locally and not exists_in_neo4j:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Delete from local storage if present
    if exists_locally:
        del _threads[thread_id]

    # Delete from Neo4j if present
    if exists_in_neo4j and memory:
        try:
            await memory.short_term.delete_conversation(thread_id)
        except Exception:
            pass

    return {"status": "deleted", "thread_id": thread_id}


@router.patch("/threads/{thread_id}")
async def update_thread(
    thread_id: str,
    title: str | None = None,
) -> ThreadSummary:
    """Update a thread's title."""
    memory = get_memory_client()
    thread_data = _threads.get(thread_id)

    # If not in local storage, try to get from Neo4j
    if thread_data is None and memory:
        try:
            conversation = await memory.short_term.get_conversation(thread_id)
            if conversation:
                # Create thread_data from Neo4j session and store locally
                thread_data = {
                    "id": thread_id,
                    "title": conversation.title or thread_id,
                    "created_at": conversation.created_at or datetime.now(timezone.utc),
                    "updated_at": conversation.updated_at or conversation.created_at or datetime.now(timezone.utc),
                }
                _threads[thread_id] = thread_data
        except Exception:
            pass

    if thread_data is None:
        raise HTTPException(status_code=404, detail="Thread not found")

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
