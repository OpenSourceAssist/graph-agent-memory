# NAMS Quickstart

Minimal end-to-end example showing the `neo4j-agent-memory` library
against the hosted **Neo4j Agent Memory Service (NAMS)**.

This script:

1. Stores a few short-term messages in a NAMS conversation.
2. Records a long-term entity.
3. Starts, steps, and completes a reasoning trace with a tool call.
4. Runs a portable read-only Cypher query.

Every call uses the unified `MemoryClient` API — flip `backend="nams"`
to `backend="bolt"` (plus a `neo4j=Neo4jConfig(password=...)`) and the
same script body runs against direct Neo4j.

## Setup

1. Get a NAMS API key from <https://memory.neo4jlabs.com>.

2. Install dependencies in a fresh venv:

   ```bash
   uv pip install -r requirements.txt
   ```

3. Configure your key:

   ```bash
   cp .env.example .env
   # edit .env, set MEMORY_API_KEY
   export MEMORY_API_KEY=nams_xxxxxxxxxxxx
   ```

## Run

```bash
uv run python main.py
```

## Expected output

```
Connected to 'https://memory.neo4jlabs.com/v1'

Conversation has 3 messages
Created entity: Alice (PERSON)
Completed reasoning trace: Recommend a restaurant for Alice.
Cypher round-trip: [{'name': 'Alice'}]

Done. The same script body runs against bolt if you flip backend='bolt'.
```

## What's next?

* `docs/.../how-to/use-nams.adoc` — full config reference.
* `docs/.../how-to/migrate-to-nams.adoc` — porting existing bolt code.
* `docs/.../explanation/backends.adoc` — when to choose bolt vs NAMS.
