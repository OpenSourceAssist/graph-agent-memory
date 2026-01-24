"""Unit tests for entity extraction."""

import pytest

from neo4j_agent_memory.extraction.base import (
    ENTITY_STOPWORDS,
    ExtractedEntity,
    ExtractedPreference,
    ExtractedRelation,
    ExtractionResult,
    NoOpExtractor,
    is_valid_entity_name,
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


class TestEntityStopwords:
    """Tests for entity stopword filtering."""

    def test_stopwords_set_exists(self):
        """Test that ENTITY_STOPWORDS is a non-empty frozenset."""
        assert isinstance(ENTITY_STOPWORDS, frozenset)
        assert len(ENTITY_STOPWORDS) > 0

    def test_common_pronouns_in_stopwords(self):
        """Test that common pronouns are in stopwords."""
        pronouns = ["i", "me", "my", "you", "your", "he", "she", "they", "them", "it", "we"]
        for pronoun in pronouns:
            assert pronoun in ENTITY_STOPWORDS, f"'{pronoun}' should be in stopwords"

    def test_common_verbs_in_stopwords(self):
        """Test that common verbs are in stopwords."""
        verbs = ["is", "are", "was", "were", "be", "been", "have", "has", "do", "does", "did"]
        for verb in verbs:
            assert verb in ENTITY_STOPWORDS, f"'{verb}' should be in stopwords"

    def test_articles_in_stopwords(self):
        """Test that articles are in stopwords."""
        articles = ["a", "an", "the"]
        for article in articles:
            assert article in ENTITY_STOPWORDS, f"'{article}' should be in stopwords"


class TestIsValidEntityName:
    """Tests for is_valid_entity_name function."""

    def test_valid_person_names(self):
        """Test that valid person names are accepted."""
        valid_names = ["John Smith", "Alice", "Bob Johnson", "María García", "李明"]
        for name in valid_names:
            assert is_valid_entity_name(name), f"'{name}' should be valid"

    def test_valid_organization_names(self):
        """Test that valid organization names are accepted."""
        valid_names = ["Acme Corp", "Google", "United Nations", "NASA"]
        for name in valid_names:
            assert is_valid_entity_name(name), f"'{name}' should be valid"

    def test_valid_location_names(self):
        """Test that valid location names are accepted."""
        valid_names = ["New York", "Paris", "Tokyo", "Mount Everest"]
        for name in valid_names:
            assert is_valid_entity_name(name), f"'{name}' should be valid"

    def test_stopwords_rejected(self):
        """Test that stopwords are rejected."""
        invalid_names = ["they", "them", "you", "me", "it", "we", "he", "she"]
        for name in invalid_names:
            assert not is_valid_entity_name(name), f"'{name}' should be invalid (stopword)"

    def test_case_insensitive_stopword_check(self):
        """Test that stopword check is case insensitive."""
        invalid_names = ["They", "THEM", "You", "ME", "It", "WE"]
        for name in invalid_names:
            assert not is_valid_entity_name(name), (
                f"'{name}' should be invalid (stopword, case insensitive)"
            )

    def test_short_names_rejected(self):
        """Test that single-character names are rejected."""
        invalid_names = ["a", "b", "x", "1", "?"]
        for name in invalid_names:
            assert not is_valid_entity_name(name), f"'{name}' should be invalid (too short)"

    def test_numeric_values_rejected(self):
        """Test that purely numeric values are rejected."""
        invalid_names = ["10", "123", "45.67", "100,000", "50%", "12 34"]
        for name in invalid_names:
            assert not is_valid_entity_name(name), f"'{name}' should be invalid (numeric)"

    def test_punctuation_only_rejected(self):
        """Test that punctuation-only strings are rejected."""
        invalid_names = ["...", "---", "!!!", "???", "..."]
        for name in invalid_names:
            assert not is_valid_entity_name(name), f"'{name}' should be invalid (punctuation only)"

    def test_whitespace_handling(self):
        """Test that names with extra whitespace are handled."""
        # Should still be valid after stripping
        assert is_valid_entity_name("  John Smith  ")
        # Empty after stripping should be invalid
        assert not is_valid_entity_name("   ")
        assert not is_valid_entity_name("")

    def test_mixed_alphanumeric_accepted(self):
        """Test that mixed alphanumeric names are accepted."""
        valid_names = ["Apollo 11", "iPhone 15", "Building 42", "Route 66"]
        for name in valid_names:
            assert is_valid_entity_name(name), f"'{name}' should be valid (mixed alphanumeric)"


class TestExtractionResultFilterInvalidEntities:
    """Tests for ExtractionResult.filter_invalid_entities method."""

    def test_filter_removes_stopword_entities(self):
        """Test that filter removes entities with stopword names."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="John Smith", type="PERSON"),
                ExtractedEntity(name="they", type="PERSON"),
                ExtractedEntity(name="Acme", type="ORGANIZATION"),
                ExtractedEntity(name="them", type="PERSON"),
            ]
        )

        filtered = result.filter_invalid_entities()

        assert filtered.entity_count == 2
        entity_names = [e.name for e in filtered.entities]
        assert "John Smith" in entity_names
        assert "Acme" in entity_names
        assert "they" not in entity_names
        assert "them" not in entity_names

    def test_filter_removes_numeric_entities(self):
        """Test that filter removes entities with numeric names."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="John", type="PERSON"),
                ExtractedEntity(name="10", type="OBJECT"),
                ExtractedEntity(name="123.45", type="OBJECT"),
            ]
        )

        filtered = result.filter_invalid_entities()

        assert filtered.entity_count == 1
        assert filtered.entities[0].name == "John"

    def test_filter_preserves_valid_relations(self):
        """Test that filter preserves relations between valid entities."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="John", type="PERSON"),
                ExtractedEntity(name="Acme", type="ORGANIZATION"),
                ExtractedEntity(name="they", type="PERSON"),
            ],
            relations=[
                ExtractedRelation(source="John", target="Acme", relation_type="works_at"),
            ],
        )

        filtered = result.filter_invalid_entities()

        assert filtered.relation_count == 1
        assert filtered.relations[0].source == "John"
        assert filtered.relations[0].target == "Acme"

    def test_filter_removes_relations_with_invalid_entities(self):
        """Test that filter removes relations referencing invalid entities."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="John", type="PERSON"),
                ExtractedEntity(name="they", type="PERSON"),
            ],
            relations=[
                ExtractedRelation(source="they", target="John", relation_type="knows"),
            ],
        )

        filtered = result.filter_invalid_entities()

        # Relation should be removed because "they" is filtered out
        assert filtered.relation_count == 0

    def test_filter_preserves_preferences(self):
        """Test that filter preserves preferences."""
        result = ExtractionResult(
            entities=[
                ExtractedEntity(name="they", type="PERSON"),
            ],
            preferences=[
                ExtractedPreference(
                    category="food",
                    preference="likes coffee",
                ),
            ],
        )

        filtered = result.filter_invalid_entities()

        assert filtered.entity_count == 0
        assert filtered.preference_count == 1

    def test_filter_returns_new_instance(self):
        """Test that filter returns a new ExtractionResult instance."""
        result = ExtractionResult(
            entities=[ExtractedEntity(name="John", type="PERSON")],
        )

        filtered = result.filter_invalid_entities()

        assert filtered is not result
        assert filtered.entities is not result.entities

    def test_filter_empty_result(self):
        """Test filtering an empty result."""
        result = ExtractionResult(entities=[])

        filtered = result.filter_invalid_entities()

        assert filtered.entity_count == 0


class TestDomainSchemas:
    """Tests for GLiNER2 domain schemas."""

    def test_domain_schema_model(self):
        """Test DomainSchema model creation."""
        from neo4j_agent_memory.extraction.gliner_extractor import DomainSchema

        schema = DomainSchema(
            name="test",
            entity_types={
                "person": "A human individual",
                "company": "A business organization",
            },
        )

        assert schema.name == "test"
        assert len(schema.entity_types) == 2
        assert "person" in schema.entity_types
        assert schema.entity_types["person"] == "A human individual"

    def test_domain_schema_with_relations(self):
        """Test DomainSchema model with relation types."""
        from neo4j_agent_memory.extraction.gliner_extractor import DomainSchema

        schema = DomainSchema(
            name="test",
            entity_types={"person": "A person"},
            relation_types={
                "works_at": "Employment relationship",
                "knows": "Personal acquaintance",
            },
        )

        assert len(schema.relation_types) == 2
        assert "works_at" in schema.relation_types

    def test_get_schema_valid(self):
        """Test get_schema with valid schema name."""
        from neo4j_agent_memory.extraction.gliner_extractor import get_schema

        schema = get_schema("poleo")

        assert schema.name == "poleo"
        assert "person" in schema.entity_types
        assert "organization" in schema.entity_types
        assert "location" in schema.entity_types
        assert "event" in schema.entity_types
        assert "object" in schema.entity_types

    def test_get_schema_invalid(self):
        """Test get_schema with invalid schema name."""
        from neo4j_agent_memory.extraction.gliner_extractor import get_schema

        with pytest.raises(ValueError, match="Unknown schema"):
            get_schema("nonexistent")

    def test_list_schemas(self):
        """Test list_schemas returns all available schemas."""
        from neo4j_agent_memory.extraction.gliner_extractor import list_schemas

        schemas = list_schemas()

        assert isinstance(schemas, list)
        assert "poleo" in schemas
        assert "podcast" in schemas
        assert "news" in schemas
        assert "scientific" in schemas
        assert "business" in schemas
        assert "entertainment" in schemas
        assert "medical" in schemas
        assert "legal" in schemas

    def test_podcast_schema_entity_types(self):
        """Test that podcast schema has appropriate entity types."""
        from neo4j_agent_memory.extraction.gliner_extractor import get_schema

        schema = get_schema("podcast")

        assert schema.name == "podcast"
        # Check podcast-specific entity types
        assert "person" in schema.entity_types
        assert "company" in schema.entity_types
        assert "product" in schema.entity_types
        assert "concept" in schema.entity_types
        assert "book" in schema.entity_types
        assert "technology" in schema.entity_types

    def test_all_schemas_have_descriptions(self):
        """Test that all entity types have descriptions."""
        from neo4j_agent_memory.extraction.gliner_extractor import DOMAIN_SCHEMAS

        for name, schema in DOMAIN_SCHEMAS.items():
            for entity_type, description in schema.entity_types.items():
                assert isinstance(description, str), (
                    f"{name}/{entity_type} should have string description"
                )
                assert len(description) > 10, (
                    f"{name}/{entity_type} description should be meaningful"
                )


class TestGLiNERConfig:
    """Tests for GLiNERConfig."""

    def test_default_config(self):
        """Test default GLiNER configuration."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNERConfig

        config = GLiNERConfig()

        assert config.model == "gliner-community/gliner_medium-v2.5"
        assert config.threshold == 0.5
        assert config.device == "cpu"
        assert config.schema_name is None

    def test_config_with_schema(self):
        """Test GLiNER configuration with schema name."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNERConfig

        config = GLiNERConfig(schema_name="podcast")

        assert config.schema_name == "podcast"

    def test_config_with_custom_labels(self):
        """Test GLiNER configuration with custom labels."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNERConfig

        config = GLiNERConfig(
            entity_labels={"person": "A person", "company": "A business"},
        )

        assert isinstance(config.entity_labels, dict)
        assert "person" in config.entity_labels


class TestGLiNERExtractorClassMethods:
    """Tests for GLiNEREntityExtractor class methods (no model loading)."""

    def test_for_schema_creates_extractor(self):
        """Test for_schema class method creates extractor with schema."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        # This creates the extractor but doesn't load the model
        extractor = GLiNEREntityExtractor.for_schema("podcast")

        assert extractor._use_descriptions is True
        assert isinstance(extractor.entity_labels, dict)
        assert "person" in extractor.entity_labels

    def test_for_poleo_creates_extractor(self):
        """Test for_poleo class method creates extractor."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        extractor = GLiNEREntityExtractor.for_poleo()

        assert extractor._use_descriptions is True  # Uses descriptions by default

    def test_for_poleo_without_descriptions(self):
        """Test for_poleo with use_descriptions=False."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        extractor = GLiNEREntityExtractor.for_poleo(use_descriptions=False)

        assert extractor._use_descriptions is False
        assert isinstance(extractor.entity_labels, list)

    def test_extractor_with_dict_labels(self):
        """Test extractor with dict labels enables descriptions."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        extractor = GLiNEREntityExtractor(
            entity_labels={
                "person": "A human individual",
                "company": "A business organization",
            }
        )

        assert extractor._use_descriptions is True

    def test_extractor_with_list_labels(self):
        """Test extractor with list labels disables descriptions."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        extractor = GLiNEREntityExtractor(entity_labels=["person", "company", "location"])

        assert extractor._use_descriptions is False

    def test_label_mapping(self):
        """Test label mapping to POLE+O types."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        extractor = GLiNEREntityExtractor()

        # Test standard mappings
        assert extractor._map_label_to_poleo("person") == ("PERSON", None)
        assert extractor._map_label_to_poleo("company") == ("ORGANIZATION", "COMPANY")
        assert extractor._map_label_to_poleo("city") == ("LOCATION", "CITY")
        assert extractor._map_label_to_poleo("meeting") == ("EVENT", "MEETING")
        assert extractor._map_label_to_poleo("product") == ("OBJECT", "PRODUCT")

    def test_custom_label_mapping(self):
        """Test adding custom label mapping."""
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        extractor = GLiNEREntityExtractor()
        extractor.add_label_mapping("custom_type", "OBJECT", "CUSTOM")

        assert extractor._map_label_to_poleo("custom_type") == ("OBJECT", "CUSTOM")

    def test_from_config_with_schema(self):
        """Test from_config with schema_name."""
        from neo4j_agent_memory.extraction.gliner_extractor import (
            GLiNERConfig,
            GLiNEREntityExtractor,
        )

        config = GLiNERConfig(schema_name="podcast")
        extractor = GLiNEREntityExtractor.from_config(config)

        assert extractor._use_descriptions is True
        assert "person" in extractor.entity_labels
