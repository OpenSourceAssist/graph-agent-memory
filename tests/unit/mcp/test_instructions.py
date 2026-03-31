"""Unit tests for MCP server instructions."""

from neo4j_agent_memory.mcp._instructions import (
    CORE_INSTRUCTIONS,
    EXTENDED_INSTRUCTIONS,
    get_instructions,
)


class TestCoreInstructions:
    """Tests for core instruction content."""

    def test_mentions_memory_get_context(self):
        assert "memory_get_context" in CORE_INSTRUCTIONS

    def test_mentions_memory_store_message(self):
        assert "memory_store_message" in CORE_INSTRUCTIONS

    def test_mentions_memory_search(self):
        assert "memory_search" in CORE_INSTRUCTIONS

    def test_mentions_memory_add_preference(self):
        assert "memory_add_preference" in CORE_INSTRUCTIONS

    def test_mentions_memory_add_entity(self):
        assert "memory_add_entity" in CORE_INSTRUCTIONS

    def test_mentions_memory_add_fact(self):
        assert "memory_add_fact" in CORE_INSTRUCTIONS

    def test_mentions_poleo(self):
        assert "POLE+O" in CORE_INSTRUCTIONS

    def test_is_nonempty_string(self):
        assert isinstance(CORE_INSTRUCTIONS, str)
        assert len(CORE_INSTRUCTIONS) > 100


class TestExtendedInstructions:
    """Tests for extended instruction content."""

    def test_includes_core_content(self):
        assert CORE_INSTRUCTIONS in EXTENDED_INSTRUCTIONS

    def test_mentions_memory_start_trace(self):
        assert "memory_start_trace" in EXTENDED_INSTRUCTIONS

    def test_mentions_memory_get_entity(self):
        assert "memory_get_entity" in EXTENDED_INSTRUCTIONS

    def test_mentions_memory_create_relationship(self):
        assert "memory_create_relationship" in EXTENDED_INSTRUCTIONS

    def test_mentions_memory_export_graph(self):
        assert "memory_export_graph" in EXTENDED_INSTRUCTIONS

    def test_mentions_graph_query(self):
        assert "graph_query" in EXTENDED_INSTRUCTIONS

    def test_is_longer_than_core(self):
        assert len(EXTENDED_INSTRUCTIONS) > len(CORE_INSTRUCTIONS)


class TestGetInstructions:
    """Tests for the get_instructions function."""

    def test_core_profile_returns_core(self):
        result = get_instructions("core")
        assert result == CORE_INSTRUCTIONS

    def test_extended_profile_returns_extended(self):
        result = get_instructions("extended")
        assert result == EXTENDED_INSTRUCTIONS

    def test_default_is_extended(self):
        result = get_instructions()
        assert result == EXTENDED_INSTRUCTIONS

    def test_unknown_profile_returns_core(self):
        result = get_instructions("unknown")
        assert result == CORE_INSTRUCTIONS
