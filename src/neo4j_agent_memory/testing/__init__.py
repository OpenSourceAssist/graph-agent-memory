"""Testing utilities for neo4j-agent-memory.

This module provides mock implementations and test fixtures for unit testing
applications that use neo4j-agent-memory without requiring a real Neo4j database.

Example:
    from neo4j_agent_memory.testing import MockMemoryClient, MemoryFixtures

    # Create mock client for testing
    async def test_my_agent():
        client = MockMemoryClient()

        # Use like real MemoryClient
        await client.short_term.add_message("session-1", "user", "Hello")
        messages = await client.short_term.get_conversation("session-1")

        assert len(messages.messages) == 1

    # Create test data with fixtures
    def test_with_fixtures():
        message = MemoryFixtures.message(role="user", content="Test message")
        conversation = MemoryFixtures.conversation(message_count=5)
        trace = MemoryFixtures.reasoning_trace(step_count=3)
"""

from neo4j_agent_memory.testing.fixtures import MemoryFixtures
from neo4j_agent_memory.testing.mocks import (
    MockLongTermMemory,
    MockMemoryClient,
    MockProceduralMemory,
    MockShortTermMemory,
)

__all__ = [
    "MockMemoryClient",
    "MockShortTermMemory",
    "MockLongTermMemory",
    "MockProceduralMemory",
    "MemoryFixtures",
]
