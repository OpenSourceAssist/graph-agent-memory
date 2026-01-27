"""Microsoft Agent Framework integration for Neo4j Agent Memory.

This module provides memory integration for Microsoft's Agent Framework,
enabling persistent conversation history, entity knowledge, graph-enhanced
context retrieval, and reasoning trace recording.

.. warning::
    This integration targets Microsoft Agent Framework v1.0.0b251223 (preview).
    APIs may change before GA release (expected Q1 2026). See the API compatibility
    documentation for version requirements and migration guidance.

Example:
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.integrations.microsoft_agent import (
        Neo4jContextProvider,
        Neo4jChatMessageStore,
        Neo4jMicrosoftMemory,
        create_memory_tools,
        record_agent_trace,
    )
    from agent_framework import ChatAgent

    async with MemoryClient(settings) as client:
        # Create context provider for memory injection
        provider = Neo4jContextProvider(
            memory_client=client,
            session_id="user-123",
        )

        # Create chat message store for persistent history
        message_store = Neo4jChatMessageStore(
            memory_client=client,
            session_id="user-123",
        )

        # Create agent with Neo4j memory
        agent = ChatAgent(
            chat_client=chat_client,
            name="assistant",
            instructions="You are a helpful assistant.",
            context_providers=[provider],
        )

        # Or use the unified interface
        memory = Neo4jMicrosoftMemory.from_memory_client(
            memory_client=client,
            session_id="user-123",
        )
"""

# Target API version - document for compatibility tracking
MICROSOFT_AGENT_FRAMEWORK_VERSION = "1.0.0b251223"
MICROSOFT_AGENT_FRAMEWORK_MIN_VERSION = "1.0.0b"

try:
    from .chat_store import Neo4jChatMessageStore
    from .context_provider import Neo4jContextProvider
    from .gds import GDSAlgorithm, GDSConfig, GDSIntegration
    from .memory import Neo4jMicrosoftMemory
    from .tools import create_memory_tools, execute_memory_tool
    from .tracing import format_traces_for_prompt, get_similar_traces, record_agent_trace

    __all__ = [
        # Core components
        "Neo4jContextProvider",
        "Neo4jChatMessageStore",
        "Neo4jMicrosoftMemory",
        # Tools
        "create_memory_tools",
        "execute_memory_tool",
        # Tracing
        "record_agent_trace",
        "get_similar_traces",
        "format_traces_for_prompt",
        # GDS
        "GDSConfig",
        "GDSAlgorithm",
        "GDSIntegration",
        # Version info
        "MICROSOFT_AGENT_FRAMEWORK_VERSION",
        "MICROSOFT_AGENT_FRAMEWORK_MIN_VERSION",
    ]
except ImportError as e:
    # Microsoft Agent Framework not installed
    import warnings

    warnings.warn(
        f"Microsoft Agent Framework integration requires the 'agent-framework' package. "
        f"Install with: pip install neo4j-agent-memory[microsoft-agent] "
        f"(Import error: {e})",
        ImportWarning,
        stacklevel=2,
    )
    __all__ = [
        "MICROSOFT_AGENT_FRAMEWORK_VERSION",
        "MICROSOFT_AGENT_FRAMEWORK_MIN_VERSION",
    ]
