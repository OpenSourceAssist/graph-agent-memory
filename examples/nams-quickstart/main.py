"""NAMS quickstart — minimal end-to-end agent-memory flow against the hosted service.

Run with:

    export MEMORY_API_KEY=nams_xxxxx
    uv run python examples/nams-quickstart/main.py

Or override the endpoint for a private deployment:

    export MEMORY_API_KEY=nams_xxxxx
    export MEMORY_ENDPOINT=https://nams.internal/v1
    uv run python examples/nams-quickstart/main.py

The script exercises the three memory types over the unified
``MemoryClient`` surface — every call you see here works identically on
the bolt backend if you swap ``backend="nams"`` for ``backend="bolt"``
(plus ``neo4j=Neo4jConfig(password=...)``).
"""

from __future__ import annotations

import asyncio
import os

from neo4j_agent_memory import MemoryClient, MemorySettings


async def main() -> None:
    if not os.environ.get("MEMORY_API_KEY"):
        raise SystemExit(
            "Set MEMORY_API_KEY to your NAMS API key. "
            "Sign up at https://memory.neo4jlabs.com to get one."
        )

    # backend="nams" is auto-selected from MEMORY_API_KEY, so this would
    # work too: ``MemorySettings()``. Being explicit here for clarity.
    settings = MemorySettings(backend="nams")

    async with MemoryClient(settings) as client:
        print(f"Connected to {client._settings.nams.endpoint!r}")
        session_id = "nams-quickstart-demo"

        # 1. Short-term memory: store a few messages.
        await client.short_term.add_message(session_id, "user", "Hi, I'm Alice.")
        await client.short_term.add_message(
            session_id, "assistant", "Nice to meet you, Alice!"
        )
        await client.short_term.add_message(
            session_id, "user", "I love Italian food and dislike crowded restaurants."
        )

        conv = await client.short_term.get_conversation(session_id)
        print(f"\nConversation has {len(conv.messages)} messages")

        # 2. Long-term memory: record an entity and a preference.
        entity = await client.long_term.add_entity(
            "Alice",
            "PERSON",
            description="The user introducing themselves.",
        )
        print(f"Created entity: {entity.name} ({entity.type})")

        pref = await client.long_term.add_preference(
            category="food",
            preference="Italian cuisine",
            context="discussed in the introduction conversation",
        )
        print(f"Recorded preference: [{pref.category}] {pref.preference}")

        # 3. Reasoning memory: start, step, and complete a trace.
        trace = await client.reasoning.start_trace(
            session_id=session_id,
            task="Recommend a restaurant for Alice.",
        )
        step = await client.reasoning.add_step(
            trace.id,
            thought="Alice likes Italian and dislikes crowds.",
            action="Look up quiet Italian places.",
            observation="Found 3 candidates.",
        )
        await client.reasoning.record_tool_call(
            step.id,
            tool_name="restaurant_search",
            arguments={"cuisine": "Italian", "noise_level": "quiet"},
            result=["Da Mario", "Trattoria Bella", "Osteria del Sole"],
        )
        await client.reasoning.complete_trace(
            trace.id, outcome="Suggested 3 restaurants.", success=True
        )
        print(f"Completed reasoning trace: {trace.task}")

        # 4. Unified Cypher accessor (Platinum, NAMS-only — also works on bolt).
        try:
            rows = await client.query.cypher(
                "MATCH (e:Entity {name: $name}) RETURN e.name AS name LIMIT 1",
                {"name": "Alice"},
            )
            print(f"Cypher round-trip: {rows}")
        except Exception as e:  # noqa: BLE001 — demo script
            print(f"Cypher query unsupported on this NAMS deployment: {e}")

        print("\nDone. The same script body runs against bolt if you flip backend='bolt'.")


if __name__ == "__main__":
    asyncio.run(main())
