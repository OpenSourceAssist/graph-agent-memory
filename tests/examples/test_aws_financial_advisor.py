"""Validation tests for the AWS Financial Services Advisor example.

These tests validate that the example:
- Has correct structure (backend/frontend directories)
- Has valid Python syntax
- Uses latest neo4j-agent-memory features
"""

import ast
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
APP_DIR = EXAMPLES_DIR / "aws-financial-services-advisor"


class TestAWSFinancialAdvisorStructure:
    """Structure validation for the AWS Financial Services Advisor example."""

    @pytest.fixture
    def app_dir(self):
        """Path to the example."""
        return APP_DIR

    def test_app_directory_exists(self, app_dir):
        """Verify the example directory exists."""
        assert app_dir.exists(), f"Example directory not found: {app_dir}"

    def test_backend_directory_exists(self, app_dir):
        """Verify the backend directory exists."""
        backend = app_dir / "backend"
        assert backend.exists(), f"Backend directory not found: {backend}"

    def test_frontend_directory_exists(self, app_dir):
        """Verify the frontend directory exists."""
        frontend = app_dir / "frontend"
        assert frontend.exists(), f"Frontend directory not found: {frontend}"

    def test_backend_pyproject_exists(self, app_dir):
        """Verify backend pyproject.toml exists."""
        pyproject = app_dir / "backend" / "pyproject.toml"
        assert pyproject.exists(), f"pyproject.toml not found: {pyproject}"

    def test_backend_pyproject_has_neo4j_agent_memory(self, app_dir):
        """Verify backend depends on neo4j-agent-memory."""
        pyproject = app_dir / "backend" / "pyproject.toml"
        content = pyproject.read_text()
        assert "neo4j-agent-memory" in content, "Backend should depend on neo4j-agent-memory"

    def test_backend_pyproject_has_version_pin(self, app_dir):
        """Verify backend has version pin for neo4j-agent-memory."""
        pyproject = app_dir / "backend" / "pyproject.toml"
        content = pyproject.read_text()
        assert ">=0.1.0" in content, "Backend should pin neo4j-agent-memory>=0.1.0"

    def test_readme_exists(self, app_dir):
        """Verify README.md exists."""
        readme = app_dir / "README.md"
        assert readme.exists(), f"README.md not found: {readme}"

    def test_backend_has_memory_service(self, app_dir):
        """Verify backend has a memory service module."""
        memory_service = app_dir / "backend" / "src" / "services" / "memory_service.py"
        assert memory_service.exists(), f"memory_service.py not found: {memory_service}"

    def test_backend_has_agents(self, app_dir):
        """Verify backend has agent modules."""
        agents_dir = app_dir / "backend" / "src" / "agents"
        assert agents_dir.exists(), f"Agents directory not found: {agents_dir}"


class TestAWSFinancialAdvisorSyntax:
    """Python syntax validation for AWS Financial Services Advisor."""

    def test_backend_python_files_valid_syntax(self):
        """Verify all backend Python files have valid syntax."""
        backend_src = APP_DIR / "backend" / "src"
        if not backend_src.exists():
            pytest.skip("Backend src not found")

        for py_file in backend_src.rglob("*.py"):
            try:
                ast.parse(py_file.read_text())
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {py_file}: {e}")


class TestAWSFinancialAdvisorFeatures:
    """Feature validation for AWS Financial Services Advisor."""

    def test_memory_service_uses_extraction_config(self):
        """Verify memory service uses ExtractionConfig."""
        service = APP_DIR / "backend" / "src" / "services" / "memory_service.py"
        if not service.exists():
            pytest.skip("memory_service.py not found")
        content = service.read_text()
        assert "ExtractionConfig" in content, "memory_service.py should use ExtractionConfig"

    def test_memory_service_references_dedup(self):
        """Verify memory service references DeduplicationConfig."""
        service = APP_DIR / "backend" / "src" / "services" / "memory_service.py"
        if not service.exists():
            pytest.skip("memory_service.py not found")
        content = service.read_text()
        assert "DeduplicationConfig" in content, (
            "memory_service.py should reference DeduplicationConfig"
        )
