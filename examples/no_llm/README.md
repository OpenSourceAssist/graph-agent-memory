# Run Without an LLM

![Neo4j Labs](https://img.shields.io/badge/Neo4j-Labs-6366F1?logo=neo4j)
![Status: Beta](https://img.shields.io/badge/Status-Beta-6366F1)
![Community Supported](https://img.shields.io/badge/Support-Community-6B7280)

> Air-gapped or budget-conscious? Use `neo4j-agent-memory` with no LLM provider — local embeddings, local NER, no API keys.

This example shows how to wire `MemorySettings` for environments where you can't (or don't want to) call an LLM. The key is `llm=None` plus a non-LLM extractor and a local embedder.

> ⚠️ **Neo4j Labs Project**
>
> This example is part of [`neo4j-agent-memory`](https://github.com/neo4j-labs/agent-memory), a Neo4j Labs project. It is actively maintained but not officially supported. APIs may change. Community support is available via the [Neo4j Community Forum](https://community.neo4j.com).

## When to use this

- Air-gapped or offline deployments where outbound API calls aren't allowed.
- Cost-sensitive workloads where every LLM call counts.
- Deterministic test environments where you want zero variability from a remote model.
- Bootstrapping a new project before you've decided on an LLM vendor.

## What this demonstrates

- **`llm=None`** — explicit opt-out. Validated at construction time.
- **Provider-string shorthand for local embeddings** — `"sentence-transformers/all-MiniLM-L6-v2"` resolves to `SentenceTransformersProvider` via `from_provider`. No external API calls.
- **`ExtractorType.PIPELINE` with `enable_llm_fallback=False`** — multi-stage spaCy + GLiNER pipeline, no LLM rescue.
- **Configuration-time validation** — if you pair `llm=None` with an extractor that requires an LLM, `MemorySettings` raises a `ValidationError` naming both fields rather than failing later at runtime.

```python
settings = MemorySettings(
    neo4j=Neo4jConfig(...),
    llm=None,                                          # explicit opt-out
    embedding="sentence-transformers/all-MiniLM-L6-v2",# local embeddings
    extraction=ExtractionConfig(
        extractor_type=ExtractorType.PIPELINE,
        enable_spacy=True,
        enable_gliner=True,
        enable_llm_fallback=False,            # required when llm=None
    ),
)
```

## Prerequisites

```bash
pip install "neo4j-agent-memory[extraction,sentence-transformers]"
python -m spacy download en_core_web_sm
```

A running Neo4j 5.x. Set `NEO4J_URI` / `NEO4J_PASSWORD` if you're not using `bolt://localhost:7687` with the default `password`.

## Run

```bash
python main.py
```

You'll see a printed memory context built without a single call to OpenAI, no API key required.

## Going further

- **How-to guide:** [`docs/modules/ROOT/pages/how-to/running-without-an-llm.adoc`](../../docs/modules/ROOT/pages/how-to/running-without-an-llm.adoc).
- **Reference:** [`docs/modules/ROOT/pages/reference/extractors.adoc`](../../docs/modules/ROOT/pages/reference/extractors.adoc) — extractor menu, when to add LLM rescue, GLiNER schema choices.

## Support

- 💬 [Neo4j Community Forum](https://community.neo4j.com)
- 🐛 [GitHub Issues](https://github.com/neo4j-labs/agent-memory/issues)
- 📖 [`neo4j-agent-memory` documentation](https://github.com/neo4j-labs/agent-memory#readme)

---

_Verified against `neo4j-agent-memory` v0.1.2 / v0.2-dev on 2026-05-03._
