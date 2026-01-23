"""Tests for POLE+O schema configuration."""

from neo4j_agent_memory.schema.models import (
    EntitySchemaConfig,
    EntityTypeConfig,
    POLEOEntityType,
    RelationTypeConfig,
    create_schema_for_types,
    get_default_schema,
    get_legacy_schema,
)


class TestPOLEOEntityType:
    """Tests for POLE+O entity type enum."""

    def test_poleo_types_exist(self):
        """Test that all POLE+O types are defined."""
        assert POLEOEntityType.PERSON.value == "PERSON"
        assert POLEOEntityType.OBJECT.value == "OBJECT"
        assert POLEOEntityType.LOCATION.value == "LOCATION"
        assert POLEOEntityType.EVENT.value == "EVENT"
        assert POLEOEntityType.ORGANIZATION.value == "ORGANIZATION"

    def test_all_types(self):
        """Test that we have exactly 5 POLE+O types."""
        assert len(POLEOEntityType) == 5


class TestEntityTypeConfig:
    """Tests for entity type configuration."""

    def test_create_entity_type_config(self):
        """Test creating entity type configuration."""
        config = EntityTypeConfig(
            name="PERSON",
            description="A person",
            subtypes=["INDIVIDUAL", "ALIAS"],
        )
        assert config.name == "PERSON"
        assert config.description == "A person"
        assert "INDIVIDUAL" in config.subtypes
        assert "ALIAS" in config.subtypes

    def test_default_values(self):
        """Test default values for entity type config."""
        config = EntityTypeConfig(name="TEST")
        assert config.description is None
        assert config.subtypes == []
        assert config.attributes == []  # attributes is a list, not a dict


class TestRelationTypeConfig:
    """Tests for relation type configuration."""

    def test_create_relation_config(self):
        """Test creating relation type configuration."""
        config = RelationTypeConfig(
            name="WORKS_AT",
            source_types=["PERSON"],
            target_types=["ORGANIZATION"],
        )
        assert config.name == "WORKS_AT"
        assert "PERSON" in config.source_types
        assert "ORGANIZATION" in config.target_types

    def test_relation_properties(self):
        """Test relation with properties configuration."""
        config = RelationTypeConfig(
            name="WORKS_AT",
            source_types=["PERSON"],
            target_types=["ORGANIZATION"],
            properties=["position", "start_date"],
        )
        assert "position" in config.properties
        assert "start_date" in config.properties


class TestEntitySchemaConfig:
    """Tests for entity schema configuration."""

    def test_create_schema_config(self):
        """Test creating schema configuration."""
        config = EntitySchemaConfig(
            name="test_schema",
            entity_types=[
                EntityTypeConfig(name="PERSON"),
                EntityTypeConfig(name="LOCATION"),
            ],
        )
        assert config.name == "test_schema"
        assert len(config.entity_types) == 2
        assert config.get_entity_type_names() == ["PERSON", "LOCATION"]

    def test_is_valid_type(self):
        """Test checking if entity type is valid."""
        config = EntitySchemaConfig(
            entity_types=[EntityTypeConfig(name="PERSON")],
            strict_types=True,
        )
        assert config.is_valid_type("PERSON") is True
        assert config.is_valid_type("person") is True  # Case insensitive
        assert config.is_valid_type("UNKNOWN") is False

    def test_normalize_type(self):
        """Test normalizing entity type."""
        config = EntitySchemaConfig(
            entity_types=[EntityTypeConfig(name="PERSON", subtypes=["INDIVIDUAL", "ALIAS"])],
        )
        assert config.normalize_type("person") == "PERSON"
        assert config.normalize_type("PERSON") == "PERSON"
        assert config.normalize_type("Person") == "PERSON"

    def test_get_subtypes(self):
        """Test getting subtypes for entity type."""
        config = EntitySchemaConfig(
            entity_types=[
                EntityTypeConfig(name="PERSON", subtypes=["INDIVIDUAL", "ALIAS"]),
                EntityTypeConfig(name="OBJECT", subtypes=["VEHICLE", "DEVICE"]),
            ],
        )
        assert config.get_subtypes("PERSON") == ["INDIVIDUAL", "ALIAS"]
        assert config.get_subtypes("OBJECT") == ["VEHICLE", "DEVICE"]
        assert config.get_subtypes("UNKNOWN") == []


class TestGetDefaultSchema:
    """Tests for default POLE+O schema."""

    def test_default_schema_is_poleo(self):
        """Test that default schema is POLE+O."""
        schema = get_default_schema()
        assert schema.name == "poleo"
        types = schema.get_entity_type_names()
        assert "PERSON" in types
        assert "OBJECT" in types
        assert "LOCATION" in types
        assert "EVENT" in types
        assert "ORGANIZATION" in types

    def test_person_subtypes(self):
        """Test PERSON subtypes in default schema."""
        schema = get_default_schema()
        subtypes = schema.get_subtypes("PERSON")
        assert "INDIVIDUAL" in subtypes
        assert "ALIAS" in subtypes
        assert "PERSONA" in subtypes

    def test_object_subtypes(self):
        """Test OBJECT subtypes in default schema."""
        schema = get_default_schema()
        subtypes = schema.get_subtypes("OBJECT")
        assert "VEHICLE" in subtypes
        assert "PHONE" in subtypes
        assert "EMAIL" in subtypes
        assert "DOCUMENT" in subtypes

    def test_location_subtypes(self):
        """Test LOCATION subtypes in default schema."""
        schema = get_default_schema()
        subtypes = schema.get_subtypes("LOCATION")
        assert "ADDRESS" in subtypes
        assert "CITY" in subtypes
        assert "COUNTRY" in subtypes

    def test_event_subtypes(self):
        """Test EVENT subtypes in default schema."""
        schema = get_default_schema()
        subtypes = schema.get_subtypes("EVENT")
        assert "INCIDENT" in subtypes
        assert "MEETING" in subtypes
        assert "TRANSACTION" in subtypes

    def test_organization_subtypes(self):
        """Test ORGANIZATION subtypes in default schema."""
        schema = get_default_schema()
        subtypes = schema.get_subtypes("ORGANIZATION")
        assert "COMPANY" in subtypes
        assert "NONPROFIT" in subtypes
        assert "GOVERNMENT" in subtypes

    def test_default_relation_types(self):
        """Test default relation types in POLE+O schema."""
        schema = get_default_schema()
        assert len(schema.relation_types) > 0

        # Find EMPLOYED_BY relation
        employed_by = next((r for r in schema.relation_types if r.name == "EMPLOYED_BY"), None)
        assert employed_by is not None
        assert "PERSON" in employed_by.source_types
        assert "ORGANIZATION" in employed_by.target_types


class TestGetLegacySchema:
    """Tests for legacy schema compatibility."""

    def test_legacy_schema_types(self):
        """Test that legacy schema has backward-compatible types."""
        schema = get_legacy_schema()
        types = schema.get_entity_type_names()
        assert "PERSON" in types
        assert "ORGANIZATION" in types
        assert "LOCATION" in types
        assert "EVENT" in types
        # Legacy types
        assert "CONCEPT" in types
        assert "EMOTION" in types
        assert "PREFERENCE" in types
        assert "FACT" in types


class TestCreateSchemaForTypes:
    """Tests for custom schema creation."""

    def test_create_custom_schema(self):
        """Test creating schema with custom types."""
        schema = create_schema_for_types(["PERSON", "CAR", "CITY"])
        assert schema.name == "custom"
        types = schema.get_entity_type_names()
        assert "PERSON" in types
        assert "CAR" in types
        assert "CITY" in types

    def test_custom_schema_no_subtypes(self):
        """Test that custom types don't have subtypes by default."""
        schema = create_schema_for_types(["CUSTOM_TYPE"])
        assert schema.get_subtypes("CUSTOM_TYPE") == []
