"""Validation tests for the google-cloud-financial-advisor example application.

These tests validate that the example app:
- Has correct directory structure
- Has required configuration files
- Has expected backend modules (agents, tools, API routes, models)

Note: These are NOT runtime tests - they validate structure and imports only.
Running the full app requires separate infrastructure (Docker, Neo4j, GCP credentials).
"""

from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"


class TestGoogleCloudFinancialAdvisor:
    """Validation tests for the google-cloud-financial-advisor example."""

    @pytest.fixture
    def app_dir(self):
        """Path to the google-cloud-financial-advisor example."""
        return EXAMPLES_DIR / "google-cloud-financial-advisor"

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

    def test_docker_compose_exists(self, app_dir):
        """Verify docker-compose.yml exists."""
        docker_compose = app_dir / "docker-compose.yml"
        assert docker_compose.exists(), f"docker-compose.yml not found: {docker_compose}"

    def test_readme_exists(self, app_dir):
        """Verify README.md exists."""
        readme = app_dir / "README.md"
        assert readme.exists(), f"README.md not found: {readme}"

    def test_makefile_exists(self, app_dir):
        """Verify Makefile exists."""
        makefile = app_dir / "Makefile"
        assert makefile.exists(), f"Makefile not found: {makefile}"

    def test_backend_pyproject_exists(self, app_dir):
        """Verify backend pyproject.toml exists."""
        pyproject = app_dir / "backend" / "pyproject.toml"
        assert pyproject.exists(), f"pyproject.toml not found: {pyproject}"

    def test_backend_pyproject_has_neo4j_agent_memory(self, app_dir):
        """Verify backend depends on neo4j-agent-memory."""
        pyproject = app_dir / "backend" / "pyproject.toml"
        content = pyproject.read_text()
        assert "neo4j-agent-memory" in content, "Backend should depend on neo4j-agent-memory"

    def test_backend_main_module_exists(self, app_dir):
        """Verify backend main.py exists."""
        main = app_dir / "backend" / "src" / "main.py"
        assert main.exists(), f"main.py not found: {main}"

    def test_backend_config_module_exists(self, app_dir):
        """Verify backend config.py exists."""
        config = app_dir / "backend" / "src" / "config.py"
        assert config.exists(), f"config.py not found: {config}"

    def test_backend_main_has_health_endpoint(self, app_dir):
        """Verify backend has health check endpoint."""
        main = app_dir / "backend" / "src" / "main.py"
        content = main.read_text()
        assert "/health" in content, "Backend should have /health endpoint"
        assert "health" in content, "Backend should have health check function"

    def test_backend_has_agents_module(self, app_dir):
        """Verify backend has agents module with expected agent files."""
        agents_dir = app_dir / "backend" / "src" / "agents"
        assert agents_dir.exists(), f"Agents directory not found: {agents_dir}"

        expected_agents = [
            "supervisor.py",
            "kyc_agent.py",
            "aml_agent.py",
            "compliance_agent.py",
            "relationship_agent.py",
            "prompts.py",
        ]
        for agent_file in expected_agents:
            assert (agents_dir / agent_file).exists(), f"Agent file not found: {agent_file}"

    def test_backend_has_tools_module(self, app_dir):
        """Verify backend has tools module with expected tool files."""
        tools_dir = app_dir / "backend" / "src" / "tools"
        assert tools_dir.exists(), f"Tools directory not found: {tools_dir}"

        expected_tools = [
            "kyc_tools.py",
            "aml_tools.py",
            "compliance_tools.py",
            "relationship_tools.py",
        ]
        for tool_file in expected_tools:
            assert (tools_dir / tool_file).exists(), f"Tool file not found: {tool_file}"

    def test_backend_has_api_routes(self, app_dir):
        """Verify backend has API routes."""
        routes_dir = app_dir / "backend" / "src" / "api" / "routes"
        assert routes_dir.exists(), f"Routes directory not found: {routes_dir}"

        expected_routes = ["chat.py", "alerts.py", "customers.py", "graph.py", "investigations.py"]
        for route in expected_routes:
            assert (routes_dir / route).exists(), f"Route file not found: {route}"

    def test_backend_has_models_module(self, app_dir):
        """Verify backend has models module."""
        models_dir = app_dir / "backend" / "src" / "models"
        assert models_dir.exists(), f"Models directory not found: {models_dir}"

        expected_models = ["chat.py", "customer.py", "alert.py", "investigation.py"]
        for model_file in expected_models:
            assert (models_dir / model_file).exists(), f"Model file not found: {model_file}"

    def test_frontend_package_json_exists(self, app_dir):
        """Verify frontend package.json exists."""
        package_json = app_dir / "frontend" / "package.json"
        assert package_json.exists(), f"package.json not found: {package_json}"

    def test_frontend_has_src_directory(self, app_dir):
        """Verify frontend has src directory with expected structure."""
        frontend_src = app_dir / "frontend" / "src"
        assert frontend_src.exists(), f"Frontend src not found: {frontend_src}"

        expected_dirs = ["components", "lib"]
        for dir_name in expected_dirs:
            assert (frontend_src / dir_name).exists(), f"Frontend src/{dir_name} not found"
