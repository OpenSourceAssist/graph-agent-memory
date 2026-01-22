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

**Additional loading options:**

```bash
# Fast loading without entity extraction (significantly faster)
make load-fast

# Resume an interrupted load (skip already loaded transcripts)
make load-resume

# Preview what would be loaded without actually loading
make load-dry-run
```

The loader shows real-time progress with ETA:
```
Overall  [████████████░░░░░░░░░░░░░░░░░░] 450/1200 (38%) ETA: 2m 15s [3/10] Brian Chesky.txt
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

1. **Data Loading**: Transcripts are parsed and stored as Messages in short-term memory
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


### 8. TypeScript/JavaScript Client

**Issue**: Frontend visualization requires custom API endpoints.

**Suggestions**:
- Publish a TypeScript client package
- Mirror the Python API for consistency
- Include type definitions
- Provide documentation and examples for easy integration
- Implement a TypeScript client library for easy integration with frontend applications and JavaScript agent frameworks like Mastra and Vercel AI SDK

---

## Data Loading Script

The `scripts/load_transcripts.py` script provides several options for loading podcast transcripts:

```bash
# Basic usage
python scripts/load_transcripts.py --data-dir data

# Options
--sample N          Load only N transcripts (for testing)
--no-entities       Skip entity extraction (faster loading)
--no-embeddings     Skip embedding generation (faster loading)
--resume            Skip transcripts that are already loaded
--dry-run           Preview what would be loaded without loading
--batch-size N      Number of messages per batch (default: 50)
-v, --verbose       Show detailed progress

# Examples
python scripts/load_transcripts.py --sample 10 --no-entities
python scripts/load_transcripts.py --resume --batch-size 100
```

**Features:**
- Real-time progress bar with ETA
- Automatic retry with exponential backoff for transient failures
- Resume capability for interrupted loads
- Detailed statistics on completion (files, turns, speakers, throughput)

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
