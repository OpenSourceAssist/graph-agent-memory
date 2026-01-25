"""Chat API endpoint with SSE streaming."""

import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from sse_starlette.sse import EventSourceResponse

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.memory.reasoning import ToolCallStatus
from neo4j_agent_memory.memory.short_term import MessageRole
from src.agent.agent import get_podcast_agent
from src.agent.dependencies import AgentDeps
from src.api.schemas import ChatRequest
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


async def get_conversation_history(
    memory: MemoryClient,
    session_id: str,
    limit: int = 20,
) -> list[ModelRequest | ModelResponse]:
    """Fetch conversation history and convert to PydanticAI message format.

    Args:
        memory: The memory client.
        session_id: The conversation session ID.
        limit: Maximum number of messages to retrieve.

    Returns:
        List of PydanticAI messages suitable for message_history parameter.
    """
    try:
        conversation = await memory.short_term.get_conversation(
            session_id=session_id,
            limit=limit,
        )

        if not conversation or not conversation.messages:
            return []

        history: list[ModelRequest | ModelResponse] = []

        for msg in conversation.messages:
            if msg.role == MessageRole.USER:
                # User messages become ModelRequest with UserPromptPart
                history.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
            elif msg.role == MessageRole.ASSISTANT:
                # Assistant messages become ModelResponse with TextPart
                history.append(ModelResponse(parts=[TextPart(content=msg.content)]))
            # Skip system messages as they're handled by the system prompt

        return history

    except Exception as e:
        logger.warning(f"Failed to fetch conversation history: {e}")
        return []


async def extract_and_store_preferences(
    memory: MemoryClient,
    message: str,
    session_id: str,
) -> None:
    """Extract preferences from user message and store in long-term memory."""
    message_lower = message.lower()

    # Check if the message contains preference indicators
    has_preference = any(indicator in message_lower for indicator in PREFERENCE_INDICATORS)

    if not has_preference:
        return

    # Categorize the preference
    category = "general"
    if any(
        word in message_lower
        for word in [
            "format",
            "summary",
            "summaries",
            "bullet",
            "concise",
            "brief",
            "detailed",
        ]
    ):
        category = "format"
    elif any(word in message_lower for word in ["topic", "subject", "podcast", "episode", "guest"]):
        category = "content"
    elif any(
        word in message_lower
        for word in [
            "product",
            "growth",
            "startup",
            "leadership",
            "career",
            "mental health",
        ]
    ):
        category = "topics"

    try:
        await memory.long_term.add_preference(
            category=category,
            preference=message,
            context=f"Extracted from conversation in session {session_id}",
            confidence=0.8,
        )
        logger.info(f"Stored preference: [{category}] {message[:50]}...")
    except Exception as e:
        logger.warning(f"Failed to store preference: {e}")


async def stream_chat_response(
    request: ChatRequest,
    memory: MemoryClient | None,
) -> AsyncGenerator[dict, None]:
    """Stream chat response as SSE events with full reasoning memory tracking."""
    message_id = str(uuid.uuid4())
    trace_id: UUID | None = None
    current_step_id: UUID | None = None
    memory_enabled = request.memory_enabled and memory is not None
    task_success = True
    error_message: str | None = None

    # Track tool call timings (tool_call_id -> start_time)
    tool_call_start_times: dict[str, float] = {}

    try:
        # Get conversation history before adding the new message
        message_history: list[ModelRequest | ModelResponse] = []
        if memory_enabled and memory:
            message_history = await get_conversation_history(
                memory=memory,
                session_id=request.thread_id,
                limit=20,  # Last 20 messages for context
            )
            logger.info(f"Loaded {len(message_history)} messages from conversation history")

        # Create agent dependencies with current query for similar trace lookup
        deps = AgentDeps.create(
            memory=memory,
            session_id=request.thread_id,
            memory_enabled=memory_enabled,
            current_query=request.message,
        )

        # Store user message in short-term memory
        if memory_enabled and memory:
            await memory.short_term.add_message(
                session_id=request.thread_id,
                role=MessageRole.USER,
                content=request.message,
            )

            # Extract and store any preferences from the user message
            await extract_and_store_preferences(
                memory=memory,
                message=request.message,
                session_id=request.thread_id,
            )

        # Start reasoning trace if memory enabled
        if memory_enabled and memory:
            trace = await memory.reasoning.start_trace(
                session_id=request.thread_id,
                task=request.message,
                metadata={"message_id": message_id},
            )
            trace_id = trace.id
            logger.info(f"Started reasoning trace: {trace_id}")

        # Run agent with streaming and conversation history
        full_response = ""
        agent = get_podcast_agent()

        async with agent.run_stream(
            request.message,
            deps=deps,
            message_history=message_history if message_history else None,
        ) as result:
            # Stream text tokens
            async for text in result.stream_text(delta=True):
                full_response += text
                yield {"data": json.dumps({"type": "token", "content": text})}

            # Process messages for tool calls and record to reasoning memory
            step_number = 0
            for msg in result.all_messages():
                if isinstance(msg, ModelResponse):
                    for part in msg.parts:
                        if isinstance(part, ToolCallPart):
                            # Get args safely using args_as_dict() method
                            args = {}
                            try:
                                args = safe_serialize(part.args_as_dict())
                            except Exception:
                                # Fallback: try direct access if args is already a dict
                                if isinstance(part.args, dict):
                                    args = safe_serialize(part.args)
                                elif isinstance(part.args, str):
                                    try:
                                        args = json.loads(part.args)
                                    except json.JSONDecodeError:
                                        args = {"raw": part.args}

                            tool_call_id = part.tool_call_id or str(uuid.uuid4())

                            # Record start time for duration calculation
                            tool_call_start_times[tool_call_id] = time.time()

                            # Create a reasoning step for this tool call if memory enabled
                            if trace_id and memory:
                                step_number += 1
                                step = await memory.reasoning.add_step(
                                    trace_id,
                                    thought=f"Need to use {part.tool_name} tool",
                                    action=f"Calling {part.tool_name} with args: {json.dumps(args)[:200]}",
                                    generate_embedding=False,  # Skip embedding for performance
                                    metadata={
                                        "tool_call_id": tool_call_id,
                                        "tool_name": part.tool_name,
                                    },
                                )
                                current_step_id = step.id
                                logger.debug(
                                    f"Created reasoning step {step_number} for tool {part.tool_name}"
                                )

                            # Emit tool call event
                            event = {
                                "type": "tool_call",
                                "id": tool_call_id,
                                "name": part.tool_name,
                                "args": args,
                            }
                            yield {"data": json.dumps(event)}

                if isinstance(msg, ModelRequest):
                    for part in msg.parts:
                        if isinstance(part, ToolReturnPart):
                            tool_call_id = part.tool_call_id or ""

                            # Calculate duration
                            duration_ms = 0
                            if tool_call_id in tool_call_start_times:
                                duration_ms = int(
                                    (time.time() - tool_call_start_times[tool_call_id]) * 1000
                                )
                                del tool_call_start_times[tool_call_id]

                            # Determine status based on result
                            result_content = safe_serialize(part.content)
                            is_error = False
                            if isinstance(result_content, list) and result_content:
                                # Check if result contains error
                                if (
                                    isinstance(result_content[0], dict)
                                    and "error" in result_content[0]
                                ):
                                    is_error = True

                            # Record tool call to reasoning memory
                            if current_step_id and memory:
                                try:
                                    await memory.reasoning.record_tool_call(
                                        step_id=current_step_id,
                                        tool_name=part.tool_name,
                                        arguments=args if "args" in dir() else {},
                                        result=result_content,
                                        status=ToolCallStatus.ERROR
                                        if is_error
                                        else ToolCallStatus.SUCCESS,
                                        duration_ms=duration_ms,
                                        error=str(result_content[0].get("error"))
                                        if is_error and isinstance(result_content, list)
                                        else None,
                                    )
                                    logger.debug(
                                        f"Recorded tool call {part.tool_name} "
                                        f"(duration: {duration_ms}ms, status: {'error' if is_error else 'success'})"
                                    )
                                except Exception as e:
                                    logger.warning(f"Failed to record tool call: {e}")

                            # Emit tool result event
                            event = {
                                "type": "tool_result",
                                "id": tool_call_id,
                                "name": part.tool_name,
                                "result": result_content,
                                "duration_ms": duration_ms,
                            }
                            yield {"data": json.dumps(event)}

        # Store assistant response in short-term memory
        if memory_enabled and memory:
            await memory.short_term.add_message(
                session_id=request.thread_id,
                role=MessageRole.ASSISTANT,
                content=full_response,
            )

    except Exception as e:
        logger.exception("Error in chat stream")
        task_success = False
        error_message = str(e)
        event = {"type": "error", "message": str(e)}
        yield {"data": json.dumps(event)}

    finally:
        # Complete reasoning trace with outcome
        if trace_id and memory:
            try:
                await memory.reasoning.complete_trace(
                    trace_id,
                    outcome=full_response[:500] if task_success else f"Error: {error_message}",
                    success=task_success,
                )
                logger.info(f"Completed reasoning trace: {trace_id} (success: {task_success})")
            except Exception as e:
                logger.warning(f"Failed to complete reasoning trace: {e}")

        # Send done event (only if not already sent error)
        if task_success:
            event = {
                "type": "done",
                "message_id": message_id,
                "trace_id": str(trace_id) if trace_id else None,
            }
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
