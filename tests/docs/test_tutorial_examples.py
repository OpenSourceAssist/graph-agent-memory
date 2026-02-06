"""Tests for tutorial code examples.

These tests execute code from tutorials against a test database to verify
the examples work as documented.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

# Import markers from main conftest if available
pytestmark = [pytest.mark.docs, pytest.mark.integration]


@pytest.mark.asyncio
class TestFirstAgentMemoryTutorial:
    """Test code from tutorials/first-agent-memory.adoc.

    This tutorial covers:
    - Creating a MemoryClient
    - Storing messages
    - Retrieving messages
    - Entity extraction basics
    """

    async def test_create_memory_client(self, memory_client):
        """Test Step 4: Create Your First Memory Client."""
        # The memory_client fixture provides an initialized client
        assert memory_client is not None
        assert memory_client.short_term is not None
        assert memory_client.long_term is not None
        assert memory_client.reasoning is not None

    async def test_store_first_message(self, memory_client):
        """Test storing a message as shown in the tutorial."""
        session_id = f"tutorial-test-{uuid4()}"

        # From the tutorial: Store a test message
        message = await memory_client.short_term.add_message(
            session_id=session_id,
            role="user",
            content="Hello! I'm looking for running shoes. I really like Nike products.",
        )

        assert message is not None
        assert message.id is not None
        assert (
            message.content == "Hello! I'm looking for running shoes. I really like Nike products."
        )

    async def test_retrieve_messages(self, memory_client):
        """Test retrieving messages from a session."""
        session_id = f"tutorial-test-{uuid4()}"

        # Store messages
        await memory_client.short_term.add_message(
            session_id=session_id,
            role="user",
            content="I need new running shoes",
        )
        await memory_client.short_term.add_message(
            session_id=session_id,
            role="assistant",
            content="I can help you find running shoes!",
        )

        # Retrieve as shown in tutorial
        conversation = await memory_client.short_term.get_conversation(
            session_id=session_id,
        )

        assert len(conversation.messages) == 2
        assert conversation.messages[0].role.value == "user"
        assert conversation.messages[1].role.value == "assistant"

    async def test_search_messages(self, memory_client):
        """Test semantic search as shown in the tutorial."""
        session_id = f"tutorial-test-{uuid4()}"

        # Store some messages
        await memory_client.short_term.add_message(
            session_id=session_id,
            role="user",
            content="I'm interested in trail running shoes for mountain hiking",
        )
        await memory_client.short_term.add_message(
            session_id=session_id,
            role="user",
            content="What's the weather like today?",
        )

        # Search for relevant messages
        results = await memory_client.short_term.search_messages(
            query="running shoes",
            session_id=session_id,
            limit=5,
        )

        # Should find the running shoes message
        assert len(results) >= 1


@pytest.mark.asyncio
class TestConversationMemoryTutorial:
    """Test code from tutorials/conversation-memory.adoc.

    This tutorial covers:
    - Building a shopping assistant
    - Storing user preferences
    - Multi-session persistence
    """

    async def test_store_user_preferences(self, memory_client):
        """Test storing user preferences for personalization."""
        # Store preferences as shown in the tutorial
        await memory_client.long_term.add_preference(
            category="brand",
            preference="Prefers Nike products",
            context="Shopping for athletic wear",
        )

        await memory_client.long_term.add_preference(
            category="size",
            preference="Wears size 10 running shoes",
        )

        await memory_client.long_term.add_preference(
            category="budget",
            preference="Budget around $150 for shoes",
        )

        # Search preferences
        prefs = await memory_client.long_term.search_preferences(
            "nike shoes",
            limit=5,
        )

        assert len(prefs) >= 1

    async def test_multi_session_persistence(self, memory_client):
        """Test that memory persists across sessions."""
        user_id = f"user-{uuid4()}"
        session1 = f"session1-{uuid4()}"
        session2 = f"session2-{uuid4()}"

        # Session 1: Store some information
        await memory_client.short_term.add_message(
            session_id=session1,
            role="user",
            content="My name is Alex and I love trail running",
            metadata={"user_id": user_id},
        )

        # Session 2: Should be able to find information from session 1
        await memory_client.short_term.add_message(
            session_id=session2,
            role="user",
            content="I'm back for more recommendations",
            metadata={"user_id": user_id},
        )

        # Search across sessions
        results = await memory_client.short_term.search_messages(
            query="trail running",
            limit=10,
        )

        # Should find the message from session 1
        found = any("trail running" in r.content for r in results)
        assert found, "Could not find cross-session message"


@pytest.mark.asyncio
class TestKnowledgeGraphTutorial:
    """Test code from tutorials/knowledge-graph.adoc.

    This tutorial covers:
    - Processing documents
    - Entity extraction
    - Building knowledge graphs
    - Querying relationships
    """

    async def test_add_entities(self, memory_client):
        """Test adding entities to the knowledge graph."""
        # Add entities as shown in the tutorial
        await memory_client.long_term.add_entity(
            name="Apple Inc.",
            entity_type="ORGANIZATION",
            description="Technology company known for iPhone and Mac",
        )

        await memory_client.long_term.add_entity(
            name="Tim Cook",
            entity_type="PERSON",
            description="CEO of Apple Inc.",
        )

        await memory_client.long_term.add_entity(
            name="Cupertino",
            entity_type="LOCATION",
            description="City in California, headquarters of Apple",
        )

        # Search for entities
        results = await memory_client.long_term.search_entities(
            query="Apple CEO",
            limit=5,
        )

        assert len(results) >= 1

    async def test_add_facts(self, memory_client):
        """Test adding facts to connect entities."""
        # Add entities first
        await memory_client.long_term.add_entity(
            name="Microsoft",
            entity_type="ORGANIZATION",
        )

        await memory_client.long_term.add_entity(
            name="Satya Nadella",
            entity_type="PERSON",
        )

        # Add fact connecting them
        await memory_client.long_term.add_fact(
            subject="Satya Nadella",
            predicate="leads",
            obj="Microsoft",
        )

        # The fact should be stored
        # (Verification depends on API - this tests the basic flow)

    async def test_process_document_text(self, memory_client):
        """Test processing a document with entity extraction."""
        session_id = f"doc-test-{uuid4()}"

        # From the tutorial: Process a financial document
        document = """
        In Q4 2024, Tesla reported strong revenue growth driven by Model Y sales.
        CEO Elon Musk announced plans to expand production at the Austin Gigafactory.
        The company expects to deliver 2 million vehicles in 2025.
        """

        # Store as a message (entity extraction happens automatically if enabled)
        message = await memory_client.short_term.add_message(
            session_id=session_id,
            role="user",
            content=document,
            metadata={"type": "document", "source": "financial_report"},
        )

        assert message is not None


@pytest.mark.asyncio
class TestTutorialPatterns:
    """Test common patterns used across tutorials."""

    async def test_context_retrieval_pattern(self, memory_client):
        """Test the get_context pattern shown in tutorials."""
        session_id = f"context-test-{uuid4()}"

        # Store some context
        await memory_client.short_term.add_message(
            session_id=session_id,
            role="user",
            content="I'm a software developer interested in AI and machine learning",
        )

        await memory_client.long_term.add_preference(
            category="interests",
            preference="Interested in AI and machine learning",
        )

        # Get combined context as shown in tutorials
        context = await memory_client.get_context(
            query="AI recommendations",
            session_id=session_id,
        )

        assert isinstance(context, str)
        assert len(context) > 0

    async def test_reasoning_trace_pattern(self, memory_client):
        """Test the reasoning trace pattern from tutorials."""
        session_id = f"reasoning-test-{uuid4()}"

        # Start a reasoning trace
        trace = await memory_client.reasoning.start_trace(
            session_id=session_id,
            task="Process user request for product recommendation",
        )

        assert trace is not None
        assert trace.id is not None

        # Add a reasoning step
        step = await memory_client.reasoning.add_step(
            trace_id=trace.id,
            thought="User is looking for product recommendations",
            action="analyze_preferences",
        )

        assert step is not None

        # Complete the trace
        completed = await memory_client.reasoning.complete_trace(
            trace_id=trace.id,
            outcome="Provided personalized recommendations",
            success=True,
        )

        assert completed.success is True
