"""Procedural memory for reasoning traces and tool usage."""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
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
    description: str | None = Field(default=None, description="Tool description")
    parameters_schema: dict[str, Any] | None = Field(default=None, description="JSON schema")
    success_rate: float = Field(default=0.0, description="Success rate")
    avg_duration_ms: float = Field(default=0.0, description="Average duration")
    total_calls: int = Field(default=0, description="Total call count")


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
    ) -> ReasoningTrace:
        """
        Start a new reasoning trace.

        Args:
            session_id: Session identifier
            task: Task description
            generate_embedding: Whether to generate task embedding
            metadata: Optional metadata

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

        return tool_call

    async def complete_trace(
        self,
        trace_id: UUID,
        *,
        outcome: str | None = None,
        success: bool | None = None,
    ) -> ReasoningTrace:
        """
        Complete a reasoning trace.

        Args:
            trace_id: Trace ID to complete
            outcome: Final outcome description
            success: Whether the task succeeded

        Returns:
            The updated reasoning trace
        """
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
                description=row.get("description"),
                success_rate=row.get("success_rate", 0.0),
                avg_duration_ms=row.get("avg_duration") or 0.0,
                total_calls=row.get("total_calls", 0),
            )

        return tools

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
        query = """
        MATCH (rt:ReasoningTrace {session_id: $session_id})
        RETURN rt
        ORDER BY rt.started_at DESC
        LIMIT $limit
        """

        results = await self._client.execute_read(
            query,
            {"session_id": session_id, "limit": limit},
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
