"""Smoke tests for google_cloud_integration example scripts.

Tests validate that the example scripts:
- Exist and have correct structure
- Use valid Python syntax
- Can import required modules
- Follow project conventions
"""

import ast
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
INTEGRATION_DIR = EXAMPLES_DIR / "google_cloud_integration"

# Check availability of optional dependencies
try:
    from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder

    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

try:
    from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

    GOOGLE_ADK_AVAILABLE = True
except ImportError:
    GOOGLE_ADK_AVAILABLE = False

try:
    from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class TestGoogleCloudIntegrationStructure:
    """Test that all google_cloud_integration example scripts exist and are valid."""

    EXPECTED_SCRIPTS = [
        "vertex_ai_embeddings.py",
        "adk_memory_service.py",
        "mcp_server_demo.py",
        "full_pipeline.py",
    ]

    def test_directory_exists(self):
        """Verify the example directory exists."""
        assert INTEGRATION_DIR.exists(), f"Example directory not found: {INTEGRATION_DIR}"

    def test_readme_exists(self):
        """Verify README.md exists."""
        readme = INTEGRATION_DIR / "README.md"
        assert readme.exists(), f"README.md not found: {readme}"

    def test_env_example_exists(self):
        """Verify .env.example exists."""
        env_example = INTEGRATION_DIR / ".env.example"
        assert env_example.exists(), f".env.example not found: {env_example}"

    @pytest.mark.parametrize("script_name", EXPECTED_SCRIPTS)
    def test_script_exists(self, script_name):
        """Verify each expected script file exists."""
        script = INTEGRATION_DIR / script_name
        assert script.exists(), f"Script not found: {script}"

    @pytest.mark.parametrize("script_name", EXPECTED_SCRIPTS)
    def test_script_valid_python(self, script_name):
        """Verify each script is valid Python syntax."""
        script = INTEGRATION_DIR / script_name
        source_code = script.read_text()
        try:
            ast.parse(source_code)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {script_name}: {e}")

    @pytest.mark.parametrize("script_name", EXPECTED_SCRIPTS)
    def test_script_has_docstring(self, script_name):
        """Verify each script has a module docstring."""
        script = INTEGRATION_DIR / script_name
        content = script.read_text()
        assert content.strip().startswith("#!/usr/bin/env python") or content.strip().startswith(
            '"""'
        ), f"{script_name} should have a module docstring or shebang"


class TestGoogleCloudIntegrationImports:
    """Test that required imports for the integration examples work."""

    def test_memory_client_importable(self):
        """Verify MemoryClient can be imported."""
        from neo4j_agent_memory import MemoryClient

        assert MemoryClient is not None

    @pytest.mark.skipif(not VERTEX_AI_AVAILABLE, reason="vertex-ai not installed")
    def test_vertex_ai_embedder_importable(self):
        """Verify VertexAIEmbedder can be imported."""
        from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder

        assert VertexAIEmbedder is not None

    @pytest.mark.skipif(not VERTEX_AI_AVAILABLE, reason="vertex-ai not installed")
    def test_vertex_ai_embedder_has_properties(self):
        """Verify VertexAIEmbedder has expected public properties."""
        from neo4j_agent_memory.embeddings.vertex_ai import VertexAIEmbedder

        embedder = VertexAIEmbedder()
        assert embedder.model == "text-embedding-004"
        assert embedder.task_type == "RETRIEVAL_DOCUMENT"
        assert embedder.dimensions == 768

    @pytest.mark.skipif(not GOOGLE_ADK_AVAILABLE, reason="google-adk not installed")
    def test_neo4j_memory_service_importable(self):
        """Verify Neo4jMemoryService can be imported."""
        from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

        assert Neo4jMemoryService is not None

    @pytest.mark.skipif(not MCP_AVAILABLE, reason="mcp not installed")
    def test_mcp_server_importable(self):
        """Verify Neo4jMemoryMCPServer can be imported."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        assert Neo4jMemoryMCPServer is not None

    def test_mcp_tools_importable(self):
        """Verify MCP tool definitions can be imported."""
        from neo4j_agent_memory.mcp.tools import MEMORY_TOOLS

        assert MEMORY_TOOLS is not None


class TestMCPToolDefinitions:
    """Test that MCP tool definitions are complete and valid."""

    def test_expected_tool_count(self):
        """Verify there are exactly 6 MCP tools defined."""
        from neo4j_agent_memory.mcp.tools import MEMORY_TOOLS

        assert len(MEMORY_TOOLS) == 6, f"Expected 6 MCP tools, found {len(MEMORY_TOOLS)}"

    def test_tools_have_required_fields(self):
        """Verify each tool has name, description, and inputSchema."""
        from neo4j_agent_memory.mcp.tools import MEMORY_TOOLS

        for tool in MEMORY_TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "inputSchema" in tool, f"Tool {tool.get('name')} missing 'inputSchema'"

    def test_expected_tool_names(self):
        """Verify the expected tool names are present."""
        from neo4j_agent_memory.mcp.tools import MEMORY_TOOLS

        tool_names = {tool["name"] for tool in MEMORY_TOOLS}
        expected_names = {
            "memory_search",
            "memory_store",
            "entity_lookup",
            "conversation_history",
            "graph_query",
            "add_reasoning_trace",
        }
        assert tool_names == expected_names, f"Expected tools {expected_names}, found {tool_names}"
