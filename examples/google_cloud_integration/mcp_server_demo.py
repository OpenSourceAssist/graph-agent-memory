#!/usr/bin/env python3
"""MCP Server Demo.

Demonstrates the Neo4j Agent Memory MCP server and its 6 tools.

Features demonstrated:
- Starting the MCP server programmatically
- Available tools and their schemas
- Tool invocation examples
- Both stdio and SSE transport modes

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

    server = create_mcp_server()  # No settings → testing mode

    print("=" * 60)
    print("MCP Server - Available Tools")
    print("=" * 60)
    print()

    print("The Neo4j Memory MCP server exposes 6 tools:")
    print()

    async with Client(server) as client:
        tools = await client.list_tools()
        for i, tool in enumerate(tools, 1):
            print(f"{i}. {tool.name}")
            print(f"   Description: {tool.description[:70]}...")
            print()

            # Show input schema
            schema = tool.inputSchema
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            print("   Parameters:")
            for prop_name, prop_def in properties.items():
                req_marker = "*" if prop_name in required else " "
                prop_type = prop_def.get("type", "any")
                prop_desc = prop_def.get("description", "")[:40]
                print(f"     {req_marker} {prop_name}: {prop_type} - {prop_desc}...")
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

    server = create_mcp_server(settings)

    from fastmcp import Client

    async with Client(server) as client:
        # 1. memory_store - Store a message
        print("1. memory_store - Storing a message")
        print("-" * 40)

        session_id = f"mcp-demo-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result = await client.call_tool(
            "memory_store",
            {
                "memory_type": "message",
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
            "memory_store",
            {
                "memory_type": "message",
                "content": "The deadline for the Q1 report is next Friday.",
                "session_id": session_id,
                "role": "assistant",
            },
        )

        # 2. memory_search - Search memories
        print("2. memory_search - Searching memories")
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

        # 3. memory_store - Store a preference
        print("3. memory_store - Storing a preference")
        print("-" * 40)

        result = await client.call_tool(
            "memory_store",
            {
                "memory_type": "preference",
                "content": "Prefers detailed weekly status reports",
                "category": "communication",
            },
        )
        data = json.loads(result.content[0].text)
        print(f"   Stored preference ID: {data.get('id', 'N/A')}")
        print()

        # 4. conversation_history - Get session history
        print("4. conversation_history - Getting session history")
        print("-" * 40)

        result = await client.call_tool(
            "conversation_history",
            {"session_id": session_id, "limit": 10},
        )
        data = json.loads(result.content[0].text)
        print(f"   Session: {session_id}")
        print(f"   Messages: {data.get('message_count', 0)}")
        print()

        # 5. graph_query - Execute Cypher query
        print("5. graph_query - Executing Cypher query")
        print("-" * 40)

        result = await client.call_tool(
            "graph_query",
            {"query": "MATCH (m:Message) RETURN count(m) as message_count"},
        )
        data = json.loads(result.content[0].text)
        print("   Query: MATCH (m:Message) RETURN count(m)")
        print(f"   Result: {data.get('rows', [])}")
        print()

        # Show read-only validation
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
# Start with stdio transport (for local MCP clients)
neo4j-memory mcp serve

# Start with SSE transport (for Cloud Run/HTTP)
neo4j-memory mcp serve --transport sse --port 8080

# With custom Neo4j connection
neo4j-memory mcp serve \\
  --neo4j-uri bolt://localhost:7687 \\
  --neo4j-user neo4j \\
  --neo4j-password secret
""")

    print("Option 2: Programmatically")
    print("-" * 40)
    print("""
import asyncio
from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.mcp.server import Neo4jMemoryMCPServer

async def main():
    settings = MemorySettings(...)
    async with MemoryClient(settings) as client:
        server = Neo4jMemoryMCPServer(client)

        # stdio transport
        await server.run()

        # Or SSE transport for HTTP
        await server.run_sse(host="0.0.0.0", port=8080)

asyncio.run(main())
""")

    print("Option 3: Claude Desktop Configuration")
    print("-" * 40)
    print("""
Add to ~/Library/Application Support/Claude/claude_desktop_config.json:

{
  "mcpServers": {
    "neo4j-memory": {
      "command": "neo4j-memory",
      "args": ["mcp", "serve"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_PASSWORD": "your-password"
      }
    }
  }
}
""")


async def demo_tool_schemas():
    """Show the JSON schemas for MCP tool inputs."""
    from fastmcp import Client

    from neo4j_agent_memory.mcp.server import create_mcp_server

    server = create_mcp_server()

    print("=" * 60)
    print("MCP Server - Tool JSON Schemas")
    print("=" * 60)
    print()

    print("Full JSON schemas for each tool (for MCP client integration):")
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
    print("  neo4j-memory mcp serve")
    print()


if __name__ == "__main__":
    asyncio.run(main())
