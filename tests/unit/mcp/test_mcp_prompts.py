"""Unit tests for MCP prompt registration and execution.

Tests the _prompts.py module with profile-aware prompt registration.
Uses FastMCP's Client for in-memory testing.
"""

import pytest
from fastmcp import Client

from tests.unit.mcp.conftest import create_prompt_server


class TestPromptRegistration:
    """Tests that prompts register correctly with profiles."""

    @pytest.mark.asyncio
    async def test_core_profile_registers_1_prompt(self):
        server = create_prompt_server(profile="core")
        async with Client(server) as client:
            prompts = await client.list_prompts()
            assert len(prompts) == 1

    @pytest.mark.asyncio
    async def test_core_prompt_is_memory_conversation(self):
        server = create_prompt_server(profile="core")
        async with Client(server) as client:
            prompts = await client.list_prompts()
            names = {p.name for p in prompts}
            assert "memory-conversation" in names

    @pytest.mark.asyncio
    async def test_extended_profile_registers_3_prompts(self):
        server = create_prompt_server(profile="extended")
        async with Client(server) as client:
            prompts = await client.list_prompts()
            assert len(prompts) == 3

    @pytest.mark.asyncio
    async def test_extended_prompt_names(self):
        server = create_prompt_server(profile="extended")
        async with Client(server) as client:
            prompts = await client.list_prompts()
            names = {p.name for p in prompts}
            assert names == {"memory-conversation", "memory-reasoning", "memory-review"}

    @pytest.mark.asyncio
    async def test_prompts_have_descriptions(self):
        server = create_prompt_server(profile="extended")
        async with Client(server) as client:
            prompts = await client.list_prompts()
            for prompt in prompts:
                assert prompt.description, f"Prompt {prompt.name} has no description"


class TestMemoryConversationPrompt:
    """Tests for the memory-conversation prompt."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        server = create_prompt_server(profile="core")
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory-conversation",
                arguments={"session_id": "test-123"},
            )
        assert len(result.messages) >= 1
        assert result.messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_includes_session_id(self):
        server = create_prompt_server(profile="core")
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory-conversation",
                arguments={"session_id": "test-123"},
            )
        content = result.messages[0].content.text
        assert "test-123" in content

    @pytest.mark.asyncio
    async def test_references_memory_tools(self):
        server = create_prompt_server(profile="core")
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory-conversation",
                arguments={"session_id": "s1"},
            )
        content = result.messages[0].content.text
        assert "memory_get_context" in content
        assert "memory_store_message" in content


class TestMemoryReasoningPrompt:
    """Tests for the memory-reasoning prompt."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        server = create_prompt_server(profile="extended")
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory-reasoning",
                arguments={"task": "Find restaurants"},
            )
        assert len(result.messages) >= 1
        content = result.messages[0].content.text
        assert "Find restaurants" in content

    @pytest.mark.asyncio
    async def test_references_trace_tools(self):
        server = create_prompt_server(profile="extended")
        async with Client(server) as client:
            result = await client.get_prompt(
                "memory-reasoning",
                arguments={"task": "test"},
            )
        content = result.messages[0].content.text
        assert "memory_start_trace" in content
        assert "memory_record_step" in content
        assert "memory_complete_trace" in content


class TestMemoryReviewPrompt:
    """Tests for the memory-review prompt."""

    @pytest.mark.asyncio
    async def test_returns_messages(self):
        server = create_prompt_server(profile="extended")
        async with Client(server) as client:
            result = await client.get_prompt("memory-review", arguments={})
        assert len(result.messages) >= 1

    @pytest.mark.asyncio
    async def test_references_search_tools(self):
        server = create_prompt_server(profile="extended")
        async with Client(server) as client:
            result = await client.get_prompt("memory-review", arguments={})
        content = result.messages[0].content.text
        assert "memory_search" in content
        assert "memory_list_sessions" in content
