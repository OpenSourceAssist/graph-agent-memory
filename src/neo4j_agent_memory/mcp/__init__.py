"""MCP (Model Context Protocol) server for Neo4j Agent Memory.

Exposes memory capabilities via MCP tools for integration with
AI platforms and Cloud API Registry.
"""

__all__ = [
    "Neo4jMemoryMCPServer",
    "create_mcp_server",
]


def __getattr__(name: str):
    if name == "Neo4jMemoryMCPServer":
        from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

        return Neo4jMemoryMCPServer
    if name == "create_mcp_server":
        from neo4j_agent_memory.mcp.server import create_mcp_server

        return create_mcp_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
