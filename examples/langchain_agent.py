#!/usr/bin/env python3
"""
LangChain integration example for neo4j-agent-memory.

This example shows how to use Neo4j Agent Memory with LangChain:
- Using Neo4jAgentMemory as agent memory
- Using Neo4jMemoryRetriever for RAG

Requirements:
    - Neo4j running at bolt://localhost:7687
    - pip install neo4j-agent-memory[langchain,openai]
    - OPENAI_API_KEY environment variable set
"""

import asyncio
import os

from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig


async def main():
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
        )
    )

    async with MemoryClient(settings) as client:
        # Pre-populate some memories
        session_id = "langchain-demo"

        await client.episodic.add_message(session_id, "user", "I prefer spicy food")
        await client.semantic.add_preference("food", "Loves spicy dishes", "Dining preferences")
        await client.semantic.add_entity(
            name="Thai Kitchen",
            entity_type="ORGANIZATION",
            description="Favorite Thai restaurant",
        )

        print("=" * 60)
        print("Neo4j Agent Memory - LangChain Integration Demo")
        print("=" * 60)

        # Try to import LangChain
        try:
            from neo4j_agent_memory.integrations.langchain import (
                Neo4jAgentMemory,
                Neo4jMemoryRetriever,
            )
        except ImportError:
            print("\n❌ LangChain not installed.")
            print("   Install with: pip install neo4j-agent-memory[langchain]")
            return

        # =================================================================
        # Using Neo4jAgentMemory
        # =================================================================
        print("\n📝 Using Neo4jAgentMemory...")

        memory = Neo4jAgentMemory(
            memory_client=client,
            session_id=session_id,
            include_episodic=True,
            include_semantic=True,
            include_procedural=True,
        )

        # Load memory variables
        variables = memory.load_memory_variables({"input": "restaurant recommendation"})

        print("Memory variables:")
        for key, value in variables.items():
            print(f"\n  {key}:")
            if isinstance(value, str):
                print(f"    {value[:200]}..." if len(value) > 200 else f"    {value}")
            else:
                print(f"    {value}")

        # Save new context
        memory.save_context(
            {"input": "What's a good Thai restaurant?"},
            {"output": "Based on your preferences, I recommend Thai Kitchen!"},
        )
        print("\n✅ Saved new interaction to memory")

        # =================================================================
        # Using Neo4jMemoryRetriever
        # =================================================================
        print("\n🔍 Using Neo4jMemoryRetriever...")

        retriever = Neo4jMemoryRetriever(
            memory_client=client,
            search_episodic=True,
            search_semantic=True,
            k=5,
        )

        # Retrieve relevant documents
        docs = retriever.invoke("spicy food preferences")

        print(f"Retrieved {len(docs)} documents:")
        for doc in docs:
            print(f"\n  Type: {doc.metadata.get('type')}")
            print(f"  Content: {doc.page_content[:100]}...")

        print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
