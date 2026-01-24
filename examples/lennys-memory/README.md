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

**Post-processing options:**

```bash
# Extract entities from already loaded sessions (if you used --no-entities initially)
make extract-entities

# Geocode Location entities (add lat/lon coordinates for spatial queries)
make geocode-locations
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

### Graph Visualization Features

The application includes an interactive graph visualization powered by Neo4j Visualization Library (NVL):

- **Conversation-Scoped Filtering**: The graph shows only nodes relevant to the current conversation/thread, making it easier to explore contextually relevant data
- **Double-Click to Expand**: Double-click any node to fetch and display its neighbors, enabling incremental graph exploration
- **Expand Neighbors Button**: Alternative expansion method via the property panel
- **Memory Type Filtering**: Toggle visibility of short-term, user-profile, and procedural memory nodes
- **Map View**: Location entities with coordinates can be viewed on an interactive map

**API Endpoints for Graph:**
- `GET /api/memory/graph?session_id={thread_id}` - Get conversation-scoped graph
- `GET /api/memory/graph/neighbors/{node_id}?depth=1&limit=50` - Get neighbors of a node for expansion

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

### Entity Extraction Pipeline

The system uses a **multi-stage extraction pipeline** that combines three complementary extractors to identify people, organizations, locations, events, and objects mentioned in the podcasts:

```
Text Input
    ↓
[Stage 1: spaCy] → Fast statistical NER
    ↓
[Stage 2: GLiNER] → Zero-shot NER for domain-specific entities
    ↓
[Stage 3: LLM Fallback] → Complex cases & relationship extraction
    ↓
[Merge by Confidence] → Combine results
    ↓
[Stopword Filtering] → Remove invalid entities (pronouns, numbers, etc.)
    ↓
Neo4j Storage
```

**The Three Extractors:**

| Extractor | Speed | Accuracy | Extracts Relations | Use Case |
|-----------|-------|----------|-------------------|----------|
| **spaCy** | Fast | Good for common entities | No | PERSON, ORG, GPE, DATE |
| **GLiNER2** | Medium | Zero-shot, domain-flexible | No | Custom entity types with descriptions |
| **LLM** | Slow | Highest, context-aware | Yes | Complex text, preferences |

**GLiNER2 Improvements:**

The entity extraction pipeline uses GLiNER2 (`gliner-community/gliner_medium-v2.5`), which provides:

- **Entity type descriptions**: GLiNER2 accepts descriptions for each entity type, significantly improving accuracy
- **Domain schemas**: Pre-defined schemas for different domains (podcast, news, scientific, etc.)
- **Better accuracy**: GLiNER2 v2.5 is more accurate than the previous v2.1 model

**Available Domain Schemas:**

| Schema | Entity Types | Best For |
|--------|-------------|----------|
| `poleo` | person, organization, location, event, object | General POLE+O model |
| `podcast` | person, company, product, concept, book, role, metric, technology | Podcast transcripts |
| `news` | person, organization, location, event, date | News articles |
| `scientific` | author, institution, method, dataset, metric, concept, tool | Research papers |
| `business` | company, person, product, industry, financial_metric, location | Business content |
| `entertainment` | actor, director, film, tv_show, character, award, studio, genre | Entertainment |
| `medical` | disease, drug, symptom, procedure, body_part, gene, organism | Medical/health |
| `legal` | case, person, organization, law, court, date, monetary_amount | Legal documents |

**Using the Podcast Schema:**

The `podcast` schema is optimized for Lenny's Podcast content:

```python
from neo4j_agent_memory.extraction import GLiNEREntityExtractor, get_schema

# Create extractor with podcast schema
extractor = GLiNEREntityExtractor.for_schema("podcast")

# Or configure in ExtractionConfig
from neo4j_agent_memory.config import ExtractionConfig

config = ExtractionConfig(
    gliner_schema="podcast",  # Use the podcast domain schema
    gliner_model="gliner-community/gliner_medium-v2.5",
)
```

The podcast schema extracts these entity types with descriptions:
- **person**: Hosts, guests, and people discussed in the podcast
- **company**: Startups, businesses, and organizations mentioned
- **product**: Products, services, apps, and software tools
- **concept**: Business methodologies, frameworks, and strategies
- **book**: Books and publications mentioned
- **technology**: Technologies, platforms, and technical tools
- **role**: Job titles and professional positions
- **metric**: Business metrics and KPIs

**Merge Strategy:** By default uses **CONFIDENCE** merge - keeps highest confidence version of each entity.

**Stopword Filtering:** After extraction, entities are automatically filtered to remove noise:
- Pronouns: "they", "them", "you", "me", "it"
- Common verbs: "is", "are", "was", "have", "do"
- Articles: "a", "an", "the"
- Numeric values: "10", "123.45", "50%"
- Conversation artifacts: "um", "uh", "hmm"

**Loading Options:**

```bash
# Default: Load with entity extraction (all 3 stages)
make load-full

# Fast: Skip entity extraction during load
make load-fast

# Later: Extract entities from already-loaded transcripts
make extract-entities
```

**Neo4j Storage:** Extracted entities are stored with dynamic labels and linked to messages:

```
(Conversation) -[:HAS_MESSAGE]-> (Message) -[:MENTIONS]-> (Entity:Person)
                                           -[:MENTIONS]-> (Entity:Organization)
                                           -[:MENTIONS]-> (Entity:Location)
```

### Background Entity Enrichment

Entities can be automatically enriched with additional context from external knowledge sources like Wikipedia and Diffbot. This adds descriptions, Wikipedia URLs, Wikidata IDs, and images to extracted entities.

**How it works:**
1. When an entity is extracted and stored, it is queued for background enrichment
2. The enrichment service fetches data from Wikipedia (free) or Diffbot (API key required)
3. The entity is updated in Neo4j with enriched properties

**Enrichment is enabled by default** in this example. To configure:

```bash
# In backend/.env
ENRICHMENT_ENABLED=true           # Enable/disable enrichment
DIFFBOT_API_KEY=your-api-key      # Optional: for richer Diffbot data
```

**Enriched properties added to entities:**
- `enriched_description`: Summary from Wikipedia/Diffbot
- `wikipedia_url`: Link to Wikipedia page
- `wikidata_id`: Wikidata Q identifier (e.g., Q937)
- `image_url`: Primary image URL
- `enriched_at`: Timestamp of enrichment

**Example: Checking enriched entities in Neo4j:**

```cypher
// Find all enriched Person entities
MATCH (e:Entity:Person)
WHERE e.enriched_description IS NOT NULL
RETURN e.name, e.enriched_description, e.wikipedia_url
LIMIT 10

// Find entities pending enrichment
MATCH (e:Entity)
WHERE e.enriched_at IS NULL
RETURN e.name, e.type
```

**Providers:**

| Provider | Cost | Features |
|----------|------|----------|
| **Wikimedia** | Free | Descriptions, Wikipedia links, Wikidata IDs, images |
| **Diffbot** | Paid API | Richer data, related entities, importance scores |

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
--sample N              Load only N transcripts (for testing)
--no-entities           Skip entity extraction (faster loading)
--no-embeddings         Skip embedding generation (faster loading)
--resume                Skip transcripts that are already loaded
--dry-run               Preview what would be loaded without loading
--batch-size N          Number of messages per batch (default: 100)
--concurrency N         Number of concurrent transcript loaders (default: 3)
--extract-entities-only Only extract entities from already loaded sessions
--skip-schema-setup     Skip database schema setup
-v, --verbose           Show detailed progress

# Examples
python scripts/load_transcripts.py --sample 10 --no-entities
python scripts/load_transcripts.py --resume --batch-size 100
python scripts/load_transcripts.py --extract-entities-only  # Post-process entities
```

**Features:**
- Real-time progress bar with ETA
- Automatic retry with exponential backoff for transient failures
- Resume capability for interrupted loads
- Concurrent loading for faster ingestion
- Batch session existence checking for efficient resume
- Detailed statistics on completion (files, turns, speakers, throughput)

## Geocoding Script

The `scripts/geocode_locations.py` script adds latitude/longitude coordinates to Location entities:

```bash
# Basic usage (uses free Nominatim/OpenStreetMap, rate limited to 1 req/sec)
python scripts/geocode_locations.py

# Options
--provider nominatim|google  Geocoding provider (default: nominatim)
--api-key KEY               API key (required for Google)
--batch-size N              Batch size for processing (default: 50)
--skip-existing             Skip locations that already have coordinates
-v, --verbose               Show detailed progress

# Examples
python scripts/geocode_locations.py --verbose
python scripts/geocode_locations.py --provider google --api-key YOUR_KEY
```

After geocoding, you can run spatial queries like finding locations within a radius:

```python
# Find locations near a point
nearby = await memory.long_term.search_locations_near(
    latitude=37.7749,
    longitude=-122.4194,
    radius_km=50.0
)
```

## Project Structure

```
lennys-memory/
├── data/                      # Podcast transcript files (299 .txt files)
├── scripts/
│   ├── load_transcripts.py    # Data loading script
│   └── geocode_locations.py   # Geocoding script for Location entities
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
