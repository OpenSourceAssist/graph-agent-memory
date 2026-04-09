# AWS Financial Services Advisor - Code Review

This document provides a comprehensive review of the AWS Financial Services Advisor example application, identifying strengths, bugs, missing components, and prioritized improvement suggestions.

**Review date**: 2026-04-08
**Compared against**: `neo4j-agent-memory` package at current HEAD and the Google Cloud Financial Advisor example

---

## 1. Architecture Strengths

The application demonstrates solid architectural decisions:

- **FastAPI lifespan management** (`backend/src/main.py`): Clean async startup/shutdown with graceful degradation when Neo4j is unavailable
- **Pydantic settings system** (`backend/src/config.py`): Well-organized per-concern BaseSettings subclasses (Neo4jSettings, BedrockSettings, AWSSettings, etc.) with `env_prefix` for each
- **Multi-agent delegation pattern** (`backend/src/agents/supervisor.py`): Strands `@tool` decorators cleanly expose delegation functions; supervisor orchestrates KYC, AML, Relationship, and Compliance agents
- **Risk service** (`backend/src/services/risk_service.py`): Real weighted scoring with FATF jurisdiction lists, industry risk categorization, and configurable component weights (geographic 25%, customer type 20%, transaction 30%, network 25%)
- **Frontend stack**: Proper Vite proxy config to backend, React Query for data fetching, Chakra UI v3 compound components, modular component structure
- **Memory service layering** (`backend/src/services/memory_service.py`): Good separation of long-term (entities), short-term (conversations), and reasoning (audit trails) with domain-specific wrapper methods
- **Comprehensive Pydantic models** across 5 model files with proper validation

---

## 2. Critical Bugs in `memory_service.py`

The memory service (`backend/src/services/memory_service.py`) has multiple API mismatches with the current `neo4j-agent-memory` package that will cause runtime errors.

### Bug 1: `add_entity()` returns tuple, code expects single Entity

**Location**: Lines 108-117, also lines 143-149, 169-179, 347-352, 399-411

`add_entity()` returns `tuple[Entity, DeduplicationResult]` but the code assigns to a single variable:

```python
# Current (broken)
entity = await self._client.long_term.add_entity(...)
return entity.id  # TypeError: tuple has no attribute 'id'

# Fix
entity, _dedup = await self._client.long_term.add_entity(...)
return entity.id
```

This affects `add_customer()`, `add_organization()`, `add_account()`, `add_transaction()`, and `add_alert()` -- essentially every entity creation method.

### Bug 2: `get_entity_graph()` does not exist on LongTermMemory

**Location**: Lines 242-245

```python
graph = await self._client.long_term.get_entity_graph(
    entity_id=customer_entity.id,
    max_depth=depth,
)
```

`LongTermMemory` has no `get_entity_graph()` method. This method only exists on the Strands integration tools. To get entity relationships, use `search_entities()` combined with graph queries, or use the `MemoryClient.graph` property for direct Cypher queries.

### Bug 3: `get_conversation()` returns `Conversation` object, not a list

**Location**: Lines 463-475

```python
# Current (broken) - iterates over Conversation object directly
messages = await self._client.short_term.get_conversation(
    session_id=session_id, limit=limit,
)
return [{"role": m.role, ...} for m in messages]  # Can't iterate Conversation

# Fix - access .messages attribute
conversation = await self._client.short_term.get_conversation(
    session_id=session_id, limit=limit,
)
return [{"role": m.role.value, ...} for m in conversation.messages]
```

Also: `m.role` is a `MessageRole` enum (needs `.value`), and `m.timestamp` doesn't exist -- the field is `m.created_at` (inherited from `MemoryEntry`).

### Bug 4: `search()` return type -- `Message` has no `session_id` or `score`

**Location**: Lines 493-506

`self._client.short_term.search()` returns `list[Message]`. The code accesses `r.session_id` and `r.score` which don't exist on `Message`. `Message` has: `role`, `content`, `conversation_id`, `tool_calls`, plus inherited `id`, `created_at`, `metadata`.

### Bug 5: `start_trace()` -- wrong parameter names

**Location**: Lines 530-540

```python
# Current (broken)
await self._client.reasoning.start_trace(
    session_id=session_id,
    trace_id=trace_id,  # NOT a parameter -- trace ID is auto-generated
    task=task,
    metadata={...},
)

# Fix
trace = await self._client.reasoning.start_trace(
    session_id=session_id,
    task=task,
    metadata={...},
)
return str(trace.id)  # Use the auto-generated trace ID
```

`start_trace()` does NOT accept a `trace_id` parameter -- it generates its own UUID internally and returns a `ReasoningTrace`.

### Bug 6: `add_step()` -- wrong parameter names

**Location**: Lines 561-572

```python
# Current (broken)
await self._client.reasoning.add_step(
    session_id=session_id,  # NOT a parameter
    trace_id=trace_id,      # Should be UUID, not str
    action=action,
    reasoning=reasoning,    # NOT a parameter -- use 'thought'
    result=result,          # NOT a parameter -- use 'observation'
    metadata={...},
)

# Fix
from uuid import UUID
await self._client.reasoning.add_step(
    UUID(trace_id),  # positional, must be UUID
    thought=reasoning,
    action=action,
    observation=str(result) if result else None,
    metadata={...},
)
```

`add_step()` signature: `(self, trace_id: UUID, *, thought=None, action=None, observation=None, metadata=None)`

### Bug 7: `complete_trace()` -- wrong parameter names

**Location**: Lines 588-593

```python
# Current (broken)
await self._client.reasoning.complete_trace(
    session_id=session_id,     # NOT a parameter
    trace_id=trace_id,         # Should be UUID
    conclusion=conclusion,     # NOT a parameter -- use 'outcome'
    success=success,
)

# Fix
await self._client.reasoning.complete_trace(
    UUID(trace_id),
    outcome=conclusion,
    success=success,
)
```

### Bug 8: `get_trace()` -- wrong parameters and return structure

**Location**: Lines 609-628

```python
# Current (broken)
trace = await self._client.reasoning.get_trace(
    session_id=session_id,  # NOT a parameter
    trace_id=trace_id,
)
# Accesses trace.status, trace.conclusion, s.reasoning, s.result

# Fix
trace = await self._client.reasoning.get_trace(trace_id)
# ReasoningTrace has: .task, .outcome, .success, .started_at, .completed_at
# ReasoningStep has: .thought, .action, .observation (not .reasoning, .result)
```

### Bug 9: `add_relationship()` may use wrong parameter names

**Location**: Lines 182-186, 206-211, 355-369, 414-419

The code calls `add_relationship()` with `source_entity_id`, `target_entity_id`, `relationship_type`, and `attributes`. Verify these parameter names match the current API -- the `LongTermMemory` relationship API may expect different parameter names.

---

## 3. Simulated Data Problem

All four specialist agents return randomly generated data instead of querying Neo4j. This is the single largest gap in the application.

### KYC Agent (`backend/src/agents/kyc_agent.py`)

| Tool | Implementation | Issue |
|------|---------------|-------|
| `verify_identity()` | `random.choice()` for verification checks | No actual document verification |
| `check_documents()` | `random.choice()` for doc validity | No document storage integration |
| `assess_customer_risk()` | Calls `RiskService` but with random transaction/network data | Transaction and network inputs are fabricated |
| `check_adverse_media()` | 5% random chance of hits | No media API integration |

### AML Agent (`backend/src/agents/aml_agent.py`)

| Tool | Implementation | Issue |
|------|---------------|-------|
| `scan_transactions()` | `random.randint()` for transaction counts/amounts | No Neo4j transaction queries |
| `detect_patterns()` | Random pattern selection from hardcoded list | No evidence-based detection |
| `flag_suspicious()` | Random alert generation | No persistence to graph |
| `analyze_velocity()` | Random velocity metrics | No historical baseline |

### Relationship Agent (`backend/src/agents/relationship_agent.py`)

| Tool | Implementation | Issue |
|------|---------------|-------|
| `find_connections()` | Random entity/relationship generation | Does NOT use `context_graph_tools` despite loading them |
| `analyze_network_risk()` | Random risk scores | No actual graph traversal |
| `detect_shell_companies()` | Random indicator selection | No corporate structure analysis |
| `map_beneficial_ownership()` | Random ownership layers | No ownership chain tracing |

### Compliance Agent (`backend/src/agents/compliance_agent.py`)

| Tool | Implementation | Issue |
|------|---------------|-------|
| `check_sanctions()` | 5% random match against sample entries | No real sanctions database |
| `verify_pep()` | 10% random PEP match | No real PEP database |
| `generate_report()` | Random section counts, no content | No actual report generation |
| `assess_regulatory_requirements()` | Real logic based on jurisdiction | Only tool with real implementation |

### Recommended Fix

Follow the Google Cloud Financial Advisor pattern:

1. Create a `Neo4jDomainService` class that queries real domain data from Neo4j via `MemoryClient.graph`
2. Store domain data (customers, transactions, sanctions lists) in Neo4j via `load_sample_data.py`
3. Pass `neo4j_service` to tool functions using the `_bind_tool()` pattern (see `google-cloud-financial-advisor/backend/src/tools/`)
4. Replace `random.choice()` calls with actual Cypher queries

---

## 4. Missing Components

### Sample Data & Loading Script

- **`scripts/load_sample_data.py`**: Referenced by `Makefile` line 65 (`make load-data`) but does not exist. The `scripts/` directory is empty.
- **`data/` directory**: Does not exist. Should contain JSON files for: customers, organizations, transactions, sanctions entries, PEP entries, and pre-built alerts.
- **Template available**: The Google Cloud example at `examples/google-cloud-financial-advisor/data/` has a complete implementation with 7 JSON data files and a loader script.

### SSE Streaming

The Google Cloud example has a `POST /api/chat/stream` endpoint that emits real-time SSE events (`agent_start`, `tool_call`, `tool_result`, `thinking`, `response`, `done`). This app only has synchronous `POST /api/chat` which blocks until the supervisor completes all agent delegations.

### Reasoning Trace Persistence in Chat

The `chat.py` endpoint stores messages in short-term memory but does NOT create reasoning traces. The investigation flow (`investigations.py`) has trace creation but uses wrong API parameters (see Bug 5-8). The supervisor agent should persist its delegation decisions and agent findings as reasoning traces.

### Agent Activity Visualization

The Google Cloud frontend has `AgentOrchestrationView` (real-time animated multi-agent visualization) and `AgentActivityTimeline` (post-completion reasoning trace). This app's frontend has no agent activity feedback beyond a loading spinner.

### Graph Routes are Stubs

`backend/src/api/routes/graph.py`:
- `get_entity_graph()` returns mock `GraphNode`/`GraphEdge` structures -- no real graph traversal
- `search_entities()` returns hardcoded relevance score of 0.9
- `find_connections()` returns empty paths with comment "Would be populated by real query"
- `get_graph_statistics()` returns all zeros

---

## 5. README Inaccuracies

| Line | Issue | Fix |
|------|-------|-----|
| 63 | `cd examples/financial-services-advisor` | `cd examples/aws-financial-services-advisor` |
| 77 | `pip install -r requirements.txt` | `cd backend && uv sync` |
| 82 | `cd ../frontend` (from `backend`) | `cd frontend` (or `cd ../frontend` if from backend) |
| 89-90 | `cd ../data` then `python load_sample_data.py` | `data/` directory and script don't exist |
| 98 | `uvicorn src.main:app --reload` | `uv run uvicorn src.main:app --reload` |
| 134 | Lists `requirements.txt` in project structure | Should be `pyproject.toml` |
| 143 | Lists `data/` directory | Does not exist |

### `.env` Location Issue

`.env.example` is at the project root but `pydantic_settings` in `config.py` reads `.env` from the CWD. Since the Makefile runs `cd backend && uv run uvicorn...`, the `.env` file must be at `backend/.env`, not the project root. Users following the README's `cp .env.example .env` will put it in the wrong place.

---

## 6. Frontend/Backend API Mismatches

| Frontend Expects | Backend Provides | Issue |
|-----------------|-----------------|-------|
| `GET /customers/{id}/network` returns `{nodes, edges}` | `get_customer_network()` calls non-existent `get_entity_graph()` | Will crash (Bug 2) |
| `GET /graph/entity/{name}` returns `{nodes, edges}` | Returns mock data with `GraphData` wrapper | Works but data is fake |
| `POST /graph/search` returns `unknown[]` | Returns `SearchResult[]` with hardcoded score=0.9 | Works but scores meaningless |
| `GET /alerts/summary` returns `{total_count, by_status, by_severity}` | Returns same plus extra fields | Compatible |
| `POST /investigations/{id}/start` returns `{status, preliminary_response}` | `preliminary_response` is `str(result)[:1000]` | Truncated, may lose info |

---

## 7. Comparison with Google Cloud Financial Advisor Example

| Aspect | Google Cloud Example | AWS Example |
|--------|---------------------|-------------|
| **Domain data** | Real Neo4j queries via `Neo4jDomainService` | In-memory dicts + `random.choice()` |
| **Agent tools** | Query Neo4j via `_bind_tool()` pattern | All simulated/random |
| **Sample data** | Complete: 7 JSON files + loader script | Missing entirely |
| **SSE streaming** | `POST /api/chat/stream` with 10+ event types | Synchronous only |
| **Reasoning traces** | Full persistence in chat flow | Wrong API parameters; only in investigations |
| **Agent visualization** | Animated `AgentOrchestrationView` + `AgentActivityTimeline` | Loading spinner only |
| **Frontend sophistication** | Framer Motion animations, Timeline, Collapsible | Basic panels and cards |
| **Memory service** | Uses `connect()` correctly, proper API calls | ~9 API mismatches |
| **Graph routes** | Real data from Neo4j | All stubs returning mock data |

---

## 8. Prioritized Improvements

### Priority 1 -- Blocking (app cannot demonstrate value without these)

1. **Fix all `memory_service.py` API mismatches** (Bugs 1-9)
   - Unpack `add_entity()` tuple returns
   - Fix `get_conversation()` to use `.messages`
   - Fix all reasoning memory method signatures
   - Remove call to non-existent `get_entity_graph()`

2. **Create sample data files and `load_sample_data.py`**
   - Create `data/` directory with JSON files (customers, orgs, transactions, sanctions, PEPs, alerts)
   - Create `scripts/load_sample_data.py` to load into Neo4j
   - Use the Google Cloud example's loader as a template

3. **Create `Neo4jDomainService`** for real domain queries
   - Use `MemoryClient.graph` for direct Cypher queries
   - Implement customer, transaction, and network query methods

4. **Replace simulated tool data with Neo4j queries**
   - KYC tools: query customer documents and verification status
   - AML tools: query transaction history and patterns
   - Relationship tools: use graph traversal for network analysis
   - Compliance tools: query sanctions/PEP lists from graph

### Priority 2 -- High Impact (feature parity with Google Cloud example)

5. **Add SSE streaming endpoint** (`POST /api/chat/stream`)
   - Emit agent lifecycle events (`agent_start`, `agent_complete`, `tool_call`, etc.)
   - Frontend `useAgentStream` hook for real-time updates

6. **Add reasoning trace persistence in chat flow**
   - Create traces in `chat.py` endpoint
   - Record agent delegations as reasoning steps
   - Store tool call results

7. **Fix README.md** with correct setup instructions

8. **Fix `.env` handling** -- either:
   - Move `.env.example` to `backend/.env.example` and update instructions, or
   - Add `env_file` path in `config.py` Settings to check both locations

### Priority 3 -- Polish

9. **Agent activity visualization** in frontend
   - Add `AgentOrchestrationView` component
   - Show which agents are active during investigation

10. **Graph routes with real data**
    - Implement `get_entity_graph()` using Cypher path queries
    - Real search scoring based on embedding similarity
    - Connection finding with variable-length path patterns

11. **Graph statistics endpoint** with real counts from Neo4j

12. **Infrastructure CDK verification** -- install deps and validate deployability

---

## Appendix: File Reference

| File | Status | Primary Issues |
|------|--------|---------------|
| `backend/src/services/memory_service.py` | Broken | 9 API mismatches |
| `backend/src/agents/kyc_agent.py` | Simulated | All tools use random.choice() |
| `backend/src/agents/aml_agent.py` | Simulated | All tools use random.randint() |
| `backend/src/agents/relationship_agent.py` | Simulated | Has context_graph_tools but doesn't use them |
| `backend/src/agents/compliance_agent.py` | Simulated | Sanctions/PEP checks are random |
| `backend/src/api/routes/graph.py` | Stub | All endpoints return mock data |
| `backend/src/api/routes/investigations.py` | Mixed | Some endpoints stub, audit trail placeholder |
| `backend/src/services/risk_service.py` | Working | Real scoring logic |
| `backend/src/api/routes/chat.py` | Working | Synchronous only, no trace recording |
| `backend/src/api/routes/customers.py` | Working | Real CRUD with Neo4j integration |
| `backend/src/api/routes/alerts.py` | Working | Real CRUD, in-memory storage |
| `backend/src/config.py` | Working | .env location issue |
| `frontend/src/lib/api.ts` | Working | Some type mismatches with backend |
| `README.md` | Outdated | Wrong paths, wrong install commands |
