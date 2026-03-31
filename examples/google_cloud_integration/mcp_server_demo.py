#!/usr/bin/env python3
"""MCP Server Demo.

Demonstrates the Neo4j Agent Memory MCP server with 16 tools
organized into core (6) and extended (16) profiles.

Features demonstrated:
- Starting the MCP server programmatically
- Core and extended tool profiles
- Tool invocation examples
- Both stdio and SSE transport modes
- Session strategies and server instructions

Requirements:
    pip install neo4j-agent-memory[mcp]
"""

import asyncio
import json
import os
from datetime import datetime

from pydantic import SecretStr


async def demo_server_tools():
    """Demonstrate MCP server tools and their schemas."""
    from fastmcp import Client

    from neo4j_agent_memory.mcp.server import create_mcp_server

    print("=" * 60)
    print("MCP Server - Tool Profiles")
    print("=" * 60)
    print()

    # Show core profile
    print("Core Profile (6 tools):")
    print("-" * 40)
    core_server = create_mcp_server(profile="core")  # No settings → testing mode
    async with Client(core_server) as client:
        tools = await client.list_tools()
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool.name} - {tool.description[:60]}...")
    print()

    # Show extended profile
    print("Extended Profile (16 tools, default):")
    print("-" * 40)
    extended_server = create_mcp_server(profile="extended")
    async with Client(extended_server) as client:
        tools = await client.list_tools()
        for i, tool in enumerate(tools, 1):
            print(f"  {i:2d}. {tool.name}")
    print()


async def demo_tool_usage():
    """Demonstrate how tools are used via FastMCP Client."""
    from neo4j_agent_memory import MemorySettings
    from neo4j_agent_memory.config.settings import Neo4jConfig
    from neo4j_agent_memory.mcp.server import create_mcp_server

    print("=" * 60)
    print("MCP Server - Tool Usage Examples")
    print("=" * 60)
    print()

    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            username=os.environ.get("NEO4J_USER", "neo4j"),
            password=SecretStr(os.environ.get("NEO4J_PASSWORD", "password")),
        )
    )

    server = create_mcp_server(settings, profile="extended")

    from fastmcp import Client

    async with Client(server) as client:
        session_id = f"mcp-demo-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 1. memory_store_message - Store a message
        print("1. memory_store_message - Storing a message")
        print("-" * 40)

        result = await client.call_tool(
            "memory_store_message",
            {
                "content": "I'm working on the Q1 report with the finance team.",
                "session_id": session_id,
                "role": "user",
            },
        )
        data = json.loads(result.content[0].text)
        print(f"   Stored message ID: {data.get('id', 'N/A')}")
        print()

        # Store another for search
        await client.call_tool(
            "memory_store_message",
            {
                "content": "The deadline for the Q1 report is next Friday.",
                "session_id": session_id,
                "role": "assistant",
            },
        )

        # 2. memory_get_context - Get assembled context
        print("2. memory_get_context - Getting session context")
        print("-" * 40)

        result = await client.call_tool(
            "memory_get_context",
            {"session_id": session_id},
        )
        data = json.loads(result.content[0].text)
        print(f"   Session: {data.get('session_id')}")
        print(f"   Has context: {data.get('has_context')}")
        print()

        # 3. memory_search - Search memories
        print("3. memory_search - Searching memories")
        print("-" * 40)

        result = await client.call_tool(
            "memory_search",
            {"query": "Q1 report deadline", "limit": 5},
        )
        data = json.loads(result.content[0].text)
        results = data.get("results", {})
        total = sum(len(v) for v in results.values())
        print("   Query: 'Q1 report deadline'")
        print(f"   Results: {total} found")
        print()

        # 4. memory_add_preference - Store a preference
        print("4. memory_add_preference - Storing a preference")
        print("-" * 40)

        result = await client.call_tool(
            "memory_add_preference",
            {
                "category": "communication",
                "preference": "Prefers detailed weekly status reports",
            },
        )
        data = json.loads(result.content[0].text)
        print(f"   Stored preference ID: {data.get('id', 'N/A')}")
        print()

        # 5. memory_get_conversation - Get session history
        print("5. memory_get_conversation - Getting session history")
        print("-" * 40)

        result = await client.call_tool(
            "memory_get_conversation",
            {"session_id": session_id, "limit": 10},
        )
        data = json.loads(result.content[0].text)
        print(f"   Session: {session_id}")
        print(f"   Messages: {data.get('message_count', 0)}")
        print()

        # 6. graph_query - Execute Cypher query
        print("6. graph_query - Executing Cypher query")
        print("-" * 40)

        result = await client.call_tool(
            "graph_query",
            {"query": "MATCH (m:Message) RETURN count(m) as message_count"},
        )
        data = json.loads(result.content[0].text)
        print("   Query: MATCH (m:Message) RETURN count(m)")
        print(f"   Result: {data.get('rows', [])}")
        print()

        print("   Note: graph_query only allows read-only queries.")
        print("   Write operations (CREATE, MERGE, DELETE) are blocked.")
        print()


async def demo_server_startup():
    """Show how to start the MCP server."""
    print("=" * 60)
    print("MCP Server - Starting the Server")
    print("=" * 60)
    print()

    print("Option 1: Using the CLI (recommended)")
    print("-" * 40)
    print("""
# Start with stdio transport (for Claude Desktop)
neo4j-memory mcp serve --password secret

# Start with SSE transport (for Cloud Run/HTTP)
neo4j-memory mcp serve --transport sse --port 8080 --password secret

# Core profile (fewer tools, less context overhead)
neo4j-memory mcp serve --profile core --password secret

# With session strategy
neo4j-memory mcp serve --session-strategy per_day --user-id alice --password secret
""")

    print("Option 2: Programmatically")
    print("-" * 40)
    print("""
import asyncio
from neo4j_agent_memory import MemorySettings
from neo4j_agent_memory.mcp.server import create_mcp_server

settings = MemorySettings(...)
server = create_mcp_server(settings, profile="extended")

# stdio transport
await server.run_async(transport="stdio")

# Or SSE transport for HTTP
await server.run_async(transport="sse", host="0.0.0.0", port=8080)
""")

    print("Option 3: Claude Desktop Configuration")
    print("-" * 40)
    print("""
Add to ~/Library/Application Support/Claude/claude_desktop_config.json:

{
  "mcpServers": {
    "neo4j-agent-memory": {
      "command": "neo4j-memory",
      "args": ["mcp", "serve", "--password", "your-password"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
""")


async def demo_tool_schemas():
    """Show the JSON schemas for MCP tool inputs."""
    from fastmcp import Client

    from neo4j_agent_memory.mcp.server import create_mcp_server

    server = create_mcp_server(profile="extended")

    print("=" * 60)
    print("MCP Server - Tool JSON Schemas (Extended Profile)")
    print("=" * 60)
    print()

    async with Client(server) as client:
        tools = await client.list_tools()
        for tool in tools:
            print(f"### {tool.name}")
            print("```json")
            print(
                json.dumps(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                    },
                    indent=2,
                )
            )
            print("```")
            print()


async def main():
    """Run all MCP server demos."""
    print("\n" + "=" * 60)
    print("Neo4j Agent Memory - MCP Server Demo")
    print("=" * 60 + "\n")

    await demo_server_tools()
    await demo_server_startup()

    # Only run tool usage if Neo4j is configured
    if os.environ.get("NEO4J_PASSWORD"):
        try:
            await demo_tool_usage()
        except Exception as e:
            print(f"Tool usage demo skipped: {e}")
    else:
        print("Skipping tool usage demo (NEO4J_PASSWORD not set)")
        print()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60 + "\n")
    print("To start the server, run:")
    print("  neo4j-memory mcp serve --password <your-password>")
    print()


if __name__ == "__main__":
    asyncio.run(main())
