"""Unit tests for MCP tool definitions."""

import pytest


class TestMCPToolDefinitions:
    """Tests for MCP tool definitions."""

    def test_get_tool_definitions_returns_6_tools(self):
        """Test that exactly 6 tools are defined."""
        from neo4j_agent_memory.mcp.tools import get_tool_definitions

        tools = get_tool_definitions()
        assert len(tools) == 6

    def test_all_tools_have_required_fields(self):
        """Test that all tools have name, description, and inputSchema."""
        from neo4j_agent_memory.mcp.tools import get_tool_definitions

        tools = get_tool_definitions()
        for tool in tools:
            assert "name" in tool, "Tool missing 'name' field"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "inputSchema" in tool, f"Tool {tool.get('name')} missing 'inputSchema'"

    def test_tool_names(self):
        """Test that the expected tools are defined."""
        from neo4j_agent_memory.mcp.tools import get_tool_definitions

        tools = get_tool_definitions()
        tool_names = {t["name"] for t in tools}

        expected_names = {
            "memory_search",
            "memory_store",
            "entity_lookup",
            "conversation_history",
            "graph_query",
            "add_reasoning_trace",
        }
        assert tool_names == expected_names

    def test_memory_search_tool_schema(self):
        """Test memory_search tool has correct schema."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("memory_search")
        assert tool is not None

        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert "memory_types" in schema["properties"]
        assert "session_id" in schema["properties"]
        assert "query" in schema["required"]

    def test_memory_store_tool_schema(self):
        """Test memory_store tool has correct schema."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("memory_store")
        assert tool is not None

        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "type" in schema["properties"]
        assert "content" in schema["properties"]
        assert "session_id" in schema["properties"]
        assert "role" in schema["properties"]
        assert "category" in schema["properties"]
        assert set(schema["required"]) == {"type", "content"}

    def test_entity_lookup_tool_schema(self):
        """Test entity_lookup tool has correct schema."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("entity_lookup")
        assert tool is not None

        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "type" in schema["properties"]
        assert "include_neighbors" in schema["properties"]
        assert "max_hops" in schema["properties"]
        assert schema["required"] == ["name"]

    def test_conversation_history_tool_schema(self):
        """Test conversation_history tool has correct schema."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("conversation_history")
        assert tool is not None

        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "session_id" in schema["properties"]
        assert "limit" in schema["properties"]
        assert "before" in schema["properties"]
        assert schema["required"] == ["session_id"]

    def test_graph_query_tool_schema(self):
        """Test graph_query tool has correct schema."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("graph_query")
        assert tool is not None

        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "parameters" in schema["properties"]
        assert schema["required"] == ["query"]

    def test_get_tool_by_name_returns_none_for_unknown(self):
        """Test that get_tool_by_name returns None for unknown tools."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        assert get_tool_by_name("unknown_tool") is None

    def test_tool_definitions_returns_copy(self):
        """Test that get_tool_definitions returns a copy."""
        from neo4j_agent_memory.mcp.tools import get_tool_definitions

        tools1 = get_tool_definitions()
        tools2 = get_tool_definitions()

        assert tools1 is not tools2
        assert tools1 == tools2


class TestMCPToolDescriptions:
    """Tests for tool descriptions."""

    def test_memory_search_description(self):
        """Test memory_search has meaningful description."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("memory_search")
        assert "search" in tool["description"].lower()
        assert "memory" in tool["description"].lower()

    def test_memory_store_description(self):
        """Test memory_store has meaningful description."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("memory_store")
        assert "store" in tool["description"].lower()
        assert "memory" in tool["description"].lower()

    def test_entity_lookup_description(self):
        """Test entity_lookup has meaningful description."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("entity_lookup")
        assert "entity" in tool["description"].lower()
        assert "relationship" in tool["description"].lower()

    def test_graph_query_description_mentions_read_only(self):
        """Test graph_query description mentions read-only."""
        from neo4j_agent_memory.mcp.tools import get_tool_by_name

        tool = get_tool_by_name("graph_query")
        assert "read-only" in tool["description"].lower()
