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
        conversation_id = "nams-langchain-demo"
        create_conversation = getattr(client.short_term, "create_conversation", None)
        if callable(create_conversation):
            conversation = await create_conversation(conversation_id)
            conversation_id = str(conversation.id)

        # Same LangChain memory adapter — no NAMS-specific variant needed.
        # Phase 6 of the v0.4 work migrated the underlying Cypher calls to
        # ``client.query.cypher``. For NAMS today, short-term memory is the
        # supported path through the adapter, so we disable the bolt-only layers.
        memory = Neo4jAgentMemory(
            memory_client=client,
            session_id=conversation_id,
            include_long_term=False,
            include_reasoning=False,
        )

        # Add a couple of messages via the adapter — these flow through
        # ``client.short_term.add_message`` over the NAMS HTTP transport.
        await memory.aadd_messages(
            [
                ("user", "I prefer dark mode in all my apps."),
                ("assistant", "Got it — I'll remember that."),
            ]
        )

        # Pull short-term memory variables back out (the standard LangChain pattern).
        variables = await memory.aload_memory_variables({})
        print(f"Loaded memory variables: {list(variables.keys())}")

        # The retriever / tools / agent wiring you'd normally do with
        # LangChain hooks up exactly the same way against ``memory``.
        # See the LangChain integration docs for the full agent example —
        # on NAMS, keep to the layers the hosted API currently exposes.
        print("Demo complete. Swap MemorySettings(backend='nams') for")
        print("MemorySettings(neo4j=Neo4jConfig(password=...)) to run on bolt.")


if __name__ == "__main__":
    asyncio.run(main())
