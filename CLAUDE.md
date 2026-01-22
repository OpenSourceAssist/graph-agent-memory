# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`neo4j-agent-memory` is a Python package that provides a comprehensive memory system for AI agents using Neo4j as the backend. It implements a three-layer memory architecture:

- **Short-Term Memory**: Conversations and messages with temporal context
- **Long-Term Memory**: Entities, preferences, and facts (declarative knowledge)
- **Procedural Memory**: Reasoning traces and tool usage patterns

### POLE+O Data Model

The long-term memory uses the POLE+O entity model (Person, Object, Location, Event, Organization):

- **PERSON**: Individuals, aliases, personas
- **OBJECT**: Physical/digital items (vehicles, phones, documents, devices)
- **LOCATION**: Geographic areas, addresses, places
- **EVENT**: Incidents, meetings, transactions
- **ORGANIZATION**: Companies, non-profits, government agencies

Each entity type supports subtypes for finer classification (e.g., `OBJECT:VEHICLE`, `LOCATION:ADDRESS`).

## Build & Development Commands

```bash
# Install dependencies (uses uv package manager)
uv sync

# Install with all optional dependencies
uv sync --all-extras

# Run unit tests only
make test-unit

# Run all tests (auto-starts Docker Neo4j)
make test-all

# Run integration tests only
make test-integration

# Start/stop Neo4j Docker container
make neo4j-start
make neo4j-stop
make neo4j-wait    # Wait for Neo4j to be ready

# Type checking
make typecheck

# Linting and formatting
make lint
make format

# Run all checks (lint, format, typecheck)
make check

# Pre-commit checks (format, lint, typecheck, unit tests)
make pre-commit
```

## Architecture

### Package Structure

```
src/neo4j_agent_memory/
├── __init__.py              # MemoryClient main entry point
├── config/settings.py       # Pydantic settings configuration
├── core/memory.py           # Base protocols and models
├── schema/
│   ├── __init__.py          # Schema exports
│   └── models.py            # POLE+O entity types, schema config
├── memory/
│   ├── short_term.py          # Conversations, messages
│   ├── long_term.py          # Entities, preferences, facts (POLE+O)
│   └── procedural.py        # Reasoning traces, tool calls
├── extraction/
│   ├── base.py              # EntityExtractor protocol, ExtractedEntity
│   ├── llm_extractor.py     # LLM-based extraction (OpenAI)
│   ├── spacy_extractor.py   # spaCy NER extraction
│   ├── gliner_extractor.py  # GLiNER zero-shot NER
│   ├── pipeline.py          # Multi-stage extraction pipeline
│   └── factory.py           # Extractor factory and builder
├── resolution/
│   ├── base.py              # EntityResolver protocol
│   ├── exact.py             # Exact string matching
│   ├── fuzzy.py             # RapidFuzz-based matching
│   ├── long_term.py          # Embedding similarity
│   └── composite.py         # Chained strategy resolver (type-aware)
├── embeddings/
│   ├── base.py              # Embedder protocol
│   └── openai.py            # OpenAI embeddings
├── graph/
│   ├── client.py            # Async Neo4j client wrapper
│   ├── schema.py            # Index/constraint management
│   ├── queries.py           # Cypher query templates
│   └── query_builder.py     # Dynamic query builder with label validation
└── integrations/
    ├── langchain/           # LangChain memory + retriever
    ├── pydantic_ai/         # Pydantic AI dependency + tools
    ├── llamaindex/          # LlamaIndex memory
    └── crewai/              # CrewAI memory
```

### Key Classes

- **`MemoryClient`**: Main entry point, manages connections and provides access to all memory types
- **`ShortTermMemory`**: Handles conversations and messages
- **`LongTermMemory`**: Handles entities (POLE+O), preferences, and facts
- **`ProceduralMemory`**: Handles reasoning traces and tool calls
- **`Neo4jClient`**: Async wrapper around neo4j Python driver
- **`ExtractionPipeline`**: Multi-stage entity extraction (spaCy → GLiNER → LLM)
- **`CompositeResolver`**: Type-aware entity resolution

### Neo4j Schema

The package creates these node types:
- `Conversation`, `Message` (short-term)
- `Entity` (with `type`, `subtype` for POLE+O), `Preference`, `Fact` (long-term)
  - Entity nodes have dynamic labels for type/subtype (e.g., `:Entity:PERSON:INDIVIDUAL`, `:Entity:OBJECT:VEHICLE`)
- `ReasoningTrace`, `ReasoningStep`, `ToolCall`, `Tool` (procedural)

#### Short-Term Memory Relationships

Messages in conversations are linked sequentially for efficient traversal:

```
(Conversation) -[:FIRST_MESSAGE]-> (Message)     # O(1) access to first message
(Conversation) -[:HAS_MESSAGE]-> (Message)       # Membership (kept for backward compat)
(Message) -[:NEXT_MESSAGE]-> (Message)           # Sequential chain
```

#### Cross-Memory Relationships

Procedural memory can link to short-term memory messages:

```
(ReasoningTrace) -[:INITIATED_BY]-> (Message)    # Trace triggered by user message
(ToolCall) -[:TRIGGERED_BY]-> (Message)          # Tool call triggered by message
```

Vector indexes are created for embedding-based search on Message, Entity, Preference, and ReasoningTrace nodes.

## Testing

### Test Structure

- `tests/unit/` - Unit tests with mocked dependencies
- `tests/integration/` - Integration tests requiring Neo4j
- `tests/benchmark/` - Performance benchmarks

### Running Tests

The test suite uses Docker to run Neo4j automatically:

```bash
# Run unit tests (no Docker needed)
make test-unit

# Run all tests (auto-starts Docker Neo4j)
make test-all

# Run integration tests only
make test-integration

# Run tests with coverage
make coverage-all
```

### Environment Variables for Tests

- `RUN_INTEGRATION_TESTS=1` - Force run integration tests
- `SKIP_INTEGRATION_TESTS=1` - Skip integration tests
- `AUTO_START_DOCKER=true` - Auto-start Docker if Neo4j not available (default)
- `AUTO_STOP_DOCKER=1` - Stop Docker after tests finish

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
    # Short-term: Store conversation (messages are auto-linked sequentially)
    message = await client.short_term.add_message(session_id, "user", "Hello")
    
    # Long-term: Store entity with POLE+O type
    await client.long_term.add_entity(
        "John Smith",
        "PERSON",
        subtype="INDIVIDUAL",
        description="A customer"
    )
    
    # Long-term: Store preference
    await client.long_term.add_preference("food", "Loves Italian cuisine")
    
    # Procedural: Record reasoning linked to triggering message
    trace = await client.procedural.start_trace(
        session_id,
        "Find restaurant",
        triggered_by_message_id=message.id,  # Links trace to message
    )
    
    # Get combined context for LLM
    context = await client.get_context("restaurant recommendation")
```

### Message Linking

Messages are automatically linked in sequence using `FIRST_MESSAGE` and `NEXT_MESSAGE` relationships:

```python
# Messages added individually or in batch are automatically linked
await client.short_term.add_message(session_id, "user", "First message")
await client.short_term.add_message(session_id, "assistant", "Second message")

# For existing data without links, migrate with:
migrated = await client.short_term.migrate_message_links()
# Returns: {"conversation_id": num_messages_linked, ...}
```

### Linking Procedural Memory to Messages

```python
# Link a reasoning trace to the message that initiated it
trace = await client.procedural.start_trace(
    session_id,
    task="Handle user request",
    triggered_by_message_id=message.id,  # Creates INITIATED_BY relationship
)

# Link a tool call to the message that triggered it
await client.procedural.record_tool_call(
    step_id,
    tool_name="search_api",
    arguments={"query": "restaurants"},
    result=[...],
    message_id=message.id,  # Creates TRIGGERED_BY relationship
)

# Or link an existing trace to a message post-hoc
await client.procedural.link_trace_to_message(trace.id, message.id)
```

### POLE+O Entity Types

```python
from neo4j_agent_memory.memory.long_term import Entity, POLEO_TYPES

# Add entities with subtypes
await client.long_term.add_entity("Ford F-150", "OBJECT", subtype="VEHICLE")
await client.long_term.add_entity("123 Main St", "LOCATION", subtype="ADDRESS")
await client.long_term.add_entity("Acme Corp", "ORGANIZATION", subtype="COMPANY")

# Type:subtype string format also works
await client.long_term.add_entity("Meeting Q1", "EVENT:MEETING")
```

### Extraction Pipeline

```python
from neo4j_agent_memory.extraction import (
    ExtractionPipeline,
    create_extractor,
    ExtractorBuilder,
)
from neo4j_agent_memory.config.settings import ExtractionConfig

# Use factory (respects config)
config = ExtractionConfig(
    enable_spacy=True,
    enable_gliner=True,
    enable_llm_fallback=True,
)
extractor = create_extractor(config)

# Or use builder for custom setup
extractor = (
    ExtractorBuilder()
    .with_spacy("en_core_web_sm")
    .with_gliner(threshold=0.5)
    .with_llm_fallback("gpt-4o-mini")
    .merge_by_confidence()
    .build()
)

result = await extractor.extract("John works at Acme Corp in NYC")
for entity in result.entities:
    print(f"{entity.name}: {entity.full_type}")  # e.g., "John: PERSON"
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

1. **POLE+O Entity Types**: Entities now use string `type` and optional `subtype` fields instead of the legacy `EntityType` enum. The enum is kept for backward compatibility but string types are preferred.

2. **Entity Subtypes**: Use `entity.full_type` to get the complete type string (e.g., `"OBJECT:VEHICLE"`). The `subtype` field is optional.

3. **Neo4j DateTime Conversion**: Neo4j returns `neo4j.time.DateTime` objects that must be converted to Python `datetime` using `.to_native()`. Helper function `_to_python_datetime()` handles this.

4. **Metadata Serialization**: Neo4j doesn't support Map types as node properties. Dict metadata must be serialized to JSON strings using `_serialize_metadata()` and deserialized with `_deserialize_metadata()`.

5. **Relationship Objects**: When querying relationships in Neo4j, the returned relationship objects have a different structure than nodes. Use `rel._properties` or handle via fallback patterns.

6. **Async Context Manager**: `MemoryClient` is designed to be used as an async context manager (`async with`) for proper connection handling.

7. **Optional Dependencies**: Framework integrations and extractors (LangChain, spaCy, GLiNER, etc.) are optional. They're wrapped in try/except ImportError blocks.

8. **Type-Aware Resolution**: The `CompositeResolver` now supports type-aware resolution - entities of different types (e.g., PERSON vs LOCATION) are never merged even if they have similar names.

9. **Entity Type Labels**: Entity `type` and `subtype` are added as Neo4j node labels (e.g., `:Entity:PERSON:INDIVIDUAL`) for efficient querying. The `query_builder.py` module validates types against POLE+O whitelist before adding labels. Custom types outside POLE+O are stored as properties only.

## Environment Variables

- `NEO4J_URI` - Neo4j connection URI (default: `bolt://localhost:7687`)
- `NEO4J_USERNAME` - Neo4j username (default: `neo4j`)
- `NEO4J_PASSWORD` - Neo4j password (default for tests: `test-password`)
- `OPENAI_API_KEY` - Required for OpenAI embeddings and LLM extraction
- `RUN_INTEGRATION_TESTS` - Set to `1` to enable integration tests
- `AUTO_START_DOCKER` - Set to `true` to auto-start Neo4j Docker (default)

## Makefile Targets

```bash
make help              # Show all available targets
make install           # Install core dependencies
make install-all       # Install all optional dependencies
make test-unit         # Run unit tests
make test-integration  # Run integration tests (starts Docker)
make test-all          # Run all tests (starts Docker)
make neo4j-start       # Start Neo4j Docker container
make neo4j-stop        # Stop Neo4j Docker container
make neo4j-wait        # Wait for Neo4j to be ready
make neo4j-shell       # Open cypher-shell to Neo4j
make check             # Run lint, format check, typecheck
make pre-commit        # Run all checks + unit tests
make ci                # Full CI simulation

# Simple Examples
make example-basic     # Run basic usage example
make example-resolution # Run entity resolution example
make example-langchain # Run LangChain integration example
make example-pydantic  # Run Pydantic AI integration example
make examples          # Run all examples

# Full-Stack Chat Agent Example
make chat-agent-install  # Install backend + frontend dependencies
make chat-agent-backend  # Run FastAPI backend server
make chat-agent-frontend # Run Next.js frontend dev server
make chat-agent          # Show instructions for running both
```

## Running Examples

Examples are located in `examples/` and can be run via Makefile targets or directly:

```bash
# Via Makefile (auto-starts Docker Neo4j if NEO4J_URI not set)
make example-basic

# Or run directly
uv run python examples/basic_usage.py
```

### Environment Configuration

Examples load environment variables from `examples/.env`. Copy the template:

```bash
cp examples/.env.example examples/.env
```

Key variables:
- `NEO4J_URI` - If set, uses this Neo4j instance; if not set, auto-starts Docker
- `NEO4J_PASSWORD` - Neo4j password (use `test-password` for Docker)
- `OPENAI_API_KEY` - Required for OpenAI embeddings and LLM extraction

If `NEO4J_URI` is not set, the Makefile targets will automatically start the Docker Neo4j container with `test-password`.

## Full-Stack Chat Agent Example

Located in `examples/full-stack-chat-agent/`, this is a complete demonstration of the neo4j-agent-memory package with:

- **Backend**: FastAPI + PydanticAI agent with all three memory types
- **Frontend**: Next.js 14 + Chakra UI with SSE streaming
- **News Graph Tools**: Search, filter, and analyze news articles
- **Memory Graph Visualization**: Interactive graph view using Neo4j Visualization Library (NVL)
- **Automatic Preference Extraction**: Detects and stores user preferences from conversation
- **Memory Context Panel**: Real-time display of short-term, long-term, and procedural memory

### Running the Chat Agent

```bash
# Install dependencies
make chat-agent-install

# Configure environment
cp examples/full-stack-chat-agent/backend/.env.example examples/full-stack-chat-agent/backend/.env
# Edit .env and add OPENAI_API_KEY

# Terminal 1: Start backend
make chat-agent-backend

# Terminal 2: Start frontend
make chat-agent-frontend

# Open http://localhost:3000
```

### Key Files

**Backend:**
- `backend/src/agent/agent.py` - PydanticAI agent with memory-enhanced system prompt
- `backend/src/agent/tools.py` - News graph query tools
- `backend/src/api/routes/chat.py` - SSE streaming chat endpoint with automatic preference extraction
- `backend/src/api/routes/memory.py` - Memory context and preferences API endpoints
- `backend/src/api/routes/threads.py` - Thread/conversation CRUD operations

**Frontend:**
- `frontend/src/hooks/useChat.ts` - React hook with SSE handling
- `frontend/src/hooks/useThreads.ts` - Thread management hook
- `frontend/src/components/chat/` - Chat UI components (MessageList, PromptInput, ToolCallDisplay)
- `frontend/src/components/memory/MemoryContext.tsx` - Memory context panel showing preferences, entities, recent messages
- `frontend/src/components/memory/MemoryGraphView.tsx` - Interactive NVL graph visualization of memory nodes
