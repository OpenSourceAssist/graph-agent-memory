# Google ADK Memory Demo

> **Note**: For comprehensive examples of all Google Cloud features (Vertex AI, MCP Server, Cloud Run),
> see the [`google_cloud_integration`](../google_cloud_integration/) directory.

This example demonstrates how to use Neo4j Agent Memory with Google's Agent Development Kit (ADK).

## Overview

The demo shows:
- Storing conversation sessions in Neo4j
- Semantic search across memories
- Entity extraction and knowledge graph building
- Preference learning from conversations

## Prerequisites

1. **Neo4j Database**: Local or Neo4j Aura
2. **Python 3.10+**
3. **Google Cloud Project** (optional, for Vertex AI embeddings)

## Setup

### 1. Install dependencies

```bash
pip install neo4j-agent-memory[google-adk,vertex-ai]
```

Or for local development:
```bash
cd neo4j-agent-memory
pip install -e ".[google-adk,vertex-ai]"
```

### 2. Configure environment

```bash
# Copy the example env file
cp .env.example .env

# Edit with your settings
# - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# - GOOGLE_CLOUD_PROJECT (optional)
```

### 3. Run the demo

```bash
python demo.py
```

## Usage with Google ADK

```python
from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

# Initialize memory client
settings = MemorySettings(
    neo4j=Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password",
    )
)

async with MemoryClient(settings) as client:
    # Create memory service for ADK
    memory_service = Neo4jMemoryService(
        memory_client=client,
        user_id="user-123",
    )
    
    # Store a session
    session = {
        "id": "session-1",
        "messages": [
            {"role": "user", "content": "I'm working on Project Alpha"},
            {"role": "assistant", "content": "Tell me more about Project Alpha"},
        ]
    }
    await memory_service.add_session_to_memory(session)
    
    # Search memories
    results = await memory_service.search_memories("project deadline")
    for entry in results:
        print(f"[{entry.memory_type}] {entry.content}")
    
    # Get session history
    history = await memory_service.get_memories_for_session("session-1")
```

## Features Demonstrated

### 1. Session Storage
Conversations are stored with full message history and automatically indexed for semantic search.

### 2. Entity Extraction
Entities (people, organizations, locations, etc.) are automatically extracted and stored in the knowledge graph.

### 3. Preference Learning
User preferences mentioned in conversations are captured and can be queried later.

### 4. Semantic Search
Search across all memory types using natural language queries with vector similarity.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Google ADK    │────▶│ Neo4jMemoryService│────▶│   Neo4j     │
│     Agent       │     │                  │     │  Database   │
└─────────────────┘     └──────────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │MemoryClient  │
                        │ - short_term │
                        │ - long_term  │
                        │ - reasoning  │
                        └──────────────┘
```

## Next Steps

- Try the MCP server for tool-based memory access
- Deploy to Cloud Run for production use
- Explore the Vertex AI embeddings for better search quality
