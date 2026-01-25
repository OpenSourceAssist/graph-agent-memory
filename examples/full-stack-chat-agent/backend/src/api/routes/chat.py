"""Chat API endpoint with SSE streaming."""

import json
import logging
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from neo4j import AsyncGraphDatabase
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)
from sse_starlette.sse import EventSourceResponse

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.memory.short_term import MessageRole
from src.agent.agent import get_news_agent
from src.agent.dependencies import AgentDeps
from src.api.schemas import ChatRequest
from src.config import get_settings
from src.memory.client import get_memory_client

router = APIRouter()
logger = logging.getLogger(__name__)


def safe_serialize(obj: Any) -> Any:
    """Safely convert an object to JSON-serializable format."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return [safe_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): safe_serialize(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        return safe_serialize(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return safe_serialize(obj.__dict__)
    # For non-serializable objects, convert to string
    return str(obj)


async def create_news_driver():
    """Create Neo4j driver for news graph."""
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.news_graph_uri,
        auth=(
            settings.news_graph_username,
            settings.news_graph_password.get_secret_value(),
        ),
    )
    return driver


# Keywords that indicate preference statements
PREFERENCE_INDICATORS = [
    "i prefer",
    "i like",
    "i want",
    "i love",
    "i enjoy",
    "i'd rather",
    "i would rather",
    "please use",
    "please give me",
    "please provide",
    "i'm interested in",
    "i am interested in",
    "my preference is",
    "my favorite",
    "i hate",
    "i don't like",
    "i dislike",
    "avoid",
    "don't give me",
]


async def extract_and_store_preferences(
    memory: MemoryClient,
    message: str,
    session_id: str,
) -> None:
    """Extract preferences from user message and store in long-term memory.

    This uses simple keyword matching to identify preference statements.
    For production, an LLM-based extractor would be more accurate.
    """
    message_lower = message.lower()

    # Check if the message contains preference indicators
    has_preference = any(indicator in message_lower for indicator in PREFERENCE_INDICATORS)

    if not has_preference:
        return

    # Categorize the preference
    category = "general"
    if any(
        word in message_lower
        for word in ["format", "summary", "summaries", "bullet", "concise", "brief", "detailed"]
    ):
        category = "format"
    elif any(word in message_lower for word in ["topic", "subject", "news", "articles", "stories"]):
        category = "content"
    elif any(
        word in message_lower
        for word in ["business", "technology", "tech", "sports", "politics", "entertainment"]
    ):
        category = "topics"
    elif any(word in message_lower for word in ["location", "city", "country", "region", "local"]):
        category = "location"

    try:
        # Store the preference
        await memory.long_term.add_preference(
            category=category,
            preference=message,
            context=f"Extracted from conversation in session {session_id}",
            confidence=0.8,  # Slightly lower confidence for auto-extracted
        )
        logger.info(f"Stored preference: [{category}] {message[:50]}...")
    except Exception as e:
        logger.warning(f"Failed to store preference: {e}")


async def stream_chat_response(
    request: ChatRequest,
    memory: MemoryClient | None,
) -> AsyncGenerator[dict, None]:
    """Stream chat response as SSE events.

    Yields dicts that EventSourceResponse will serialize to JSON.
    """
    message_id = str(uuid.uuid4())
    trace_id = None
    memory_enabled = request.memory_enabled and memory is not None

    try:
        # Create news driver
        news_driver = await create_news_driver()

        try:
            # Create agent dependencies
            deps = AgentDeps.create(
                memory=memory,
                session_id=request.thread_id,
                news_driver=news_driver,
                memory_enabled=memory_enabled,
            )

            # Store user message in short-term memory
            user_message_id = None
            if memory_enabled and memory:
                user_message = await memory.short_term.add_message(
                    session_id=request.thread_id,
                    role=MessageRole.USER,
                    content=request.message,
                )
                user_message_id = user_message.id

                # Extract and store any preferences from the user message
                await extract_and_store_preferences(
                    memory=memory,
                    message=request.message,
                    session_id=request.thread_id,
                )

            # Start reasoning trace if memory enabled, linked to user message
            if memory_enabled and memory:
                trace = await memory.reasoning.start_trace(
                    session_id=request.thread_id,
                    task=request.message,
                    triggered_by_message_id=user_message_id,  # Link trace to triggering message
                )
                trace_id = trace.id

            # Run agent with streaming
            full_response = ""
            agent = get_news_agent()

            async with agent.run_stream(
                request.message,
                deps=deps,
            ) as result:
                # Stream text tokens
                async for text in result.stream_text(delta=True):
                    full_response += text
                    yield {"data": json.dumps({"type": "token", "content": text})}

                # Process messages for tool calls
                for msg in result.all_messages():
                    if isinstance(msg, ModelResponse):
                        for part in msg.parts:
                            if isinstance(part, ToolCallPart):
                                # Get args safely
                                args = {}
                                if hasattr(part.args, "args_dict"):
                                    args = safe_serialize(part.args.args_dict)
                                elif hasattr(part.args, "model_dump"):
                                    args = safe_serialize(part.args.model_dump())

                                # Emit tool call event
                                event = {
                                    "type": "tool_call",
                                    "id": part.tool_call_id or str(uuid.uuid4()),
                                    "name": part.tool_name,
                                    "args": args,
                                }
                                yield {"data": json.dumps(event)}

                    if isinstance(msg, ModelRequest):
                        for part in msg.parts:
                            if isinstance(part, ToolReturnPart):
                                # Emit tool result event
                                event = {
                                    "type": "tool_result",
                                    "id": part.tool_call_id or "",
                                    "name": part.tool_name,
                                    "result": safe_serialize(part.content),
                                    "duration_ms": 0,
                                }
                                yield {"data": json.dumps(event)}

            # Store assistant response in short-term memory
            if memory_enabled and memory:
                await memory.short_term.add_message(
                    session_id=request.thread_id,
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                )

            # Complete reasoning trace
            if trace_id and memory:
                await memory.reasoning.complete_trace(
                    trace_id,
                    outcome=full_response[:500],
                    success=True,
                )

            # Send done event
            event = {
                "type": "done",
                "message_id": message_id,
                "trace_id": str(trace_id) if trace_id else None,
            }
            yield {"data": json.dumps(event)}

        finally:
            await news_driver.close()

    except Exception as e:
        # Send error event
        event = {"type": "error", "message": str(e)}
        yield {"data": json.dumps(event)}


@router.post("/chat")
async def chat(
    request: ChatRequest,
) -> EventSourceResponse:
    """Handle chat with SSE streaming response.

    Request body:
    - thread_id: The conversation thread ID
    - message: The user's message
    - memory_enabled: Whether to use memory (default True)

    Response: Server-Sent Events stream with:
    - {"type": "token", "content": "..."}
    - {"type": "tool_call", "id": "...", "name": "...", "args": {...}}
    - {"type": "tool_result", "id": "...", "name": "...", "result": {...}}
    - {"type": "done", "message_id": "...", "trace_id": "..."}
    - {"type": "error", "message": "..."}
    """
    memory = get_memory_client()
    return EventSourceResponse(stream_chat_response(request, memory))
