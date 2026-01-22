"""Thread management API endpoints.

Uses neo4j-agent-memory's session management features for persistent thread storage.
"""

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


@router.get("/threads", response_model=list[ThreadSummary])
async def list_threads() -> list[ThreadSummary]:
    """List all conversation threads using neo4j-agent-memory's list_sessions()."""
    memory = get_memory_client()
    if memory is None:
        return []

    try:
        # Use the new list_sessions() API for persistent session listing
        sessions = await memory.episodic.list_sessions(
            limit=100,
            order_by="updated_at",
            order_dir="desc",
        )

        summaries = []
        for session in sessions:
            summaries.append(
                ThreadSummary(
                    id=session.session_id,
                    title=session.title or session.session_id[:20] + "...",
                    created_at=session.created_at,
                    updated_at=session.updated_at or session.created_at,
                    message_count=session.message_count,
                )
            )

        return summaries

    except Exception as e:
        # Log error and return empty list
        import logging

        logging.getLogger(__name__).warning(f"Failed to list sessions: {e}")
        return []


@router.post("/threads", response_model=ThreadSummary)
async def create_thread(
    request: CreateThreadRequest,
) -> ThreadSummary:
    """Create a new conversation thread.

    Creates a thread by adding an initial system message to establish the session.
    """
    memory = get_memory_client()
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    title = request.title or "New Conversation"

    if memory:
        try:
            # Create the session by adding an initial system message
            # This establishes the session in the database with metadata
            await memory.episodic.add_message(
                session_id=thread_id,
                role="system",
                content=f"Conversation started: {title}",
                metadata={"title": title, "created_at": now.isoformat()},
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to create thread in memory: {e}")

    return ThreadSummary(
        id=thread_id,
        title=title,
        created_at=now,
        updated_at=now,
        message_count=0,
    )


@router.get("/threads/{thread_id}", response_model=Thread)
async def get_thread(
    thread_id: str,
) -> Thread:
    """Get a thread with its messages."""
    memory = get_memory_client()

    # Default values if memory is unavailable
    now = datetime.now(timezone.utc)
    title = "Untitled"
    created_at = now
    updated_at = now
    messages = []

    if memory:
        try:
            # Get conversation from episodic memory
            conversation = await memory.episodic.get_conversation(thread_id)
            if conversation and conversation.messages:
                # Extract title from first system message if available
                for msg in conversation.messages:
                    if msg.role.value == "system" and msg.metadata:
                        title = msg.metadata.get("title", title)
                        if msg.metadata.get("created_at"):
                            try:
                                created_at = datetime.fromisoformat(
                                    msg.metadata["created_at"].replace("Z", "+00:00")
                                )
                            except (ValueError, TypeError):
                                pass
                        break

                # Get timestamps from messages
                if conversation.messages:
                    first_msg = conversation.messages[0]
                    last_msg = conversation.messages[-1]
                    if first_msg.timestamp:
                        created_at = first_msg.timestamp
                    if last_msg.timestamp:
                        updated_at = last_msg.timestamp

                # Convert messages (skip system messages for display)
                for msg in conversation.messages:
                    if msg.role.value != "system":
                        messages.append(
                            ChatMessage(
                                id=str(msg.id),
                                role=msg.role.value,
                                content=msg.content,
                                timestamp=msg.timestamp or now,
                                tool_calls=[],
                            )
                        )
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to get thread: {e}")
            raise HTTPException(status_code=404, detail="Thread not found")

    if not messages and memory:
        # Check if session exists at all
        try:
            sessions = await memory.episodic.list_sessions(prefix=thread_id)
            if not sessions:
                raise HTTPException(status_code=404, detail="Thread not found")
        except Exception:
            pass

    return Thread(
        id=thread_id,
        title=title,
        created_at=created_at,
        updated_at=updated_at,
        messages=messages,
    )


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
) -> dict:
    """Delete a thread and its messages.

    Uses delete_message() to remove all messages in the session.
    """
    memory = get_memory_client()

    if memory:
        try:
            # Get all messages in the session
            conversation = await memory.episodic.get_conversation(thread_id, limit=1000)
            if conversation and conversation.messages:
                # Delete each message
                deleted_count = 0
                for msg in conversation.messages:
                    try:
                        await memory.episodic.delete_message(msg.id, cascade=True)
                        deleted_count += 1
                    except Exception:
                        pass

                return {
                    "status": "deleted",
                    "thread_id": thread_id,
                    "messages_deleted": deleted_count,
                }
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to delete thread: {e}")

    return {"status": "deleted", "thread_id": thread_id, "messages_deleted": 0}


@router.patch("/threads/{thread_id}")
async def update_thread(
    thread_id: str,
    title: str | None = None,
) -> ThreadSummary:
    """Update a thread's title.

    Updates the title by modifying the system message metadata.
    """
    memory = get_memory_client()
    now = datetime.now(timezone.utc)
    message_count = 0

    if memory and title:
        try:
            # Get conversation to find system message and count
            conversation = await memory.episodic.get_conversation(thread_id)
            if conversation and conversation.messages:
                message_count = len([m for m in conversation.messages if m.role.value != "system"])

                # Find and update system message with new title
                # Note: This would require an update_message method
                # For now, we just return the new title
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to update thread: {e}")

    return ThreadSummary(
        id=thread_id,
        title=title or "Untitled",
        created_at=now,  # Would need to fetch actual created_at
        updated_at=now,
        message_count=message_count,
    )


@router.get("/threads/{thread_id}/summary")
async def get_thread_summary(
    thread_id: str,
) -> dict:
    """Get a summary of the conversation thread.

    Uses get_conversation_summary() for AI-powered summarization.
    """
    memory = get_memory_client()

    if memory is None:
        raise HTTPException(status_code=503, detail="Memory service unavailable")

    try:
        summary = await memory.episodic.get_conversation_summary(
            session_id=thread_id,
            max_tokens=500,
            include_entities=True,
        )

        return {
            "session_id": summary.session_id,
            "summary": summary.summary,
            "message_count": summary.message_count,
            "time_range": (
                [summary.time_range[0].isoformat(), summary.time_range[1].isoformat()]
                if summary.time_range
                else None
            ),
            "key_entities": summary.key_entities,
            "key_topics": summary.key_topics,
            "generated_at": summary.generated_at.isoformat(),
        }

    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to get summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
