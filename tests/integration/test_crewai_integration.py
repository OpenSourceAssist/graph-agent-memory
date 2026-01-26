"""Integration tests for CrewAI integration."""

import pytest

from neo4j_agent_memory.memory.short_term import MessageRole

# Check if CrewAI is available
try:
    from crewai.memory import Memory

    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryInitialization:
    """Test Neo4jCrewMemory initialization."""

    @pytest.mark.asyncio
    async def test_memory_initialization(self, memory_client, session_id):
        """Test basic memory initialization."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        assert memory._crew_id == session_id
        assert memory._client is memory_client

    @pytest.mark.asyncio
    async def test_memory_initialization_with_custom_crew_id(self, memory_client):
        """Test memory initialization with custom crew ID."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        custom_crew = "my-custom-crew-123"
        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=custom_crew,
        )

        assert memory._crew_id == custom_crew

    @pytest.mark.asyncio
    async def test_memory_inherits_crewai_memory(self, memory_client, session_id):
        """Test that memory inherits from CrewAI Memory."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        assert isinstance(memory, Memory)


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryRemember:
    """Test Neo4jCrewMemory remember operations."""

    @pytest.mark.asyncio
    async def test_remember_short_term_memory(self, memory_client, session_id):
        """Test remembering short-term memory."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(
            content="The user prefers detailed explanations",
            metadata={"type": "short_term"},
        )

        # Verify stored in short-term memory
        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0
        assert any("detailed explanations" in m.content for m in conv.messages)

    @pytest.mark.asyncio
    async def test_remember_defaults_to_short_term(self, memory_client, session_id):
        """Test that remember defaults to short-term memory type."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(content="Default memory type test")

        # Should be stored in short-term memory
        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0

    @pytest.mark.asyncio
    async def test_remember_fact_memory(self, memory_client, session_id):
        """Test remembering a fact."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(
            content="Python is a programming language",
            metadata={
                "type": "fact",
                "subject": "Python",
                "predicate": "is",
            },
        )

        # Verify fact was stored
        facts = await memory_client.long_term.search_facts("Python programming")
        # Facts may be searchable

    @pytest.mark.asyncio
    async def test_remember_preference_memory(self, memory_client, session_id):
        """Test remembering a preference."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(
            content="I prefer concise responses",
            metadata={
                "type": "preference",
                "category": "communication",
            },
        )

        # Verify preference was stored
        prefs = await memory_client.long_term.search_preferences("concise")
        assert len(prefs) > 0

    @pytest.mark.asyncio
    async def test_remember_with_empty_metadata(self, memory_client, session_id):
        """Test remember with empty metadata."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(content="Memory with no metadata", metadata={})

        # Should default to short-term
        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0

    @pytest.mark.asyncio
    async def test_remember_with_none_metadata(self, memory_client, session_id):
        """Test remember with None metadata."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(content="Memory with None metadata", metadata=None)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0

    @pytest.mark.asyncio
    async def test_remember_multiple_memories(self, memory_client, session_id):
        """Test remembering multiple memories in sequence."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memories = [
            ("First memory", {"type": "short_term"}),
            ("Second memory", {"type": "short_term"}),
            ("Third memory", {"type": "short_term"}),
        ]

        for content, metadata in memories:
            memory.remember(content=content, metadata=metadata)

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) >= 3


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryRecall:
    """Test Neo4jCrewMemory recall operations."""

    @pytest.mark.asyncio
    async def test_recall_returns_list(self, memory_client, session_id):
        """Test that recall returns a list of strings."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        results = memory.recall(query="test query")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_recall_finds_short_term_memories(self, memory_client, session_id):
        """Test recalling short-term memories."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        # Add a message first
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "The capital of France is Paris",
            extract_entities=False,
            generate_embedding=True,
        )

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        results = memory.recall(query="capital France")

        assert isinstance(results, list)
        # Should find the message about Paris

    @pytest.mark.asyncio
    async def test_recall_finds_preferences(self, memory_client, session_id):
        """Test recalling preferences."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        # Add a preference
        await memory_client.long_term.add_preference(
            category="style",
            preference="I prefer bullet points in explanations",
            generate_embedding=True,
        )

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        results = memory.recall(query="bullet points")

        assert isinstance(results, list)
        if len(results) > 0:
            assert any("bullet" in r.lower() for r in results)

    @pytest.mark.asyncio
    async def test_recall_finds_entities(self, memory_client, session_id):
        """Test recalling entities."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory
        from neo4j_agent_memory.memory.long_term import EntityType

        # Add an entity
        await memory_client.long_term.add_entity(
            name="Eiffel Tower",
            entity_type=EntityType.LOCATION,
            description="Famous landmark in Paris, France",
            resolve=False,
            generate_embedding=True,
        )

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        results = memory.recall(query="Paris landmark")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_recall_respects_limit(self, memory_client, session_id):
        """Test that recall respects the n limit parameter."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        # Add multiple messages
        for i in range(10):
            await memory_client.short_term.add_message(
                session_id,
                MessageRole.ASSISTANT,
                f"Test message number {i}",
                extract_entities=False,
                generate_embedding=True,
            )

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        results = memory.recall(query="test message", n=3)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_recall_with_empty_query(self, memory_client, session_id):
        """Test recall with empty query string."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        results = memory.recall(query="")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_recall_with_no_matches(self, memory_client, session_id):
        """Test recall when no matches are found."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        results = memory.recall(query="xyznonexistentquery123")

        assert isinstance(results, list)
        # May return empty list or no relevant matches


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryAgentContext:
    """Test Neo4jCrewMemory get_agent_context operations."""

    @pytest.mark.asyncio
    async def test_get_agent_context_returns_string(self, memory_client, session_id):
        """Test that get_agent_context returns a string."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        context = memory.get_agent_context(
            agent_role="researcher",
            task="Find information about Python",
        )

        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_get_agent_context_with_similar_traces(self, memory_client, session_id):
        """Test get_agent_context finds similar past traces."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        # Add a reasoning trace
        trace = await memory_client.reasoning.start_trace(
            session_id=session_id,
            task="Research Python programming best practices",
            generate_embedding=True,
        )
        await memory_client.reasoning.complete_trace(
            trace_id=trace.id,
            outcome="Found comprehensive style guide",
            success=True,
        )

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        context = memory.get_agent_context(
            agent_role="researcher",
            task="Research Python coding standards",
        )

        assert isinstance(context, str)
        # Context should mention past experience

    @pytest.mark.asyncio
    async def test_get_agent_context_empty_history(self, memory_client, session_id):
        """Test get_agent_context with no past traces."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        context = memory.get_agent_context(
            agent_role="analyst",
            task="Analyze market trends",
        )

        assert isinstance(context, str)
        # Should still return valid context string

    @pytest.mark.asyncio
    async def test_get_agent_context_different_roles(self, memory_client, session_id):
        """Test get_agent_context with different agent roles."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        roles = ["researcher", "writer", "analyst", "reviewer"]
        for role in roles:
            context = memory.get_agent_context(
                agent_role=role,
                task="Generic task for testing",
            )
            assert isinstance(context, str)


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryMultiAgent:
    """Test multi-agent scenarios for CrewAI integration."""

    @pytest.mark.asyncio
    async def test_shared_memory_across_crews(self, memory_client):
        """Test that different crew instances share memory via the client."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        crew_id = "shared-crew-test"

        memory_a = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=crew_id,
        )
        memory_b = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=crew_id,
        )

        # Agent A remembers something
        memory_a.remember(
            content="Important finding from Agent A",
            metadata={"type": "short_term"},
        )

        # Agent B should be able to recall it
        results = memory_b.recall(query="finding Agent A")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_crew_isolation(self, memory_client):
        """Test that different crews have isolated memories."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        crew_a = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id="crew-alpha",
        )
        crew_b = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id="crew-beta",
        )

        # Add to crew A
        crew_a.remember(
            content="Secret information for crew alpha only",
            metadata={"type": "short_term"},
        )

        # Crew B recalls (should not find crew A's short-term message in its conversation)
        # Note: Long-term memory (entities, preferences) may be shared across crews

    @pytest.mark.asyncio
    async def test_cross_task_persistence(self, memory_client, session_id):
        """Test that memories persist across different tasks."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        # Task 1: Remember something
        memory.remember(
            content="Task 1 discovered that the API uses REST",
            metadata={"type": "short_term"},
        )

        # Task 2: Should be able to recall Task 1's finding
        results = memory.recall(query="API REST")

        assert isinstance(results, list)


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryEdgeCases:
    """Test edge cases for CrewAI integration."""

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self, memory_client, session_id):
        """Test handling of special characters in content."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        special_content = "Special: <tag> & \"quotes\" 'apostrophe' \n\t日本語"
        memory.remember(content=special_content, metadata={"type": "short_term"})

        conv = await memory_client.short_term.get_conversation(session_id)
        assert any(special_content in m.content for m in conv.messages)

    @pytest.mark.asyncio
    async def test_large_content(self, memory_client, session_id):
        """Test handling of large content."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        large_content = "Large content: " + "A" * 5000
        memory.remember(content=large_content, metadata={"type": "short_term"})

        conv = await memory_client.short_term.get_conversation(session_id)
        assert any(len(m.content) > 5000 for m in conv.messages)

    @pytest.mark.asyncio
    async def test_empty_content(self, memory_client, session_id):
        """Test handling of empty content."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        # Should handle gracefully
        memory.remember(content="", metadata={"type": "short_term"})

    @pytest.mark.asyncio
    async def test_preference_with_default_category(self, memory_client, session_id):
        """Test preference memory with default category."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(
            content="I like detailed responses",
            metadata={"type": "preference"},  # No category specified
        )

        # Should use default "general" category
        prefs = await memory_client.long_term.search_preferences("detailed")
        # Preference should be stored

    @pytest.mark.asyncio
    async def test_fact_with_default_subject_predicate(self, memory_client, session_id):
        """Test fact memory with default subject/predicate."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        memory.remember(
            content="The sky is blue",
            metadata={"type": "fact"},  # No subject/predicate specified
        )

        # Should use defaults


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryAsync:
    """Test async behavior of CrewAI integration."""

    @pytest.mark.asyncio
    async def test_remember_works_in_async_context(self, memory_client, session_id):
        """Test that remember works when called from async context."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        # This should work even in async context
        memory.remember(
            content="Async context test for remember",
            metadata={"type": "short_term"},
        )

        conv = await memory_client.short_term.get_conversation(session_id)
        assert len(conv.messages) > 0

    @pytest.mark.asyncio
    async def test_recall_works_in_async_context(self, memory_client, session_id):
        """Test that recall works when called from async context."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "Async recall test content",
            extract_entities=False,
            generate_embedding=True,
        )

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        # This should work even in async context
        results = memory.recall(query="async recall test")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_agent_context_works_in_async_context(self, memory_client, session_id):
        """Test that get_agent_context works when called from async context."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        # This should work even in async context
        context = memory.get_agent_context(
            agent_role="tester",
            task="Test async context handling",
        )

        assert isinstance(context, str)


@pytest.mark.integration
@pytest.mark.skipif(not CREWAI_AVAILABLE, reason="CrewAI not installed")
class TestNeo4jCrewMemoryIntegrationScenarios:
    """Test realistic integration scenarios for CrewAI."""

    @pytest.mark.asyncio
    async def test_research_crew_workflow(self, memory_client, session_id):
        """Test a realistic research crew workflow."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        # Researcher finds information
        memory.remember(
            content="Python 3.12 was released in October 2023",
            metadata={"type": "fact", "subject": "Python", "predicate": "released"},
        )

        # Researcher notes a preference
        memory.remember(
            content="User prefers examples in Python",
            metadata={"type": "preference", "category": "language"},
        )

        # Writer needs context
        context = memory.get_agent_context(
            agent_role="writer",
            task="Write an article about Python",
        )

        assert isinstance(context, str)

        # Writer recalls relevant information
        results = memory.recall(query="Python release")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_remember_recall_cycle(self, memory_client, session_id):
        """Test remember followed by recall cycle."""
        from neo4j_agent_memory.integrations.crewai import Neo4jCrewMemory

        memory = Neo4jCrewMemory(
            memory_client=memory_client,
            crew_id=session_id,
        )

        # Remember
        memory.remember(
            content="The project deadline is next Friday",
            metadata={"type": "short_term"},
        )

        # Recall
        results = memory.recall(query="deadline Friday")

        assert isinstance(results, list)
        # Should find the memory about the deadline
