# Running without an LLM

This example shows how to use `neo4j-agent-memory` with no LLM provider — useful for:

- Air-gapped or offline environments
- Deployments without an `OPENAI_API_KEY`
- Deterministic, free, fully-local extraction

The key configuration is:

```python
settings = MemorySettings(
    neo4j=Neo4jConfig(...),
    llm=None,                                # explicit opt-out
    embedding=EmbeddingConfig(
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        model="all-MiniLM-L6-v2",
        dimensions=384,
    ),
    extraction=ExtractionConfig(
        extractor_type=ExtractorType.PIPELINE,
        enable_spacy=True,
        enable_gliner=True,
        enable_llm_fallback=False,           # required when llm=None
    ),
)
```

If you set `llm=None` together with an LLM-dependent extractor (`extractor_type=LLM` or `enable_llm_fallback=True`), `MemorySettings` raises a `ValidationError` at construction time naming both fields.

## Setup

```bash
pip install "neo4j-agent-memory[extraction,sentence-transformers]"
python -m spacy download en_core_web_sm
```

Start Neo4j however you like (Docker, Aura, local). Set `NEO4J_URI` / `NEO4J_PASSWORD` if not using `bolt://localhost:7687` with the default `password`.

## Run

```bash
python main.py
```

You should see a printed memory context with no calls to OpenAI and no need for any API key.
