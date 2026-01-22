"""Procedural memory for reasoning traces and tool usage."""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from neo4j_agent_memory.core.memory import BaseMemory, MemoryEntry
from neo4j_agent_memory.graph import queries


def _serialize_json(data: dict[str, Any] | list | None) -> str | None:
    """Serialize dict/list to JSON string for Neo4j storage."""
    if data is None or data == {} or data == []:
        return None
    return json.dumps(data)


def _deserialize_json(data_str: str | None) -> dict[str, Any] | list | None:
    """Deserialize JSON string."""
    if data_str is None:
        return None
    try:
        return json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        return None


def _to_python_datetime(neo4j_datetime) -> datetime:
    """Convert Neo4j DateTime to Python datetime."""
    if neo4j_datetime is None:
        return datetime.utcnow()
    if isinstance(neo4j_datetime, datetime):
        return neo4j_datetime
    # Neo4j DateTime has to_native() method
    try:
        return neo4j_datetime.to_native()
    except AttributeError:
        return datetime.utcnow()


if TYPE_CHECKING:
    from neo4j_agent_memory.embeddings.base import Embedder
    from neo4j_agent_memory.graph.client import Neo4jClient


class ToolCallStatus(str, Enum):
    """Status of a tool call."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ToolCall(MemoryEntry):
    """A tool call made during reasoning."""

    tool_name: str = Field(description="Name of the tool")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    result: Any | None = Field(default=None, description="Tool result")
    status: ToolCallStatus = Field(default=ToolCallStatus.PENDING, description="Call status")
    duration_ms: int | None = Field(default=None, description="Duration in milliseconds")
    error: str | None = Field(default=None, description="Error message if failed")
    step_id: UUID | None = Field(default=None, description="Parent reasoning step ID")


class ReasoningStep(MemoryEntry):
    """A step in the agent's reasoning process."""

    trace_id: UUID = Field(description="Parent trace ID")
    step_number: int = Field(description="Step number in sequence")
    thought: str | None = Field(default=None, description="Agent's thought/reasoning")
    action: str | None = Field(default=None, description="Action taken")
    observation: str | None = Field(default=None, description="Observation from action")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tool calls in this step")


class ReasoningTrace(MemoryEntry):
    """A complete reasoning trace for a task."""

    session_id: str = Field(description="Session identifier")
    task: str = Field(description="Task description")
    task_embedding: list[float] | None = Field(default=None, description="Task embedding")
    steps: list[ReasoningStep] = Field(default_factory=list, description="Reasoning steps")
    outcome: str | None = Field(default=None, description="Final outcome")
    success: bool | None = Field(default=None, description="Whether task succeeded")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Start time")
    completed_at: datetime | None = Field(default=None, description="Completion time")


class Tool(BaseModel):
    """A registered tool that can be used by the agent."""

    name: str = Field(description="Unique tool name")


class ToolStats(BaseModel):
    """Pre-aggregated statistics for a tool.

    These stats are maintained incrementally on Tool nodes for fast retrieval
    without needing to aggregate across all ToolCall nodes.
    """

    name: str = Field(description="Tool name")
    description: str | None = Field(default=None, description="Tool description")
    total_calls: int = Field(default=0, description="Total number of calls")
    successful_calls: int = Field(default=0, description="Number of successful calls")
    failed_calls: int = Field(default=0, description="Number of failed calls (error/timeout)")
    success_rate: float = Field(default=0.0, description="Success rate (0.0 to 1.0)")
    avg_duration_ms: float | None = Field(default=None, description="Average duration in ms")
    last_used_at: datetime | None = Field(default=None, description="Last time tool was used")


class StreamingTraceRecorder:
    """
    Context manager for recording traces during streaming agent execution.

    Handles timing automatically and provides convenient methods for recording
    tool calls and observations during streaming responses.

    Example:
        async with StreamingTraceRecorder(memory.procedural, session_id, "Find restaurants") as recorder:
            step = await recorder.start_step(thought="Searching for restaurants")

            start = time.time()
            result = await search_tool(query="Italian restaurants")
            duration = int((time.time() - start) * 1000)

            await recorder.record_tool_call(
                "search",
                {"query": "Italian"},
                result=result,
                duration_ms=duration,
            )

            await recorder.add_observation(f"Found {len(result)} restaurants")

        # Trace is automatically completed when exiting the context
    """

    def __init__(
        self,
        procedural_memory: "ProceduralMemory",
        session_id: str,
        task: str,
        *,
        generate_task_embedding: bool = True,
        generate_step_embeddings: bool = False,
    ):
        """
        Initialize the streaming trace recorder.

        Args:
            procedural_memory: The ProceduralMemory instance to use
            session_id: Session identifier
            task: Task description
            generate_task_embedding: Whether to generate embedding for the task
            generate_step_embeddings: Whether to generate embeddings for steps during
                                     recording. If False, can batch generate at completion
                                     using complete_trace(generate_step_embeddings=True)
        """
        self.memory = procedural_memory
        self.session_id = session_id
        self.task = task
        self.generate_task_embedding = generate_task_embedding
        self.generate_step_embeddings = generate_step_embeddings

        self.trace: ReasoningTrace | None = None
        self.current_step: ReasoningStep | None = None
        self._step_start_time: datetime | None = None
        self._tool_call_times: dict[str, datetime] = {}
        self._outcome: str | None = None
        self._success: bool | None = None
        self._error: Exception | None = None

    async def __aenter__(self) -> "StreamingTraceRecorder":
        """Start the trace when entering the context."""
        self.trace = await self.memory.start_trace(
            self.session_id,
            self.task,
            generate_embedding=self.generate_task_embedding,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Complete the trace when exiting the context."""
        if self.trace is None:
            return

        # Determine success based on exception
        if exc_type is not None:
            self._success = False
            self._outcome = str(exc_val) if exc_val else f"Error: {exc_type.__name__}"
            self._error = exc_val

        await self.memory.complete_trace(
            self.trace.id,
            outcome=self._outcome,
            success=self._success if self._success is not None else True,
            generate_step_embeddings=self.generate_step_embeddings,
        )

    async def start_step(
        self,
        *,
        thought: str | None = None,
        action: str | None = None,
    ) -> ReasoningStep:
        """
        Start a new reasoning step.

        Args:
            thought: The agent's reasoning/thought
            action: The action being taken

        Returns:
            The created ReasoningStep
        """
        if self.trace is None:
            raise RuntimeError("Trace not started. Use within 'async with' context.")

        self._step_start_time = datetime.utcnow()
        self.current_step = await self.memory.add_step(
            self.trace.id,
            thought=thought,
            action=action,
            generate_embedding=self.generate_step_embeddings,
        )
        return self.current_step

    async def record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        result: Any = None,
        status: ToolCallStatus = ToolCallStatus.SUCCESS,
        duration_ms: int | None = None,
        error: str | None = None,
        auto_observation: bool = False,
    ) -> ToolCall:
        """
        Record a tool call with optional automatic timing.

        If no step is active, automatically creates one with action set to the tool name.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            result: Tool result
            status: Call status
            duration_ms: Duration in milliseconds (if not provided, calculated from step start)
            error: Error message if failed
            auto_observation: If True, set the step's observation from the result

        Returns:
            The created ToolCall
        """
        if self.trace is None:
            raise RuntimeError("Trace not started. Use within 'async with' context.")

        # Auto-create step if none exists
        if self.current_step is None:
            await self.start_step(action=f"call:{tool_name}")

        # Calculate duration if not provided
        if duration_ms is None and self._step_start_time is not None:
            duration_ms = int((datetime.utcnow() - self._step_start_time).total_seconds() * 1000)

        return await self.memory.record_tool_call(
            self.current_step.id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
            duration_ms=duration_ms,
            error=error,
            auto_observation=auto_observation,
        )

    async def add_observation(self, observation: str) -> None:
        """
        Add an observation to the current step.

        Args:
            observation: The observation text
        """
        if self.current_step is None:
            raise RuntimeError("No active step. Call start_step() first.")

        await self.memory._client.execute_write(
            "MATCH (s:ReasoningStep {id: $id}) SET s.observation = $observation",
            {"id": str(self.current_step.id), "observation": observation},
        )

    def set_outcome(self, outcome: str, success: bool = True) -> None:
        """
        Set the outcome for the trace (will be applied on context exit).

        Args:
            outcome: The outcome description
            success: Whether the task succeeded
        """
        self._outcome = outcome
        self._success = success

    @property
    def trace_id(self) -> UUID | None:
        """Get the current trace ID."""
        return self.trace.id if self.trace else None

    @property
    def step_id(self) -> UUID | None:
        """Get the current step ID."""
        return self.current_step.id if self.current_step else None


class ProceduralMemory(BaseMemory[ReasoningStep]):
    """
    Procedural memory stores reasoning traces and tool usage patterns.

    Provides:
    - Reasoning trace recording
    - Tool call tracking with statistics
    - Similar task retrieval for learning from past experiences
    """

    def __init__(
        self,
        client: "Neo4jClient",
        embedder: "Embedder | None" = None,
    ):
        """Initialize procedural memory."""
        super().__init__(client, embedder, None)

    async def add(self, content: str, **kwargs: Any) -> ReasoningStep:
        """Add content as a reasoning step."""
        trace_id = kwargs.get("trace_id")
        if not trace_id:
            raise ValueError("trace_id is required")
        return await self.add_step(
            trace_id,
            thought=content,
            action=kwargs.get("action"),
            observation=kwargs.get("observation"),
        )

    async def start_trace(
        self,
        session_id: str,
        task: str,
        *,
        generate_embedding: bool = True,
        metadata: dict[str, Any] | None = None,
        triggered_by_message_id: UUID | str | None = None,
    ) -> ReasoningTrace:
        """
        Start a new reasoning trace.

        Args:
            session_id: Session identifier
            task: Task description
            generate_embedding: Whether to generate task embedding
            metadata: Optional metadata
            triggered_by_message_id: Optional message ID that initiated this trace.
                Creates an INITIATED_BY relationship from ReasoningTrace to Message.

        Returns:
            The created reasoning trace
        """
        # Generate task embedding
        task_embedding = None
        if generate_embedding and self._embedder is not None:
            task_embedding = await self._embedder.embed(task)

        trace = ReasoningTrace(
            id=uuid4(),
            session_id=session_id,
            task=task,
            task_embedding=task_embedding,
            metadata=metadata or {},
        )

        await self._client.execute_write(
            queries.CREATE_REASONING_TRACE,
            {
                "id": str(trace.id),
                "session_id": trace.session_id,
                "task": trace.task,
                "task_embedding": trace.task_embedding,
                "outcome": None,
                "success": None,
                "completed_at": None,
                "metadata": _serialize_json(trace.metadata),
            },
        )

        # Link to message if provided
        if triggered_by_message_id is not None:
            msg_id_str = (
                str(triggered_by_message_id)
                if isinstance(triggered_by_message_id, UUID)
                else triggered_by_message_id
            )
            await self._client.execute_write(
                queries.LINK_TRACE_TO_MESSAGE,
                {
                    "trace_id": str(trace.id),
                    "message_id": msg_id_str,
                },
            )

        return trace

    async def add_step(
        self,
        trace_id: UUID,
        *,
        thought: str | None = None,
        action: str | None = None,
        observation: str | None = None,
        generate_embedding: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ReasoningStep:
        """
        Add a reasoning step to a trace.

        Args:
            trace_id: Parent trace ID
            thought: Agent's thought/reasoning
            action: Action taken
            observation: Observation from action
            generate_embedding: Whether to generate step embedding
            metadata: Optional metadata

        Returns:
            The created reasoning step
        """
        # Get current step count
        results = await self._client.execute_read(
            "MATCH (:ReasoningTrace {id: $id})-[:HAS_STEP]->(s:ReasoningStep) "
            "RETURN count(s) AS count",
            {"id": str(trace_id)},
        )
        step_number = results[0]["count"] + 1 if results else 1

        # Generate embedding
        embedding = None
        if generate_embedding and self._embedder is not None:
            text_parts = []
            if thought:
                text_parts.append(f"Thought: {thought}")
            if action:
                text_parts.append(f"Action: {action}")
            if observation:
                text_parts.append(f"Observation: {observation}")
            if text_parts:
                embedding = await self._embedder.embed(" ".join(text_parts))

        step = ReasoningStep(
            id=uuid4(),
            trace_id=trace_id,
            step_number=step_number,
            thought=thought,
            action=action,
            observation=observation,
            embedding=embedding,
            metadata=metadata or {},
        )

        await self._client.execute_write(
            queries.CREATE_REASONING_STEP,
            {
                "trace_id": str(trace_id),
                "id": str(step.id),
                "step_number": step.step_number,
                "thought": step.thought,
                "action": step.action,
                "observation": step.observation,
                "embedding": step.embedding,
                "metadata": _serialize_json(step.metadata),
            },
        )

        return step

    async def record_tool_call(
        self,
        step_id: UUID,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        result: Any | None = None,
        status: ToolCallStatus = ToolCallStatus.SUCCESS,
        duration_ms: int | None = None,
        error: str | None = None,
        auto_observation: bool = False,
        message_id: UUID | str | None = None,
    ) -> ToolCall:
        """
        Record a tool call within a reasoning step.

        Args:
            step_id: Parent reasoning step ID
            tool_name: Name of the tool
            arguments: Tool arguments
            result: Tool result
            status: Call status
            duration_ms: Duration in milliseconds
            error: Error message if failed
            auto_observation: If True, automatically set the step's observation field
                from the tool result. Useful for ReAct-style agents where the observation
                is the tool's output.
            message_id: Optional message ID that triggered this tool call.
                Creates a TRIGGERED_BY relationship from ToolCall to Message.

        Returns:
            The created tool call
        """
        tool_call = ToolCall(
            id=uuid4(),
            step_id=step_id,
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
            duration_ms=duration_ms,
            error=error,
        )

        await self._client.execute_write(
            queries.CREATE_TOOL_CALL,
            {
                "step_id": str(step_id),
                "id": str(tool_call.id),
                "tool_name": tool_name,
                "arguments": _serialize_json(arguments),
                "result": _serialize_json(result) if result is not None else None,
                "status": status.value,
                "duration_ms": duration_ms,
                "error": error,
            },
        )

        # Link to message if provided
        if message_id is not None:
            msg_id_str = str(message_id) if isinstance(message_id, UUID) else message_id
            await self._client.execute_write(
                queries.LINK_TOOL_CALL_TO_MESSAGE,
                {
                    "tool_call_id": str(tool_call.id),
                    "message_id": msg_id_str,
                },
            )

        # Auto-populate the step's observation from the tool result
        if auto_observation and result is not None:
            observation = self._format_observation(result)
            await self._client.execute_write(
                "MATCH (s:ReasoningStep {id: $id}) SET s.observation = $observation",
                {"id": str(step_id), "observation": observation},
            )

        return tool_call

    def _format_observation(self, result: Any, max_length: int = 1000) -> str:
        """
        Format a tool result as an observation string.

        Args:
            result: The tool result to format
            max_length: Maximum length of the observation string

        Returns:
            Formatted observation string
        """
        if isinstance(result, str):
            return result[:max_length] if len(result) > max_length else result
        if isinstance(result, (dict, list)):
            formatted = json.dumps(result, indent=2, default=str)
            return formatted[:max_length] if len(formatted) > max_length else formatted
        return str(result)[:max_length]

    async def complete_trace(
        self,
        trace_id: UUID,
        *,
        outcome: str | None = None,
        success: bool | None = None,
        generate_step_embeddings: bool = False,
    ) -> ReasoningTrace:
        """
        Complete a reasoning trace.

        Args:
            trace_id: Trace ID to complete
            outcome: Final outcome description
            success: Whether the task succeeded
            generate_step_embeddings: If True, batch generate embeddings for all steps
                that don't have them yet. Useful when steps were recorded with
                generate_embedding=False during streaming.

        Returns:
            The updated reasoning trace
        """
        # Batch generate step embeddings if requested
        if generate_step_embeddings and self._embedder is not None:
            await self._generate_step_embeddings_batch(trace_id)

        results = await self._client.execute_write(
            queries.UPDATE_REASONING_TRACE,
            {
                "id": str(trace_id),
                "outcome": outcome,
                "success": success,
            },
        )

        if not results:
            raise ValueError(f"Trace not found: {trace_id}")

        trace_data = dict(results[0]["rt"])
        return ReasoningTrace(
            id=UUID(trace_data["id"]),
            session_id=trace_data["session_id"],
            task=trace_data["task"],
            task_embedding=trace_data.get("task_embedding"),
            outcome=trace_data.get("outcome"),
            success=trace_data.get("success"),
            started_at=_to_python_datetime(trace_data.get("started_at")),
            completed_at=_to_python_datetime(trace_data.get("completed_at"))
            if trace_data.get("completed_at")
            else None,
        )

    async def link_trace_to_message(
        self,
        trace_id: UUID | str,
        message_id: UUID | str,
    ) -> None:
        """
        Link a reasoning trace to the message that initiated it.

        Creates an INITIATED_BY relationship from ReasoningTrace to Message.
        This is useful for linking traces after they've been created, for example
        when the message context wasn't available at trace creation time.

        Args:
            trace_id: The reasoning trace ID
            message_id: The message ID that initiated this trace

        Example:
            # Link a trace to its triggering message
            await memory.procedural.link_trace_to_message(trace.id, user_message.id)
        """
        trace_id_str = str(trace_id) if isinstance(trace_id, UUID) else trace_id
        msg_id_str = str(message_id) if isinstance(message_id, UUID) else message_id

        await self._client.execute_write(
            queries.LINK_TRACE_TO_MESSAGE,
            {
                "trace_id": trace_id_str,
                "message_id": msg_id_str,
            },
        )

    async def _generate_step_embeddings_batch(self, trace_id: UUID) -> int:
        """
        Batch generate embeddings for all steps in a trace that don't have them.

        Args:
            trace_id: Trace ID to process

        Returns:
            Number of steps that had embeddings generated
        """
        if self._embedder is None:
            return 0

        # Get all steps without embeddings
        results = await self._client.execute_read(
            """
            MATCH (rt:ReasoningTrace {id: $id})-[:HAS_STEP]->(s:ReasoningStep)
            WHERE s.embedding IS NULL
            RETURN s.id AS id, s.thought AS thought, s.action AS action, s.observation AS observation
            """,
            {"id": str(trace_id)},
        )

        if not results:
            return 0

        # Build texts for embedding
        texts = []
        step_ids = []
        for step in results:
            text_parts = []
            if step["thought"]:
                text_parts.append(f"Thought: {step['thought']}")
            if step["action"]:
                text_parts.append(f"Action: {step['action']}")
            if step["observation"]:
                text_parts.append(f"Observation: {step['observation']}")
            if text_parts:
                texts.append(" ".join(text_parts))
                step_ids.append(step["id"])

        if not texts:
            return 0

        # Batch generate embeddings
        embeddings = await self._embedder.embed_batch(texts)

        # Batch update steps with embeddings
        for step_id, embedding in zip(step_ids, embeddings):
            await self._client.execute_write(
                "MATCH (s:ReasoningStep {id: $id}) SET s.embedding = $embedding",
                {"id": step_id, "embedding": embedding},
            )

        return len(step_ids)

    async def search(self, query: str, **kwargs: Any) -> list[ReasoningStep]:
        """Search is not directly supported for procedural memory."""
        return []

    async def get_similar_traces(
        self,
        task: str,
        *,
        limit: int = 5,
        success_only: bool = True,
        threshold: float = 0.7,
    ) -> list[ReasoningTrace]:
        """
        Find similar past reasoning traces.

        Args:
            task: Task description to match
            limit: Maximum number of results
            success_only: Only return successful traces
            threshold: Minimum similarity threshold

        Returns:
            List of similar reasoning traces
        """
        if self._embedder is None:
            return []

        task_embedding = await self._embedder.embed(task)

        results = await self._client.execute_read(
            queries.SEARCH_TRACES_BY_EMBEDDING,
            {
                "embedding": task_embedding,
                "limit": limit,
                "threshold": threshold,
                "success_only": success_only,
            },
        )

        traces = []
        for row in results:
            trace_data = dict(row["rt"])
            trace = ReasoningTrace(
                id=UUID(trace_data["id"]),
                session_id=trace_data["session_id"],
                task=trace_data["task"],
                task_embedding=trace_data.get("task_embedding"),
                outcome=trace_data.get("outcome"),
                success=trace_data.get("success"),
                started_at=_to_python_datetime(trace_data.get("started_at")),
                completed_at=_to_python_datetime(trace_data.get("completed_at"))
                if trace_data.get("completed_at")
                else None,
                metadata={"similarity": row["score"]},
            )
            traces.append(trace)

        return traces

    async def get_tool_usage_stats(
        self,
        tool_name: str | None = None,
    ) -> dict[str, Tool]:
        """
        Get tool usage statistics.

        .. deprecated:: Use get_tool_stats() instead for pre-aggregated stats.

        Args:
            tool_name: Optional filter by tool name

        Returns:
            Dictionary of tool name to Tool statistics
        """
        results = await self._client.execute_read(queries.GET_TOOL_STATS)

        tools = {}
        for row in results:
            name = row["name"]
            if tool_name and name != tool_name:
                continue

            tools[name] = Tool(
                name=name,
            )

        return tools

    async def get_tool_stats(
        self,
        tool_name: str | None = None,
    ) -> list[ToolStats]:
        """
        Get pre-aggregated tool statistics.

        Returns tool usage statistics that are maintained incrementally on Tool nodes.
        This is much faster than computing stats from ToolCall nodes, especially
        with many tool calls.

        Args:
            tool_name: Optional filter by specific tool name

        Returns:
            List of ToolStats objects ordered by total_calls descending

        Example:
            # Get stats for all tools
            stats = await memory.procedural.get_tool_stats()
            for tool in stats:
                print(f"{tool.name}: {tool.total_calls} calls, {tool.success_rate:.1%} success")

            # Get stats for a specific tool
            stats = await memory.procedural.get_tool_stats("search_memory")
        """
        results = await self._client.execute_read(queries.GET_TOOL_STATS)

        tool_stats = []
        for row in results:
            name = row["name"]
            if tool_name and name != tool_name:
                continue

            total_calls = row.get("total_calls", 0)
            success_rate = row.get("success_rate", 0.0)
            avg_duration = row.get("avg_duration")

            tool_stats.append(
                ToolStats(
                    name=name,
                    description=row.get("description"),
                    total_calls=total_calls,
                    successful_calls=int(total_calls * success_rate) if total_calls > 0 else 0,
                    failed_calls=total_calls - int(total_calls * success_rate)
                    if total_calls > 0
                    else 0,
                    success_rate=success_rate,
                    avg_duration_ms=avg_duration,
                )
            )

        return tool_stats

    async def migrate_tool_stats(self) -> dict[str, int]:
        """
        Migrate tool statistics from ToolCall nodes to pre-aggregated Tool node properties.

        This is a one-time migration for existing data. New tool calls automatically
        update the pre-aggregated stats. Run this if you have existing ToolCall data
        that was created before the pre-aggregation optimization was added.

        Returns:
            Dictionary mapping tool names to number of calls migrated

        Example:
            # Run migration for existing data
            migrated = await memory.procedural.migrate_tool_stats()
            print(f"Migrated stats for {len(migrated)} tools")
            for tool, count in migrated.items():
                print(f"  {tool}: {count} calls")
        """
        results = await self._client.execute_write(queries.MIGRATE_TOOL_STATS)

        return {row["name"]: row["migrated_calls"] for row in results}

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """
        Get procedural context for similar tasks.

        Args:
            query: Task description to find similar traces
            max_traces: Maximum traces to include
            include_successful_only: Only include successful traces

        Returns:
            Formatted context string
        """
        max_traces = kwargs.get("max_traces", 3)
        success_only = kwargs.get("include_successful_only", True)

        traces = await self.get_similar_traces(query, limit=max_traces, success_only=success_only)

        if not traces:
            return ""

        parts = ["### Similar Past Tasks"]
        for trace in traces:
            similarity = trace.metadata.get("similarity", 0)
            parts.append(f"\n**Task**: {trace.task}")
            parts.append(f"- Similarity: {similarity:.2f}")
            if trace.outcome:
                parts.append(f"- Outcome: {trace.outcome}")
            if trace.success is not None:
                parts.append(f"- Success: {'Yes' if trace.success else 'No'}")

        return "\n".join(parts)

    async def get_trace_with_steps(self, trace_id: UUID) -> ReasoningTrace | None:
        """
        Get a complete trace with all steps and tool calls.

        Args:
            trace_id: Trace ID to retrieve

        Returns:
            Complete reasoning trace or None
        """
        import json

        results = await self._client.execute_read(
            queries.GET_TRACE_WITH_STEPS,
            {"id": str(trace_id)},
        )

        if not results:
            return None

        row = results[0]
        trace_data = dict(row["rt"])
        steps_data = row.get("steps", [])
        tool_calls_data = row.get("tool_calls", [])

        # Parse tool calls
        tool_calls_by_step: dict[str, list[ToolCall]] = {}
        for tc_data in tool_calls_data:
            tc = dict(tc_data)
            step_id = tc.get("step_id")
            if step_id:
                if step_id not in tool_calls_by_step:
                    tool_calls_by_step[step_id] = []
                tool_calls_by_step[step_id].append(
                    ToolCall(
                        id=UUID(tc["id"]),
                        tool_name=tc["tool_name"],
                        arguments=json.loads(tc.get("arguments", "{}")),
                        result=json.loads(tc["result"]) if tc.get("result") else None,
                        status=ToolCallStatus(tc.get("status", "success")),
                        duration_ms=tc.get("duration_ms"),
                        error=tc.get("error"),
                    )
                )

        # Parse steps
        steps = []
        for step_data in steps_data:
            sd = dict(step_data)
            step = ReasoningStep(
                id=UUID(sd["id"]),
                trace_id=trace_id,
                step_number=sd["step_number"],
                thought=sd.get("thought"),
                action=sd.get("action"),
                observation=sd.get("observation"),
                tool_calls=tool_calls_by_step.get(sd["id"], []),
            )
            steps.append(step)

        # Sort steps by step number
        steps.sort(key=lambda s: s.step_number)

        return ReasoningTrace(
            id=UUID(trace_data["id"]),
            session_id=trace_data["session_id"],
            task=trace_data["task"],
            task_embedding=trace_data.get("task_embedding"),
            steps=steps,
            outcome=trace_data.get("outcome"),
            success=trace_data.get("success"),
            started_at=_to_python_datetime(trace_data.get("started_at")),
            completed_at=_to_python_datetime(trace_data.get("completed_at"))
            if trace_data.get("completed_at")
            else None,
        )

    async def get_trace(self, trace_id: UUID | str) -> ReasoningTrace | None:
        """
        Get a trace by ID (alias for get_trace_with_steps).

        Args:
            trace_id: Trace ID to retrieve (UUID or string)

        Returns:
            Complete reasoning trace or None
        """
        if isinstance(trace_id, str):
            try:
                trace_id = UUID(trace_id)
            except ValueError:
                return None
        return await self.get_trace_with_steps(trace_id)

    async def get_session_traces(
        self,
        session_id: str,
        *,
        limit: int = 100,
    ) -> list[ReasoningTrace]:
        """
        Get all traces for a session.

        Args:
            session_id: Session identifier
            limit: Maximum traces to return

        Returns:
            List of reasoning traces for the session
        """
        return await self.list_traces(session_id=session_id, limit=limit)

    async def list_traces(
        self,
        *,
        session_id: str | None = None,
        success_only: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Literal["started_at", "completed_at"] = "started_at",
        order_dir: Literal["asc", "desc"] = "desc",
    ) -> list[ReasoningTrace]:
        """
        List reasoning traces with filtering and pagination.

        Args:
            session_id: Filter by session (optional)
            success_only: Filter by success status (None for all, True for successful,
                         False for failed)
            since: Only traces started after this time
            until: Only traces started before this time
            limit: Maximum traces to return
            offset: Number of traces to skip (for pagination)
            order_by: Field to order by ('started_at' or 'completed_at')
            order_dir: Sort direction ('asc' or 'desc')

        Returns:
            List of ReasoningTrace objects (without steps - use get_trace for full details)
        """
        results = await self._client.execute_read(
            queries.LIST_TRACES,
            {
                "session_id": session_id,
                "success": success_only,
                "since": since.isoformat() if since else None,
                "until": until.isoformat() if until else None,
                "limit": limit,
                "offset": offset,
                "order_by": order_by,
                "order_dir": order_dir,
            },
        )

        traces = []
        for row in results:
            trace_data = dict(row["rt"])
            trace = ReasoningTrace(
                id=UUID(trace_data["id"]),
                session_id=trace_data["session_id"],
                task=trace_data["task"],
                task_embedding=trace_data.get("task_embedding"),
                outcome=trace_data.get("outcome"),
                success=trace_data.get("success"),
                started_at=_to_python_datetime(trace_data.get("started_at")),
                completed_at=_to_python_datetime(trace_data.get("completed_at"))
                if trace_data.get("completed_at")
                else None,
            )
            traces.append(trace)

        return traces
