"""Integration tests for example scripts.

These tests verify that example code works correctly against a real Neo4j database.
"""

import pytest

from neo4j_agent_memory.memory.long_term import EntityType
from neo4j_agent_memory.memory.procedural import ToolCallStatus
from neo4j_agent_memory.memory.short_term import MessageRole


@pytest.mark.integration
class TestBasicUsageExample:
    """Test basic_usage.py example patterns."""

    @pytest.mark.asyncio
    async def test_memory_client_context_manager(
        self, memory_settings, mock_embedder, mock_extractor, mock_resolver
    ):
        """Test MemoryClient as async context manager."""
        from neo4j_agent_memory import MemoryClient

        async with MemoryClient(
            memory_settings,
            embedder=mock_embedder,
            extractor=mock_extractor,
            resolver=mock_resolver,
        ) as client:
            # Basic connectivity check
            stats = await client.get_stats()
            assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_short_term_memory_operations(self, memory_client, session_id):
        """Test short-term memory operations from basic example."""
        # Add messages
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "Hello, my name is Alice",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "Hello Alice! How can I help you today?",
            extract_entities=False,
            generate_embedding=True,
        )

        # Get conversation
        conv = await memory_client.short_term.get_conversation(session_id)

        assert len(conv.messages) >= 2
        assert any("Alice" in m.content for m in conv.messages)

    @pytest.mark.asyncio
    async def test_long_term_memory_operations(self, memory_client):
        """Test long-term memory operations from basic example."""
        # Add entities
        entity, _ = await memory_client.long_term.add_entity(
            name="Alice Smith",
            entity_type=EntityType.PERSON,
            description="A software engineer",
            resolve=False,
            generate_embedding=True,
        )

        assert entity.name == "Alice Smith"
        assert entity.type == EntityType.PERSON

        # Add preferences
        pref = await memory_client.long_term.add_preference(
            category="programming",
            preference="Prefers Python over JavaScript",
            generate_embedding=True,
        )

        assert pref.category == "programming"

        # Add facts
        fact = await memory_client.long_term.add_fact(
            subject="Alice Smith",
            predicate="works_at",
            obj="Tech Corp",
            generate_embedding=True,
        )

        assert fact.subject == "Alice Smith"
        assert fact.predicate == "works_at"

    @pytest.mark.asyncio
    async def test_procedural_memory_operations(self, memory_client, session_id):
        """Test procedural memory operations from basic example."""
        # Start a reasoning trace
        trace = await memory_client.procedural.start_trace(
            session_id,
            task="Find nearby restaurants",
            generate_embedding=True,
        )

        assert trace.task == "Find nearby restaurants"

        # Add steps
        step = await memory_client.procedural.add_step(
            trace.id,
            thought="I need to search for restaurants",
            action="search_restaurants",
            generate_embedding=False,
        )

        assert step.thought == "I need to search for restaurants"

        # Record tool call
        tool_call = await memory_client.procedural.record_tool_call(
            step.id,
            tool_name="restaurant_api",
            arguments={"location": "downtown", "cuisine": "italian"},
            result={"restaurants": [{"name": "La Trattoria"}]},
            status=ToolCallStatus.SUCCESS,
        )

        assert tool_call.tool_name == "restaurant_api"

        # Complete trace
        completed = await memory_client.procedural.complete_trace(
            trace.id,
            outcome="Found 1 restaurant",
            success=True,
        )

        assert completed.success is True

    @pytest.mark.asyncio
    async def test_get_context(self, memory_client, session_id):
        """Test combined context retrieval."""
        # Add some data first
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I enjoy Italian cuisine",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.long_term.add_preference(
            category="food",
            preference="Loves pasta dishes",
            generate_embedding=True,
        )

        # Get context
        context = await memory_client.get_context(
            "restaurant recommendations",
            session_id=session_id,
        )

        assert isinstance(context, str)


@pytest.mark.integration
class TestEntityResolutionExample:
    """Test entity_resolution.py example patterns."""

    @pytest.mark.asyncio
    async def test_exact_match_resolver(self, memory_client):
        """Test ExactMatchResolver from example."""
        from neo4j_agent_memory.resolution.exact import ExactMatchResolver

        resolver = ExactMatchResolver()

        # Create existing entities
        await memory_client.long_term.add_entity(
            name="Google",
            entity_type=EntityType.ORGANIZATION,
            resolve=False,
            generate_embedding=False,
        )

        # Resolve against existing
        result = await resolver.resolve(
            "google",
            "ORGANIZATION",
            existing_entities=["Google", "Apple", "Microsoft"],
        )

        assert result.canonical_name == "Google"

    @pytest.mark.asyncio
    async def test_composite_resolver(self, mock_embedder):
        """Test CompositeResolver from example."""
        from neo4j_agent_memory.resolution.composite import CompositeResolver

        resolver = CompositeResolver(embedder=mock_embedder)

        result = await resolver.resolve(
            "New York City",
            "LOCATION",
            existing_entities=["New York", "Los Angeles", "Chicago"],
        )

        # Should match "New York" via fuzzy matching
        assert result is not None

    @pytest.mark.asyncio
    async def test_entity_with_resolution(self, memory_client):
        """Test adding entity with resolution enabled."""
        # Add initial entity
        await memory_client.long_term.add_entity(
            name="Microsoft Corporation",
            entity_type=EntityType.ORGANIZATION,
            resolve=False,
            generate_embedding=True,
        )

        # Add similar entity with resolution
        entity, _ = await memory_client.long_term.add_entity(
            name="microsoft corporation",
            entity_type=EntityType.ORGANIZATION,
            resolve=True,
            generate_embedding=True,
        )

        # Should resolve to the existing canonical name
        assert entity.canonical_name == "Microsoft Corporation"


@pytest.mark.integration
class TestLangChainAgentExample:
    """Test langchain_agent.py example patterns."""

    @pytest.mark.asyncio
    async def test_langchain_memory_setup(self, memory_client, session_id):
        """Test LangChain memory setup from example."""
        try:
            from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory

            memory = Neo4jAgentMemory(
                memory_client=memory_client,
                session_id=session_id,
                max_messages=10,
                max_preferences=5,
            )

            assert memory.session_id == session_id
            assert memory.max_messages == 10
        except ImportError:
            pytest.skip("LangChain not installed")

    @pytest.mark.asyncio
    async def test_langchain_retriever_setup(self, memory_client, session_id):
        """Test LangChain retriever setup from example."""
        try:
            from neo4j_agent_memory.integrations.langchain import Neo4jMemoryRetriever

            retriever = Neo4jMemoryRetriever(
                memory_client=memory_client,
                session_id=session_id,
                max_results=10,
            )

            assert retriever.session_id == session_id
        except ImportError:
            pytest.skip("LangChain not installed")


@pytest.mark.integration
class TestPydanticAIAgentExample:
    """Test pydantic_ai_agent.py example patterns."""

    @pytest.mark.asyncio
    async def test_memory_dependency_setup(self, memory_client, session_id):
        """Test MemoryDependency setup from example."""
        from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency

        deps = MemoryDependency(
            client=memory_client,
            session_id=session_id,
        )

        # Test get_context
        context = await deps.get_context("test query")
        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_memory_tools_creation(self, memory_client):
        """Test memory tools creation from example."""
        from neo4j_agent_memory.integrations.pydantic_ai import create_memory_tools

        tools = create_memory_tools(memory_client)

        assert len(tools) == 3
        assert all(callable(t) for t in tools)

    @pytest.mark.asyncio
    async def test_save_and_recall_preferences(self, memory_client, session_id):
        """Test save and recall preference workflow from example."""
        from neo4j_agent_memory.integrations.pydantic_ai import MemoryDependency

        deps = MemoryDependency(
            client=memory_client,
            session_id=session_id,
        )

        # Save preference
        await deps.add_preference(
            category="communication",
            preference="Prefers detailed explanations",
            context="When learning new concepts",
        )

        # Search preferences
        results = await deps.search_preferences("communication style")

        assert isinstance(results, list)


@pytest.mark.integration
class TestExampleCodeImports:
    """Test that example code modules can be imported."""

    def test_import_basic_types(self):
        """Test importing basic types used in examples."""
        from neo4j_agent_memory import MemoryClient, MemorySettings
        from neo4j_agent_memory.memory.long_term import EntityType
        from neo4j_agent_memory.memory.short_term import MessageRole

        assert MemoryClient is not None
        assert MemorySettings is not None
        assert MessageRole is not None
        assert EntityType is not None

    def test_import_resolution_types(self):
        """Test importing resolution types used in examples."""
        from neo4j_agent_memory.resolution.composite import CompositeResolver
        from neo4j_agent_memory.resolution.exact import ExactMatchResolver

        assert ExactMatchResolver is not None
        assert CompositeResolver is not None

    def test_import_integrations(self):
        """Test importing integration modules."""
        # Pydantic AI should always work
        from neo4j_agent_memory.integrations.pydantic_ai import (
            MemoryDependency,
            create_memory_tools,
        )

        assert MemoryDependency is not None
        assert create_memory_tools is not None

    def test_import_langchain_integration(self):
        """Test importing LangChain integration (if available)."""
        try:
            from neo4j_agent_memory.integrations.langchain import (
                Neo4jAgentMemory,
                Neo4jMemoryRetriever,
            )

            assert Neo4jAgentMemory is not None
            assert Neo4jMemoryRetriever is not None
        except ImportError:
            pytest.skip("LangChain not installed")
