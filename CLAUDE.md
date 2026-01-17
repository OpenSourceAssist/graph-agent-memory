# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`neo4j-agent-memory` is a Python package that provides a comprehensive memory system for AI agents using Neo4j as the backend. It implements a three-layer memory architecture:

- **Episodic Memory**: Conversations and messages with temporal context
- **Semantic Memory**: Entities, preferences, and facts (declarative knowledge)
- **Procedural Memory**: Reasoning traces and tool usage patterns

## Build & Development Commands

```bash
# Install dependencies (uses uv package manager)
uv sync

# Install with all optional dependencies
uv sync --all-extras

# Run all tests
uv run pytest

# Run unit tests only
uv run pytest tests/unit -v

# Run integration tests (requires Neo4j running)
RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration -v

# Start Neo4j for testing via Docker
docker compose -f docker-compose.test.yml up -d

# Type checking
uv run mypy src

# Linting
uv run ruff check src tests

# Format code
uv run ruff format src tests
```

## Architecture

### Package Structure

```
src/neo4j_agent_memory/
├── __init__.py              # MemoryClient main entry point
├── config/settings.py       # Pydantic settings configuration
├── core/memory.py           # Base protocols and models
├── memory/
│   ├── episodic.py          # Conversations, messages
│   ├── semantic.py          # Entities, preferences, facts
│   └── procedural.py        # Reasoning traces, tool calls
├── extraction/
│   ├── base.py              # EntityExtractor protocol
│   └── llm_extractor.py     # LLM-based extraction
├── resolution/
│   ├── base.py              # EntityResolver protocol
│   ├── exact.py             # Exact string matching
│   ├── fuzzy.py             # RapidFuzz-based matching
│   ├── semantic.py          # Embedding similarity
│   └── composite.py         # Chained strategy resolver
├── embeddings/
│   ├── base.py              # Embedder protocol
│   └── openai.py            # OpenAI embeddings
├── graph/
│   ├── client.py            # Async Neo4j client wrapper
│   ├── schema.py            # Index/constraint management
│   └── queries.py           # Cypher query templates
└── integrations/
    ├── langchain/           # LangChain memory + retriever
    ├── pydantic_ai/         # Pydantic AI dependency + tools
    ├── llamaindex/          # LlamaIndex memory
    └── crewai/              # CrewAI memory
```

### Key Classes

- **`MemoryClient`**: Main entry point, manages connections and provides access to all memory types
- **`EpisodicMemory`**: Handles conversations and messages
- **`SemanticMemory`**: Handles entities, preferences, and facts
- **`ProceduralMemory`**: Handles reasoning traces and tool calls
- **`Neo4jClient`**: Async wrapper around neo4j Python driver

### Neo4j Schema

The package creates these node types:
- `Conversation`, `Message` (episodic)
- `Entity`, `Preference`, `Fact` (semantic)
- `ReasoningTrace`, `ReasoningStep`, `ToolCall`, `Tool` (procedural)

Vector indexes are created for embedding-based search on Message, Entity, Preference, and ReasoningTrace nodes.

## Testing

### Test Structure

- `tests/unit/` - Unit tests with mocked dependencies
- `tests/integration/` - Integration tests requiring Neo4j
- `tests/benchmark/` - Performance benchmarks

### Running Integration Tests

Integration tests require a running Neo4j instance:

```bash
# Start Neo4j
docker compose -f docker-compose.test.yml up -d

# Wait for Neo4j to be ready, then run tests
RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration -v
```

### Test Fixtures

Key fixtures in `tests/conftest.py`:
- `memory_settings` - Configuration for test Neo4j instance
- `memory_client` - Connected MemoryClient with mock embedder/extractor/resolver
- `clean_memory_client` - Same as above but cleans database before/after each test
- `mock_embedder`, `mock_extractor`, `mock_resolver` - Mock implementations for testing

## Common Patterns

### Basic Usage

```python
from neo4j_agent_memory import MemoryClient, MemorySettings

settings = MemorySettings(
    neo4j={"uri": "bolt://localhost:7687", "password": "password"}
)

async with MemoryClient(settings) as client:
    # Episodic: Store conversation
    await client.episodic.add_message(session_id, "user", "Hello")
    
    # Semantic: Store preference
    await client.semantic.add_preference("food", "Loves Italian cuisine")
    
    # Procedural: Record reasoning
    trace = await client.procedural.start_trace(session_id, "Find restaurant")
    
    # Get combined context for LLM
    context = await client.get_context("restaurant recommendation")
```

### Framework Integrations

```python
# LangChain
from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory
memory = Neo4jAgentMemory(memory_client=client, session_id="user-123")

# Pydantic AI
from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency
deps = MemoryDependency(client=client, session_id="user-123")
```

## Important Implementation Details

1. **Neo4j DateTime Conversion**: Neo4j returns `neo4j.time.DateTime` objects that must be converted to Python `datetime` using `.to_native()`. Helper function `_to_python_datetime()` handles this.

2. **Metadata Serialization**: Neo4j doesn't support Map types as node properties. Dict metadata must be serialized to JSON strings using `_serialize_metadata()` and deserialized with `_deserialize_metadata()`.

3. **Relationship Objects**: When querying relationships in Neo4j, the returned relationship objects have a different structure than nodes. Use `rel._properties` or handle via fallback patterns.

4. **Async Context Manager**: `MemoryClient` is designed to be used as an async context manager (`async with`) for proper connection handling.

5. **Optional Dependencies**: Framework integrations (LangChain, Pydantic AI, etc.) are optional. They're wrapped in try/except ImportError blocks.

## Environment Variables

- `NEO4J_URI` - Neo4j connection URI (default: `bolt://localhost:7687`)
- `NEO4J_USERNAME` - Neo4j username (default: `neo4j`)
- `NEO4J_PASSWORD` - Neo4j password
- `OPENAI_API_KEY` - Required for OpenAI embeddings
- `RUN_INTEGRATION_TESTS` - Set to `1` to enable integration tests
