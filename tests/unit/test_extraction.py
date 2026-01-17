"""Unit tests for entity extraction."""

import pytest

from neo4j_agent_memory.extraction.base import (
    ExtractedEntity,
    ExtractedPreference,
    ExtractedRelation,
    ExtractionResult,
    NoOpExtractor,
)


class TestExtractedEntity:
    """Tests for ExtractedEntity model."""

    def test_create_entity(self):
        """Test creating an extracted entity."""
        entity = ExtractedEntity(
            name="John Smith",
            type="PERSON",
            confidence=0.95,
        )

        assert entity.name == "John Smith"
        assert entity.type == "PERSON"
        assert entity.confidence == 0.95

    def test_normalized_name(self):
        """Test normalized name property."""
        entity = ExtractedEntity(
            name="  John Smith  ",
            type="PERSON",
        )

        assert entity.normalized_name == "john smith"

    def test_entity_with_span(self):
        """Test entity with character span."""
        entity = ExtractedEntity(
            name="Acme",
            type="ORGANIZATION",
            start_pos=10,
            end_pos=14,
        )

        assert entity.start_pos == 10
        assert entity.end_pos == 14


class TestExtractedRelation:
    """Tests for ExtractedRelation model."""

    def test_create_relation(self):
        """Test creating an extracted relation."""
        relation = ExtractedRelation(
            source="John",
            target="Acme",
            relation_type="works_at",
        )

        assert relation.source == "John"
        assert relation.target == "Acme"
        assert relation.relation_type == "works_at"

    def test_as_triple(self):
        """Test as_triple property."""
        relation = ExtractedRelation(
            source="Alice",
            target="Bob",
            relation_type="knows",
        )

        assert relation.as_triple == ("Alice", "knows", "Bob")


class TestExtractionResult:
    """Tests for ExtractionResult model."""

    def test_create_result(self):
        """Test creating an extraction result."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="John", type="PERSON"),
                ExtractedEntity(name="Acme", type="ORGANIZATION"),
            ],
            relations=[ExtractedRelation(source="John", target="Acme", relation_type="works_at")],
        )

        assert result.entity_count == 2
        assert result.relation_count == 1

    def test_entities_by_type(self):
        """Test grouping entities by type."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="John", type="PERSON"),
                ExtractedEntity(name="Jane", type="PERSON"),
                ExtractedEntity(name="Acme", type="ORGANIZATION"),
            ]
        )

        by_type = result.entities_by_type()

        assert len(by_type["PERSON"]) == 2
        assert len(by_type["ORGANIZATION"]) == 1

    def test_get_entities_of_type(self):
        """Test getting entities of a specific type."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="John", type="PERSON"),
                ExtractedEntity(name="Acme", type="ORGANIZATION"),
            ]
        )

        people = result.get_entities_of_type("PERSON")
        orgs = result.get_entities_of_type("organization")  # Case insensitive

        assert len(people) == 1
        assert people[0].name == "John"
        assert len(orgs) == 1


class TestNoOpExtractor:
    """Tests for NoOpExtractor."""

    @pytest.mark.asyncio
    async def test_noop_extraction(self):
        """Test that NoOpExtractor returns empty result."""
        extractor = NoOpExtractor()

        result = await extractor.extract("Hello, I'm John from Acme")

        assert result.entity_count == 0
        assert result.relation_count == 0
        assert result.preference_count == 0
        assert result.source_text == "Hello, I'm John from Acme"
