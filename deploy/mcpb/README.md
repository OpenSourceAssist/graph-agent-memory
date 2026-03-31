# Neo4j Agent Memory - MCP Desktop Extension

MCP server extension for Claude Desktop that provides persistent graph memory backed by Neo4j.

## Features

- **Three memory types**: Short-term (conversations), Long-term (entities, preferences, facts), Reasoning (traces)
- **POLE+O entity extraction**: Automatic extraction of Person, Object, Location, Event, Organization entities
- **Knowledge graph**: Entities linked by typed relationships in Neo4j
- **Automatic preference detection**: Learns user preferences from natural conversation
- **Observational memory**: Context compression for long conversations
- **Two tool profiles**: Core (6 tools) or Extended (16 tools)

## Requirements

- Neo4j 5.x instance (local or remote)
- Python 3.10+ (for `uvx` runtime)
- Optional: OpenAI API key for embeddings

## Quick Start

1. Install from Claude Desktop extension directory
2. Set `NEO4J_PASSWORD` environment variable
3. Start a conversation - the server loads memory context automatically

## Alternative Installation (Developer Path)

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "neo4j-agent-memory": {
      "command": "uvx",
      "args": [
        "neo4j-agent-memory[mcp]",
        "mcp",
        "serve",
        "--neo4j-uri", "bolt://localhost:7687",
        "--neo4j-password", "your-password"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

## Tool Profiles

### Core (6 tools)
| Tool | Description |
|------|-------------|
| `memory_search` | Hybrid vector + graph search across all memory types |
| `memory_get_context` | Assembled context for a session |
| `memory_store_message` | Store message with auto entity extraction |
| `memory_add_entity` | Create/update entity with POLE+O typing |
| `memory_add_preference` | Record user preference |
| `memory_add_fact` | Store subject-predicate-object triple |

### Extended (+10 tools)
| Tool | Description |
|------|-------------|
| `memory_get_conversation` | Full conversation history |
| `memory_list_sessions` | Browse stored sessions |
| `memory_get_entity` | Entity details with graph relationships |
| `memory_export_graph` | Subgraph export for visualization |
| `memory_create_relationship` | Link entities together |
| `memory_start_trace` | Begin reasoning trace |
| `memory_record_step` | Record reasoning step |
| `memory_complete_trace` | Complete reasoning trace |
| `memory_get_observations` | Session observations and insights |
| `graph_query` | Read-only Cypher queries |

## Links

- [Documentation](https://neo4j.com/labs/agent-memory)
- [GitHub](https://github.com/neo4j-labs/agent-memory)
- [PyPI](https://pypi.org/project/neo4j-agent-memory/)

---
Neo4j Labs Project - Community Supported
