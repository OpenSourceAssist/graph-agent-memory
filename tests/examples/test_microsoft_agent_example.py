"""Validation tests for the microsoft_agent_retail_assistant example.

These tests validate that the example app:
- Has correct structure
- Has required files
- Python files have valid syntax
- Key imports are present

Note: These are NOT runtime tests. Running the full app requires
separate infrastructure (Neo4j, Azure OpenAI, etc.).
"""

import ast
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
APP_DIR = EXAMPLES_DIR / "microsoft_agent_retail_assistant"


class TestMicrosoftAgentExampleStructure:
    """Validate directory structure of the Microsoft Agent retail assistant."""

    def test_app_directory_exists(self):
        """Verify the example directory exists."""
        assert APP_DIR.exists(), f"Example directory not found: {APP_DIR}"

    def test_readme_exists(self):
        """Verify README.md exists."""
        readme = APP_DIR / "README.md"
        assert readme.exists(), f"README.md not found: {readme}"

    def test_backend_directory_exists(self):
        """Verify the backend directory exists."""
        assert (APP_DIR / "backend").exists()

    def test_frontend_directory_exists(self):
        """Verify the frontend directory exists."""
        assert (APP_DIR / "frontend").exists()

    def test_backend_main_exists(self):
        """Verify backend main.py exists."""
        assert (APP_DIR / "backend" / "main.py").exists()

    def test_backend_agent_exists(self):
        """Verify backend agent.py exists."""
        assert (APP_DIR / "backend" / "agent.py").exists()

    def test_backend_memory_config_exists(self):
        """Verify backend memory_config.py exists."""
        assert (APP_DIR / "backend" / "memory_config.py").exists()

    def test_backend_requirements_exists(self):
        """Verify backend requirements.txt exists."""
        assert (APP_DIR / "backend" / "requirements.txt").exists()

    def test_backend_tools_directory_exists(self):
        """Verify backend tools directory exists."""
        tools_dir = APP_DIR / "backend" / "tools"
        assert tools_dir.exists()

    def test_backend_tools_have_expected_modules(self):
        """Verify all expected tool modules are present."""
        tools_dir = APP_DIR / "backend" / "tools"
        expected = ["product_search.py", "recommendations.py", "inventory.py", "cart.py"]
        for module in expected:
            assert (tools_dir / module).exists(), f"Tool module not found: {module}"

    def test_frontend_package_json_exists(self):
        """Verify frontend package.json exists."""
        assert (APP_DIR / "frontend" / "package.json").exists()


class TestMicrosoftAgentExampleDependencies:
    """Validate that the example declares correct dependencies."""

    def test_requirements_has_agent_framework(self):
        """Verify requirements.txt includes agent-framework."""
        content = (APP_DIR / "backend" / "requirements.txt").read_text()
        assert "agent-framework" in content

    def test_requirements_has_neo4j_agent_memory(self):
        """Verify requirements.txt includes neo4j-agent-memory."""
        content = (APP_DIR / "backend" / "requirements.txt").read_text()
        assert "neo4j-agent-memory" in content or "microsoft-agent" in content

    def test_requirements_has_fastapi(self):
        """Verify requirements.txt includes fastapi."""
        content = (APP_DIR / "backend" / "requirements.txt").read_text()
        assert "fastapi" in content


class TestMicrosoftAgentExampleSyntax:
    """Validate Python files have valid syntax."""

    @pytest.fixture(
        params=[
            "main.py",
            "agent.py",
            "memory_config.py",
            "tools/product_search.py",
            "tools/recommendations.py",
            "tools/inventory.py",
            "tools/cart.py",
        ]
    )
    def python_file(self, request):
        """Parameterized fixture for each Python file."""
        return APP_DIR / "backend" / request.param

    def test_python_file_has_valid_syntax(self, python_file):
        """Verify Python file can be parsed without syntax errors."""
        if not python_file.exists():
            pytest.skip(f"File not found: {python_file}")
        source = python_file.read_text()
        try:
            ast.parse(source, filename=str(python_file))
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {python_file.name}: {e}")


class TestMicrosoftAgentExampleImports:
    """Validate that key imports are present in the example code."""

    def test_agent_imports_neo4j_memory(self):
        """Verify agent.py imports neo4j_agent_memory integration."""
        content = (APP_DIR / "backend" / "agent.py").read_text()
        assert "neo4j_agent_memory" in content or "microsoft_agent" in content

    def test_memory_config_imports_memory_client(self):
        """Verify memory_config.py imports MemoryClient."""
        content = (APP_DIR / "backend" / "memory_config.py").read_text()
        assert "MemoryClient" in content

    def test_main_imports_fastapi(self):
        """Verify main.py imports FastAPI."""
        content = (APP_DIR / "backend" / "main.py").read_text()
        assert "fastapi" in content or "FastAPI" in content

    def test_agent_uses_create_memory_tools(self):
        """Verify agent.py uses create_memory_tools."""
        content = (APP_DIR / "backend" / "agent.py").read_text()
        assert "create_memory_tools" in content

    def test_agent_uses_context_provider(self):
        """Verify agent.py uses context provider pattern."""
        content = (APP_DIR / "backend" / "agent.py").read_text()
        assert (
            "context_provider" in content
            or "Neo4jContextProvider" in content
            or "Neo4jMicrosoftMemory" in content
        )
