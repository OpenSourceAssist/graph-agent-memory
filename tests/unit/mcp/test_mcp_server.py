"""Unit tests for FastMCP server creation and configuration."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCreateMCPServer:
    """Tests for the create_mcp_server factory function."""

    def test_create_mcp_server_returns_fastmcp_instance(self):
        """Test that create_mcp_server returns a FastMCP server."""
        from fastmcp import FastMCP

        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server()
        assert isinstance(server, FastMCP)

    def test_create_mcp_server_default_name(self):
        """Test that the default server name is 'neo4j-agent-memory'."""
        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server()
        assert server.name == "neo4j-agent-memory"

    def test_create_mcp_server_custom_name(self):
        """Test that a custom server name can be provided."""
        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server(server_name="custom-server")
        assert server.name == "custom-server"

    def test_create_mcp_server_with_settings_is_configured(self):
        """Test that a server created with settings is a valid FastMCP instance."""
        from fastmcp import FastMCP

        from neo4j_agent_memory.mcp.server import create_mcp_server

        mock_settings = MagicMock()
        server = create_mcp_server(settings=mock_settings)
        assert isinstance(server, FastMCP)
        assert server.name == "neo4j-agent-memory"

    def test_create_mcp_server_without_settings_registers_tools(self):
        """Test that a server without settings has tools registered and accessible."""
        import asyncio

        from fastmcp import Client

        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server()

        async def _check():
            async with Client(server) as client:
                tools = await client.list_tools()
                # Extended profile (default) registers 16 tools
                assert len(tools) == 16

        asyncio.run(_check())

    def test_create_mcp_server_core_profile(self):
        """Test that core profile registers 6 tools."""
        import asyncio

        from fastmcp import Client

        from neo4j_agent_memory.mcp.server import create_mcp_server

        server = create_mcp_server(profile="core")

        async def _check():
            async with Client(server) as client:
                tools = await client.list_tools()
                assert len(tools) == 6

        asyncio.run(_check())


class TestNeo4jMemoryMCPServerBackwardCompat:
    """Tests for backward-compatible Neo4jMemoryMCPServer wrapper."""

    def test_neo4j_memory_mcp_server_accepts_client(self):
        """Test that Neo4jMemoryMCPServer can be created with a pre-connected client."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client)
        assert server._client is mock_client

    def test_neo4j_memory_mcp_server_has_mcp_attribute(self):
        """Test that the wrapper exposes the underlying FastMCP instance."""
        from fastmcp import FastMCP

        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client)
        assert isinstance(server._mcp, FastMCP)

    def test_neo4j_memory_mcp_server_default_name(self):
        """Test the default server name in backward-compat mode."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client)
        assert server._mcp.name == "neo4j-agent-memory"

    def test_neo4j_memory_mcp_server_custom_name(self):
        """Test custom server name in backward-compat mode."""
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        mock_client = MagicMock()
        server = Neo4jMemoryMCPServer(mock_client, server_name="custom")
        assert server._mcp.name == "custom"


class TestCLIEntryPoint:
    """Tests for the CLI entry point."""

    def test_main_function_exists(self):
        """Test that main() is importable."""
        from neo4j_agent_memory.mcp.server import main

        assert callable(main)

    def test_run_server_function_exists(self):
        """Test that run_server() is importable."""
        from neo4j_agent_memory.mcp.server import run_server

        assert callable(run_server)


class TestModuleExports:
    """Tests for module-level exports."""

    def test_init_exports_create_mcp_server(self):
        """Test that create_mcp_server is exported from __init__."""
        from neo4j_agent_memory.mcp import create_mcp_server

        assert callable(create_mcp_server)

    def test_init_exports_neo4j_memory_mcp_server(self):
        """Test that Neo4jMemoryMCPServer is exported from __init__."""
        from neo4j_agent_memory.mcp import Neo4jMemoryMCPServer

        assert Neo4jMemoryMCPServer is not None


class TestRunServerProviderKwargs:
    """Tests provider-specific kwargs handling in run_server()."""

    async def test_run_server_passes_openai_llm_kwargs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import neo4j_agent_memory as nam
        import neo4j_agent_memory.config.settings as settings_mod
        import neo4j_agent_memory.llm as llm_mod
        import neo4j_agent_memory.mcp.server as server_mod

        captured: dict[str, object] = {}
        created_provider = object()
        fake_server = MagicMock()
        fake_server.run_async = AsyncMock()
        created_settings: list[object] = []

        def fake_from_provider(model: str, *, kind: str = "llm", **kwargs: object) -> object:
            captured["model"] = model
            captured["kind"] = kind
            captured["kwargs"] = kwargs
            return created_provider

        class _FakeSettings:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        class _FakeNeo4jConfig:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        monkeypatch.setattr(llm_mod, "from_provider", fake_from_provider)
        monkeypatch.setattr(nam, "MemorySettings", _FakeSettings)
        monkeypatch.setattr(settings_mod, "Neo4jConfig", _FakeNeo4jConfig)

        def fake_create_mcp_server(settings, *_args, **_kwargs):
            created_settings.append(settings)
            return fake_server

        monkeypatch.setattr(server_mod, "create_mcp_server", fake_create_mcp_server)

        await server_mod.run_server(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test-password",
            llm="openai/gpt-4o-mini",
            llm_api_key="sk-test",
            llm_api_base="https://example.invalid/v1",
        )

        assert captured["model"] == "openai/gpt-4o-mini"
        assert captured["kind"] == "llm"
        assert captured["kwargs"] == {
            "api_key": "sk-test",
            "api_base": "https://example.invalid/v1",
        }
        assert len(created_settings) == 1
        assert created_settings[0].kwargs["llm"] is created_provider

    async def test_run_server_rejects_bedrock_llm_api_base(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import neo4j_agent_memory as nam
        import neo4j_agent_memory.config.settings as settings_mod
        import neo4j_agent_memory.mcp.server as server_mod

        class _FakeSettings:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        class _FakeNeo4jConfig:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        monkeypatch.setattr(nam, "MemorySettings", _FakeSettings)
        monkeypatch.setattr(settings_mod, "Neo4jConfig", _FakeNeo4jConfig)

        with pytest.raises(
            ValueError, match=r"--llm-api-base is not supported for bedrock/\* providers"
        ):
            await server_mod.run_server(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="test-password",
                llm="bedrock/us.anthropic.claude-3-5-sonnet-20240620-v1:0",
                llm_api_base="https://example.invalid/v1",
            )

    async def test_run_server_rejects_bedrock_llm_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import neo4j_agent_memory as nam
        import neo4j_agent_memory.config.settings as settings_mod
        import neo4j_agent_memory.mcp.server as server_mod

        class _FakeSettings:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        class _FakeNeo4jConfig:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        monkeypatch.setattr(nam, "MemorySettings", _FakeSettings)
        monkeypatch.setattr(settings_mod, "Neo4jConfig", _FakeNeo4jConfig)

        with pytest.raises(
            ValueError, match=r"--llm-api-key is not supported for bedrock/\* providers"
        ):
            await server_mod.run_server(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="test-password",
                llm="bedrock/us.anthropic.claude-3-5-sonnet-20240620-v1:0",
                llm_api_key="test-key",
            )

    async def test_run_server_uses_nams_env_fallbacks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import neo4j_agent_memory as nam
        import neo4j_agent_memory.mcp.server as server_mod

        fake_server = MagicMock()
        fake_server.run_async = AsyncMock()
        created_settings: list[object] = []

        class _FakeSettings:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        class _FakeNamsConfig:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

        monkeypatch.setenv("MEMORY_API_KEY", "nams_from_env")
        monkeypatch.setenv("MEMORY_ENDPOINT", "https://memory.example.test/v1")
        monkeypatch.setattr(nam, "MemorySettings", _FakeSettings)
        monkeypatch.setattr(nam, "NamsConfig", _FakeNamsConfig)

        def fake_create_mcp_server(settings, *_args, **_kwargs):
            created_settings.append(settings)
            return fake_server

        monkeypatch.setattr(server_mod, "create_mcp_server", fake_create_mcp_server)

        await server_mod.run_server(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test-password",
            backend="nams",
        )

        assert len(created_settings) == 1
        nams_config = created_settings[0].kwargs["nams"]
        assert nams_config.kwargs["endpoint"] == "https://memory.example.test/v1"
        assert nams_config.kwargs["api_key"].get_secret_value() == "nams_from_env"
