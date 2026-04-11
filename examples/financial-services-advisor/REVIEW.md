# Financial Services Advisor - Implementation Review

Review of the AWS and Google Cloud financial advisor example applications.

**Last updated**: 2026-04-11

---

## Overview

Both examples implement a multi-agent financial compliance investigation system:

- **Supervisor agent** orchestrates 4 specialist agents (KYC, AML, Relationship, Compliance)
- **16 tools** query real domain data from Neo4j via `Neo4jDomainService`
- **3 memory types**: short-term (conversations), long-term (entities), reasoning (audit trails)
- **Shared sample data**: 3 customers, 16 transactions, 6 organizations, sanctions/PEP lists, alerts

---

## Architecture Strengths

- **Clean FastAPI lifespan management**: Graceful init/close of memory service and Neo4j domain service
- **Pydantic settings**: Per-concern BaseSettings subclasses with env_prefix
- **`bind_tool()` pattern**: Cleanly injects `neo4j_service` while hiding it from LLM signatures
- **`Neo4jDomainService`**: ~30 async Cypher query methods covering all domain operations
- **Risk service**: Real weighted scoring with FATF jurisdiction lists and industry risk categorization
- **Shared data layer**: Both apps use identical JSON data files and the same Neo4j schema
- **Frontend**: Chakra UI v3 + Framer Motion agent visualization with expandable tool call cards
- **Reasoning traces**: Full audit trail stored in Neo4j via `MemoryClient.reasoning`

---

## Resolved Issues

The following issues from the initial implementation have been fixed:

### Memory Service API (9 bugs fixed)
- `add_entity()` tuple unpacking
- `get_conversation()` now accesses `.messages` attribute
- `start_trace()`, `add_step()`, `complete_trace()`, `get_trace()` all use correct parameter names (`thought`/`action`/`observation`/`outcome` instead of `reasoning`/`result`/`conclusion`)
- `search_messages()` used instead of non-existent method

### Simulated Data (replaced with Neo4j queries)
All 16 tools now query real Neo4j data:
- KYC tools query customer documents and verification status
- AML tools detect structuring ($9,500 cash deposits), rapid movement, and layering via Cypher
- Relationship tools use graph traversal for network analysis and shell company detection
- Compliance tools query sanctions/PEP lists from Neo4j

### Domain Routes (replaced in-memory storage)
Customer, alert, and graph routes now use `Neo4jDomainService` instead of Python dicts.

### Sample Data & Loading
Shared `data/` directory with 6 JSON files and async `load_sample_data.py` script.

---

## Remaining Framework Differences

### SSE Streaming Depth

**GCP** uses ADK's `Runner.run_async()` which yields events as each sub-agent executes (11 event types including `tool_call`, `memory_access`, `agent_delegate`).

**AWS** uses Strands' synchronous `agent(prompt)` which blocks until all sub-agents complete. The streaming endpoint emits events post-completion (5 event types).

This is an inherent framework difference, not fixable at the application layer.

### Reasoning Trace Granularity

**GCP** records 1 step per sub-agent with nested `record_tool_call()` entries.

**AWS** records 1 flat step per supervisor invocation.

Improving this would require Strands callback hooks or custom tool wrappers to capture per-agent execution details.

---

## Project Structure

```
financial-services-advisor/
├── data/                              # Shared sample data (6 JSON files + loader)
├── aws-financial-services-advisor/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── agents/               # Strands agents with delegation tools
│   │   │   ├── tools/                # 16 Neo4j-backed tool functions
│   │   │   ├── api/routes/           # FastAPI endpoints (Neo4j-backed)
│   │   │   └── services/             # memory_service, neo4j_service, risk_service
│   │   └── tests/                    # 113 unit tests
│   └── frontend/                     # React + Chakra + Framer Motion
├── google-cloud-financial-advisor/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── agents/               # ADK agents with native sub_agents
│   │   │   ├── tools/                # 16 Neo4j-backed tool functions
│   │   │   ├── api/routes/           # FastAPI endpoints (Neo4j-backed)
│   │   │   └── services/             # memory_service, neo4j_service
│   │   └── tests/                    # In repo tests/examples/
│   └── frontend/                     # React + Chakra + Framer Motion
├── COMPARISON.md                     # Side-by-side comparison
└── REVIEW.md                         # This document
```

---

## Potential Improvements

1. **Strands event hooks**: If Strands adds callback support, the AWS SSE streaming could emit real-time per-agent events
2. **Richer trace recording**: Wrap delegation tools to capture per-agent steps and nested tool calls
3. **Entity extraction on chat**: Trigger `neo4j-agent-memory` entity extraction pipeline on chat messages
4. **Graph visualization**: Add NVL (Neo4j Visualization Library) component for interactive graph exploration
5. **Authentication**: Wire up Cognito (AWS) / Firebase Auth (GCP) for user management
6. **Persistent investigations**: Store investigations in Neo4j instead of in-memory dicts
