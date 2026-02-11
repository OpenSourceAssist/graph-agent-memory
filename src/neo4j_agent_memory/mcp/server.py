"""MCP Server implementation for Neo4j Agent Memory.

Provides a Model Context Protocol server that exposes memory capabilities
as tools for AI platforms and Cloud API Registry integration.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from neo4j_agent_memory.mcp.handlers import MCPHandlers
from neo4j_agent_memory.mcp.tools import get_tool_definitions

if TYPE_CHECKING:
    from neo4j_agent_memory import MemoryClient

logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    class Neo4jMemoryMCPServer:
        """MCP server exposing Neo4j Agent Memory capabilities.

        Designed for registration with Google Cloud API Registry and integration
        with AI platforms supporting the Model Context Protocol.

        Example:
            from neo4j_agent_memory import MemoryClient, MemorySettings
            from neo4j_agent_memory.mcp import Neo4jMemoryMCPServer

            settings = MemorySettings(...)
            async with MemoryClient(settings) as client:
                server = Neo4jMemoryMCPServer(client)
                await server.run()

        Tools:
            - memory_search: Hybrid vector + graph search
            - memory_store: Store messages, facts, preferences
            - entity_lookup: Get entity with relationships
            - conversation_history: Get conversation for session
            - graph_query: Execute read-only Cypher queries
        """

        def __init__(
            self,
            memory_client: MemoryClient,
            *,
            server_name: str = "neo4j-agent-memory",
            server_version: str = "0.0.3",
        ):
            """Initialize the MCP server.

            Args:
                memory_client: Connected MemoryClient instance.
                server_name: Server name for MCP registration.
                server_version: Server version string.
            """
            self._client = memory_client
            self._handlers = MCPHandlers(memory_client)
            self._server_name = server_name
            self._server_version = server_version
            self._server: Server | None = None

        def get_tools(self) -> list[Tool]:
            """Get the list of MCP tools.

            Returns:
                List of Tool objects in MCP format.
            """
            tool_defs = get_tool_definitions()
            return [
                Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=t["inputSchema"],
                )
                for t in tool_defs
            ]

        async def handle_tool_call(
            self,
            name: str,
            arguments: dict[str, Any],
        ) -> list[TextContent]:
            """Handle a tool call from MCP client.

            Args:
                name: Tool name.
                arguments: Tool arguments.

            Returns:
                List of TextContent with results.
            """
            result = await self._handlers.execute_tool(name, arguments)
            return [TextContent(type="text", text=result)]

        def _create_server(self) -> Server:
            """Create and configure the MCP server."""
            server = Server(self._server_name)

            @server.list_tools()
            async def list_tools() -> list[Tool]:
                return self.get_tools()

            @server.call_tool()
            async def call_tool(name: str, arguments: dict) -> list[TextContent]:
                return await self.handle_tool_call(name, arguments or {})

            return server

        async def run(self) -> None:
            """Run the MCP server using stdio transport.

            This starts the server and listens for MCP requests via stdin/stdout.
            """
            self._server = self._create_server()

            async with stdio_server() as (read_stream, write_stream):
                await self._server.run(
                    read_stream,
                    write_stream,
                    self._server.create_initialization_options(),
                )

        async def run_sse(self, host: str = "127.0.0.1", port: int = 8080) -> None:
            """Run the MCP server using SSE transport.

            Args:
                host: Host to bind to.
                port: Port to listen on.
            """
            try:
                import uvicorn
                from mcp.server.sse import SseServerTransport
                from starlette.applications import Starlette
                from starlette.routing import Route
            except ImportError:
                raise ImportError(
                    "SSE transport requires additional dependencies. "
                    "Install with: pip install mcp[sse] uvicorn starlette"
                )

            self._server = self._create_server()
            sse = SseServerTransport("/messages")

            async def handle_sse(request):
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await self._server.run(
                        streams[0],
                        streams[1],
                        self._server.create_initialization_options(),
                    )

            app = Starlette(
                routes=[
                    Route("/sse", endpoint=handle_sse),
                    Route("/messages", endpoint=sse.handle_post_message, methods=["POST"]),
                ]
            )

            config = uvicorn.Config(app, host=host, port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()

    def create_mcp_server(
        memory_client: MemoryClient,
        **kwargs: Any,
    ) -> Neo4jMemoryMCPServer:
        """Factory function to create an MCP server.

        Args:
            memory_client: Connected MemoryClient instance.
            **kwargs: Additional server configuration.

        Returns:
            Configured Neo4jMemoryMCPServer instance.
        """
        return Neo4jMemoryMCPServer(memory_client, **kwargs)

    async def run_server(
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        neo4j_database: str = "neo4j",
        transport: str = "stdio",
        host: str = "127.0.0.1",
        port: int = 8080,
    ) -> None:
        """Run the MCP server with Neo4j connection.

        Convenience function for CLI usage.

        Args:
            neo4j_uri: Neo4j connection URI.
            neo4j_user: Neo4j username.
            neo4j_password: Neo4j password.
            neo4j_database: Neo4j database name.
            transport: Transport type (stdio or sse).
            host: Host for SSE transport.
            port: Port for SSE transport.
        """
        from pydantic import SecretStr

        from neo4j_agent_memory import MemoryClient, MemorySettings
        from neo4j_agent_memory.config.settings import Neo4jConfig

        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=neo4j_uri,
                username=neo4j_user,
                password=SecretStr(neo4j_password),
                database=neo4j_database,
            )
        )

        async with MemoryClient(settings) as client:
            server = Neo4jMemoryMCPServer(client)
            if transport == "sse":
                await server.run_sse(host=host, port=port)
            else:
                await server.run()

except ImportError:
    # MCP not installed
    class Neo4jMemoryMCPServer:  # type: ignore[no-redef]
        """Placeholder when MCP is not installed."""

        def __init__(self, *args: Any, **kwargs: Any):
            raise ImportError(
                "MCP package not installed. Install with: pip install neo4j-agent-memory[mcp]"
            )

    def create_mcp_server(*args: Any, **kwargs: Any) -> Neo4jMemoryMCPServer:
        raise ImportError(
            "MCP package not installed. Install with: pip install neo4j-agent-memory[mcp]"
        )


def main() -> None:
    """CLI entry point for running the MCP server."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Neo4j Agent Memory MCP Server")
    parser.add_argument(
        "--neo4j-uri",
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j connection URI",
    )
    parser.add_argument(
        "--neo4j-user",
        default=os.environ.get("NEO4J_USER", "neo4j"),
        help="Neo4j username",
    )
    parser.add_argument(
        "--neo4j-password",
        default=os.environ.get("NEO4J_PASSWORD", ""),
        help="Neo4j password",
    )
    parser.add_argument(
        "--neo4j-database",
        default=os.environ.get("NEO4J_DATABASE", "neo4j"),
        help="Neo4j database name",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport type",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE transport (use 0.0.0.0 to expose on all interfaces)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for SSE transport",
    )

    args = parser.parse_args()

    asyncio.run(
        run_server(
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password,
            neo4j_database=args.neo4j_database,
            transport=args.transport,
            host=args.host,
            port=args.port,
        )
    )


if __name__ == "__main__":
    main()
