# PR: Microsoft Agent Framework Provider Update

## Summary

This PR updates the Microsoft Agent Framework provider to align with the latest
`agent-framework` interfaces and modernizes all Cypher queries to follow Neo4j
best practices. It also fixes several broken API calls in the retail assistant
example so the backend passes all smoke tests (9/9).

---

## 1. Callable FunctionTool Conversion

The framework's streaming model requires **callable** `FunctionTool` instances so
it can auto-invoke tools during `agent.run(stream=True)`. The previous JSON
schema dict approach forced manual argument accumulation and dispatch, which
broke on partial streaming chunks.

### Provider changes (`src/neo4j_agent_memory/integrations/microsoft_agent/`)

| File | Change |
|------|--------|
| `tools.py` | `create_memory_tools()` now returns `list[FunctionTool]` using `@tool`-decorated async closures. All 9 tools converted (search_memory, remember_preference, recall_preferences, search_knowledge, remember_fact, find_similar_tasks, find_connection_path, find_similar_items, find_important_entities). `execute_memory_tool()` retained with `DeprecationWarning`. |

### Example changes (`examples/microsoft_agent_retail_assistant/backend/`)

| File | Change |
|------|--------|
| `agent.py` | `get_product_tools()` converted to callable tools. `execute_product_tool()` removed. `run_agent_stream()` simplified to observe-only streaming (no manual tool execution). Fixed `Agent.stream()` → `agent.run(msg, stream=True)`. |
| `main.py` | Health check fixed to use `memory_client.is_connected`. Fixed `get_messages()` → `get_conversation()`. Fixed `get_preferences()` → `search_preferences()` / `get_preferences_by_category()`. Fixed `get_entities()` → `search_entities()`. Fixed `execute_query()` → `execute_read()` / `execute_write()`. Fixed `memory_client.embeddings` → `memory_client._embedder`. Fixed product/graph endpoints to project fields in Cypher instead of relying on Node object serialization. |
| `tools/recommendations.py` | Fixed `get_preferences()` → `search_preferences()` API call. |
| `requirements.txt` | Pinned `agent-framework>=1.0.0b260212`. |

### Backward compatibility

- `create_memory_tools()` return type changes from `list[dict]` to `list[FunctionTool]`. Both types are accepted by `Agent(tools=...)`.
- `execute_memory_tool()` is deprecated but still functional.

---

## 2. Core Library: `MemoryClient.graph` Property

Added a public `graph` property to `MemoryClient` in `src/neo4j_agent_memory/__init__.py`
that exposes the internal `Neo4jClient` for custom Cypher queries.

```python
@property
def graph(self) -> Neo4jClient:
    """Access the Neo4j client for custom Cypher queries."""
```

**Rationale:** `BaseMemory` already exposes `.client` publicly on every memory
store. `MemoryClient` itself kept `_client` private, forcing consumers to reach
through `memory_client.short_term.client` or access `_client` directly. The GDS
integration was already breaking encapsulation via `self._client._client.session()`.

---

## 3. Modern Cypher Best Practices

### 3a. Replaced `id()` with `elementId()`

The `id()` function is removed in Neo4j 5.x. All usages replaced with `elementId()`.

**`src/neo4j_agent_memory/graph/queries.py`** — Graph export queries:

| Query constant | Change |
|----------------|--------|
| `GET_GRAPH_SHORT_TERM` | `id(r)` → `elementId(r)` |
| `GET_GRAPH_LONG_TERM` | `id(r)` → `elementId(r)` |
| `GET_GRAPH_REASONING` | `id(r1)`, `id(r2)` → `elementId(r1)`, `elementId(r2)` |
| `GET_GRAPH_ALL` | `id(n)`, `id(r)`, `id(m)` → `elementId(n)`, `elementId(r)`, `elementId(m)`. Also removed `toString()` wrappers (elementId already returns a string). |

**`src/neo4j_agent_memory/integrations/microsoft_agent/gds.py`** — GDS queries:

| Method | Change |
|--------|--------|
| `_pagerank_gds` | `id(e)` → `elementId(e)` in node/relationship projections and node matching |
| `_communities_gds` | `id(e)` → `elementId(e)` in node/relationship projections and node matching |

### 3b. Added NULL filtering for sorted properties

Queries that ORDER BY a property now include `NULLS LAST` to prevent unexpected
sort behavior when properties are null.

**`src/neo4j_agent_memory/graph/queries.py`:**

| Query constant | Sort property |
|----------------|---------------|
| `GET_CONVERSATION_BY_SESSION` | `c.created_at` |
| `LIST_CONVERSATIONS` | `c.updated_at` |
| `SEARCH_ENTITIES_BY_TYPE` | `e.created_at` |
| `LIST_SESSIONS` | `created_at`, `updated_at`, `message_count` (all 6 CASE branches) |

**`examples/microsoft_agent_retail_assistant/backend/tools/product_search.py`:**

| Function | Sort property |
|----------|---------------|
| `search_products` (text fallback) | `p.popularity` |
| `get_products_by_category` | `p.popularity`, `p.price`, `p.created_at` (all 4 order clause mappings) |

**`examples/microsoft_agent_retail_assistant/backend/tools/recommendations.py`:**

| Function | Sort property |
|----------|---------------|
| `get_recommendations` (preference query) | `p.popularity` |
| `get_recommendations` (popularity fallback) | `p.popularity` |

### 3c. Replaced deprecated GDS API in recommendations example

**`examples/microsoft_agent_retail_assistant/backend/tools/recommendations.py`:**

The "fill remaining slots with popular items" query used deprecated GDS 1.x
anonymous graph syntax (`gds.pageRank.stream({nodeProjection: ...})`) and
`gds.util.asNode(nodeId)`. Replaced with a degree centrality approximation
using standard Cypher — the same pattern used in `gds.py`'s `_pagerank_fallback`.
This removes the hard GDS dependency from the example while preserving the
ranking behavior.

---

## Files Changed

### Core library

| File | Type |
|------|------|
| `src/neo4j_agent_memory/__init__.py` | Added `MemoryClient.graph` property |
| `src/neo4j_agent_memory/graph/queries.py` | `id()` → `elementId()`, added `NULLS LAST` |
| `src/neo4j_agent_memory/integrations/microsoft_agent/tools.py` | Callable `FunctionTool` conversion |
| `src/neo4j_agent_memory/integrations/microsoft_agent/gds.py` | `id()` → `elementId()` |

### Example: Retail assistant

| File | Type |
|------|------|
| `examples/microsoft_agent_retail_assistant/backend/agent.py` | Callable tools, streaming fix |
| `examples/microsoft_agent_retail_assistant/backend/main.py` | API fixes, health check, field projection |
| `examples/microsoft_agent_retail_assistant/backend/requirements.txt` | Dependency pin |
| `examples/microsoft_agent_retail_assistant/backend/tools/cart.py` | `execute_query` → `execute_read`/`execute_write` |
| `examples/microsoft_agent_retail_assistant/backend/tools/inventory.py` | `execute_query` → `execute_read` |
| `examples/microsoft_agent_retail_assistant/backend/tools/product_search.py` | `execute_query` → `execute_read`, `NULLS LAST` |
| `examples/microsoft_agent_retail_assistant/backend/tools/recommendations.py` | Deprecated GDS removal, `NULLS LAST`, API fix |

---

## Testing

```bash
# Unit tests (no Neo4j required)
uv run pytest tests/unit/integrations/test_microsoft_agent.py -v

# Integration tests (requires Neo4j or Docker for testcontainers)
uv run pytest tests/integration/test_microsoft_agent_integration.py -v -m integration

# Retail assistant smoke tests (requires running backend)
cd examples/microsoft_agent_retail_assistant/backend
python test_backend.py
```
