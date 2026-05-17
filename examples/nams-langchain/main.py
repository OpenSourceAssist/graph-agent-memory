"""NAMS + LangChain — the existing LangChain integration works unchanged on NAMS.

Demonstrates that the ``Neo4jAgentMemory`` LangChain memory adapter,
the LangChain retriever, and any other LangChain wiring are
backend-agnostic. The same import + the same construction call works
against the hosted NAMS service — you only swap the
``MemorySettings.backend`` field.

Run:

    export MEMORY_API_KEY=nams_xxxxx
    export OPENAI_API_KEY=sk-...
    uv run python examples/nams-langchain/main.py
"""

from __future__ import annotations

import asyncio
import os

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory


async def main() -> None:
    if not os.environ.get("MEMORY_API_KEY"):
        raise SystemExit(
            "Set MEMORY_API_KEY to your NAMS API key. "
            "Sign up at https://memory.neo4jlabs.com."
        )

    settings = MemorySettings(backend="nams")

    async with MemoryClient(settings) as client:
        # Same LangChain memory adapter — no NAMS-specific variant needed.
        # Phase 6 of the v0.4 work migrated the underlying Cypher calls to
        # ``client.query.cypher``, so this works on both backends.
        memory = Neo4jAgentMemory(
            memory_client=client,
            session_id="nams-langchain-demo",
        )

        # Add a couple of messages via the adapter — these flow through
        # ``client.short_term.add_message`` over the NAMS HTTP transport.
        await memory.aadd_messages(
            [
                ("user", "I prefer dark mode in all my apps."),
                ("assistant", "Got it — I'll remember that."),
            ]
        )

        # Pull memory variables back out (the standard LangChain pattern).
        variables = await memory.aload_memory_variables({})
        print(f"Loaded memory variables: {list(variables.keys())}")

        # The retriever / tools / agent wiring you'd normally do with
        # LangChain hooks up exactly the same way against ``memory``.
        # See the LangChain integration docs for the full agent example —
        # the only NAMS-specific change is settings.backend.
        print("Demo complete. Swap MemorySettings(backend='nams') for")
        print("MemorySettings(neo4j=Neo4jConfig(password=...)) to run on bolt.")


if __name__ == "__main__":
    asyncio.run(main())
