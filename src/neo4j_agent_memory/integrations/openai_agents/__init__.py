"""OpenAI Agents SDK integration for Neo4j Agent Memory.

This module provides memory integration for OpenAI's Agents SDK,
enabling persistent conversation history, entity knowledge, and
reasoning trace recording.

Example:
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.integrations.openai_agents import (
        Neo4jOpenAIMemory,
        create_memory_tools,
        record_agent_trace,
    )

    async with MemoryClient(settings) as client:
        memory = Neo4jOpenAIMemory(
            memory_client=client,
            session_id="user-123",
        )

        # Get context for system prompt
        context = await memory.get_context("user query")

        # Create function tools for the agent
        tools = create_memory_tools(memory)

        # Record agent execution as reasoning trace
        await record_agent_trace(memory, messages, task="Help user")
"""

try:
    from .memory import Neo4jOpenAIMemory, create_memory_tools
    from .tracing import record_agent_trace

    __all__ = [
        "Neo4jOpenAIMemory",
        "create_memory_tools",
        "record_agent_trace",
    ]
except ImportError:
    # OpenAI not installed
    __all__ = []
