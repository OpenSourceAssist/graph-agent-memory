"""Microsoft Agent Framework tracing integration.

Records agent executions as reasoning traces for learning from
past interactions and improving future responses.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j_agent_memory.memory.reasoning import ReasoningTrace

    from .memory import Neo4jMicrosoftMemory

logger = logging.getLogger(__name__)

try:
    # Import for type checking, ChatMessage used for isinstance checks
    from agent_framework import ChatMessage  # noqa: F401

    async def record_agent_trace(
        memory: Neo4jMicrosoftMemory,
        messages: list[Any],
        task: str,
        tool_calls: list[dict[str, Any]] | None = None,
        outcome: str | None = None,
        success: bool = True,
        generate_embedding: bool = True,
    ) -> ReasoningTrace:
        """
        Record an agent execution as a reasoning trace.

        Captures the agent's conversation and tool usage as a reasoning trace
        that can be retrieved for similar future tasks.

        .. note::
            Microsoft Agent Framework API - may change before GA.
            Currently targets v1.0.0b251223.

        Args:
            memory: The Neo4jMicrosoftMemory instance.
            messages: The conversation messages from the agent execution.
            task: Description of the task the agent was performing.
            tool_calls: Optional list of tool calls made during execution.
            outcome: Optional description of the outcome.
            success: Whether the task completed successfully.
            generate_embedding: Whether to generate embedding for similarity search.

        Returns:
            The created ReasoningTrace object.

        Example:
            # After agent completes
            trace = await record_agent_trace(
                memory=memory,
                messages=thread.messages,
                task="Help user find running shoes",
                tool_calls=extracted_tool_calls,
                outcome="Recommended 3 pairs of running shoes",
                success=True,
            )
        """
        client = memory.memory_client

        # Start the trace
        trace = await client.reasoning.start_trace(
            session_id=memory.session_id,
            task=task,
            generate_embedding=generate_embedding,
        )

        # Process messages and extract steps
        current_step = None

        for msg in messages:
            role = _get_role(msg)
            content = _get_content(msg)

            if role == "user":
                # User messages become the context/input
                if current_step is None:
                    thought = (
                        f"User input: {content[:200]}"
                        if len(content) > 200
                        else f"User input: {content}"
                    )
                    current_step = await client.reasoning.add_step(
                        trace_id=trace.id,
                        thought=thought,
                    )

            elif role == "assistant":
                # Assistant messages - check for tool calls
                msg_tool_calls = _get_tool_calls(msg)

                if msg_tool_calls:
                    # Create step for tool usage
                    if current_step is None:
                        current_step = await client.reasoning.add_step(
                            trace_id=trace.id,
                            thought="Processing request with tools",
                            action="Using function tools",
                        )

                    # Record each tool call
                    for tc in msg_tool_calls:
                        tool_name = _get_tool_name(tc)
                        arguments = _get_tool_arguments(tc)

                        await client.reasoning.record_tool_call(
                            step_id=current_step.id,
                            tool_name=tool_name,
                            arguments=arguments,
                            status="success",
                        )

                elif content:
                    # Assistant message without tool calls (response)
                    if current_step is None:
                        action = content[:200] + "..." if len(content) > 200 else content
                        current_step = await client.reasoning.add_step(
                            trace_id=trace.id,
                            thought="Generating response",
                            action=action,
                        )

            elif role == "tool":
                # Tool response message
                pass  # Could record tool results here

        # Process explicit tool_calls if provided
        if tool_calls:
            if current_step is None:
                current_step = await client.reasoning.add_step(
                    trace_id=trace.id,
                    thought="Executing tools",
                )

            for tc in tool_calls:
                tool_name = tc.get("name", tc.get("function", {}).get("name", "unknown"))
                arguments = tc.get("arguments", tc.get("function", {}).get("arguments", {}))
                result = tc.get("result")
                status = tc.get("status", "success")
                error = tc.get("error")

                # Parse arguments if string
                if isinstance(arguments, str):
                    try:
                        import json

                        arguments = json.loads(arguments)
                    except (json.JSONDecodeError, TypeError):
                        arguments = {"raw": arguments}

                await client.reasoning.record_tool_call(
                    step_id=current_step.id,
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    status=status,
                    error=error,
                )

        # Complete the trace
        await client.reasoning.complete_trace(
            trace_id=trace.id,
            outcome=outcome,
            success=success,
        )

        # Return the completed trace
        return await client.reasoning.get_trace(trace.id)

    async def get_similar_traces(
        memory: Neo4jMicrosoftMemory,
        task: str,
        limit: int = 5,
    ) -> list[ReasoningTrace]:
        """
        Find similar past reasoning traces for a task.

        Use this to retrieve past experiences that may help inform
        the agent's approach to a similar task.

        Args:
            memory: The Neo4jMicrosoftMemory instance.
            task: The task description to find similar traces for.
            limit: Maximum number of traces to return.

        Returns:
            List of similar ReasoningTrace objects.
        """
        return await memory.memory_client.reasoning.get_similar_traces(
            task=task,
            limit=limit,
        )

    def format_traces_for_prompt(traces: list[ReasoningTrace]) -> str:
        """
        Format reasoning traces for inclusion in a system prompt.

        Args:
            traces: List of ReasoningTrace objects.

        Returns:
            Formatted string describing past similar tasks.
        """
        if not traces:
            return ""

        parts = ["## Past experience with similar tasks:\n"]

        for trace in traces:
            parts.append(f"### Task: {trace.task}")

            if trace.steps:
                parts.append("Steps taken:")
                for step in trace.steps[:3]:  # Limit steps shown
                    if step.thought:
                        thought = (
                            step.thought[:100] + "..." if len(step.thought) > 100 else step.thought
                        )
                        parts.append(f"  - Thought: {thought}")
                    if step.action:
                        action = (
                            step.action[:100] + "..." if len(step.action) > 100 else step.action
                        )
                        parts.append(f"  - Action: {action}")

            if trace.outcome:
                parts.append(f"Outcome: {trace.outcome}")

            if trace.success is not None:
                status = "Succeeded" if trace.success else "Failed"
                parts.append(f"Status: {status}")

            parts.append("")  # Blank line between traces

        return "\n".join(parts)

    # --- Helper functions ---

    def _get_role(msg: Any) -> str | None:
        """Extract role from a message."""
        if isinstance(msg, dict):
            return msg.get("role")
        if hasattr(msg, "role"):
            role = msg.role
            return role.value if hasattr(role, "value") else str(role)
        return None

    def _get_content(msg: Any) -> str:
        """Extract content from a message."""
        if isinstance(msg, dict):
            return msg.get("content", "")
        if hasattr(msg, "content"):
            return msg.content or ""
        return ""

    def _get_tool_calls(msg: Any) -> list[Any]:
        """Extract tool calls from a message."""
        if isinstance(msg, dict):
            return msg.get("tool_calls", [])
        if hasattr(msg, "tool_calls"):
            return msg.tool_calls or []
        return []

    def _get_tool_name(tc: Any) -> str:
        """Extract tool name from a tool call."""
        if isinstance(tc, dict):
            func = tc.get("function", {})
            if isinstance(func, dict):
                return func.get("name", "unknown")
            return tc.get("name", "unknown")
        if hasattr(tc, "function"):
            func = tc.function
            if hasattr(func, "name"):
                return func.name
            if isinstance(func, dict):
                return func.get("name", "unknown")
        if hasattr(tc, "name"):
            return tc.name
        return "unknown"

    def _get_tool_arguments(tc: Any) -> dict[str, Any]:
        """Extract arguments from a tool call."""
        import json

        if isinstance(tc, dict):
            func = tc.get("function", {})
            if isinstance(func, dict):
                args = func.get("arguments", {})
            else:
                args = tc.get("arguments", {})
        elif hasattr(tc, "function"):
            func = tc.function
            if hasattr(func, "arguments"):
                args = func.arguments
            elif isinstance(func, dict):
                args = func.get("arguments", {})
            else:
                args = {}
        elif hasattr(tc, "arguments"):
            args = tc.arguments
        else:
            args = {}

        # Parse if string
        if isinstance(args, str):
            try:
                return json.loads(args)
            except (json.JSONDecodeError, TypeError):
                return {"raw": args}

        return args if isinstance(args, dict) else {}


except ImportError:
    # Microsoft Agent Framework not installed
    pass
