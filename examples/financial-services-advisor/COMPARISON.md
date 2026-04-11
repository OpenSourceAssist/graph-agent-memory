# AWS vs Google Cloud Financial Advisor - Comparison

Side-by-side comparison of the two financial compliance example applications. Both implement the same multi-agent investigation system with Neo4j-backed tools, shared sample data, and equivalent functionality.

| | [AWS](aws-financial-services-advisor/) | [Google Cloud](google-cloud-financial-advisor/) |
|-|----------------------------------------|------------------------------------------------|
| **Agent Framework** | AWS Strands Agents | Google ADK |
| **LLM** | Bedrock (Claude Sonnet 4) | Gemini 2.5 Flash |
| **Embeddings** | Titan Embed V2 | Vertex AI text-embedding-004 |
| **Status** | Functional | Functional |

---

## Shared Components

Both examples share:

- **Sample data** (`../data/`): 3 customers, 6 organizations, 16 transactions, 3 sanctions entries, 3 PEPs, 3 alerts
- **Neo4jDomainService**: ~30 Cypher query methods for domain data (customers, transactions, AML patterns, network analysis, alerts, sanctions, PEPs)
- **16 agent tools**: 4 KYC + 4 AML + 4 Relationship + 4 Compliance, all querying Neo4j
- **`bind_tool()` pattern**: Hides `neo4j_service` from LLM function signatures
- **Memory service**: Short-term (conversations), long-term (entities), reasoning (audit trails)
- **Frontend**: React 18 + Vite + Chakra UI v3 + Framer Motion agent visualization

---

## Agent Architecture

### AWS Strands

```python
# Explicit delegation via @tool functions
@tool
def delegate_to_kyc_agent(customer_id, task):
    kyc_agent = _create_sub_agent("kyc", KYC_PROMPT, kyc_tools)
    result = kyc_agent(prompt)
    return {"agent": "kyc", "findings": str(result)}

supervisor = Agent(model=BedrockModel(...), tools=[delegate_to_kyc_agent, ...])
```

- Sub-agents created as separate `Agent` instances with their own model
- Supervisor invokes sub-agents via `@tool` delegation functions
- Synchronous execution: `supervisor(prompt)` blocks until complete

### Google ADK

```python
# Native sub_agents parameter
kyc_agent = LlmAgent(name="kyc_agent", model=model, tools=[...])
supervisor = LlmAgent(name="supervisor", sub_agents=[kyc_agent, ...])

# Async event stream
async for event in Runner.run_async(user_id, session_id, message):
    # Real-time events as each agent executes
```

- Native `sub_agents=[]` parameter handles delegation automatically
- `Runner.run_async()` yields events in real-time as sub-agents execute
- Agent transitions detected via `event.author` field

---

## SSE Streaming

This is the primary UX difference between the two implementations.

| Aspect | AWS | Google Cloud |
|--------|-----|-------------|
| **Streaming mode** | Post-completion | Real-time |
| **Event types** | 5 (agent_start, agent_complete, response, trace_saved, done) | 11 (+ agent_delegate, tool_call, tool_result, memory_access, thinking) |
| **Sub-agent visibility** | After completion only | Live as each agent runs |
| **Framework constraint** | Strands `agent(prompt)` is synchronous | ADK `Runner.run_async()` is async generator |

**Why the difference**: Strands doesn't expose an async event generator during agent execution. The AWS streaming endpoint wraps the synchronous response in SSE format and emits events after the supervisor finishes. The GCP version uses ADK's native async generator which yields events as each sub-agent starts, calls tools, and completes.

---

## Reasoning Trace Recording

| Aspect | AWS | Google Cloud |
|--------|-----|-------------|
| **Trace creation** | After each chat | After each chat stream |
| **Granularity** | 1 step per supervisor invocation | 1 step per sub-agent with nested tool calls |
| **Tool call nesting** | Not recorded | `record_tool_call(step_id, ...)` per tool |

Both persist traces to Neo4j via `MemoryClient.reasoning` and expose them via `GET /api/traces/{session_id}`.

---

## Route Implementations

All domain routes in both examples query Neo4j via `Neo4jDomainService`:

| Route | AWS | Google Cloud |
|-------|-----|-------------|
| `GET /api/customers` | `neo4j_service.list_customers()` | Same |
| `GET /api/customers/{id}/risk` | Inline `_compute_risk()` | Same |
| `GET /api/customers/{id}/network` | `neo4j_service.find_connections()` | Same |
| `GET /api/alerts` | `neo4j_service.list_alerts()` | Same |
| `POST /api/alerts` | `neo4j_service.create_alert()` | Same |
| `GET /api/graph/stats` | `neo4j_service.get_graph_stats()` | Same |
| `GET /api/graph/neighbors/{id}` | Graph traversal via Cypher | Same |
| `POST /api/chat` | Sync supervisor call | Sync ADK runner |
| `POST /api/chat/stream` | Post-completion SSE | Real-time SSE |
| `GET /api/traces/{session_id}` | Reasoning trace retrieval | Same |

---

## Configuration

| Variable | AWS | Google Cloud |
|----------|-----|-------------|
| LLM credentials | `AWS_REGION`, `AWS_PROFILE`, `BEDROCK_MODEL_ID` | `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT` |
| Embedding model | `BEDROCK_EMBEDDING_MODEL_ID` | `VERTEX_AI_MODEL_ID`, `VERTEX_AI_LOCATION` |
| Neo4j | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Same |
| Deployment | AWS Lambda + CDK | Google Cloud Run |

Both read `.env` from `backend/.env` with fallback to parent directories.

---

## Testing

| Test Suite | AWS | Google Cloud |
|-----------|-----|-------------|
| Unit tests (backend) | 113 tests in `backend/tests/` | Tests in repo `tests/examples/` |
| Structure validation | `tests/examples/test_aws_financial_advisor.py` | `tests/examples/test_google_cloud_financial_advisor.py` |
| Neo4j integration | `tests/examples/test_financial_advisor_neo4j_integration.py` | Same file |

---

## Getting Started

- **AWS**: See [aws-financial-services-advisor/GETTING_STARTED.md](aws-financial-services-advisor/GETTING_STARTED.md)
- **Google Cloud**: See [google-cloud-financial-advisor/GETTING_STARTED.md](google-cloud-financial-advisor/GETTING_STARTED.md)

Both use the same shared data directory (`data/`) with `make load-data` to populate Neo4j.
