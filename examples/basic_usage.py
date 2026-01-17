#!/usr/bin/env python3
"""
Basic usage example for neo4j-agent-memory.

This example demonstrates the core functionality of the memory system:
- Adding messages to episodic memory
- Storing preferences in semantic memory
- Recording reasoning traces in procedural memory
- Getting combined context for LLM prompts

Requirements:
    - Neo4j running at bolt://localhost:7687
    - pip install neo4j-agent-memory[openai]
    - OPENAI_API_KEY environment variable set
"""

import asyncio
import os

from pydantic import SecretStr

from neo4j_agent_memory import (
    EmbeddingConfig,
    EmbeddingProvider,
    EntityType,
    ExtractionConfig,
    ExtractorType,
    MemoryClient,
    MemorySettings,
    MessageRole,
    Neo4jConfig,
    ToolCallStatus,
)


async def main():
    # Configure the memory client
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
        ),
        embedding=EmbeddingConfig(
            provider=EmbeddingProvider.OPENAI,
            model="text-embedding-3-small",
        ),
        extraction=ExtractionConfig(
            extractor_type=ExtractorType.LLM,
        ),
    )

    async with MemoryClient(settings) as memory:
        session_id = "demo-session"

        print("=" * 60)
        print("Neo4j Agent Memory - Basic Usage Demo")
        print("=" * 60)

        # =================================================================
        # EPISODIC MEMORY: Conversation History
        # =================================================================
        print("\n📝 Adding messages to episodic memory...")

        await memory.episodic.add_message(
            session_id,
            MessageRole.USER,
            "Hi! I'm looking for restaurant recommendations. I love Italian food.",
        )

        await memory.episodic.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "I'd be happy to help you find Italian restaurants! Do you have any specific preferences like price range or location?",
        )

        await memory.episodic.add_message(
            session_id,
            MessageRole.USER,
            "Something mid-range in downtown. I'm vegetarian.",
        )

        # Retrieve conversation
        conversation = await memory.episodic.get_conversation(session_id)
        print(f"✅ Stored {len(conversation.messages)} messages")

        # =================================================================
        # SEMANTIC MEMORY: Facts and Preferences
        # =================================================================
        print("\n🧠 Adding facts and preferences to semantic memory...")

        # Add user preferences
        await memory.semantic.add_preference(
            category="food",
            preference="Loves Italian cuisine",
            context="Restaurant recommendations",
        )

        await memory.semantic.add_preference(
            category="dietary",
            preference="Vegetarian diet",
            context="All meals",
        )

        await memory.semantic.add_preference(
            category="budget",
            preference="Prefers mid-range restaurants",
        )

        # Add entities
        await memory.semantic.add_entity(
            name="Downtown",
            entity_type=EntityType.LOCATION,
            description="User's preferred dining area",
        )

        # Add facts
        await memory.semantic.add_fact(
            subject="User",
            predicate="dietary_restriction",
            obj="vegetarian",
        )

        print("✅ Stored preferences, entities, and facts")

        # Search preferences
        print("\n🔍 Searching for food-related preferences...")
        food_prefs = await memory.semantic.search_preferences("food", limit=5)
        for pref in food_prefs:
            print(f"   [{pref.category}] {pref.preference}")

        # =================================================================
        # PROCEDURAL MEMORY: Reasoning Traces
        # =================================================================
        print("\n⚙️  Recording reasoning trace...")

        # Start a trace
        trace = await memory.procedural.start_trace(
            session_id,
            task="Find vegetarian Italian restaurant in downtown",
        )

        # Add reasoning steps
        step1 = await memory.procedural.add_step(
            trace.id,
            thought="I need to search for Italian restaurants in downtown that offer vegetarian options",
            action="search_restaurants",
        )

        # Record tool call
        await memory.procedural.record_tool_call(
            step1.id,
            tool_name="restaurant_search_api",
            arguments={
                "cuisine": "Italian",
                "location": "downtown",
                "dietary": "vegetarian",
            },
            result=[
                {"name": "La Trattoria Verde", "rating": 4.5},
                {"name": "Pasta Paradise", "rating": 4.3},
            ],
            status=ToolCallStatus.SUCCESS,
            duration_ms=250,
        )

        step2 = await memory.procedural.add_step(
            trace.id,
            thought="Found two good options. La Trattoria Verde has better ratings.",
            action="recommend",
            observation="La Trattoria Verde is highly rated and fits all criteria",
        )

        # Complete the trace
        await memory.procedural.complete_trace(
            trace.id,
            outcome="Recommended La Trattoria Verde",
            success=True,
        )

        print("✅ Recorded reasoning trace with 2 steps")

        # =================================================================
        # COMBINED CONTEXT
        # =================================================================
        print("\n📋 Getting combined context for LLM prompt...")

        context = await memory.get_context(
            "restaurant recommendation",
            session_id=session_id,
        )

        print("-" * 40)
        print(context)
        print("-" * 40)

        # =================================================================
        # MEMORY STATS
        # =================================================================
        print("\n📊 Memory statistics:")
        stats = await memory.get_stats()
        print(f"   Conversations: {stats.get('conversations', 0)}")
        print(f"   Messages: {stats.get('messages', 0)}")
        print(f"   Entities: {stats.get('entities', 0)}")
        print(f"   Preferences: {stats.get('preferences', 0)}")
        print(f"   Facts: {stats.get('facts', 0)}")
        print(f"   Reasoning Traces: {stats.get('traces', 0)}")

        print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
