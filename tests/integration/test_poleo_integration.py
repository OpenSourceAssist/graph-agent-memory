"""Integration tests for POLE+O data model."""

from uuid import uuid4

import pytest

from neo4j_agent_memory.memory.long_term import (
    POLEO_TYPES,
    Entity,
    EntityType,
    LongTermMemory,
    normalize_entity_type,
    parse_entity_type,
)


class TestPOLEOEntityTypes:
    """Tests for POLE+O entity type handling."""

    def test_normalize_entity_type_string(self):
        """Test normalizing string entity types."""
        assert normalize_entity_type("person") == "PERSON"
        assert normalize_entity_type("PERSON") == "PERSON"
        assert normalize_entity_type("Person") == "PERSON"

    def test_normalize_entity_type_enum(self):
        """Test normalizing EntityType enum."""
        assert normalize_entity_type(EntityType.PERSON) == "PERSON"
        assert normalize_entity_type(EntityType.ORGANIZATION) == "ORGANIZATION"

    def test_parse_entity_type_simple(self):
        """Test parsing simple entity types."""
        entity_type, subtype = parse_entity_type("PERSON")
        assert entity_type == "PERSON"
        assert subtype is None

    def test_parse_entity_type_with_subtype(self):
        """Test parsing entity types with subtypes."""
        entity_type, subtype = parse_entity_type("OBJECT:VEHICLE")
        assert entity_type == "OBJECT"
        assert subtype == "VEHICLE"

    def test_parse_entity_type_case_insensitive(self):
        """Test that parsing is case insensitive."""
        entity_type, subtype = parse_entity_type("location:address")
        assert entity_type == "LOCATION"
        assert subtype == "ADDRESS"


class TestPOLEOEntity:
    """Tests for POLE+O Entity model."""

    def test_entity_with_subtype(self):
        """Test creating entity with subtype."""
        entity = Entity(
            id=uuid4(),
            name="Ford F-150",
            type="OBJECT",
            subtype="VEHICLE",
            description="A pickup truck",
        )
        assert entity.type == "OBJECT"
        assert entity.subtype == "VEHICLE"
        assert entity.full_type == "OBJECT:VEHICLE"

    def test_entity_without_subtype(self):
        """Test creating entity without subtype."""
        entity = Entity(
            id=uuid4(),
            name="John Doe",
            type="PERSON",
        )
        assert entity.type == "PERSON"
        assert entity.subtype is None
        assert entity.full_type == "PERSON"

    def test_entity_with_attributes(self):
        """Test creating entity with attributes."""
        entity = Entity(
            id=uuid4(),
            name="iPhone 15",
            type="OBJECT",
            subtype="DEVICE",
            attributes={
                "brand": "Apple",
                "model": "iPhone 15",
                "color": "blue",
            },
        )
        assert entity.attributes["brand"] == "Apple"
        assert entity.attributes["color"] == "blue"

    def test_entity_with_aliases(self):
        """Test creating entity with aliases."""
        entity = Entity(
            id=uuid4(),
            name="John Smith",
            type="PERSON",
            aliases=["Johnny", "J. Smith", "John S."],
        )
        assert "Johnny" in entity.aliases
        assert len(entity.aliases) == 3

    def test_entity_type_backward_compat(self):
        """Test backward compatibility with EntityType enum."""
        entity = Entity(
            id=uuid4(),
            name="Test",
            type="PERSON",
        )
        assert entity.entity_type == EntityType.PERSON

        # Unknown type should return None
        entity2 = Entity(
            id=uuid4(),
            name="Test",
            type="CUSTOM_TYPE",
        )
        assert entity2.entity_type is None


@pytest.mark.integration
class TestLongTermMemoryPOLEO:
    """Integration tests for long-term memory with POLE+O types."""

    @pytest.mark.asyncio
    async def test_add_entity_with_string_type(self, long_term_memory: LongTermMemory):
        """Test adding entity with string type."""
        entity, _ = await long_term_memory.add_entity(
            "John Doe",
            "PERSON",
            description="A test person",
            generate_embedding=False,
        )

        assert entity.type == "PERSON"
        assert entity.name == "John Doe"

    @pytest.mark.asyncio
    async def test_add_entity_with_enum_type(self, long_term_memory: LongTermMemory):
        """Test adding entity with EntityType enum (backward compat)."""
        entity, _ = await long_term_memory.add_entity(
            "Acme Corp",
            EntityType.ORGANIZATION,
            description="A test company",
            generate_embedding=False,
        )

        assert entity.type == "ORGANIZATION"
        assert entity.name == "Acme Corp"

    @pytest.mark.asyncio
    async def test_add_entity_with_subtype(self, long_term_memory: LongTermMemory):
        """Test adding entity with subtype."""
        entity, _ = await long_term_memory.add_entity(
            "Ford F-150",
            "OBJECT",
            subtype="VEHICLE",
            description="A pickup truck",
            generate_embedding=False,
        )

        assert entity.type == "OBJECT"
        assert entity.subtype == "VEHICLE"
        assert entity.full_type == "OBJECT:VEHICLE"

    @pytest.mark.asyncio
    async def test_add_entity_with_type_subtype_string(self, long_term_memory: LongTermMemory):
        """Test adding entity with type:subtype string format."""
        entity, _ = await long_term_memory.add_entity(
            "123 Main St",
            "LOCATION:ADDRESS",
            description="An address",
            generate_embedding=False,
        )

        assert entity.type == "LOCATION"
        assert entity.subtype == "ADDRESS"

    @pytest.mark.asyncio
    async def test_add_entity_with_attributes(self, long_term_memory: LongTermMemory):
        """Test adding entity with custom attributes."""
        entity, _ = await long_term_memory.add_entity(
            "iPhone 15",
            "OBJECT",
            subtype="DEVICE",
            attributes={"brand": "Apple", "color": "blue"},
            generate_embedding=False,
        )

        assert entity.attributes["brand"] == "Apple"
        assert entity.attributes["color"] == "blue"

    @pytest.mark.asyncio
    async def test_add_entity_with_aliases(self, long_term_memory: LongTermMemory):
        """Test adding entity with aliases."""
        entity, _ = await long_term_memory.add_entity(
            "John Smith",
            "PERSON",
            aliases=["Johnny", "J. Smith"],
            generate_embedding=False,
        )

        assert "Johnny" in entity.aliases

    @pytest.mark.asyncio
    async def test_get_entity_by_name(self, long_term_memory: LongTermMemory):
        """Test retrieving entity by name."""
        # Create entity
        created, _ = await long_term_memory.add_entity(
            "Test Entity",
            "OBJECT",
            subtype="DEVICE",
            generate_embedding=False,
        )

        # Retrieve by name
        retrieved = await long_term_memory.get_entity_by_name("Test Entity")

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.type == "OBJECT"
        assert retrieved.subtype == "DEVICE"

    @pytest.mark.asyncio
    async def test_add_all_poleo_types(self, long_term_memory: LongTermMemory):
        """Test adding entities of all POLE+O types."""
        entities = []

        # PERSON
        person, _ = await long_term_memory.add_entity(
            "Alice Johnson",
            "PERSON",
            subtype="INDIVIDUAL",
            generate_embedding=False,
        )
        entities.append(person)
        assert person.type == "PERSON"

        # OBJECT
        obj, _ = await long_term_memory.add_entity(
            "Blue Honda Civic",
            "OBJECT",
            subtype="VEHICLE",
            generate_embedding=False,
        )
        entities.append(obj)
        assert obj.type == "OBJECT"

        # LOCATION
        location, _ = await long_term_memory.add_entity(
            "San Francisco",
            "LOCATION",
            subtype="CITY",
            generate_embedding=False,
        )
        entities.append(location)
        assert location.type == "LOCATION"

        # EVENT
        event, _ = await long_term_memory.add_entity(
            "Company Meeting Q1 2024",
            "EVENT",
            subtype="MEETING",
            generate_embedding=False,
        )
        entities.append(event)
        assert event.type == "EVENT"

        # ORGANIZATION
        org, _ = await long_term_memory.add_entity(
            "Tech Startup Inc",
            "ORGANIZATION",
            subtype="COMPANY",
            generate_embedding=False,
        )
        entities.append(org)
        assert org.type == "ORGANIZATION"

        assert len(entities) == 5

    @pytest.mark.asyncio
    async def test_relationship_between_poleo_entities(self, long_term_memory: LongTermMemory):
        """Test creating relationships between POLE+O entities."""
        # Create entities
        person, _ = await long_term_memory.add_entity(
            "Bob Williams",
            "PERSON",
            generate_embedding=False,
        )

        org, _ = await long_term_memory.add_entity(
            "TechCorp",
            "ORGANIZATION",
            generate_embedding=False,
        )

        location, _ = await long_term_memory.add_entity(
            "New York",
            "LOCATION",
            subtype="CITY",
            generate_embedding=False,
        )

        # Create relationships
        works_at = await long_term_memory.add_relationship(
            person,
            org,
            "WORKS_AT",
            description="Bob works at TechCorp",
        )

        located_in = await long_term_memory.add_relationship(
            org,
            location,
            "LOCATED_IN",
            description="TechCorp is in New York",
        )

        # Verify relationships
        assert works_at.type == "WORKS_AT"
        assert located_in.type == "LOCATED_IN"

        # Get related entities
        related = await long_term_memory.get_related_entities(person)
        assert len(related) >= 1


@pytest.fixture
def long_term_memory(memory_client):
    """Create long-term memory instance for tests."""
    return memory_client.long_term
