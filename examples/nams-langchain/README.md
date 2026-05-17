# NAMS + LangChain

Demonstrates that the existing **LangChain memory adapter** works
unchanged against NAMS — the integration is fully backend-agnostic.

The same `Neo4jAgentMemory(memory_client=client, session_id=...)`
construction call you use today on bolt works against NAMS when the
underlying `MemoryClient` is configured with `backend="nams"`.

## Setup

```bash
uv pip install -r requirements.txt
cp .env.example .env
# edit .env, set MEMORY_API_KEY (and OPENAI_API_KEY if you wire up a chat model)
export MEMORY_API_KEY=nams_xxxxxxxxxxxx
```

## Run

```bash
uv run python main.py
```

## Switching to bolt

The whole point: you don't need a NAMS-specific LangChain integration.
Drop in a bolt `MemorySettings`:

```python
from neo4j_agent_memory.config.settings import Neo4jConfig
from pydantic import SecretStr

settings = MemorySettings(
    neo4j=Neo4jConfig(password=SecretStr("your-password")),
)
```

The rest of the script stays the same.

## What about the agent/chat-model wiring?

This script focuses on the memory adapter. For a full agent example
(adapter + chat model + tools + retriever), see the LangChain
integration how-to in the docs. Every part of that example works on
NAMS by changing only the `MemorySettings`.
