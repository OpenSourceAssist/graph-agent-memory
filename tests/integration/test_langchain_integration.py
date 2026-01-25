"""Integration tests for LangChain integration."""

import pytest

from neo4j_agent_memory.memory.short_term import MessageRole

# Check if langchain is available
try:
    from langchain_core.memory import BaseMemory

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestNeo4jAgentMemory:
    """Test Neo4jAgentMemory LangChain integration."""

    @pytest.mark.asyncio
    async def test_memory_initialization(self, memory_client, session_id):
        """Test initializing Neo4jAgentMemory."""
        from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory

        memory = Neo4jAgentMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        assert memory.session_id == session_id
        assert memory.include_episodic is True
        assert memory.include_semantic is True
        assert memory.include_reasoning is True

    @pytest.mark.asyncio
    async def test_memory_variables(self, memory_client, session_id):
        """Test memory_variables property."""
        from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory

        memory = Neo4jAgentMemory(
            memory_client=memory_client,
            session_id=session_id,
        )

        variables = memory.memory_variables
        assert "history" in variables
        assert "context" in variables
        assert "preferences" in variables
        assert "similar_tasks" in variables

    @pytest.mark.asyncio
    async def test_memory_variables_filtered(self, memory_client, session_id):
        """Test memory_variables with filters."""
        from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory

        memory = Neo4jAgentMemory(
            memory_client=memory_client,
            session_id=session_id,
            include_episodic=False,
            include_reasoning=False,
        )

        variables = memory.memory_variables
        assert "history" not in variables
        assert "context" in variables
        assert "similar_tasks" not in variables

    @pytest.mark.asyncio
    async def test_save_and_load_context(self, memory_client, session_id):
        """Test saving and loading conversation context."""
        from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory

        memory = Neo4jAgentMemory(
            memory_client=memory_client,
            session_id=session_id,
            include_semantic=False,
            include_reasoning=False,
        )

        # Save context
        memory.save_context(
            {"input": "Hello, I am John"},
            {"output": "Hello John! How can I help you today?"},
        )

        # Load context
        variables = memory.load_memory_variables({"input": "What is my name?"})

        assert "history" in variables
        assert "John" in variables["history"]
        assert "Hello" in variables["history"]

    @pytest.mark.asyncio
    async def test_load_memory_with_semantic(self, memory_client, session_id):
        """Test loading memory with semantic context."""
        from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory
        from neo4j_agent_memory.memory.long_term import EntityType

        # Add some semantic data
        await memory_client.long_term.add_preference(
            category="food",
            preference="I love Italian food",
            generate_embedding=True,
        )
        await memory_client.long_term.add_entity(
            name="Italian Restaurant",
            entity_type=EntityType.CONCEPT,
            resolve=False,
            generate_embedding=True,
        )

        memory = Neo4jAgentMemory(
            memory_client=memory_client,
            session_id=session_id,
            include_episodic=False,
            include_reasoning=False,
        )

        variables = memory.load_memory_variables({"input": "food recommendations"})

        assert "context" in variables
        assert "preferences" in variables
        # Preferences should be a list
        assert isinstance(variables["preferences"], list)


@pytest.mark.integration
@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestNeo4jMemoryRetriever:
    """Test Neo4jMemoryRetriever LangChain integration."""

    @pytest.mark.asyncio
    async def test_retriever_initialization(self, memory_client, session_id):
        """Test initializing Neo4jMemoryRetriever."""
        from neo4j_agent_memory.integrations.langchain import Neo4jMemoryRetriever

        retriever = Neo4jMemoryRetriever(
            memory_client=memory_client,
            session_id=session_id,
        )

        assert retriever.session_id == session_id

    @pytest.mark.asyncio
    async def test_retriever_get_relevant_documents(self, memory_client, session_id):
        """Test retrieving relevant documents."""
        from neo4j_agent_memory.integrations.langchain import Neo4jMemoryRetriever

        # Add some data
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.USER,
            "I love hiking in the mountains",
            extract_entities=False,
            generate_embedding=True,
        )
        await memory_client.short_term.add_message(
            session_id,
            MessageRole.ASSISTANT,
            "That sounds wonderful! Do you have a favorite trail?",
            extract_entities=False,
            generate_embedding=True,
        )

        retriever = Neo4jMemoryRetriever(
            memory_client=memory_client,
            session_id=session_id,
        )

        # Get relevant documents
        docs = retriever.get_relevant_documents("outdoor activities")

        assert isinstance(docs, list)


@pytest.mark.integration
@pytest.mark.skipif(not LANGCHAIN_AVAILABLE, reason="LangChain not installed")
class TestLangChainIntegrationEdgeCases:
    """Test edge cases for LangChain integration."""

    @pytest.mark.asyncio
    async def test_empty_conversation_history(self, memory_client, session_id):
        """Test loading memory with no conversation history."""
        from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory

        memory = Neo4jAgentMemory(
            memory_client=memory_client,
            session_id=session_id,
            include_semantic=False,
            include_reasoning=False,
        )

        variables = memory.load_memory_variables({"input": "Hello"})

        assert "history" in variables
        # Empty history should be an empty string or contain no messages
        assert isinstance(variables["history"], str)

    @pytest.mark.asyncio
    async def test_multiple_save_contexts(self, memory_client, session_id):
        """Test saving multiple contexts in sequence."""
        from neo4j_agent_memory.integrations.langchain import Neo4jAgentMemory

        memory = Neo4jAgentMemory(
            memory_client=memory_client,
            session_id=session_id,
            include_semantic=False,
            include_reasoning=False,
        )

        # Save multiple exchanges
        exchanges = [
            ("Hello", "Hi there!"),
            ("My name is Alice", "Nice to meet you, Alice!"),
            ("What time is it?", "I don't have access to the current time."),
        ]

        for user_input, assistant_output in exchanges:
            memory.save_context(
                {"input": user_input},
                {"output": assistant_output},
            )

        # Load and verify
        variables = memory.load_memory_variables({"input": "recap"})

        assert "Alice" in variables["history"]
        assert "Hello" in variables["history"]
