# Lenny's Podcast Memory Explorer

A full-stack application that loads Lenny's Podcast transcripts into neo4j-agent-memory and provides an AI agent for exploring podcast content with graph visualization.

## Overview

This example demonstrates how to use the `neo4j-agent-memory` package to:
- Load and store conversational content (podcast transcripts)
- Build AI agents that can search and retrieve relevant content
- Visualize the memory graph using NVL (Neo4j Visualization Library)

## Tech Stack

- **Backend**: FastAPI + PydanticAI + neo4j-agent-memory
- **Frontend**: Next.js 14 + Chakra UI v3 + NVL
- **Database**: Neo4j 5.x
- **Package Management**: uv (Python), npm (Node.js)

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Neo4j)
- OpenAI API key

## Quick Start

### 1. Start Neo4j

```bash
make neo4j
```

This starts Neo4j at http://localhost:7474 (user: `neo4j`, password: `password`)

### 2. Install Dependencies

```bash
make install
```

### 3. Configure Environment

Backend:
```bash
cd backend
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Frontend:
```bash
cd frontend
cp .env.example .env
```

### 4. Load Podcast Transcripts

Load a sample (5 transcripts) for quick testing:
```bash
make load-sample
```

Or load the full dataset (299 transcripts):
```bash
make load-full
```

### 5. Run the Application

Backend (port 8000):
```bash
make run-backend
```

Frontend (port 3000):
```bash
make run-frontend
```

Visit http://localhost:3000 to start exploring Lenny's Podcast!

## Example Questions

- "What did Brian Chesky say about product management?"
- "Find discussions about growth strategies"
- "What advice did guests give about career transitions?"
- "What episodes cover mental health?"
- "Who talked about startup fundraising?"

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Next.js       │────▶│   FastAPI       │────▶│   Neo4j         │
│   Frontend      │     │   + PydanticAI  │     │   + Memory      │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │   OpenAI        │
                        │   GPT-4o        │
                        └─────────────────┘
```

### Data Flow

1. **Data Loading**: Transcripts are parsed and stored as Messages in episodic memory
2. **Chat**: User questions trigger agent tool calls to search memory
3. **Memory**: Agent retrieves relevant transcript segments via semantic search
4. **Visualization**: NVL renders the memory graph for exploration

### Memory Structure

- **Conversation**: One per episode (session_id: `lenny-podcast-{guest-slug}`)
- **Message**: Each speaker turn with metadata:
  - `speaker`: "Lenny" or guest name
  - `episode_guest`: Guest name from filename
  - `timestamp`: Original HH:MM:SS
  - `source`: "lenny_podcast"
- **Entities**: Extracted people, companies, topics (when enabled)
- **Procedural Memory**: Reasoning traces and tool usage patterns
  - `ReasoningTrace`: Complete trace of an agent task
  - `ReasoningStep`: Individual reasoning steps with thoughts and actions
  - `ToolCall`: Tool invocations with arguments, results, and timing

### Procedural Memory Usage

This example demonstrates full procedural memory integration:

1. **Trace Lifecycle**: Each chat request creates a reasoning trace
2. **Step Tracking**: Tool calls are recorded as reasoning steps with thoughts and actions
3. **Tool Call Recording**: Arguments, results, duration, and status are captured
4. **Error Handling**: Failed tasks are properly recorded with error information
5. **Similar Task Retrieval**: Find past successful traces for similar tasks

API endpoints for procedural memory:
- `GET /api/memory/traces` - List all reasoning traces
- `GET /api/memory/traces/{trace_id}` - Get trace with steps and tool calls
- `GET /api/memory/tool-stats` - Get tool usage statistics
- `GET /api/memory/similar-traces?task=...` - Find similar past traces

---

## Improvement Notes for neo4j-agent-memory

The following observations were made during implementation that could improve the `neo4j-agent-memory` package:

### 1. Bulk Loading Performance

**Issue**: Loading 299 transcripts with ~180k lines takes considerable time due to individual message insertions.

**Suggestions**:
- Add a batch `add_messages()` method for bulk loading
- Support disabling embedding generation during bulk load, then batch-generate afterward
- Add progress callbacks for long-running operations
- Consider transaction batching for better Neo4j performance

```python
# Proposed API
await memory.episodic.add_messages_batch(
    session_id="...",
    messages=[...],  # List of message dicts
    batch_size=100,
    generate_embeddings=True,
    on_progress=lambda current, total: print(f"{current}/{total}")
)
```

### 2. Session-Based Filtering in Search

**Issue**: The `search_messages()` method's session filtering could be more intuitive.

**Current**: Session filtering works but requires knowing the exact session_id format.

**Suggestions**:
- Add a `list_sessions()` method to discover available sessions
- Support partial/fuzzy session matching
- Add session metadata (title, created_at, message_count) retrieval

```python
# Proposed API
sessions = await memory.episodic.list_sessions(
    prefix="lenny-podcast-",
    limit=50
)
```

### 3. Metadata Querying

**Issue**: Searching by metadata fields (e.g., speaker name) requires custom Cypher queries.

**Suggestions**:
- Add metadata-based filtering to `search_messages()`
- Support indexed metadata fields for faster queries

```python
# Proposed API
messages = await memory.episodic.search_messages(
    query="product management",
    metadata_filters={"speaker": "Brian Chesky"},
    limit=10
)
```

### 4. Entity Extraction Control

**Issue**: Entity extraction during bulk loading is slow and may not be desired for pre-processed content.

**Suggestions**:
- Make entity extraction lazy/deferred
- Add bulk entity extraction as a separate operation
- Support custom entity extraction pipelines

```python
# Proposed API
# First load without extraction
await memory.episodic.add_message(..., extract_entities=False)

# Later, batch extract entities
await memory.semantic.extract_entities_from_session(session_id="...")
```

### 5. Graph Export for Visualization

**Issue**: Getting graph data for visualization requires raw Cypher queries.

**Suggestions**:
- Add a `get_graph()` method on MemoryClient
- Support filtering by memory type, session, time range
- Include pagination for large graphs

```python
# Proposed API
graph = await memory.get_graph(
    include_episodic=True,
    include_semantic=True,
    include_procedural=False,
    session_ids=["lenny-podcast-brian-chesky"],
    limit=1000
)
```

### 6. Message Deletion

**Issue**: No method to delete messages or clear a session.

**Suggestions**:
- Add `delete_message()` and `clear_session()` methods
- Support cascading deletion of related entities

```python
# Proposed API
await memory.episodic.clear_session(session_id="...")
await memory.episodic.delete_message(message_id="...")
```

### 7. Conversation Summary

**Issue**: Long conversations can exceed context limits.

**Suggestions**:
- Add automatic conversation summarization
- Support retrieving summary instead of full history
- Configurable summarization triggers (message count, token count)

```python
# Proposed API
summary = await memory.episodic.get_conversation_summary(
    session_id="...",
    max_tokens=1000
)
```

### 8. TypeScript/JavaScript Client

**Issue**: Frontend visualization requires custom API endpoints.

**Suggestions**:
- Publish a TypeScript client package
- Mirror the Python API for consistency
- Include type definitions

### 9. Documentation Improvements

**Suggestions**:
- Add more examples for common use cases (bulk loading, search patterns)
- Document metadata storage format
- Provide migration guides for schema changes
- Include performance tuning guidelines

### 10. Testing Utilities

**Suggestions**:
- Add fixtures/factories for testing
- Provide mock clients for unit testing
- Include integration test helpers

### 11. Procedural Memory: Streaming Integration

**Issue**: Recording tool calls during streaming agent execution requires manual tracking of tool call IDs and timing.

**Current Approach**: In this example, we manually track `tool_call_start_times` to calculate duration, and match tool results to their corresponding steps.

**Suggestions**:
- Add a `StreamingTraceRecorder` helper class that handles timing automatically
- Provide decorators or context managers for tool call recording
- Support automatic correlation between tool calls and results

```python
# Proposed API
async with memory.procedural.streaming_trace(session_id, task) as recorder:
    async for event in agent.run_stream(...):
        if is_tool_call(event):
            await recorder.record_tool_call(event)  # Automatically tracks timing
        elif is_tool_result(event):
            await recorder.record_tool_result(event)  # Auto-correlates with call
```

### 12. Procedural Memory: PydanticAI Integration

**Issue**: Integrating procedural memory with PydanticAI requires parsing `ModelResponse` and `ModelRequest` message types manually.

**Suggestions**:
- Add a PydanticAI-specific integration module
- Provide automatic trace recording from PydanticAI result objects
- Support extracting reasoning from model messages

```python
# Proposed API
from neo4j_agent_memory.integrations.pydantic_ai import record_agent_trace

async with agent.run_stream(prompt, deps=deps) as result:
    # ... stream handling ...
    
# Automatically record trace from result
await record_agent_trace(memory, result, session_id)
```

### 13. Procedural Memory: List All Traces

**Issue**: `get_session_traces()` requires a session_id, but there's no way to list all traces across sessions without raw Cypher.

**Suggestions**:
- Add a `list_traces()` method with optional filters
- Support pagination for large numbers of traces
- Include filtering by time range, success status, etc.

```python
# Proposed API
traces = await memory.procedural.list_traces(
    limit=50,
    offset=0,
    success_only=True,
    since=datetime(2024, 1, 1),
)
```

### 14. Procedural Memory: Tool Stats Query Performance

**Issue**: The `GET_TOOL_STATS` query may be slow with many tool calls as it aggregates across all records.

**Suggestions**:
- Maintain pre-aggregated statistics on the Tool node
- Update stats incrementally when recording tool calls
- Add caching for frequently accessed stats

```python
# Proposed: Update stats incrementally
await memory.procedural.record_tool_call(
    step_id=step.id,
    tool_name="search_podcast",
    arguments={...},
    result=result,
    status=ToolCallStatus.SUCCESS,
    duration_ms=150,
    update_stats=True,  # Incrementally update Tool node stats
)
```

### 15. Procedural Memory: Observation Field Usage

**Issue**: The `observation` field in `ReasoningStep` is intended to capture the result of an action, but it's unclear how to populate it in agentic frameworks where tool results come separately.

**Suggestions**:
- Clarify the intended use of `thought`, `action`, and `observation` fields
- Consider auto-populating `observation` from the first tool call result
- Document patterns for different agent architectures (ReAct, etc.)

### 16. Procedural Memory: Embedding Generation Control

**Issue**: Generating embeddings for every reasoning step during streaming can impact performance. The current workaround is `generate_embedding=False`.

**Suggestions**:
- Make embedding generation async/batched after trace completion
- Add a `complete_trace()` option to batch-generate embeddings for all steps
- Support configuring embedding strategy per memory type

```python
# Proposed API
await memory.procedural.complete_trace(
    trace_id,
    outcome=outcome,
    success=True,
    generate_step_embeddings=True,  # Batch generate all step embeddings
)
```

---

## Project Structure

```
lennys-memory/
├── data/                      # Podcast transcript files (299 .txt files)
├── scripts/
│   └── load_transcripts.py    # Data loading script
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   └── src/
│       ├── main.py            # FastAPI entry point
│       ├── config.py          # Settings
│       ├── agent/             # PydanticAI agent
│       │   ├── agent.py
│       │   ├── dependencies.py
│       │   └── tools.py
│       ├── api/               # API routes
│       │   └── routes/
│       │       ├── chat.py    # SSE streaming
│       │       ├── threads.py
│       │       └── memory.py
│       └── memory/
│           └── client.py      # Memory singleton
├── frontend/
│   ├── package.json
│   └── src/
│       ├── app/               # Next.js pages
│       ├── components/        # React components
│       │   ├── chat/
│       │   ├── layout/
│       │   └── memory/        # Including MemoryGraphView
│       ├── hooks/
│       └── lib/
│           ├── api.ts
│           └── types.ts
├── Makefile
├── docker-compose.yml
└── README.md
```

## License

This example is part of the neo4j-agent-memory project.
