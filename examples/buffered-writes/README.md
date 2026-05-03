# buffered-writes

Demonstrates the v0.4 P1.1 fire-and-forget write API:

- `MemorySettings.memory.write_mode = "buffered"`
- `client.buffered.submit(query, params)` queues writes and returns immediately
- `client.flush()` drains the queue
- `client.write_errors` exposes background failures

The agent's response to the user is **not** blocked on Neo4j round-trips
when writes go through the buffered API.

## Running

```bash
uv run python -m examples.buffered-writes.main
```

You should see something like:

```
50 turns produced 50 responses in 12.3 ms
Pending writes after responses returned: 14
flush() drained the queue in 95.2 ms
AgentTurn rows in Neo4j: 50
No buffered-write errors.
```

## See Also

- `how-to/buffered-writes.adoc` — full how-to walkthrough.
