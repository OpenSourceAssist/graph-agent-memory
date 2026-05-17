# NAMS Integration Tests (TCK Conformance)

Integration test scaffold for verifying the v0.4 NAMS backend against
either:

1. **A real NAMS sandbox API key** (preferred for nightly CI), or
2. **A local TCK reference implementation** (Docker image — see below).

The unit tests in `tests/unit/nams/` use `respx` to mock HTTP responses
and cover transport mechanics, error mapping, and per-method request /
response shapes. The integration tests here verify that the client's
inferred endpoint shapes and request bodies actually match what a
SPEC-conformant server expects.

## Running

### Against a real NAMS sandbox

```bash
export NAMS_SANDBOX_URL=https://memory.neo4jlabs.com/v1
export NAMS_SANDBOX_KEY=nams_sandbox_xxxxx

make test-nams-integration
```

Tests requiring a real key are gated on `NAMS_SANDBOX_KEY` — they skip
when unset.

### Against a local TCK reference impl

If/when the TCK reference Docker image becomes available
(`ghcr.io/neo4j-labs/agent-memory-tck-reference:latest`):

```bash
docker-compose -f docker-compose.test.yml up -d nams-tck
export NAMS_TCK_URL=http://localhost:8765
make test-nams-integration
docker-compose -f docker-compose.test.yml stop nams-tck
```

## Status (v0.4 ship)

Integration test files are placeholders pending TCK reference impl
publication. The conformance matrix is:

* `test_tck_bronze.py` — Bronze tier (short-term core).
* `test_tck_silver.py` — Silver tier (long-term + reasoning).
* `test_tck_gold.py` — Gold tier (cross-memory, similar traces).
* `test_tck_platinum.py` — Platinum tier (hosted-only operations).
* `test_smoke.py` — End-to-end smoke against sandbox.

Each currently `pytest.skip`s with the env var its presence depends on.
Replace skip with real test bodies once the SPEC endpoints are
finalized.

## What needs verifying once a server is live

The `TODO(nams-spec)` comments in `src/neo4j_agent_memory/nams/*.py`
mark endpoint shapes that were inferred from REST conventions and need
confirmation against the live SPEC. Search for these comments and
update both the source and any integration test fixtures.
