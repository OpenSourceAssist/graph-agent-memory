"""Pydantic AI integration for neo4j-agent-memory."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from pydantic_ai.result import RunResult

    from neo4j_agent_memory import MemoryClient
    from neo4j_agent_memory.memory.procedural import ProceduralMemory, ReasoningTrace

T = TypeVar("T")


@dataclass
class MemoryDependency:
    """
    Pydantic AI dependency for memory access.

    This can be used as the deps_type for a Pydantic AI agent to provide
    memory capabilities.

    Example:
        from pydantic_ai import Agent
        from neo4j_agent_memory import MemoryClient, MemorySettings
        from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency

        agent = Agent(
            'openai:gpt-4o',
            deps_type=MemoryDependency,
            system_prompt=dynamic_system_prompt,
        )

        async def dynamic_system_prompt(ctx: RunContext[MemoryDependency]) -> str:
            memory = ctx.deps
            context = await memory.get_context(ctx.messages[-1].content)
            return f"You are a helpful assistant.\\n\\nContext:\\n{context}"

        async with MemoryClient(settings) as client:
            deps = MemoryDependency(client=client, session_id="user-123")
            result = await agent.run("Find me a restaurant", deps=deps)
    """

    client: "MemoryClient"
    session_id: str

    async def get_context(self, query: str) -> str:
        """
        Get combined context from all memory types.

        Args:
            query: Query to find relevant context

        Returns:
            Formatted context string for LLM prompts
        """
        return await self.client.get_context(query, session_id=self.session_id)

    async def save_interaction(
        self,
        user_message: str,
        assistant_message: str,
        *,
        extract_entities: bool = True,
    ) -> None:
        """
        Save an interaction to memory.

        Args:
            user_message: The user's message
            assistant_message: The assistant's response
            extract_entities: Whether to extract entities from messages
        """
        await self.client.short_term.add_message(
            self.session_id,
            "user",
            user_message,
            extract_entities=extract_entities,
        )
        await self.client.short_term.add_message(
            self.session_id,
            "assistant",
            assistant_message,
            extract_entities=extract_entities,
        )

    async def add_preference(
        self,
        category: str,
        preference: str,
        context: str | None = None,
    ) -> None:
        """
        Add a user preference.

        Args:
            category: Preference category
            preference: The preference statement
            context: When/where preference applies
        """
        await self.client.long_term.add_preference(category, preference, context=context)

    async def search_preferences(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant preferences.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of preference dictionaries
        """
        prefs = await self.client.long_term.search_preferences(query, limit=limit)
        return [
            {
                "category": p.category,
                "preference": p.preference,
                "context": p.context,
                "confidence": p.confidence,
            }
            for p in prefs
        ]


def create_memory_tools(memory: "MemoryClient") -> list[Callable]:
    """
    Create Pydantic AI tools for memory operations.

    Returns tools that can be registered with a Pydantic AI agent for:
    - search_memory: Search across all memory types
    - save_preference: Save a user preference
    - recall_preferences: Get user preferences for a topic

    Example:
        from pydantic_ai import Agent
        from neo4j_agent_memory.integrations.pydantic_ai import create_memory_tools

        async with MemoryClient(settings) as client:
            tools = create_memory_tools(client)
            agent = Agent('openai:gpt-4o', tools=tools)
    """

    async def search_memory(
        query: str,
        memory_types: list[str] | None = None,
    ) -> str:
        """
        Search the agent's memory for relevant information.

        Args:
            query: Search query
            memory_types: Types to search (episodic, semantic, procedural)

        Returns:
            Relevant memories as formatted text
        """
        results = []
        types = memory_types or ["short_term", "long_term", "procedural"]

        if "short_term" in types:
            messages = await memory.short_term.search_messages(query, limit=5)
            for msg in messages:
                results.append(f"[{msg.role.value}] {msg.content}")

        if "long_term" in types:
            entities = await memory.long_term.search_entities(query, limit=5)
            for entity in entities:
                desc = f": {entity.description}" if entity.description else ""
                results.append(f"[{entity.type.value}] {entity.display_name}{desc}")

            prefs = await memory.long_term.search_preferences(query, limit=5)
            for pref in prefs:
                results.append(f"[PREFERENCE:{pref.category}] {pref.preference}")

        if "procedural" in types:
            traces = await memory.procedural.get_similar_traces(query, limit=3)
            for trace in traces:
                status = "succeeded" if trace.success else "failed"
                results.append(f"[TASK] {trace.task} - {status}")

        return "\n".join(results) if results else "No relevant memories found."

    async def save_preference(
        category: str,
        preference: str,
        context: str | None = None,
    ) -> str:
        """
        Save a user preference to memory.

        Args:
            category: Preference category (food, music, etc.)
            preference: The preference statement
            context: When/where it applies

        Returns:
            Confirmation message
        """
        await memory.long_term.add_preference(category, preference, context=context)
        return f"Saved preference: {preference} (category: {category})"

    async def recall_preferences(topic: str) -> str:
        """
        Recall user preferences related to a topic.

        Args:
            topic: Topic to search for

        Returns:
            Relevant preferences as formatted text
        """
        prefs = await memory.long_term.search_preferences(topic, limit=10)
        if not prefs:
            return "No preferences found for this topic."
        return "\n".join([f"- [{p.category}] {p.preference}" for p in prefs])

    return [search_memory, save_preference, recall_preferences]


async def record_agent_trace(
    procedural_memory: "ProceduralMemory",
    session_id: str,
    result: "RunResult[T]",
    *,
    task: str | None = None,
    include_tool_calls: bool = True,
    generate_embeddings: bool = False,
) -> "ReasoningTrace":
    """
    Record a reasoning trace from a PydanticAI RunResult.

    This function extracts tool calls and their results from a completed
    PydanticAI agent run and records them as a reasoning trace in procedural
    memory.

    Args:
        procedural_memory: The procedural memory instance to record to
        session_id: Session ID for the trace
        result: The RunResult from a PydanticAI agent run
        task: Optional task description (defaults to extracting from messages)
        include_tool_calls: Whether to record individual tool calls
        generate_embeddings: Whether to generate embeddings for steps

    Returns:
        The created ReasoningTrace

    Example:
        from pydantic_ai import Agent
        from neo4j_agent_memory.integrations.pydantic_ai import record_agent_trace

        agent = Agent('openai:gpt-4o')
        result = await agent.run("Find restaurants near me")

        # Record the trace
        trace = await record_agent_trace(
            client.procedural,
            session_id="user-123",
            result=result,
            task="Find restaurants",
        )
    """
    # Import here to avoid circular imports and allow optional pydantic-ai dependency
    try:
        from pydantic_ai.messages import (
            ModelRequest,
            ModelResponse,
            ToolCallPart,
            ToolReturnPart,
            UserPromptPart,
        )
    except ImportError as e:
        raise ImportError(
            "pydantic-ai is required for record_agent_trace. Install with: pip install pydantic-ai"
        ) from e

    from neo4j_agent_memory.memory.procedural import ToolCallStatus

    # Extract task from first user message if not provided
    if task is None:
        for msg in result.all_messages():
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        task = str(part.content)[:500]  # Truncate long tasks
                        break
            if task:
                break
        if task is None:
            task = "PydanticAI agent run"

    # Start the trace
    trace = await procedural_memory.start_trace(
        session_id=session_id,
        task=task,
        metadata={
            "source": "pydantic_ai",
            "model": getattr(result, "model", None),
        },
    )

    if include_tool_calls:
        # Collect tool calls and their results
        # Tool calls come from ModelResponse, results come from ModelRequest
        tool_calls: dict[str, dict[str, Any]] = {}  # tool_call_id -> {name, args}
        tool_results: dict[str, Any] = {}  # tool_call_id -> result

        for msg in result.all_messages():
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        tool_call_id = part.tool_call_id or f"call_{len(tool_calls)}"
                        # Extract args safely
                        args = {}
                        if hasattr(part.args, "args_dict"):
                            args = part.args.args_dict
                        elif hasattr(part.args, "model_dump"):
                            args = part.args.model_dump()
                        elif isinstance(part.args, dict):
                            args = part.args

                        tool_calls[tool_call_id] = {
                            "name": part.tool_name,
                            "args": args,
                        }

            elif isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, ToolReturnPart):
                        tool_call_id = part.tool_call_id or ""
                        tool_results[tool_call_id] = part.content

        # Create steps for each tool call
        step_number = 0
        for tool_call_id, call_info in tool_calls.items():
            step_number += 1
            tool_name = call_info["name"]
            tool_args = call_info["args"]
            tool_result = tool_results.get(tool_call_id)

            # Create a reasoning step
            step = await procedural_memory.add_step(
                trace.id,
                thought=f"Using {tool_name} tool",
                action=f"Call {tool_name}",
                observation=_format_tool_result(tool_result) if tool_result else None,
                generate_embedding=generate_embeddings,
                metadata={
                    "tool_call_id": tool_call_id,
                    "step_number": step_number,
                },
            )

            # Record the tool call
            is_error = _is_error_result(tool_result)
            await procedural_memory.record_tool_call(
                step_id=step.id,
                tool_name=tool_name,
                arguments=tool_args,
                result=tool_result,
                status=ToolCallStatus.ERROR if is_error else ToolCallStatus.SUCCESS,
                error=str(tool_result) if is_error else None,
            )

    # Complete the trace with the final output
    final_output = str(result.data) if hasattr(result, "data") else None
    completed_trace = await procedural_memory.complete_trace(
        trace.id,
        outcome=final_output[:1000] if final_output else "Completed",
        success=True,
        generate_step_embeddings=generate_embeddings,
    )

    return completed_trace


def _format_tool_result(result: Any) -> str:
    """Format a tool result for observation field."""
    if result is None:
        return "No result"
    if isinstance(result, str):
        return result[:500] if len(result) > 500 else result
    if isinstance(result, (list, dict)):
        import json

        try:
            formatted = json.dumps(result, default=str)
            return formatted[:500] if len(formatted) > 500 else formatted
        except Exception:
            return str(result)[:500]
    return str(result)[:500]


def _is_error_result(result: Any) -> bool:
    """Check if a tool result indicates an error."""
    if result is None:
        return False
    if isinstance(result, dict):
        return "error" in result or "Error" in result
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            return "error" in first or "Error" in first
    if isinstance(result, str):
        return result.lower().startswith("error:")
    return False
