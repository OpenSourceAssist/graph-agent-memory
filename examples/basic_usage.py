#!/usr/bin/env python3
"""
Basic usage example for neo4j-agent-memory.

This example demonstrates the core functionality of the memory system:
- Adding messages to episodic memory
- Storing preferences in semantic memory
- Recording reasoning traces in procedural memory
- Getting combined context for LLM prompts

Requirements:
    - Neo4j running (or set NEO4J_URI in .env)
    - pip install neo4j-agent-memory[openai]
    - OPENAI_API_KEY environment variable set (or in .env)

Environment variables can be set in examples/.env file.
"""

import asyncio
import os
from pathlib import Path

from pydantic import SecretStr


def load_env_files():
    """Load environment variables from .env files."""
    # Try to load from dotenv if available
    try:
        from dotenv import load_dotenv

        # Load from examples/.env (same directory as this script)
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"Loaded environment from {env_file}")

        # Also try parent directory .env
        parent_env = Path(__file__).parent.parent / ".env"
        if parent_env.exists():
            load_dotenv(parent_env)
            print(f"Loaded environment from {parent_env}")
    except ImportError:
        # dotenv not installed, try manual parsing
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("\"'")
                        if key and key not in os.environ:
                            os.environ[key] = value
            print(f"Loaded environment from {env_file}")


# Load environment variables before anything else
load_env_files()

from neo4j_agent_memory import (
    EmbeddingConfig,
    EmbeddingProvider,
    ExtractionConfig,
    ExtractorType,
    MemoryClient,
    MemorySettings,
    MessageRole,
    Neo4jConfig,
    ToolCallStatus,
)


async def main():
    # Configure embedding provider based on available API keys
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if openai_api_key:
        # Use OpenAI embeddings if API key is available
        embedding_config = EmbeddingConfig(
            provider=EmbeddingProvider.OPENAI,
            model="text-embedding-3-small",
        )
        extraction_config = ExtractionConfig(
            extractor_type=ExtractorType.LLM,
        )
        print("Using OpenAI embeddings and LLM extraction")
    else:
        # Fall back to sentence-transformers (requires: pip install neo4j-agent-memory[sentence-transformers])
        try:
            import sentence_transformers  # noqa: F401

            embedding_config = EmbeddingConfig(
                provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
                model="all-MiniLM-L6-v2",
                dimensions=384,
            )
            extraction_config = ExtractionConfig(
                extractor_type=ExtractorType.NONE,  # Disable extraction without LLM
            )
            print("Using sentence-transformers embeddings (no OPENAI_API_KEY found)")
            print("Note: Entity extraction disabled without OpenAI API key")
        except ImportError:
            print("ERROR: No embedding provider available!")
            print("Either:")
            print("  1. Set OPENAI_API_KEY environment variable, or")
            print(
                "  2. Install sentence-transformers: pip install neo4j-agent-memory[sentence-transformers]"
            )
            return

    # Configure the memory client
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
        ),
        embedding=embedding_config,
        extraction=extraction_config,
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

        # Add entities (using POLE+O types)
        await memory.semantic.add_entity(
            name="Downtown",
            entity_type="LOCATION",  # POLE+O type
            subtype="LANDMARK",  # Optional subtype
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
        # NEW FEATURES: Batch Loading
        # =================================================================
        print("\n🚀 Demonstrating batch message loading...")

        bulk_session = "bulk-demo-session"
        messages = [
            {
                "role": "user",
                "content": "What's the weather like?",
                "metadata": {"topic": "weather"},
            },
            {
                "role": "assistant",
                "content": "It's sunny and 72°F today!",
                "metadata": {"topic": "weather"},
            },
            {
                "role": "user",
                "content": "Great! What should I wear?",
                "metadata": {"topic": "fashion"},
            },
            {
                "role": "assistant",
                "content": "Light clothing would be perfect.",
                "metadata": {"topic": "fashion"},
            },
        ]

        loaded_messages = await memory.episodic.add_messages_batch(
            bulk_session,
            messages,
            batch_size=2,
            generate_embeddings=True,
            extract_entities=False,  # Skip for speed
        )
        print(f"✅ Bulk loaded {len(loaded_messages)} messages")

        # =================================================================
        # NEW FEATURES: Session Listing
        # =================================================================
        print("\n📋 Listing sessions...")

        sessions = await memory.episodic.list_sessions(
            limit=10,
            order_by="updated_at",
            order_dir="desc",
        )
        print(f"Found {len(sessions)} sessions:")
        for s in sessions[:3]:
            print(f"   - {s.session_id}: {s.message_count} messages")

        # =================================================================
        # NEW FEATURES: Metadata Search
        # =================================================================
        print("\n🔎 Searching messages with metadata filters...")

        weather_messages = await memory.episodic.search_messages(
            "weather",
            session_id=bulk_session,
            metadata_filters={"topic": "weather"},
            limit=5,
        )
        print(f"Found {len(weather_messages)} messages about weather")

        # =================================================================
        # NEW FEATURES: StreamingTraceRecorder
        # =================================================================
        print("\n⏱️  Using StreamingTraceRecorder for trace recording...")

        from neo4j_agent_memory import StreamingTraceRecorder

        async with StreamingTraceRecorder(
            memory.procedural, session_id, "Process customer inquiry"
        ) as recorder:
            # Record steps during streaming
            step = await recorder.start_step(
                thought="Analyzing customer request",
                action="process_inquiry",
            )
            await recorder.record_tool_call(
                "analyze_text",
                {"text": "Customer asking about returns"},
                {"intent": "return_policy", "confidence": 0.95},
            )
            await recorder.add_observation("Customer wants to know about return policy")

        print("✅ Streaming trace recorded automatically with timing")

        # =================================================================
        # NEW FEATURES: List Traces
        # =================================================================
        print("\n📊 Listing reasoning traces...")

        traces = await memory.procedural.list_traces(
            session_id=session_id,
            success_only=True,
            limit=5,
        )
        print(f"Found {len(traces)} successful traces for session")

        # =================================================================
        # NEW FEATURES: Tool Stats (optimized)
        # =================================================================
        print("\n🔧 Getting optimized tool statistics...")

        tool_stats = await memory.procedural.get_tool_stats()
        print(f"Found stats for {len(tool_stats)} tools:")
        for stat in tool_stats[:3]:
            print(f"   - {stat.name}: {stat.total_calls} calls, {stat.success_rate:.0%} success")

        # =================================================================
        # NEW FEATURES: Graph Export
        # =================================================================
        print("\n🌐 Exporting memory graph...")

        graph = await memory.get_graph(
            memory_types=["episodic", "semantic"],
            session_id=session_id,
            include_embeddings=False,
            limit=100,
        )
        print(f"Graph export: {len(graph.nodes)} nodes, {len(graph.relationships)} relationships")

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
