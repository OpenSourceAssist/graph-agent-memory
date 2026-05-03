# existing-graph

End-to-end example showing how to layer `neo4j-agent-memory` on top of an
existing domain graph using `client.schema.adopt_existing_graph(...)` and
`SchemaModel.CUSTOM`.

This is the first runnable example in the repo that uses
`SchemaModel.CUSTOM` with a domain other than POLE+O.

## What this demonstrates

- Adopting nodes from an existing graph as long-term memory entities,
  attaching the `:Entity` super-label, `id`, `type`, and `name` properties.
- Configuring `SchemaModel.CUSTOM` so library writes (entity extraction,
  MERGE-on-mention) target the same domain types as the seed graph.
- Idempotent re-runs: the helper can be called repeatedly.

## What it doesn't

- An LLM. The example runs with `llm=None` and a local
  sentence-transformers embedder so it works without API keys.

## Files

| File | Purpose |
|---|---|
| `seed_domain_graph.cypher` | Loads three `:Person`, three `:Movie`, two `:Genre` nodes with relationships. Pre-library style — no `:Entity` labels. |
| `memory_settings.py` | `build_settings()` — `SchemaModel.CUSTOM`, custom entity types, no LLM. |
| `adopt.py` | Calls `client.schema.adopt_existing_graph(...)` to attach `:Entity` to the seed nodes. |
| `memory_io.py` | Writes a couple of messages and verifies MENTIONS edges link to the existing domain nodes (no duplicates). |
| `run.sh` | Loads → adopts → writes → verifies. |

## Running

You'll need a running Neo4j 5.x at `bolt://localhost:7687`. Either:

- Start the test container: `make neo4j-start` from the repo root, or
- Point `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` at your own instance.

Then from the repo root:

```bash
bash examples/existing-graph/run.sh
```

You should see:

```
Adopted 8 nodes (0 already adopted, 0 skipped).
  Person → PERSON: +3 new, =0 already, ~0 skipped
  Movie → MOVIE: +3 new, =0 already, ~0 skipped
  Genre → GENRE: +2 new, =0 already, ~0 skipped
…
Per-name node count after writes (1 means adoption worked):
  Bob Singh      -> 1
  Carol Reyes    -> 1
  Inception      -> 1
  Arrival        -> 1
```

## How it works

`adopt_existing_graph(label_to_type, name_property_per_label=...)`:

1. For each input label, attaches the `:Entity` super-label.
2. Sets `type` from the mapping, `name` from the configured property
   (defaulting to the existing `name`), and `id` from any existing `id`
   property — falling back to a deterministic `label:name` hash.
3. Skips nodes that lack the configured name property.
4. Reports per-label counts.

After this runs, library APIs that MERGE on `(:Entity {name, type})`
(message-mention extraction, relation writes, preference targeting) link
to the existing domain nodes instead of creating duplicates.
