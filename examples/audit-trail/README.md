# audit-trail

End-to-end example of the v0.3 reasoning-region polish:

- `record_tool_call(touched_entities=[...])` — explicit `:TOUCHED` edges.
- `@client.reasoning.on_tool_call_recorded` — domain-specific inference
  of touched entities from tool call results.
- `TraceOutcome` — structured outcomes with indexable `error_kind`.
- The headline 1-hop audit query: `MATCH (c)<-[:TOUCHED]-(s)`.

## Files

| File | Purpose |
|---|---|
| `tool_calls.py` | Domain mapping from tool names to `EntityRef` lists. Hand-written per agent; not auto-derivable. |
| `main.py` | Registers the observer hook, runs a trace, completes with structured outcome. |
| `queries.cypher` | The headline audit query plus error-kind and per-entity history queries. |

## Running

```bash
# from repo root
uv run python -m examples.audit-trail.main
```

You should see the audit query produce a row that links `Anthem` back
through a `:TOUCHED` edge to a `:ReasoningStep` and its parent
`:ReasoningTrace`.

Then in `cypher-shell`:

```bash
cypher-shell -a $NEO4J_URI -u $NEO4J_USERNAME -p $NEO4J_PASSWORD \
    < examples/audit-trail/queries.cypher
```
