# Neo4j Agent Memory

A comprehensive memory system for AI agents using Neo4j as the persistence layer.

[![CI](https://github.com/neo4j-labs/neo4j-agent-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/neo4j-labs/neo4j-agent-memory/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/neo4j-agent-memory.svg)](https://badge.fury.io/py/neo4j-agent-memory)
[![Python versions](https://img.shields.io/pypi/pyversions/neo4j-agent-memory.svg)](https://pypi.org/project/neo4j-agent-memory/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Features

- **Three Memory Types**: Episodic (conversations), Semantic (facts/preferences), and Procedural (reasoning traces)
- **Entity Extraction**: LLM-based or GLiNER for extracting entities from conversations
- **Entity Resolution**: Multi-strategy deduplication (exact, fuzzy, semantic matching)
- **Vector Search**: Semantic similarity search across all memory types
- **Temporal Relationships**: Track when facts become valid or invalid
- **Agent Framework Integrations**: LangChain, Pydantic AI, LlamaIndex, CrewAI

## Installation

```bash
# Basic installation
pip install neo4j-agent-memory

# With OpenAI embeddings
pip install neo4j-agent-memory[openai]

# With LangChain integration
pip install neo4j-agent-memory[langchain]

# With all optional dependencies
pip install neo4j-agent-memory[all]
```

Using uv:

```bash
uv add neo4j-agent-memory
uv add neo4j-agent-memory --extra openai
```

## Quick Start

```python
import asyncio
from pydantic import SecretStr
from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig

async def main():
    # Configure settings
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            password=SecretStr("your-password"),
        )
    )

    # Use the memory client
    async with MemoryClient(settings) as memory:
        # Store a conversation message
        await memory.episodic.add_message(
            session_id="user-123",
            role="user",
            content="Hi, I'm John and I love Italian food!"
        )

        # Add a preference
        await memory.semantic.add_preference(
            category="food",
            preference="Loves Italian cuisine",
            context="Dining preferences"
        )

        # Search for relevant memories
        preferences = await memory.semantic.search_preferences("restaurant recommendation")
        for pref in preferences:
            print(f"[{pref.category}] {pref.preference}")

        # Get combined context for an LLM prompt
        context = await memory.get_context(
            "What restaurant should I recommend?",
            session_id="user-123"
        )
        print(context)

asyncio.run(main())
```

## Memory Types

### Episodic Memory

Stores conversation history and experiences:

```python
# Add messages to a conversation
await memory.episodic.add_message(
    session_id="user-123",
    role="user",
    content="I'm looking for a restaurant"
)

# Get conversation history
conversation = await memory.episodic.get_conversation("user-123")
for msg in conversation.messages:
    print(f"{msg.role}: {msg.content}")

# Search past messages
results = await memory.episodic.search_messages("Italian food")
```

### Semantic Memory

Stores facts, preferences, and entities:

```python
# Add entities
entity = await memory.semantic.add_entity(
    name="John Smith",
    entity_type=EntityType.PERSON,
    description="A customer who loves Italian food"
)

# Add preferences
pref = await memory.semantic.add_preference(
    category="food",
    preference="Prefers vegetarian options",
    context="When dining out"
)

# Add facts with temporal validity
from datetime import datetime
fact = await memory.semantic.add_fact(
    subject="John",
    predicate="works_at",
    obj="Acme Corp",
    valid_from=datetime(2023, 1, 1)
)

# Search for relevant entities
entities = await memory.semantic.search_entities("Italian restaurants")
```

### Procedural Memory

Stores reasoning traces and tool usage patterns:

```python
# Start a reasoning trace
trace = await memory.procedural.start_trace(
    session_id="user-123",
    task="Find a restaurant recommendation"
)

# Add reasoning steps
step = await memory.procedural.add_step(
    trace.id,
    thought="I should search for nearby restaurants",
    action="search_restaurants"
)

# Record tool calls
await memory.procedural.record_tool_call(
    step.id,
    tool_name="search_api",
    arguments={"query": "Italian restaurants"},
    result=["La Trattoria", "Pasta Palace"],
    status=ToolCallStatus.SUCCESS,
    duration_ms=150
)

# Complete the trace
await memory.procedural.complete_trace(
    trace.id,
    outcome="Recommended La Trattoria",
    success=True
)

# Find similar past tasks
similar = await memory.procedural.get_similar_traces("restaurant recommendation")
```

## Agent Framework Integrations

### LangChain

```python
from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory, Neo4jMemoryRetriever

# As memory for an agent
memory = Neo4jAgentMemory(
    memory_client=client,
    session_id="user-123"
)

# As a retriever
retriever = Neo4jMemoryRetriever(
    memory_client=client,
    k=10
)
docs = retriever.invoke("Italian restaurants")
```

### Pydantic AI

```python
from pydantic_ai import Agent
from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency, create_memory_tools

# As a dependency
agent = Agent('openai:gpt-4o', deps_type=MemoryDependency)

@agent.system_prompt
async def system_prompt(ctx):
    context = await ctx.deps.get_context(ctx.messages[-1].content)
    return f"You are helpful.\n\nContext:\n{context}"

# Or create tools for the agent
tools = create_memory_tools(client)
```

### LlamaIndex

```python
from neo4j_agent_memory.integrations.llamaindex import Neo4jLlamaIndexMemory

memory = Neo4jLlamaIndexMemory(
    memory_client=client,
    session_id="user-123"
)
nodes = memory.get("Italian food")
```

### CrewAI

```python
from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

memory = Neo4jCrewMemory(
    memory_client=client,
    crew_id="my-crew"
)
memories = memory.recall("restaurant recommendation")
```

## Configuration

### Environment Variables

```bash
# Neo4j connection
NAM_NEO4J__URI=bolt://localhost:7687
NAM_NEO4J__USERNAME=neo4j
NAM_NEO4J__PASSWORD=your-password

# Embedding provider
NAM_EMBEDDING__PROVIDER=openai
NAM_EMBEDDING__MODEL=text-embedding-3-small

# OpenAI API key (if using OpenAI embeddings/extraction)
OPENAI_API_KEY=your-api-key
```

### Programmatic Configuration

```python
from neo4j_agent_memory import (
    MemorySettings,
    Neo4jConfig,
    EmbeddingConfig,
    EmbeddingProvider,
    ExtractionConfig,
    ExtractorType,
    ResolutionConfig,
    ResolverStrategy,
)

settings = MemorySettings(
    neo4j=Neo4jConfig(
        uri="bolt://localhost:7687",
        password=SecretStr("password"),
    ),
    embedding=EmbeddingConfig(
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model="all-MiniLM-L6-v2",
        dimensions=384,
    ),
    extraction=ExtractionConfig(
        extractor_type=ExtractorType.LLM,
        entity_types=["PERSON", "ORGANIZATION", "LOCATION"],
    ),
    resolution=ResolutionConfig(
        strategy=ResolverStrategy.COMPOSITE,
        fuzzy_threshold=0.85,
        semantic_threshold=0.8,
    ),
)
```

## Entity Resolution

The package includes multiple strategies for resolving duplicate entities:

```python
from neo4j_agent_memory.resolution import (
    ExactMatchResolver,
    FuzzyMatchResolver,
    SemanticMatchResolver,
    CompositeResolver,
)

# Exact matching (case-insensitive)
resolver = ExactMatchResolver()

# Fuzzy matching using RapidFuzz
resolver = FuzzyMatchResolver(threshold=0.85)

# Semantic matching using embeddings
resolver = SemanticMatchResolver(embedder, threshold=0.8)

# Composite: tries exact -> fuzzy -> semantic
resolver = CompositeResolver(
    embedder=embedder,
    fuzzy_threshold=0.85,
    semantic_threshold=0.8,
)
```

## Neo4j Schema

The package automatically creates the following schema:

### Node Labels
- `Conversation`, `Message` - Episodic memory
- `Entity`, `Preference`, `Fact` - Semantic memory
- `ReasoningTrace`, `ReasoningStep`, `Tool`, `ToolCall` - Procedural memory

### Indexes
- Unique constraints on all ID fields
- Vector indexes for semantic search (requires Neo4j 5.11+)
- Regular indexes on frequently queried properties

## Requirements

- Python 3.10+
- Neo4j 5.x (5.11+ recommended for vector indexes)

## Development

```bash
# Clone the repository
git clone https://github.com/neo4j-labs/neo4j-agent-memory.git
cd neo4j-agent-memory

# Install with uv
uv sync --group dev

# Run unit tests
uv run pytest tests/unit -v

# Run linting
uv run ruff check src tests
uv run ruff format src tests

# Run type checking
uv run mypy src
```

### Running Integration Tests

Integration tests require a running Neo4j instance. The easiest way is to use Docker:

```bash
# Option 1: Use the provided script
./scripts/run-integration-tests.sh

# Option 2: Manual setup
# Start Neo4j
docker compose -f docker-compose.test.yml up -d

# Wait for Neo4j to be ready, then run tests
RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration -v

# Stop Neo4j when done
docker compose -f docker-compose.test.yml down -v
```

The integration test script supports several options:

```bash
# Keep Neo4j running after tests (useful for debugging)
./scripts/run-integration-tests.sh --keep

# Run with verbose output
./scripts/run-integration-tests.sh --verbose

# Run specific test pattern
./scripts/run-integration-tests.sh --pattern "test_episodic"
```

## Publishing to PyPI

1. Update version in `pyproject.toml`
2. Create and push a tag:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. GitHub Actions will automatically build and publish to PyPI

## License

Apache License 2.0

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting a pull request.
