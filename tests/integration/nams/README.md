# NAMS Integration Tests

Live-service integration suite for the v0.4 NAMS backend. Runs in CI
via `.github/workflows/nams-integration.yml` against the hosted NAMS
sandbox using the `NAMS_SANDBOX_KEY` repo secret.

## Test layout

| File | Purpose | Test count |
|---|---|---|
| `test_smoke.py` | Single end-to-end happy path through all three memory types. Fails fast if anything fundamental is broken. | 1 |
| `test_auth.py` | Auth probe, lifecycle (connect/close/reopen), 401 on bad key, empty-key rejection, `validate_on_connect` semantics. | 4 |
| `test_tck_bronze.py` | SPEC §1+§2 — short-term core. `add_message` (single/multi/metadata/user_id), `get_conversation` (empty/limit), `search_messages` (scoped/threshold), `list_sessions`, `clear_session` (idempotent), `delete_message`, session isolation (§2.2.4). | 13 |
| `test_tck_silver.py` | SPEC §3+§4 — long-term + reasoning. Entity/preference/fact CRUD + search. Full reasoning trace lifecycle. Trace retrieval (`get_trace`, `get_trace_with_steps`, `get_session_traces`). `search_steps`, `get_similar_traces`. | 13 |
| `test_tck_gold.py` | SPEC §5 — cross-memory. Relationships, `get_related_entities`, `get_entity_provenance`, `get_tool_stats`, `link_trace_to_message`, entity sharing across sessions (§5.1.3). | 7 |
| `test_tck_platinum.py` | Volume 5 — hosted-only ops. `create_conversation`, `list_conversations`, `bulk_add_messages`, `get_observations`, `get_reflections`, `set_entity_feedback`, `get_entity_history`, `client.query.cypher` (read + params + write-rejection). | 10 |
| `test_errors.py` | Negative paths: 404→None, `NotSupportedError` boundaries for bolt-only accessors (`client.graph`, `users`, `buffered`, `consolidation`, `schema.adopt_existing_graph`, `get_stats`, `get_graph`, `get_locations`), write-Cypher rejection, warn-and-ignore for inactive client-side layers. | 12 |

**Total: ~60 live-service tests.**

## Running locally

### Against the hosted sandbox

```bash
export NAMS_SANDBOX_KEY=nams_sandbox_xxxxx
# Optional: override the endpoint (defaults to https://memory.neo4jlabs.com/v1)
# export NAMS_SANDBOX_URL=https://nams.sandbox.internal/v1

make test-nams-integration

# Or run a single tier:
uv run pytest tests/integration/nams/test_tck_bronze.py -v
```

### Against a local TCK reference impl

If the TCK reference Docker image is available
(`ghcr.io/neo4j-labs/agent-memory-tck-reference:latest`):

```bash
docker run -d --rm -p 8765:8000 \
    -e TCK_API_KEY=test-tck-key \
    --name nams-tck \
    ghcr.io/neo4j-labs/agent-memory-tck-reference:latest

export NAMS_TCK_URL=http://localhost:8765
export NAMS_TCK_KEY=test-tck-key

make test-nams-integration

docker stop nams-tck
```

Without either env var set, all tests **skip cleanly** — they don't fail
on local dev machines or PR runs from forks.

## CI behavior

Triggers on `push` + `pull_request` to `main` and nightly at 06:00 UTC.

PR runs from forks have no access to the `NAMS_SANDBOX_KEY` secret —
the workflow's top-level `if:` clause skips the whole job rather than
running tests that would all skip individually.

The workflow:

1. **Smoke test** (`test_smoke.py`) runs first — fails fast.
2. **Auth tests** run second — also foundational.
3. **TCK tier suites** (Bronze → Silver → Gold → Platinum) run with
   `continue-on-error: true` so a failure in one tier doesn't mask
   failures in another. Each tier is independent.
4. **Error-path tests** run with `continue-on-error: true`.
5. A **consolidated run** at the end determines overall pass/fail.

## Expected first-run failures

The v0.4 NAMS implementation has `TODO(nams-spec)` markers throughout
`src/neo4j_agent_memory/nams/*.py` flagging endpoint paths that were
inferred from REST conventions rather than verified against the live
SPEC. The integration suite **exists in part to surface these
inferences**.

Common failure shapes and what they mean:

| Symptom | Likely cause | Fix |
|---|---|---|
| `HTTP 404` on a specific method | Wrong `rest_path` in `EndpointSpec` | Check the matching `TODO(nams-spec)` marker; align with the live route |
| `HTTP 400` with `details={"field": ...}` | Wrong request body shape | Inspect `details`, update the request builder in `Nams*Memory.<method>` |
| `KeyError` on response parsing | NAMS returned a different wrapper shape | Update `payload_to_model` call to handle the actual response |
| `pydantic.ValidationError` on response | Field name mismatch | Adjust the relevant Pydantic model or response transform |
| `RateLimitError` | Sandbox tier rate-limit | Reduce test parallelism; raise `NamsConfig.max_retries` |

When tests fail, **don't disable them**. File issues, fix the SPEC
inference, retry. The whole point is to discover the wire-shape gaps
the unit tests can't catch.

## Test isolation

Every test uses a UUID-suffixed `session_id` (and entity name where
applicable) so concurrent CI runs and re-runs don't collide in the
shared sandbox. The `cleanup_registry` fixture best-effort calls
`clear_session()` on each registered session at teardown — failures
during cleanup are logged but don't fail the test.

Tests are independent: each can run in isolation, no ordering
dependency.

## What's not covered (yet)

* **Multi-tenancy / workspace boundaries.** Sandbox keys are
  single-workspace; cross-workspace isolation can't be tested without
  multiple keys.
* **Server-side rate limits.** Hard to deterministically trigger 429
  responses against a sandbox.
* **OpenTelemetry export.** The transport's tracer integration is unit
  tested with mocks; a real OTel collector check is out of scope.
* **GLI / 502 / 503 cascade behavior.** Server-side faults that retry
  paths handle gracefully — hard to provoke against sandbox.
* **Concurrent client behavior.** The HTTP transport is async-safe;
  concurrent request testing is left to the unit suite.

## Adding tests

* Place new tests in the right tier file (`test_tck_<tier>.py`) so
  the CI tier grouping stays accurate.
* Always use the `cleanup_registry` fixture if you create a session.
* Use `unique_name("prefix")` for entity / preference / fact identifiers
  that need to be unique per test.
* Don't depend on global state — each test must work in isolation.
* Mark with `pytest.mark.integration` (the module-level `pytestmark`
  applies to all tests in this directory).
