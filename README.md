# Neo4j Agent Memory

A comprehensive memory system for AI agents using Neo4j as the persistence layer.

[![CI](https://github.com/neo4j-labs/neo4j-agent-memory/actions/workflows/ci.yml/badge.svg)](https://github.com/neo4j-labs/neo4j-agent-memory/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/neo4j-agent-memory.svg)](https://badge.fury.io/py/neo4j-agent-memory)
[![Python versions](https://img.shields.io/pypi/pyversions/neo4j-agent-memory.svg)](https://pypi.org/project/neo4j-agent-memory/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Features

- **Three Memory Types**: Short-Term (conversations), Long-Term (facts/preferences), and Procedural (reasoning traces)
- **POLE+O Data Model**: Configurable entity schema based on Person, Object, Location, Event, Organization types with subtypes
- **Multi-Stage Entity Extraction**: Pipeline combining spaCy, GLiNER2, and LLM extractors with configurable merge strategies
- **Entity Resolution**: Multi-strategy deduplication (exact, fuzzy, semantic matching) with type-aware resolution
- **Vector Search**: Semantic similarity search across all memory types
- **Temporal Relationships**: Track when facts become valid or invalid
- **Agent Framework Integrations**: LangChain, Pydantic AI, LlamaIndex, CrewAI

## Installation

```bash
# Basic installation
pip install neo4j-agent-memory

# With OpenAI embeddings
pip install neo4j-agent-memory[openai]

# With spaCy for fast entity extraction
pip install neo4j-agent-memory[spacy]
python -m spacy download en_core_web_sm

# With LangChain integration
pip install neo4j-agent-memory[langchain]

# With all optional dependencies
pip install neo4j-agent-memory[all]
```

Using uv:

```bash
uv add neo4j-agent-memory
uv add neo4j-agent-memory --extra openai
uv add neo4j-agent-memory --extra spacy
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
        await memory.short_term.add_message(
            session_id="user-123",
            role="user",
            content="Hi, I'm John and I love Italian food!"
        )

        # Add a preference
        await memory.long_term.add_preference(
            category="food",
            preference="Loves Italian cuisine",
            context="Dining preferences"
        )

        # Search for relevant memories
        preferences = await memory.long_term.search_preferences("restaurant recommendation")
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

### Short-Term Memory

Stores conversation history and experiences:

```python
# Add messages to a conversation
await memory.short_term.add_message(
    session_id="user-123",
    role="user",
    content="I'm looking for a restaurant"
)

# Get conversation history
conversation = await memory.short_term.get_conversation("user-123")
for msg in conversation.messages:
    print(f"{msg.role}: {msg.content}")

# Search past messages
results = await memory.short_term.search_messages("Italian food")
```

### Long-Term Memory

Stores facts, preferences, and entities:

```python
# Add entities with POLE+O types and subtypes
entity = await memory.long_term.add_entity(
    name="John Smith",
    entity_type="PERSON",  # POLE+O type
    subtype="INDIVIDUAL",  # Optional subtype
    description="A customer who loves Italian food"
)

# Add preferences
pref = await memory.long_term.add_preference(
    category="food",
    preference="Prefers vegetarian options",
    context="When dining out"
)

# Add facts with temporal validity
from datetime import datetime
fact = await memory.long_term.add_fact(
    subject="John",
    predicate="works_at",
    obj="Acme Corp",
    valid_from=datetime(2023, 1, 1)
)

# Search for relevant entities
entities = await memory.long_term.search_entities("Italian restaurants")
```

### Procedural Memory

Stores reasoning traces and tool usage patterns:

```python
# Start a reasoning trace (optionally linked to a triggering message)
trace = await memory.procedural.start_trace(
    session_id="user-123",
    task="Find a restaurant recommendation",
    triggered_by_message_id=user_message.id,  # Optional: link to message
)

# Add reasoning steps
step = await memory.procedural.add_step(
    trace.id,
    thought="I should search for nearby restaurants",
    action="search_restaurants"
)

# Record tool calls (optionally linked to a message)
await memory.procedural.record_tool_call(
    step.id,
    tool_name="search_api",
    arguments={"query": "Italian restaurants"},
    result=["La Trattoria", "Pasta Palace"],
    status=ToolCallStatus.SUCCESS,
    duration_ms=150,
    message_id=user_message.id,  # Optional: link tool call to message
)

# Complete the trace
await memory.procedural.complete_trace(
    trace.id,
    outcome="Recommended La Trattoria",
    success=True
)

# Find similar past tasks
similar = await memory.procedural.get_similar_traces("restaurant recommendation")

# Link an existing trace to a message (post-hoc)
await memory.procedural.link_trace_to_message(trace.id, message.id)
```

## Advanced Features

### Session Management

List and manage conversation sessions:

```python
# List all sessions with metadata
sessions = await memory.short_term.list_sessions(
    prefix="user-",  # Optional: filter by prefix
    limit=50,
    offset=0,
    order_by="updated_at",  # "created_at", "updated_at", or "message_count"
    order_dir="desc",
)

for session in sessions:
    print(f"{session.session_id}: {session.message_count} messages")
    print(f"  First: {session.first_message_preview}")
    print(f"  Last: {session.last_message_preview}")
```

### Metadata-Based Search

Search messages with MongoDB-style metadata filters:

```python
# Search with metadata filters
results = await memory.short_term.search_messages(
    "restaurant",
    session_id="user-123",
    metadata_filters={
        "speaker": "Lenny",                    # Exact match
        "turn_index": {"$gt": 5},              # Greater than
        "source": {"$in": ["web", "mobile"]},  # In list
        "archived": {"$exists": False},        # Field doesn't exist
    },
    limit=10,
)
```

### Conversation Summaries

Generate summaries of conversations:

```python
# Basic summary (no LLM required)
summary = await memory.short_term.get_conversation_summary("user-123")
print(summary.summary)
print(f"Messages: {summary.message_count}")
print(f"Key entities: {summary.key_entities}")

# With custom LLM summarizer
async def my_summarizer(transcript: str) -> str:
    # Your LLM call here
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize this conversation concisely."},
            {"role": "user", "content": transcript}
        ]
    )
    return response.choices[0].message.content

summary = await memory.short_term.get_conversation_summary(
    "user-123",
    summarizer=my_summarizer,
    include_entities=True,
)
```

### Streaming Trace Recording

Record reasoning traces during streaming responses:

```python
from neo4j_agent_memory import StreamingTraceRecorder

async with StreamingTraceRecorder(
    memory.procedural,
    session_id="user-123",
    task="Process customer inquiry"
) as recorder:
    # Start a step
    step = await recorder.start_step(
        thought="Analyzing the request",
        action="analyze",
    )
    
    # Record tool calls
    await recorder.record_tool_call(
        "search_api",
        {"query": "customer history"},
        {"found": 5, "results": [...]},
    )
    
    # Add observations
    await recorder.add_observation("Found 5 relevant records")
    
    # Start another step
    await recorder.start_step(thought="Formulating response")

# Trace is automatically completed with timing when context exits
```

### List and Filter Traces

Query reasoning traces with filtering and pagination:

```python
# List traces with filters
traces = await memory.procedural.list_traces(
    session_id="user-123",           # Optional session filter
    success_only=True,               # Only successful traces
    since=datetime(2024, 1, 1),      # After this date
    until=datetime(2024, 12, 31),    # Before this date
    limit=50,
    offset=0,
    order_by="started_at",           # "started_at" or "completed_at"
    order_dir="desc",
)

for trace in traces:
    print(f"{trace.task}: {'Success' if trace.success else 'Failed'}")
```

### Tool Statistics (Optimized)

Get pre-aggregated tool usage statistics:

```python
# Get stats for all tools (uses pre-aggregated data for speed)
stats = await memory.procedural.get_tool_stats()

for tool in stats:
    print(f"{tool.name}:")
    print(f"  Total calls: {tool.total_calls}")
    print(f"  Success rate: {tool.success_rate:.1%}")
    print(f"  Avg duration: {tool.avg_duration_ms}ms")

# Migrate existing data to use pre-aggregation
migrated = await memory.procedural.migrate_tool_stats()
print(f"Migrated stats for {len(migrated)} tools")
```

### Graph Export for Visualization

Export memory graph data for visualization:

```python
# Export the full memory graph
graph = await memory.get_graph(
    memory_types=["short_term", "long_term", "procedural"],  # Optional filter
    session_id="user-123",  # Optional session filter
    include_embeddings=False,  # Don't include large embedding vectors
    limit=1000,
)

print(f"Nodes: {len(graph.nodes)}")
print(f"Relationships: {len(graph.relationships)}")

# Access graph data
for node in graph.nodes:
    print(f"{node.labels}: {node.properties.get('name', node.id)}")

for rel in graph.relationships:
    print(f"{rel.from_node} -[{rel.type}]-> {rel.to_node}")
```

### PydanticAI Trace Recording

Automatically record PydanticAI agent runs as reasoning traces:

```python
from pydantic_ai import Agent
from neo4j_agent_memory.integrations.pydantic_ai import record_agent_trace

agent = Agent('openai:gpt-4o')

# Run the agent
result = await agent.run("Find me a good restaurant")

# Record the trace automatically
trace = await record_agent_trace(
    memory.procedural,
    session_id="user-123",
    result=result,
    task="Restaurant recommendation",
    include_tool_calls=True,
)

print(f"Recorded trace with {len(trace.steps)} steps")
```

## POLE+O Data Model

The package uses the POLE+O data model for entity classification, an extension of the POLE (Person, Object, Location, Event) model commonly used in law enforcement and intelligence analysis:

| Type | Description | Example Subtypes |
|------|-------------|------------------|
| **PERSON** | Individuals, aliases, personas | INDIVIDUAL, ALIAS, PERSONA |
| **OBJECT** | Physical/digital items | VEHICLE, PHONE, EMAIL, DOCUMENT, DEVICE |
| **LOCATION** | Geographic areas, places | ADDRESS, CITY, REGION, COUNTRY, LANDMARK |
| **EVENT** | Incidents, occurrences | INCIDENT, MEETING, TRANSACTION, COMMUNICATION |
| **ORGANIZATION** | Companies, groups | COMPANY, NONPROFIT, GOVERNMENT, EDUCATIONAL |

### Using Entity Types and Subtypes

```python
from neo4j_agent_memory.memory.long_term import Entity, POLEO_TYPES

# Create an entity with type and subtype
entity = Entity(
    name="Toyota Camry",
    type="OBJECT",
    subtype="VEHICLE",
    description="Silver 2023 Toyota Camry"
)

# Access the full type (e.g., "OBJECT:VEHICLE")
print(entity.full_type)

# Available POLE+O types
print(POLEO_TYPES)  # ['PERSON', 'OBJECT', 'LOCATION', 'EVENT', 'ORGANIZATION']
```

### Entity Type Labels in Neo4j

Entity `type` and `subtype` are automatically added as Neo4j node labels in addition to being stored as properties. This enables efficient querying by type:

```python
# When you create this entity:
await client.long_term.add_entity(
    name="Toyota Camry",
    entity_type="OBJECT",
    subtype="VEHICLE",
    description="Silver sedan"
)

# Neo4j creates a node with multiple PascalCase labels:
# (:Entity:Object:Vehicle {name: "Toyota Camry", type: "OBJECT", subtype: "VEHICLE", ...})
```

This allows efficient Cypher queries by type (using PascalCase labels):

```cypher
-- Find all vehicles
MATCH (v:Vehicle) RETURN v

-- Find all people
MATCH (p:Person) RETURN p

-- Find all organizations
MATCH (o:Organization) RETURN o

-- Combine with other criteria
MATCH (v:Vehicle {name: "Toyota Camry"}) RETURN v
```

**Custom Entity Types:** If you define custom entity types outside the POLE+O model, they are also added as PascalCase labels as long as they are valid Neo4j label identifiers (start with a letter, contain only letters, numbers, and underscores):

```python
# Custom types also become PascalCase labels
await client.long_term.add_entity(
    name="Widget Pro",
    entity_type="PRODUCT",      # Custom type -> becomes :Product label
    subtype="ELECTRONICS",      # Custom subtype -> becomes :Electronics label
)

# Neo4j node: (:Entity:Product:Electronics {name: "Widget Pro", ...})

# Query custom types
MATCH (p:Product:Electronics) RETURN p
```

For POLE+O types, subtypes are validated against the known subtypes for that type. For custom types, any valid identifier can be used as a subtype.

## Entity Extraction Pipeline

The package provides a multi-stage extraction pipeline that combines different extractors for optimal accuracy and cost efficiency:

### Pipeline Architecture

```
Text → [spaCy NER] → [GLiNER] → [LLM Fallback] → Merged Results
           ↓              ↓            ↓
       Fast/Free    Zero-shot     High accuracy
```

### Using the Default Pipeline

```python
from neo4j_agent_memory.extraction import create_extractor
from neo4j_agent_memory.config import ExtractionConfig

# Create the default pipeline (spaCy → GLiNER → LLM)
config = ExtractionConfig(
    extractor_type="PIPELINE",
    enable_spacy=True,
    enable_gliner=True,
    enable_llm_fallback=True,
    merge_strategy="confidence",  # Keep highest confidence per entity
)

extractor = create_extractor(config)
result = await extractor.extract("John Smith works at Acme Corp in New York.")
```

### Building a Custom Pipeline

```python
from neo4j_agent_memory.extraction import ExtractorBuilder

# Use the fluent builder API
extractor = (
    ExtractorBuilder()
    .with_spacy(model="en_core_web_sm")
    .with_gliner(model="urchade/gliner_medium-v2.1", threshold=0.5)
    .with_llm_fallback(model="gpt-4o-mini")
    .with_merge_strategy("confidence")
    .build()
)

result = await extractor.extract("Meeting with Jane Doe at Central Park on Friday.")
for entity in result.entities:
    print(f"{entity.name}: {entity.type} (confidence: {entity.confidence:.2f})")
```

### Merge Strategies

When combining results from multiple extractors:

| Strategy | Description |
|----------|-------------|
| `union` | Keep all unique entities from all stages |
| `intersection` | Only keep entities found by multiple extractors |
| `confidence` | Keep highest confidence result per entity |
| `cascade` | Use first extractor's results, fill gaps with others |
| `first_success` | Stop at first stage that returns results |

### Individual Extractors

```python
from neo4j_agent_memory.extraction import (
    SpacyEntityExtractor,
    GLiNEREntityExtractor,
    LLMEntityExtractor,
)

# spaCy - Fast, free, good for common entity types
spacy_extractor = SpacyEntityExtractor(model="en_core_web_sm")

# GLiNER - Zero-shot NER with custom entity types
gliner_extractor = GLiNEREntityExtractor(
    model="urchade/gliner_medium-v2.1",
    entity_types=["person", "organization", "location", "vehicle", "weapon"],
    threshold=0.5,
)

# LLM - Most accurate but higher cost
llm_extractor = LLMEntityExtractor(
    model="gpt-4o-mini",
    entity_types=["PERSON", "ORGANIZATION", "LOCATION", "EVENT", "OBJECT"],
)
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
        # Use the multi-stage pipeline (default)
        extractor_type=ExtractorType.PIPELINE,
        
        # Pipeline stages
        enable_spacy=True,
        enable_gliner=True,
        enable_llm_fallback=True,
        
        # spaCy settings
        spacy_model="en_core_web_sm",
        
        # GLiNER settings
        gliner_model="urchade/gliner_medium-v2.1",
        gliner_threshold=0.5,
        
        # LLM settings
        llm_model="gpt-4o-mini",
        
        # POLE+O entity types
        entity_types=["PERSON", "ORGANIZATION", "LOCATION", "EVENT", "OBJECT"],
        
        # Merge strategy for combining results
        merge_strategy="confidence",
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
- `Conversation`, `Message` - Short-term memory
- `Entity`, `Preference`, `Fact` - Long-term memory
  - Entity nodes also have type/subtype labels (e.g., `:Entity:Person:Individual`, `:Entity:Object:Vehicle`)
- `ReasoningTrace`, `ReasoningStep`, `Tool`, `ToolCall` - Procedural memory

### Relationships

**Short-term memory:**
- `(Conversation)-[:HAS_MESSAGE]->(Message)` - Membership
- `(Conversation)-[:FIRST_MESSAGE]->(Message)` - First message in conversation
- `(Message)-[:NEXT_MESSAGE]->(Message)` - Sequential message chain

**Cross-memory linking:**
- `(ReasoningTrace)-[:INITIATED_BY]->(Message)` - Trace triggered by message
- `(ToolCall)-[:TRIGGERED_BY]->(Message)` - Tool call triggered by message

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

# Or use the Makefile
make install
```

### Using the Makefile

The project includes a comprehensive Makefile for common development tasks:

```bash
# Run all tests (unit + integration with auto-Docker)
make test

# Run unit tests only
make test-unit

# Run integration tests (auto-starts Neo4j via Docker)
make test-integration

# Code quality
make lint         # Run ruff linter
make format       # Format code with ruff
make typecheck    # Run mypy type checking
make check        # Run all checks (lint + typecheck + test)

# Docker management for Neo4j
make neo4j-start  # Start Neo4j container
make neo4j-stop   # Stop Neo4j container
make neo4j-logs   # View Neo4j logs
make neo4j-clean  # Stop and remove volumes

# Run examples
make example-basic      # Basic usage example
make example-resolution # Entity resolution example
make example-langchain  # LangChain integration example
make example-pydantic   # Pydantic AI integration example
make examples           # Run all examples

# Full-stack chat agent
make chat-agent-install  # Install backend + frontend dependencies
make chat-agent-backend  # Run FastAPI backend (port 8000)
make chat-agent-frontend # Run Next.js frontend (port 3000)
make chat-agent          # Show setup instructions
```

### Running Examples

Examples are located in `examples/` and demonstrate various features:

| Example | Description | Requirements |
|---------|-------------|--------------|
| `basic_usage.py` | Core memory operations (short-term, long-term, procedural) | Neo4j, OpenAI API key |
| `entity_resolution.py` | Entity matching strategies | None |
| `langchain_agent.py` | LangChain integration | Neo4j, OpenAI, langchain extra |
| `pydantic_ai_agent.py` | Pydantic AI integration | Neo4j, OpenAI, pydantic-ai extra |
| `full-stack-chat-agent/` | Complete web app with FastAPI backend and Next.js frontend | Neo4j, OpenAI, Node.js |

#### Environment Setup

Examples load environment variables from `examples/.env`. Copy the template:

```bash
cp examples/.env.example examples/.env
# Edit examples/.env with your settings
```

Key variables:
- `NEO4J_URI` - If set, uses this Neo4j; if not set, auto-starts Docker
- `NEO4J_PASSWORD` - Neo4j password (`test-password` for Docker)
- `OPENAI_API_KEY` - Required for OpenAI embeddings and LLM extraction

```bash
# Run with your own Neo4j (uses NEO4J_URI from .env)
make example-basic

# Or without .env (auto-starts Docker Neo4j)
rm examples/.env  # Ensure no .env file
make example-basic  # Will start Docker with test-password
```

### Environment Variables for Testing

```bash
# Control integration test behavior
RUN_INTEGRATION_TESTS=1      # Enable integration tests
SKIP_INTEGRATION_TESTS=1     # Skip integration tests
AUTO_START_DOCKER=1          # Auto-start Neo4j via Docker (default: true)
AUTO_STOP_DOCKER=1           # Auto-stop Neo4j after tests (default: false)
```

The integration test script supports several options:

```bash
# Keep Neo4j running after tests (useful for debugging)
./scripts/run-integration-tests.sh --keep

# Run with verbose output
./scripts/run-integration-tests.sh --verbose

# Run specific test pattern
./scripts/run-integration-tests.sh --pattern "test_short_term"
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
