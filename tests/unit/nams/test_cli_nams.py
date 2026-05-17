"""Phase 7 tests: CLI flags for the NAMS backend.

Covers ``--backend``, ``--api-key``, ``--endpoint`` on ``mcp serve``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from neo4j_agent_memory.cli.main import cli


@pytest.fixture
def runner(monkeypatch):
    """Strip env vars so the resolver doesn't pick up developer defaults."""
    for var in (
        "NEO4J_PASSWORD",
        "NEO4J_USER",
        "NEO4J_USERNAME",
        "NEO4J_URI",
        "MEMORY_API_KEY",
        "MEMORY_ENDPOINT",
        "NAM_BACKEND",
    ):
        monkeypatch.delenv(var, raising=False)
    return CliRunner()


class TestHelpAdvertisesFlags:
    def test_backend_flag_in_help(self, runner):
        result = runner.invoke(cli, ["mcp", "serve", "--help"])
        assert "--backend" in result.output
        assert "bolt" in result.output
        assert "nams" in result.output

    def test_api_key_flag_in_help(self, runner):
        result = runner.invoke(cli, ["mcp", "serve", "--help"])
        assert "--api-key" in result.output

    def test_endpoint_flag_in_help(self, runner):
        result = runner.invoke(cli, ["mcp", "serve", "--help"])
        assert "--endpoint" in result.output


class TestBackendResolution:
    @patch("neo4j_agent_memory.cli.main.asyncio")
    @patch("neo4j_agent_memory.mcp.server.run_server", new_callable=AsyncMock)
    def test_explicit_bolt_requires_password(self, _run_server, mock_asyncio, runner):
        mock_asyncio.run = lambda _coro: None
        result = runner.invoke(cli, ["mcp", "serve", "--backend", "bolt"])
        assert result.exit_code == 1
        assert "password required" in result.output.lower()

    @patch("neo4j_agent_memory.cli.main.asyncio")
    @patch("neo4j_agent_memory.mcp.server.run_server", new_callable=AsyncMock)
    def test_explicit_nams_requires_api_key(
        self, _run_server, mock_asyncio, runner
    ):
        mock_asyncio.run = lambda _coro: None
        result = runner.invoke(cli, ["mcp", "serve", "--backend", "nams"])
        assert result.exit_code == 1
        assert "api key" in result.output.lower()

    @patch("neo4j_agent_memory.cli.main.asyncio")
    @patch("neo4j_agent_memory.mcp.server.run_server", new_callable=AsyncMock)
    def test_nams_with_api_key_succeeds(
        self, _run_server, mock_asyncio, runner
    ):
        mock_asyncio.run = lambda _coro: None
        result = runner.invoke(
            cli,
            [
                "mcp",
                "serve",
                "--backend",
                "nams",
                "--api-key",
                "nams_test_key",
            ],
        )
        assert result.exit_code == 0

    @patch("neo4j_agent_memory.cli.main.asyncio")
    @patch("neo4j_agent_memory.mcp.server.run_server", new_callable=AsyncMock)
    def test_api_key_env_var(
        self, _run_server, mock_asyncio, runner, monkeypatch
    ):
        """Setting MEMORY_API_KEY env defaults backend to nams."""
        mock_asyncio.run = lambda _coro: None
        monkeypatch.setenv("MEMORY_API_KEY", "nams_from_env")
        result = runner.invoke(cli, ["mcp", "serve"])
        assert result.exit_code == 0

    @patch("neo4j_agent_memory.cli.main.asyncio")
    @patch("neo4j_agent_memory.mcp.server.run_server", new_callable=AsyncMock)
    def test_bolt_with_api_key_warns(
        self, _run_server, mock_asyncio, runner
    ):
        """--api-key with --backend=bolt emits a warning but doesn't fail."""
        mock_asyncio.run = lambda _coro: None
        result = runner.invoke(
            cli,
            [
                "mcp",
                "serve",
                "--backend",
                "bolt",
                "--password",
                "test-pw",
                "--api-key",
                "nams_ignored",
            ],
        )
        assert result.exit_code == 0
        assert "warning" in result.output.lower() or "ignoring" in result.output.lower()


class TestRunServerKwargs:
    """Verify the CLI passes the new NAMS kwargs through to run_server."""

    @patch("neo4j_agent_memory.cli.main.asyncio")
    @patch("neo4j_agent_memory.mcp.server.run_server", new_callable=AsyncMock)
    def test_nams_kwargs_forwarded(
        self, mock_run_server, mock_asyncio, runner
    ):
        captured: dict = {}

        def _capture(coro):
            # Pull the kwargs back off the wrapped coroutine — we patched
            # run_server with an AsyncMock so its call_args is populated
            # at coroutine-construction time.
            captured["call_args"] = mock_run_server.call_args
            return None

        mock_asyncio.run = _capture

        result = runner.invoke(
            cli,
            [
                "mcp",
                "serve",
                "--backend",
                "nams",
                "--api-key",
                "nams_test",
                "--endpoint",
                "https://memory.test/v1",
            ],
        )
        assert result.exit_code == 0
        kwargs = captured["call_args"].kwargs
        assert kwargs["backend"] == "nams"
        assert kwargs["nams_api_key"] == "nams_test"
        assert kwargs["nams_endpoint"] == "https://memory.test/v1"
