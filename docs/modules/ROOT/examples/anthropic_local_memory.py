"""Explicit Anthropic extraction with local embeddings and storage in AuraDB."""

import asyncio
import os
from uuid import uuid4

from aura_connection import aura_config


async def main():
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.llm import from_provider

    llm = from_provider(f"anthropic/{os.environ['ANTHROPIC_MODEL']}", kind="llm")
    embedding = from_provider("BAAI/bge-small-en-v1.5", kind="embedding")
    print(f"LLM adapter: {type(llm).__name__}")
    print(f"Embedding adapter: {type(embedding).__name__}; dimensions={embedding.dimensions}")
    settings = MemorySettings(
        backend="bolt",
        neo4j=aura_config(),
        llm=llm,
        embedding=embedding,
        extraction={"extractor_type": "llm"},
    )
    session_id = f"anthropic-tutorial-{uuid4().hex[:8]}"
    async with MemoryClient(settings) as client:
        # Database time before the write: extraction creates or updates entities after it.
        [started] = await client.query.cypher("RETURN datetime() AS now")
        message = await client.short_term.add_message(
            session_id=session_id,
            role="user",
            content="Maya Chen works at Northstar Robotics in Denver.",
            extract_entities=True,
        )
        history = (await client.short_term.get_conversation(session_id)).messages
        if not any(stored.id == message.id for stored in history):
            raise RuntimeError("The saved message was missing from readback")
        print(f"Verified message readback; session={session_id}")
        # Read back the entities extraction wrote. In 0.6.0 extracted entities are
        # stored without vectors, so an exact graph read checks them, not search_entities.
        entities = await client.query.cypher(
            "MATCH (entity:Entity) "
            "WHERE coalesce(entity.updated_at, entity.created_at) >= $since "
            "RETURN entity.name AS name, entity.type AS type ORDER BY name",
            {"since": started["now"]},
        )
        if not entities:
            raise RuntimeError(
                "No entity candidates returned; inspect extraction before continuing"
            )
        for entity in entities:
            print(f"Entity candidate: {entity['name']} ({entity['type']})")
        context = await client.get_context("Maya Chen", session_id=session_id)
        if not context.strip():
            raise RuntimeError("Context assembly returned empty text")
        print("Verified: context assembly returned text")
        print(context)


if __name__ == "__main__":
    asyncio.run(main())
