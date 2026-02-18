"""Unit tests for FastMCP prompt registration and execution.

Tests the _prompts.py module that provides guided workflows via MCP prompts.
Uses FastMCP's Client for in-memory testing.
"""

import pytest
from fastmcp import Client, FastMCP


def _create_server():
    """Create a FastMCP server with prompts registered."""
    mcp = FastMCP("test-prompts")

    from neo4j_agent_memory.mcp._prompts import register_prompts

    register_prompts(mcp)
    return mcp


class TestPromptRegistration:
    """Tests that all 3 prompts register correctly on a FastMCP server."""

    @pytest.fixture
    def server(self):
        return _create_server()

    @pytest.mark.asyncio
    async def test_registers_3_prompts(self, server):
        """All 3 memory prompts should be registered."""
        async with Client(server) as client:
            prompts = await client.list_prompts()
            assert len(prompts) == 3

    @pytest.mark.asyncio
    async def test_prompt_names(self, server):
        """Prompts should have the expected names."""
        async with Client(server) as client:
            prompts = await client.list_prompts()
            names = {p.name for p in prompts}
            assert names == {
                "memory_search_guide",
                "entity_analysis",
                "conversation_summary",
            }

    @pytest.mark.asyncio
    async def test_prompts_have_descriptions(self, server):
        """Every prompt should have a non-empty description."""
        async with Client(server) as client:
            prompts = await client.list_prompts()
            for prompt in prompts:
                assert prompt.description, f"Prompt {prompt.name} has no description"


class TestMemorySearchGuidePrompt:
    """Tests for the memory_search_guide prompt."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        """memory_search_guide returns prompt messages."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory_search_guide",
                arguments={"topic": "project deadlines"},
            )

        assert len(result.messages) >= 1
        assert result.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_includes_topic_in_content(self):
        """memory_search_guide includes the topic in message content."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory_search_guide",
                arguments={"topic": "project deadlines"},
            )

        content = result.messages[0].content.text
        assert "project deadlines" in content

    @pytest.mark.asyncio
    async def test_includes_memory_types(self):
        """memory_search_guide includes specified memory types."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory_search_guide",
                arguments={
                    "topic": "test",
                    "memory_types": "messages,entities",
                },
            )

        content = result.messages[0].content.text
        assert "messages" in content
        assert "entities" in content

    @pytest.mark.asyncio
    async def test_includes_search_suggestions(self):
        """memory_search_guide includes suggestions for improving search."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory_search_guide",
                arguments={"topic": "test"},
            )

        content = result.messages[0].content.text
        assert "memory_search" in content
        assert "threshold" in content


class TestEntityAnalysisPrompt:
    """Tests for the entity_analysis prompt."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        """entity_analysis returns prompt messages."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "entity_analysis",
                arguments={"entity_name": "Alice"},
            )

        assert len(result.messages) >= 1
        assert result.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_includes_entity_name(self):
        """entity_analysis includes the entity name in content."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "entity_analysis",
                arguments={"entity_name": "Alice"},
            )

        content = result.messages[0].content.text
        assert "Alice" in content

    @pytest.mark.asyncio
    async def test_includes_analysis_steps(self):
        """entity_analysis includes structured analysis steps."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "entity_analysis",
                arguments={"entity_name": "Alice"},
            )

        content = result.messages[0].content.text
        assert "entity_lookup" in content
        assert "relationship" in content.lower()


class TestConversationSummaryPrompt:
    """Tests for the conversation_summary prompt."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        """conversation_summary returns prompt messages."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "conversation_summary",
                arguments={"session_id": "session-123"},
            )

        assert len(result.messages) >= 1
        assert result.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_includes_session_id(self):
        """conversation_summary includes the session ID in content."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "conversation_summary",
                arguments={"session_id": "session-123"},
            )

        content = result.messages[0].content.text
        assert "session-123" in content

    @pytest.mark.asyncio
    async def test_includes_summary_steps(self):
        """conversation_summary includes structured summary steps."""
        server = _create_server()
        async with Client(server) as client:
            result = await client.get_prompt(
                "conversation_summary",
                arguments={"session_id": "session-123"},
            )

        content = result.messages[0].content.text
        assert "conversation_history" in content
        assert "action items" in content.lower()
