# eval-harness

Demonstrates the v0.5 P2.3 evaluation harness — labeled regression
tests for memory quality across three dimensions:

- **Retrieval**: recall@k against expected entity ids.
- **Audit**: coverage of `(:Entity)<-[:TOUCHED]-(:ReasoningStep)` paths.
- **Preference**: F1 against expected active preferences.

## Running

```bash
uv run python -m examples.eval-harness.main
```

You should see something like:

```
=== Eval report ===
Overall: 1.00
Audit:    cases=1 score=1.00
Pref:     cases=1 score=1.00
```

## See Also

- `how-to/evaluation.adoc` — the design and broader usage.
