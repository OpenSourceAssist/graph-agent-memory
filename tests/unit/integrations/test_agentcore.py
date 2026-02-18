"""Unit tests for AgentCore Memory Provider integration."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestMemoryType:
    """Tests for MemoryType enum."""

    def test_memory_types_defined(self) -> None:
        """Test that all memory types are defined."""
        from neo4j_agent_memory.integrations.agentcore.types import MemoryType

        assert MemoryType.MESSAGE == "message"
        assert MemoryType.ENTITY == "entity"
        assert MemoryType.PREFERENCE == "preference"
        assert MemoryType.FACT == "fact"
        assert MemoryType.TRACE == "trace"


class TestMemory:
    """Tests for Memory dataclass."""

    def test_memory_creation(self) -> None:
        """Test creating a Memory instance."""
        from neo4j_agent_memory.integrations.agentcore.types import Memory, MemoryType

        memory = Memory(
            id="mem-123",
            content="Test content",
            memory_type=MemoryType.MESSAGE,
            session_id="session-1",
        )

        assert memory.id == "mem-123"
        assert memory.content == "Test content"
        assert memory.memory_type == MemoryType.MESSAGE
        assert memory.session_id == "session-1"

    def test_memory_to_dict(self) -> None:
        """Test converting Memory to dictionary."""
        from neo4j_agent_memory.integrations.agentcore.types import Memory, MemoryType

        memory = Memory(
            id="mem-123",
            content="Test content",
            memory_type=MemoryType.MESSAGE,
            session_id="session-1",
            score=0.95,
        )

        result = memory.to_dict()

        assert result["id"] == "mem-123"
        assert result["content"] == "Test content"
        assert result["memory_type"] == "message"
        assert result["session_id"] == "session-1"
        assert result["score"] == 0.95

    def test_memory_from_message(self) -> None:
        """Test creating Memory from a message object."""
        from neo4j_agent_memory.integrations.agentcore.types import Memory

        # Create mock message
        message = MagicMock()
        message.id = "msg-123"
        message.content = "Hello, world!"
        message.role = MagicMock(value="user")
        message.created_at = datetime(2024, 1, 1, 12, 0, 0)
        message.metadata = {"key": "value"}

        memory = Memory.from_message(message, session_id="session-1")

        assert memory.id == "msg-123"
        assert memory.content == "Hello, world!"
        assert memory.session_id == "session-1"
        assert memory.metadata["role"] == "user"

    def test_memory_from_entity(self) -> None:
        """Test creating Memory from an entity object."""
        from neo4j_agent_memory.integrations.agentcore.types import Memory, MemoryType

        # Create mock entity
        entity = MagicMock()
        entity.id = "ent-123"
        entity.display_name = "John Doe"
        entity.type = MagicMock(value="PERSON")
        entity.description = "A software engineer"
        entity.aliases = ["JD"]

        memory = Memory.from_entity(entity)

        assert memory.id == "ent-123"
        assert "John Doe" in memory.content
        assert memory.memory_type == MemoryType.ENTITY
        assert memory.metadata["entity_type"] == "PERSON"
        assert memory.metadata["display_name"] == "John Doe"

    def test_memory_from_preference(self) -> None:
        """Test creating Memory from a preference object."""
        from neo4j_agent_memory.integrations.agentcore.types import Memory, MemoryType

        # Create mock preference
        preference = MagicMock()
        preference.id = "pref-123"
        preference.preference = "Prefers dark mode"
        preference.category = "ui"
        preference.context = "always"
        preference.confidence = 0.9

        memory = Memory.from_preference(preference)

        assert memory.id == "pref-123"
        assert memory.content == "Prefers dark mode"
        assert memory.memory_type == MemoryType.PREFERENCE
        assert memory.metadata["category"] == "ui"
        assert memory.metadata["confidence"] == 0.9

    def test_memory_from_trace(self) -> None:
        """Test creating Memory from a reasoning trace object."""
        from neo4j_agent_memory.integrations.agentcore.types import Memory, MemoryType

        # Create mock trace
        trace = MagicMock()
        trace.id = "trace-123"
        trace.task = "Find restaurants"
        trace.outcome = "Found 5 restaurants"
        trace.success = True
        trace.session_id = "session-1"
        trace.started_at = datetime(2024, 1, 1, 12, 0, 0)
        trace.steps = [MagicMock(), MagicMock()]

        memory = Memory.from_trace(trace)

        assert memory.id == "trace-123"
        assert "Find restaurants" in memory.content
        assert memory.memory_type == MemoryType.TRACE
        assert memory.metadata["success"] is True
        assert memory.metadata["step_count"] == 2


class TestMemorySearchResult:
    """Tests for MemorySearchResult dataclass."""

    def test_search_result_creation(self) -> None:
        """Test creating a MemorySearchResult."""
        from neo4j_agent_memory.integrations.agentcore.types import (
            Memory,
            MemorySearchResult,
        )

        memories = [
            Memory(id="1", content="First"),
            Memory(id="2", content="Second"),
        ]

        result = MemorySearchResult(
            memories=memories,
            total_count=2,
            query="test query",
        )

        assert len(result.memories) == 2
        assert result.total_count == 2
        assert result.query == "test query"

    def test_search_result_to_dict(self) -> None:
        """Test converting MemorySearchResult to dictionary."""
        from neo4j_agent_memory.integrations.agentcore.types import (
            Memory,
            MemorySearchResult,
        )

        memories = [Memory(id="1", content="First")]

        result = MemorySearchResult(
            memories=memories,
            total_count=1,
            query="test",
            filters_applied={"threshold": 0.5},
        )

        dict_result = result.to_dict()

        assert len(dict_result["memories"]) == 1
        assert dict_result["query"] == "test"
        assert dict_result["filters_applied"]["threshold"] == 0.5


class TestSessionContext:
    """Tests for SessionContext dataclass."""

    def test_session_context_creation(self) -> None:
        """Test creating a SessionContext."""
        from neo4j_agent_memory.integrations.agentcore.types import SessionContext

        context = SessionContext(
            session_id="session-123",
            user_id="user-456",
            namespace="my-app",
        )

        assert context.session_id == "session-123"
        assert context.user_id == "user-456"
        assert context.namespace == "my-app"

    def test_session_context_defaults(self) -> None:
        """Test SessionContext default values."""
        from neo4j_agent_memory.integrations.agentcore.types import SessionContext

        context = SessionContext(session_id="session-123")

        assert context.user_id is None
        assert context.namespace == "default"
        assert context.metadata == {}


class TestNeo4jMemoryProvider:
    """Tests for Neo4jMemoryProvider class."""

    @pytest.fixture
    def mock_memory_client(self) -> MagicMock:
        """Create a mock MemoryClient."""
        client = MagicMock()
        client.short_term = MagicMock()
        client.long_term = MagicMock()
        client.reasoning = MagicMock()
        client._client = MagicMock()
        client.get_context = AsyncMock(return_value="Formatted context")
        return client

    def test_provider_initialization(self, mock_memory_client: MagicMock) -> None:
        """Test Neo4jMemoryProvider initialization."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        provider = Neo4jMemoryProvider(
            memory_client=mock_memory_client,
            namespace="test-ns",
            extract_entities=True,
        )

        assert provider.namespace == "test-ns"
        assert provider._extract_entities is True

    def test_provider_default_namespace(self, mock_memory_client: MagicMock) -> None:
        """Test Neo4jMemoryProvider default namespace."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        assert provider.namespace == "default"

    @pytest.mark.asyncio
    async def test_store_memory_message(self, mock_memory_client: MagicMock) -> None:
        """Test storing a message memory."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        # Setup mock
        mock_message = MagicMock()
        mock_message.id = "msg-123"
        mock_message.content = "Test message"
        mock_message.role = MagicMock(value="user")
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {}
        mock_memory_client.short_term.add_message = AsyncMock(return_value=mock_message)

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        memory = await provider.store_memory(
            session_id="session-1",
            content="Test message",
        )

        assert memory.id == "msg-123"
        assert memory.content == "Test message"
        mock_memory_client.short_term.add_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_memory_preference(self, mock_memory_client: MagicMock) -> None:
        """Test storing a preference memory."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        # Setup mock
        mock_preference = MagicMock()
        mock_preference.id = "pref-123"
        mock_preference.preference = "Likes dark mode"
        mock_preference.category = "ui"
        mock_preference.context = None
        mock_preference.confidence = 0.9
        mock_memory_client.long_term.add_preference = AsyncMock(return_value=mock_preference)

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        memory = await provider.store_memory(
            session_id="session-1",
            content="Likes dark mode",
            memory_type="preference",
            metadata={"category": "ui"},
        )

        assert memory.id == "pref-123"
        assert memory.content == "Likes dark mode"
        mock_memory_client.long_term.add_preference.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_memory_invalid_type(self, mock_memory_client: MagicMock) -> None:
        """Test storing with invalid memory type raises error."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        with pytest.raises(ValueError, match="Unknown memory_type"):
            await provider.store_memory(
                session_id="session-1",
                content="Test",
                memory_type="invalid",
            )

    @pytest.mark.asyncio
    async def test_search_memory(self, mock_memory_client: MagicMock) -> None:
        """Test searching memories."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        # Setup mocks
        mock_message = MagicMock()
        mock_message.id = "msg-1"
        mock_message.content = "Found message"
        mock_message.role = MagicMock(value="user")
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {"similarity": 0.95}

        mock_memory_client.short_term.search_messages = AsyncMock(return_value=[mock_message])
        mock_memory_client.long_term.search_entities = AsyncMock(return_value=[])
        mock_memory_client.long_term.search_preferences = AsyncMock(return_value=[])

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        result = await provider.search_memory(query="test query")

        assert len(result.memories) >= 1
        assert result.query == "test query"

    @pytest.mark.asyncio
    async def test_get_session_memories(self, mock_memory_client: MagicMock) -> None:
        """Test getting session memories."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        # Setup mock
        mock_message = MagicMock()
        mock_message.id = "msg-1"
        mock_message.content = "Session message"
        mock_message.role = MagicMock(value="user")
        mock_message.created_at = datetime.utcnow()
        mock_message.metadata = {}

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_message]
        mock_memory_client.short_term.get_conversation = AsyncMock(return_value=mock_conversation)

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        memories = await provider.get_session_memories("session-1")

        assert len(memories) == 1
        assert memories[0].content == "Session message"

    @pytest.mark.asyncio
    async def test_delete_memory(self, mock_memory_client: MagicMock) -> None:
        """Test deleting a memory."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        # Setup mock
        mock_memory_client._client.execute_write = AsyncMock(return_value=[{"deleted": 1}])

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        result = await provider.delete_memory("mem-123")

        assert result is True
        mock_memory_client._client.execute_write.assert_called()

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, mock_memory_client: MagicMock) -> None:
        """Test deleting a non-existent memory."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        # Setup mock to return 0 deleted
        mock_memory_client._client.execute_write = AsyncMock(return_value=[{"deleted": 0}])

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        result = await provider.delete_memory("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_session(self, mock_memory_client: MagicMock) -> None:
        """Test clearing a session."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        # Setup mock
        mock_memory_client._client.execute_write = AsyncMock(return_value=[{"deleted": 5}])

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        count = await provider.clear_session("session-1")

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_context(self, mock_memory_client: MagicMock) -> None:
        """Test getting formatted context."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        context = await provider.get_context("test query", session_id="session-1")

        assert context == "Formatted context"
        mock_memory_client.get_context.assert_called_once()

    def test_get_session_context(self, mock_memory_client: MagicMock) -> None:
        """Test getting session context."""
        from neo4j_agent_memory.integrations.agentcore import Neo4jMemoryProvider
        from neo4j_agent_memory.integrations.agentcore.types import SessionContext

        provider = Neo4jMemoryProvider(memory_client=mock_memory_client)

        # Initially no session
        assert provider.get_session_context("session-1") is None

        # Add a session
        provider._sessions["session-1"] = SessionContext(session_id="session-1")

        context = provider.get_session_context("session-1")
        assert context is not None
        assert context.session_id == "session-1"
