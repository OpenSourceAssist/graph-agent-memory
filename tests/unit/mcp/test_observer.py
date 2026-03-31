"""Unit tests for the Observational Memory observer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from neo4j_agent_memory.mcp._observer import MemoryObserver, Observation, SessionContext


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.short_term = MagicMock()
    return client


@pytest.fixture
def observer(mock_client):
    return MemoryObserver(mock_client, threshold_tokens=100)


class TestSessionTracking:
    """Tests for session context accumulation."""

    @pytest.mark.asyncio
    async def test_on_message_updates_char_count(self, observer):
        await observer.on_message_stored("s1", "Hello world", role="user")
        ctx = observer._get_session("s1")
        assert ctx.total_chars == 11
        assert ctx.message_count == 1

    @pytest.mark.asyncio
    async def test_multiple_messages_accumulate(self, observer):
        await observer.on_message_stored("s1", "Hello", role="user")
        await observer.on_message_stored("s1", "World!", role="assistant")
        ctx = observer._get_session("s1")
        assert ctx.total_chars == 11
        assert ctx.message_count == 2

    @pytest.mark.asyncio
    async def test_separate_sessions_tracked_independently(self, observer):
        await observer.on_message_stored("s1", "Hello", role="user")
        await observer.on_message_stored("s2", "Different session", role="user")
        assert observer._get_session("s1").message_count == 1
        assert observer._get_session("s2").message_count == 1


class TestInlineObservations:
    """Tests for inline observation extraction from messages."""

    @pytest.mark.asyncio
    async def test_detects_decision(self, observer):
        await observer.on_message_stored(
            "s1",
            "I decided to go with the blue design for the landing page.",
            role="user",
        )
        ctx = observer._get_session("s1")
        decisions = [o for o in ctx.observations if o.type == "decision"]
        assert len(decisions) == 1
        assert "blue design" in decisions[0].content

    @pytest.mark.asyncio
    async def test_detects_fact(self, observer):
        await observer.on_message_stored(
            "s1",
            "I found out that the API has a rate limit of 100 requests per minute.",
            role="user",
        )
        ctx = observer._get_session("s1")
        facts = [o for o in ctx.observations if o.type == "fact"]
        assert len(facts) == 1

    @pytest.mark.asyncio
    async def test_no_observations_from_assistant(self, observer):
        await observer.on_message_stored(
            "s1",
            "I decided to help you with that.",
            role="assistant",
        )
        ctx = observer._get_session("s1")
        assert len(ctx.observations) == 0

    @pytest.mark.asyncio
    async def test_no_observations_from_neutral_message(self, observer):
        await observer.on_message_stored(
            "s1",
            "What time is it?",
            role="user",
        )
        ctx = observer._get_session("s1")
        assert len(ctx.observations) == 0


class TestReflectionGeneration:
    """Tests for reflection generation when threshold is exceeded."""

    @pytest.mark.asyncio
    async def test_threshold_triggers_reflection(self, mock_client):
        # Low threshold to trigger easily
        observer = MemoryObserver(
            mock_client,
            threshold_tokens=5,  # Very low: ~20 chars
            recent_message_window=2,
        )

        # Create mock conversation with enough messages
        mock_msgs = []
        for i in range(5):
            msg = MagicMock()
            msg.content = f"Message {i} with Some Capitalized Words and More Content here"
            mock_msgs.append(msg)

        mock_conv = MagicMock()
        mock_conv.messages = mock_msgs
        mock_client.short_term.get_conversation = AsyncMock(return_value=mock_conv)

        # Send enough messages to exceed threshold
        for i in range(5):
            await observer.on_message_stored(
                "s1",
                f"Message {i} with Some Capitalized Words and More Content here",
                role="user",
            )

        ctx = observer._get_session("s1")
        # Should have generated at least one reflection
        assert ctx.last_compression_at > 0

    @pytest.mark.asyncio
    async def test_no_reflection_below_threshold(self, observer):
        # Default threshold is 100 tokens, short message won't trigger
        await observer.on_message_stored("s1", "Hi", role="user")
        ctx = observer._get_session("s1")
        assert len(ctx.reflections) == 0
        assert ctx.last_compression_at == 0


class TestGetObservations:
    """Tests for the get_observations API."""

    @pytest.mark.asyncio
    async def test_returns_complete_structure(self, observer):
        await observer.on_message_stored(
            "s1", "I decided to use React for the frontend.", role="user"
        )

        result = await observer.get_observations("s1")
        assert result["session_id"] == "s1"
        assert result["message_count"] == 1
        assert "approximate_tokens" in result
        assert "threshold_exceeded" in result
        assert "reflections" in result
        assert "observations" in result
        assert isinstance(result["observations"], list)

    @pytest.mark.asyncio
    async def test_empty_session_returns_defaults(self, observer):
        result = await observer.get_observations("nonexistent")
        assert result["session_id"] == "nonexistent"
        assert result["message_count"] == 0
        assert result["observations"] == []
        assert result["reflections"] == []

    @pytest.mark.asyncio
    async def test_threshold_exceeded_flag(self, mock_client):
        observer = MemoryObserver(mock_client, threshold_tokens=5)
        # Add enough text to exceed 5 tokens (~20 chars)
        await observer.on_message_stored(
            "s1",
            "This is a long enough message to exceed the very low threshold",
            role="user",
        )
        result = await observer.get_observations("s1")
        assert result["threshold_exceeded"] is True


class TestResetSession:
    """Tests for session reset."""

    @pytest.mark.asyncio
    async def test_reset_clears_state(self, observer):
        await observer.on_message_stored("s1", "Hello", role="user")
        assert observer._get_session("s1").message_count == 1

        observer.reset_session("s1")
        # After reset, session should start fresh
        result = await observer.get_observations("s1")
        assert result["message_count"] == 0

    def test_reset_nonexistent_session_is_safe(self, observer):
        observer.reset_session("nonexistent")  # Should not raise


class TestObservationModel:
    """Tests for the Observation dataclass."""

    def test_default_values(self):
        obs = Observation(type="fact", content="The sky is blue")
        assert obs.confidence == 0.8
        assert obs.source_message_id is None
        assert obs.timestamp is None

    def test_custom_values(self):
        obs = Observation(
            type="decision",
            content="Use React",
            source_message_id="m-1",
            timestamp="2026-03-31T00:00:00Z",
            confidence=0.9,
        )
        assert obs.type == "decision"
        assert obs.source_message_id == "m-1"
