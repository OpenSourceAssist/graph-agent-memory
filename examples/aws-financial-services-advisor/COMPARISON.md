# AWS vs Google Cloud Financial Advisor - Detailed Comparison

Side-by-side comparison of the two financial compliance example applications in the `neo4j-agent-memory` repository.

| | [AWS Financial Services Advisor](.) | [Google Cloud Financial Advisor](../google-cloud-financial-advisor/) |
|-|-------------------------------------|---------------------------------------------------------------------|
| **Directory** | `examples/aws-financial-services-advisor/` | `examples/google-cloud-financial-advisor/` |
| **Status** | Alpha/Demo -- simulated tool data, API bugs | Functional -- real Neo4j queries, SSE streaming |

---

## 1. Tech Stack

| Component | AWS Example | Google Cloud Example |
|-----------|-------------|---------------------|
| **Agent Framework** | AWS Strands Agents (`strands-agents`) | Google ADK (`google-adk`) |
| **LLM** | Amazon Bedrock (Claude Sonnet 4) | Google Gemini 2.5 Flash (via AI Studio) |
| **Embeddings** | Amazon Titan Embed V2 | Vertex AI `text-embedding-004` |
| **Backend** | FastAPI + Uvicorn | FastAPI + Uvicorn |
| **Frontend** | React 18 + Vite + Chakra UI v3 | React 18 + Vite + Chakra UI v3 |
| **Database** | Neo4j (via neo4j-agent-memory) | Neo4j (via neo4j-agent-memory) |
| **Package Manager** | uv (Python), npm (Node) | uv (Python), npm (Node) |
| **Deployment** | AWS Lambda + CDK (planned) | Google Cloud Run (scripted) |
| **Auth** | Amazon Cognito (configured, not wired) | Not implemented |

---

## 2. Agent Architecture

### Agent Creation

**AWS Strands**:
```python
from strands import Agent, tool
from strands.models import BedrockModel

@tool
def delegate_to_kyc_agent(customer_id: str, task: str) -> dict:
    kyc_agent = get_kyc_agent()
    result = kyc_agent(prompt)
    return {"agent": "kyc", "findings": str(result)}

supervisor = Agent(
    model=BedrockModel(model_id="anthropic.claude-sonnet-4-20250514-v1:0"),
    tools=[delegate_to_kyc_agent, ...] + memory_tools,
    system_prompt=SUPERVISOR_SYSTEM_PROMPT,
)
```
- Delegation is explicit: supervisor has `@tool` functions that call sub-agents
- Sub-agents are invoked directly with `agent(prompt)` -- synchronous call
- No native sub-agent concept; orchestration is manual via tool returns

**Google ADK**:
```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

kyc_agent = LlmAgent(
    name="kyc_agent",
    model="gemini-2.5-flash",
    instruction=KYC_INSTRUCTION,
    tools=[FunctionTool(bind_tool(verify_identity, neo4j_service))],
)

supervisor = LlmAgent(
    name="supervisor",
    model="gemini-2.5-flash",
    instruction=SUPERVISOR_INSTRUCTION,
    sub_agents=[kyc_agent, aml_agent, relationship_agent, compliance_agent],
)
```
- Native `sub_agents` parameter; ADK handles delegation via `transfer_to_agent`
- Runner yields events as agents execute -- enables SSE streaming
- Agent transitions tracked via `event.author` field

### Tool Binding

**AWS**: Tools are top-level `@tool` functions that import and call sub-agents. No dependency injection for Neo4j service. Tools return simulated data via `random.choice()`.

**Google Cloud**: Uses `_bind_tool()` pattern to inject `neo4j_service` while hiding it from the LLM's function signature:
```python
def bind_tool(func, neo4j_service):
    sig = inspect.signature(func)
    new_params = [p for name, p in sig.parameters.items() if name != "neo4j_service"]
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        kwargs["neo4j_service"] = neo4j_service
        return await func(*args, **kwargs)
    
    wrapper.__signature__ = sig.replace(parameters=new_params)
    return wrapper
```

---

## 3. Data Layer

### Domain Data

**AWS**: No sample data. No `data/` directory. No `load_sample_data.py`. Agent tools generate random data at runtime:
```python
# From kyc_agent.py
verification_checks = {
    "document_authenticity": random.choice(["passed", "passed", "passed", "flagged"]),
    "photo_match": random.choice(["confirmed", "confirmed", "inconclusive"]),
    ...
}
```

**Google Cloud**: Complete sample data in `data/` with 7 JSON files:

| File | Contents |
|------|----------|
| `customers.json` | 3 customers (low/medium/high risk) with KYC docs, risk factors |
| `organizations.json` | Shell companies in Cayman, Seychelles, BVI |
| `transactions.json` | 16 transactions including structuring ($9,500 x4), rapid movement, layering |
| `sanctions.json` | Sanctioned entities with aliases |
| `pep.json` | Politically Exposed Persons with relatives |
| `alerts.json` | Pre-built compliance alerts |

The loader (`load_sample_data.py`) creates Neo4j constraints, nodes (`:Customer`, `:Organization`, `:Transaction`, `:SanctionedEntity`, `:PEP`, `:Alert`, `:Document`), and relationships (`:HAS_TRANSACTION`, `:HAS_ALERT`, `:HAS_DOCUMENT`, `:CONNECTED_TO`, `:IS_RELATIVE_OF`).

### Neo4j Domain Service

**AWS**: Does not exist. Routes either use in-memory Python dicts or return stubs.

**Google Cloud**: `Neo4jDomainService` class (~30 methods) queries all domain data via Cypher:

| Category | Methods |
|----------|---------|
| **Customers** | `list_customers()`, `get_customer()`, `get_customer_documents()` |
| **Transactions** | `get_transactions()`, `detect_structuring()`, `detect_rapid_movement()`, `detect_layering()`, `get_velocity_metrics()` |
| **Network** | `find_connections()`, `detect_shell_companies()`, `trace_ownership()`, `get_network_risk()` |
| **Alerts** | `list_alerts()`, `get_alert()`, `create_alert()`, `update_alert()` |
| **Compliance** | `check_sanctions()`, `check_pep()`, `get_pep_relatives()` |

Initialized in FastAPI lifespan sharing the same Neo4j connection:
```python
neo4j_service = Neo4jDomainService(memory_service.client.graph)
app.state.neo4j_service = neo4j_service
```

---

## 4. Tool Implementations

### KYC Tools

| Tool | AWS | Google Cloud |
|------|-----|-------------|
| `verify_identity` | `random.choice()` for all checks | Queries `neo4j_service.get_customer()`, checks actual documents |
| `check_documents` | `random.choice()` for doc validity | Queries `neo4j_service.get_customer_documents()` |
| `assess_customer_risk` | Calls RiskService but with random inputs | Queries real transaction/network data for risk scoring |
| `check_adverse_media` | 5% random hit chance | Queries news/media data from graph |

### AML Tools

| Tool | AWS | Google Cloud |
|------|-----|-------------|
| `scan_transactions` | `random.randint()` for counts/amounts | `neo4j_service.get_transactions()` with date filtering |
| `detect_patterns` | Random pattern from hardcoded list | `detect_structuring()`, `detect_rapid_movement()`, `detect_layering()` |
| `analyze_velocity` | Random velocity metrics | `get_velocity_metrics()` with historical baseline |
| `flag_suspicious` | Random alert with `randint` ID | `create_alert()` with MERGE to avoid duplicates |

### Relationship Tools

| Tool | AWS | Google Cloud |
|------|-----|-------------|
| `find_connections` | Random entities/relationships | `find_connections()` with variable-length Cypher paths |
| `detect_shell_companies` | Random indicators from fixed list | `detect_shell_companies()` checking actual corporate structure |
| `trace_ownership` | Random ownership layers | `trace_ownership()` following relationship chains |
| `network_risk` | Random risk scores | `get_network_risk()` aggregating actual connection risk |

### Compliance Tools

| Tool | AWS | Google Cloud |
|------|-----|-------------|
| `check_sanctions` | 5% random match against 3 sample entries | `check_sanctions()` Cypher query with fuzzy name matching |
| `check_pep` | 10% random match | `check_pep()` + `get_pep_relatives()` from graph |
| `generate_report` | Random section counts, no content | Actual SAR generation from investigation findings |

---

## 5. Chat & Streaming

### AWS Example

- **Endpoint**: `POST /api/chat` (synchronous only)
- **Flow**: Request → store message → call `supervisor(prompt)` → `str(result)` → store response → return JSON
- **Response time**: Blocks 15-30s while all sub-agents complete
- **Frontend feedback**: Loading spinner only

### Google Cloud Example

- **Endpoints**: `POST /api/chat` (sync) + `POST /api/chat/stream` (SSE)
- **SSE Event Types** (11 distinct types):

| Event | Data | Purpose |
|-------|------|---------|
| `agent_start` | `{agent, timestamp}` | Agent begins processing |
| `agent_delegate` | `{from, to, timestamp}` | Supervisor delegates to sub-agent |
| `agent_complete` | `{agent, timestamp}` | Agent finishes |
| `thinking` | `{agent, thought, timestamp}` | Intermediate reasoning |
| `tool_call` | `{agent, tool, args, timestamp}` | Tool invocation |
| `tool_result` | `{agent, tool, result, timestamp}` | Tool response (truncated to 500 chars) |
| `memory_access` | `{agent, operation, tool, timestamp}` | Neo4j memory read/write |
| `response` | `{content, session_id}` | Final text response |
| `trace_saved` | `{trace_id, step_count, tool_call_count}` | Trace persisted to Neo4j |
| `done` | `{session_id, agents_consulted, total_duration_ms}` | Stream complete |
| `error` | `{message}` | Error during processing |

- **Frontend**: Real-time animated visualization showing which agents are active, which tools are being called, and memory operations as they happen

---

## 6. Reasoning Trace Persistence

### AWS Example

- **Memory service has trace methods** but they all have wrong API parameter names (see REVIEW.md Bugs 5-8)
- `start_trace()` passes non-existent `trace_id` parameter
- `add_step()` passes `reasoning` and `result` instead of `thought` and `observation`
- `complete_trace()` passes `conclusion` instead of `outcome`
- **Chat endpoint does NOT record traces** -- only investigation endpoints attempt it (and fail due to API bugs)

### Google Cloud Example

- **Traces recorded after every chat stream completes**:
```python
trace = await reasoning.start_trace(session_id, task=user_message)
for event in trace_events:
    step = await reasoning.add_step(trace.id, thought=agent_name, action=tool_name)
    await reasoning.record_tool_call(step.id, tool_name, arguments, result, status)
await reasoning.complete_trace(trace.id, outcome=response_text, success=True)
```
- **Dedicated trace retrieval API**:
  - `GET /api/traces/{session_id}` -- all traces for a session
  - `GET /api/traces/detail/{trace_id}` -- single trace with steps and tool calls
- **Frontend timeline** (`AgentActivityTimeline`) renders the trace after each response

---

## 7. Frontend Comparison

### Layout & Navigation

Both use: React Router + Sidebar + Chakra UI v3

| Route | AWS | Google Cloud |
|-------|-----|-------------|
| `/` | CustomerDashboard | CustomerDashboard |
| `/chat` | ChatInterface | ChatInterface |
| `/customers` | CustomerDashboard | CustomerDashboard |
| `/investigations` | InvestigationPanel | InvestigationPanel |
| `/alerts` | AlertsPanel | AlertsPanel |

### Chat Interface

**AWS**:
- Text input → POST → loading spinner → response text
- No agent activity feedback
- Simple message bubbles (user=teal, assistant=gray)

**Google Cloud**:
- Text input → SSE stream → real-time agent cards → response text + trace timeline
- `AgentOrchestrationView`: Framer Motion animated cards showing live agent activity
  - Color-coded by agent (supervisor=blue, KYC=teal, AML=orange, relationship=purple, compliance=red)
  - Pulsing active dots, staggered tool call animations
  - Memory access indicators with Neo4j database icon
- `AgentActivityTimeline`: Post-completion Chakra UI `Timeline` showing reasoning trace
  - Expandable/collapsible sections per agent
  - Tool call details, memory operations
  - Summary: agent count, tool count, total duration
- `ToolCallCard`: Animated tool display with spinning loader → checkmark transition
- `MemoryAccessIndicator`: Flash animation for Neo4j read/write operations

### Data Fetching

Both use: React Query (`@tanstack/react-query`) + Axios

**AWS**: All queries are standard request/response.

**Google Cloud**: Standard queries + `streamChatMessage()` using `fetch()` with `ReadableStream` for SSE parsing.

---

## 8. Memory Service Integration

### AWS Example (`backend/src/services/memory_service.py`)

```python
class FinancialMemoryService:
    def __init__(self):
        settings = get_settings()
        self._client = MemoryClient(MemorySettings(
            neo4j=Neo4jConfig(...),
            embedding=EmbeddingConfig(provider=EmbeddingProvider.BEDROCK, ...),
        ))
    
    async def initialize(self):
        await self._client.connect()
    
    # ~15 wrapper methods for long_term, short_term, reasoning
    # ALL reasoning methods have wrong parameter names (see REVIEW.md)
```

**Issues**:
- `add_entity()` doesn't unpack `(Entity, DeduplicationResult)` tuple
- `get_conversation()` iterates `Conversation` instead of `.messages`
- All reasoning methods pass wrong parameter names
- `get_entity_graph()` calls non-existent method
- No `Neo4jDomainService` -- domain queries don't exist

### Google Cloud Example (`backend/src/services/memory_service.py`)

```python
class FinancialMemoryService:
    def __init__(self):
        settings = get_settings()
        self._client = MemoryClient(MemorySettings(
            neo4j=Neo4jConfig(...),
            embedding=EmbeddingConfig(provider=EmbeddingProvider.VERTEX_AI, ...),
        ))
        self._adk_memory = None  # Lazy-init Neo4jMemoryService
    
    async def initialize(self):
        await self._client.connect()
    
    @property
    def client(self) -> MemoryClient:
        return self._client  # Exposed for Neo4jDomainService
    
    # Correct API usage throughout
```

**Key difference**: Exposes `client` property so `Neo4jDomainService` can share the connection:
```python
# In main.py lifespan:
neo4j_service = Neo4jDomainService(memory_service.client.graph)
```

---

## 9. Configuration

### Environment Variables

| Variable | AWS | Google Cloud |
|----------|-----|-------------|
| LLM credentials | `AWS_REGION`, `AWS_PROFILE`, `BEDROCK_MODEL_ID` | `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT` |
| Embedding model | `BEDROCK_EMBEDDING_MODEL_ID` | `VERTEX_AI_MODEL_ID`, `VERTEX_AI_LOCATION` |
| Neo4j | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Same |
| Auth | `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID` | N/A |
| Storage | `S3_BUCKET_NAME`, `S3_REGION` | N/A |

### `.env` Location

**AWS**: `.env.example` at project root, but must be copied to `backend/.env` (undocumented)

**Google Cloud**: `.env.example` at project root, `config.py` reads from `("../.env", ".env")` -- works from either location

### Dependencies

**AWS** (`pyproject.toml`):
```toml
"strands-agents>=0.1.0"
"boto3>=1.34.0"
"neo4j-agent-memory>=0.1.0"  # No extras
```

**Google Cloud** (`pyproject.toml`):
```toml
"google-adk>=0.3.0"
"google-cloud-aiplatform>=1.38.0"
"sse-starlette>=1.8.0"
"neo4j-agent-memory[google-adk,vertex-ai]>=0.1.0"  # With extras
"neo4j>=5.14.0"
```

---

## 10. Testing

**AWS**: Test scaffolding exists (`tests/conftest.py`, 4 test files) but tests call simulated tools.

**Google Cloud**: Two test suites in the main package:
- `tests/examples/test_google_cloud_financial_advisor.py` -- structure validation
- `tests/examples/test_financial_advisor_neo4j_integration.py` -- unit tests for Neo4jDomainService, tool functions, bind_tool, SSE helpers, trace routes

---

## 11. What AWS Needs to Reach Parity

### Must-Have (functional equivalence)

| # | Task | Files to Create/Modify | Reference in Google Cloud |
|---|------|----------------------|--------------------------|
| 1 | Fix memory_service.py API bugs | `backend/src/services/memory_service.py` | `services/memory_service.py` |
| 2 | Create sample data + loader | `data/*.json`, `scripts/load_sample_data.py` | `data/load_sample_data.py` |
| 3 | Create `Neo4jDomainService` | `backend/src/services/neo4j_service.py` | `services/neo4j_service.py` |
| 4 | Replace simulated tools with Neo4j queries | All 4 agent files + new `tools/` dir | `tools/kyc_tools.py`, etc. |
| 5 | Add SSE streaming endpoint | `backend/src/api/routes/chat.py` | `api/routes/chat.py` (stream section) |
| 6 | Add reasoning trace persistence | `backend/src/api/routes/chat.py` | `api/routes/chat.py` (trace recording) |
| 7 | Add trace retrieval endpoints | New `backend/src/api/routes/traces.py` | `api/routes/traces.py` |

### Nice-to-Have (UX parity)

| # | Task | Files to Create/Modify | Reference in Google Cloud |
|---|------|----------------------|--------------------------|
| 8 | Add `useAgentStream` hook | `frontend/src/hooks/useAgentStream.ts` | `hooks/useAgentStream.ts` |
| 9 | Add `AgentOrchestrationView` | `frontend/src/components/Chat/` | `components/Chat/AgentOrchestrationView.tsx` |
| 10 | Add `AgentActivityTimeline` | `frontend/src/components/Chat/` | `components/Chat/AgentActivityTimeline.tsx` |
| 11 | Adapt `_bind_tool` for Strands | `backend/src/agents/__init__.py` | `agents/__init__.py` |

### Strands-Specific Considerations

The Strands framework doesn't have ADK's native `sub_agents` or `Runner.run_async()` event stream. To implement SSE streaming with Strands:

1. **Agent callback/hooks**: Check if Strands supports execution callbacks or event hooks
2. **Tool-level events**: Emit SSE events from within `@tool` functions before/after sub-agent calls
3. **Background execution**: Run the supervisor in a background task, emit events via an async queue

The `_bind_tool` pattern can be adapted for Strands by modifying the `@tool` decorator functions to accept a `neo4j_service` parameter, or by creating a service registry that tools can access.

---

## Summary

The Google Cloud example is a **complete, functional reference implementation** that demonstrates real Neo4j queries, SSE streaming, reasoning trace persistence, and animated agent visualization. The AWS example has the same architectural intent but needs the data layer (sample data + Neo4j queries), API bug fixes, and streaming/visualization features to match. The gap is significant but addressable -- the Google Cloud example provides a clear template for each missing piece.
