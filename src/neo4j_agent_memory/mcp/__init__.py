"""MCP (Model Context Protocol) server for Neo4j Agent Memory.

Exposes memory capabilities via MCP tools, resources, and prompts
for integration with AI platforms like Claude Desktop, Claude Code,
Cursor, and VS Code Copilot.

Built on FastMCP for decorator-based tool/resource/prompt registration.

Supports two tool profiles:
- Core (6 tools): Essential read/write cycle
- Extended (16 tools): Full surface with reasoning, entities, graph export
"""

from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer, create_mcp_server

__all__ = [
    "Neo4jMemoryMCPServer",
    "create_mcp_server",
]
