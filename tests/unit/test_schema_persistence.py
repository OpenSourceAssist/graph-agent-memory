"""Unit tests for schema persistence."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from neo4j_agent_memory.schema import (
    EntitySchemaConfig,
    EntityTypeConfig,
    RelationTypeConfig,
    SchemaListItem,
    SchemaManager,
    StoredSchema,
)


@pytest.fixture
def mock_client():
    """Create a mock Neo4jClient."""
    client = MagicMock()
    client.execute_read = AsyncMock()
    client.execute_write = AsyncMock()
    return client


@pytest.fixture
def sample_schema():
    """Create a sample schema for testing."""
    return EntitySchemaConfig(
        name="test_schema",
        version="1.0",
        description="Test schema for unit tests",
        entity_types=[
            EntityTypeConfig(
                name="PERSON",
                description="A person entity",
                subtypes=["EMPLOYEE", "CUSTOMER"],
                attributes=["name", "email"],
            ),
            EntityTypeConfig(
                name="ORGANIZATION",
                description="An organization entity",
                subtypes=["COMPANY", "NONPROFIT"],
                attributes=["name", "industry"],
            ),
        ],
        relation_types=[
            RelationTypeConfig(
                name="WORKS_FOR",
                description="Person works for organization",
                source_types=["PERSON"],
                target_types=["ORGANIZATION"],
            ),
        ],
    )


@pytest.fixture
def stored_schema_node():
    """Create a mock stored schema node from Neo4j."""
    return {
        "id": str(uuid4()),
        "name": "test_schema",
        "version": "1.0",
        "description": "Test schema",
        "config": '{"name": "test_schema", "version": "1.0", "description": "Test schema", "entity_types": [{"name": "PERSON", "description": null, "subtypes": [], "attributes": [], "color": null}], "relation_types": [], "default_entity_type": "OBJECT", "enable_subtypes": true, "strict_types": false}',
        "is_active": True,
        "created_at": datetime.now(),
        "created_by": "test_user",
    }


class TestStoredSchema:
    """Tests for StoredSchema dataclass."""

    def test_from_node_basic(self, stored_schema_node):
        """Test creating StoredSchema from a Neo4j node."""
        stored = StoredSchema.from_node(stored_schema_node)

        assert stored.name == "test_schema"
        assert stored.version == "1.0"
        assert stored.description == "Test schema"
        assert stored.is_active is True
        assert stored.created_by == "test_user"
        assert isinstance(stored.config, EntitySchemaConfig)
        assert stored.config.name == "test_schema"

    def test_from_node_uuid_string(self, stored_schema_node):
        """Test that string UUID is properly converted."""
        stored = StoredSchema.from_node(stored_schema_node)
        assert isinstance(stored.id, UUID)

    def test_from_node_uuid_object(self, stored_schema_node):
        """Test that UUID object is preserved."""
        stored_schema_node["id"] = uuid4()
        stored = StoredSchema.from_node(stored_schema_node)
        assert isinstance(stored.id, UUID)

    def test_from_node_missing_optional_fields(self):
        """Test handling of missing optional fields."""
        minimal_node = {
            "id": str(uuid4()),
            "name": "minimal",
            "version": "1.0",
            "config": '{"name": "minimal", "version": "1.0"}',
        }
        stored = StoredSchema.from_node(minimal_node)

        assert stored.name == "minimal"
        assert stored.description is None
        assert stored.is_active is True  # Default
        assert stored.created_by is None


class TestSchemaManager:
    """Tests for SchemaManager class."""

    @pytest.mark.asyncio
    async def test_save_schema_new(self, mock_client, sample_schema):
        """Test saving a new schema."""
        # Setup mock - first deactivate returns empty, then create returns node
        mock_client.execute_write.side_effect = [
            [],  # DEACTIVATE_SCHEMA_VERSIONS
            [
                {
                    "s": {
                        "id": str(uuid4()),
                        "name": sample_schema.name,
                        "version": sample_schema.version,
                        "description": sample_schema.description,
                        "config": sample_schema.model_dump_json(),
                        "is_active": True,
                        "created_at": datetime.now(),
                        "created_by": "tester",
                    }
                }
            ],
        ]

        manager = SchemaManager(mock_client)
        result = await manager.save_schema(sample_schema, created_by="tester")

        assert result.name == "test_schema"
        assert result.version == "1.0"
        assert result.is_active is True
        assert result.created_by == "tester"
        assert mock_client.execute_write.call_count == 2

    @pytest.mark.asyncio
    async def test_save_schema_not_active(self, mock_client, sample_schema):
        """Test saving a schema without setting it active."""
        mock_client.execute_write.side_effect = [
            [
                {
                    "s": {
                        "id": str(uuid4()),
                        "name": sample_schema.name,
                        "version": sample_schema.version,
                        "description": sample_schema.description,
                        "config": sample_schema.model_dump_json(),
                        "is_active": False,
                        "created_at": datetime.now(),
                        "created_by": None,
                    }
                }
            ],
        ]

        manager = SchemaManager(mock_client)
        result = await manager.save_schema(sample_schema, set_active=False)

        assert result.is_active is False
        # Should only call create, not deactivate
        assert mock_client.execute_write.call_count == 1

    @pytest.mark.asyncio
    async def test_save_schema_fallback(self, mock_client, sample_schema):
        """Test fallback when node not returned properly."""
        mock_client.execute_write.side_effect = [
            [],  # DEACTIVATE_SCHEMA_VERSIONS
            [{}],  # CREATE_SCHEMA with no 's' key
        ]

        manager = SchemaManager(mock_client)
        result = await manager.save_schema(sample_schema)

        # Should return constructed StoredSchema
        assert result.name == sample_schema.name
        assert result.version == sample_schema.version
        assert result.config == sample_schema

    @pytest.mark.asyncio
    async def test_load_schema_found(self, mock_client, stored_schema_node):
        """Test loading an existing schema."""
        mock_client.execute_read.return_value = [{"s": stored_schema_node}]

        manager = SchemaManager(mock_client)
        result = await manager.load_schema("test_schema")

        assert result is not None
        assert isinstance(result, EntitySchemaConfig)
        assert result.name == "test_schema"

    @pytest.mark.asyncio
    async def test_load_schema_not_found(self, mock_client):
        """Test loading a non-existent schema."""
        mock_client.execute_read.return_value = []

        manager = SchemaManager(mock_client)
        result = await manager.load_schema("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_schema_version_found(self, mock_client, stored_schema_node):
        """Test loading a specific schema version."""
        stored_schema_node["version"] = "2.0"
        mock_client.execute_read.return_value = [{"s": stored_schema_node}]

        manager = SchemaManager(mock_client)
        result = await manager.load_schema_version("test_schema", "2.0")

        assert result is not None
        # Config is parsed from the stored JSON, so check the node version
        mock_client.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_schema_version_not_found(self, mock_client):
        """Test loading a non-existent schema version."""
        mock_client.execute_read.return_value = []

        manager = SchemaManager(mock_client)
        result = await manager.load_schema_version("test_schema", "99.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stored_schema(self, mock_client, stored_schema_node):
        """Test getting full stored schema details."""
        mock_client.execute_read.return_value = [{"s": stored_schema_node}]

        manager = SchemaManager(mock_client)
        result = await manager.get_stored_schema("test_schema")

        assert result is not None
        assert isinstance(result, StoredSchema)
        assert result.name == "test_schema"
        assert result.created_by == "test_user"

    @pytest.mark.asyncio
    async def test_get_stored_schema_by_id(self, mock_client, stored_schema_node):
        """Test getting stored schema by ID."""
        schema_id = UUID(stored_schema_node["id"])
        mock_client.execute_read.return_value = [{"s": stored_schema_node}]

        manager = SchemaManager(mock_client)
        result = await manager.get_stored_schema_by_id(schema_id)

        assert result is not None
        assert result.id == schema_id

    @pytest.mark.asyncio
    async def test_get_stored_schema_by_id_string(self, mock_client, stored_schema_node):
        """Test getting stored schema by string ID."""
        schema_id = stored_schema_node["id"]
        mock_client.execute_read.return_value = [{"s": stored_schema_node}]

        manager = SchemaManager(mock_client)
        result = await manager.get_stored_schema_by_id(schema_id)

        assert result is not None

    @pytest.mark.asyncio
    async def test_list_schemas(self, mock_client):
        """Test listing all schemas."""
        mock_client.execute_read.return_value = [
            {
                "name": "schema1",
                "latest": {
                    "version": "1.0",
                    "description": "First schema",
                    "is_active": True,
                },
                "version_count": 2,
            },
            {
                "name": "schema2",
                "latest": {
                    "version": "3.0",
                    "description": "Second schema",
                    "is_active": True,
                },
                "version_count": 3,
            },
        ]

        manager = SchemaManager(mock_client)
        result = await manager.list_schemas()

        assert len(result) == 2
        assert all(isinstance(item, SchemaListItem) for item in result)
        assert result[0].name == "schema1"
        assert result[0].latest_version == "1.0"
        assert result[0].version_count == 2
        assert result[1].name == "schema2"
        assert result[1].version_count == 3

    @pytest.mark.asyncio
    async def test_list_schemas_filtered(self, mock_client):
        """Test listing schemas filtered by name."""
        mock_client.execute_read.return_value = [
            {
                "name": "medical",
                "latest": {
                    "version": "2.0",
                    "description": "Medical schema",
                    "is_active": True,
                },
                "version_count": 2,
            },
        ]

        manager = SchemaManager(mock_client)
        result = await manager.list_schemas(name="medical")

        assert len(result) == 1
        assert result[0].name == "medical"
        mock_client.execute_read.assert_called_once()
        call_args = mock_client.execute_read.call_args
        assert call_args[0][1]["name"] == "medical"

    @pytest.mark.asyncio
    async def test_list_schemas_empty(self, mock_client):
        """Test listing schemas when none exist."""
        mock_client.execute_read.return_value = []

        manager = SchemaManager(mock_client)
        result = await manager.list_schemas()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_schema_versions(self, mock_client, stored_schema_node):
        """Test listing all versions of a schema."""
        v1 = {**stored_schema_node, "version": "1.0"}
        v2 = {**stored_schema_node, "version": "2.0", "id": str(uuid4())}
        mock_client.execute_read.return_value = [{"s": v2}, {"s": v1}]

        manager = SchemaManager(mock_client)
        result = await manager.list_schema_versions("test_schema")

        assert len(result) == 2
        assert all(isinstance(s, StoredSchema) for s in result)

    @pytest.mark.asyncio
    async def test_set_active_version_success(self, mock_client, stored_schema_node):
        """Test setting a specific version as active."""
        mock_client.execute_read.return_value = [{"s": stored_schema_node}]
        mock_client.execute_write.return_value = [{"active": stored_schema_node}]

        manager = SchemaManager(mock_client)
        result = await manager.set_active_version("test_schema", "1.0")

        assert result is not None
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_set_active_version_not_found(self, mock_client):
        """Test setting active version when schema not found."""
        mock_client.execute_read.return_value = []

        manager = SchemaManager(mock_client)
        result = await manager.set_active_version("nonexistent", "1.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_schema_success(self, mock_client):
        """Test deleting a schema by ID."""
        schema_id = uuid4()
        mock_client.execute_write.return_value = [{"deleted": True}]

        manager = SchemaManager(mock_client)
        result = await manager.delete_schema(schema_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_schema_not_found(self, mock_client):
        """Test deleting a non-existent schema."""
        mock_client.execute_write.return_value = [{"deleted": False}]

        manager = SchemaManager(mock_client)
        result = await manager.delete_schema(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_schema_string_id(self, mock_client):
        """Test deleting a schema with string ID."""
        schema_id = str(uuid4())
        mock_client.execute_write.return_value = [{"deleted": True}]

        manager = SchemaManager(mock_client)
        result = await manager.delete_schema(schema_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_all_versions(self, mock_client):
        """Test deleting all versions of a schema."""
        mock_client.execute_write.return_value = [{"deleted_count": 3}]

        manager = SchemaManager(mock_client)
        result = await manager.delete_all_versions("test_schema")

        assert result == 3

    @pytest.mark.asyncio
    async def test_delete_all_versions_empty(self, mock_client):
        """Test deleting versions when schema doesn't exist."""
        mock_client.execute_write.return_value = [{"deleted_count": 0}]

        manager = SchemaManager(mock_client)
        result = await manager.delete_all_versions("nonexistent")

        assert result == 0

    @pytest.mark.asyncio
    async def test_schema_exists_true(self, mock_client, stored_schema_node):
        """Test checking if schema exists (true case)."""
        mock_client.execute_read.return_value = [{"s": stored_schema_node}]

        manager = SchemaManager(mock_client)
        result = await manager.schema_exists("test_schema")

        assert result is True

    @pytest.mark.asyncio
    async def test_schema_exists_false(self, mock_client):
        """Test checking if schema exists (false case)."""
        mock_client.execute_read.return_value = []

        manager = SchemaManager(mock_client)
        result = await manager.schema_exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_schema_index(self, mock_client):
        """Test creating schema indexes."""
        mock_client.execute_write.return_value = []

        manager = SchemaManager(mock_client)
        await manager.ensure_schema_index()

        assert mock_client.execute_write.call_count == 2


class TestSchemaListItem:
    """Tests for SchemaListItem dataclass."""

    def test_schema_list_item_creation(self):
        """Test creating a SchemaListItem."""
        item = SchemaListItem(
            name="test",
            latest_version="1.0",
            description="Test description",
            version_count=5,
            is_active=True,
        )

        assert item.name == "test"
        assert item.latest_version == "1.0"
        assert item.description == "Test description"
        assert item.version_count == 5
        assert item.is_active is True

    def test_schema_list_item_optional_description(self):
        """Test SchemaListItem with None description."""
        item = SchemaListItem(
            name="test",
            latest_version="1.0",
            description=None,
            version_count=1,
            is_active=False,
        )

        assert item.description is None
        assert item.is_active is False


class TestSchemaManagerEdgeCases:
    """Edge case tests for SchemaManager."""

    @pytest.mark.asyncio
    async def test_save_schema_complex_config(self, mock_client):
        """Test saving a schema with complex configuration."""
        complex_schema = EntitySchemaConfig(
            name="complex",
            version="1.0",
            description="Complex schema with many types",
            entity_types=[
                EntityTypeConfig(
                    name=f"TYPE_{i}",
                    description=f"Type number {i}",
                    subtypes=[f"SUBTYPE_{j}" for j in range(5)],
                    attributes=[f"attr_{k}" for k in range(10)],
                    color=f"#{i:06x}",
                )
                for i in range(10)
            ],
            relation_types=[
                RelationTypeConfig(
                    name=f"REL_{i}",
                    description=f"Relation {i}",
                    source_types=["TYPE_0", "TYPE_1"],
                    target_types=["TYPE_2", "TYPE_3"],
                    properties=[f"prop_{j}" for j in range(3)],
                )
                for i in range(5)
            ],
            default_entity_type="TYPE_0",
            enable_subtypes=True,
            strict_types=True,
        )

        mock_client.execute_write.side_effect = [
            [],  # DEACTIVATE
            [{}],  # CREATE (fallback case)
        ]

        manager = SchemaManager(mock_client)
        result = await manager.save_schema(complex_schema)

        assert result.name == "complex"
        assert len(result.config.entity_types) == 10
        assert len(result.config.relation_types) == 5

    @pytest.mark.asyncio
    async def test_list_schemas_missing_latest_node(self, mock_client):
        """Test listing schemas when latest node is missing."""
        mock_client.execute_read.return_value = [
            {
                "name": "broken",
                "latest": None,
                "version_count": 0,
            },
        ]

        manager = SchemaManager(mock_client)
        result = await manager.list_schemas()

        # Should skip entries with no latest node
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_empty_execute_write_result(self, mock_client):
        """Test handling empty execute_write results."""
        mock_client.execute_write.return_value = []

        manager = SchemaManager(mock_client)
        result = await manager.delete_all_versions("test")

        assert result == 0

    @pytest.mark.asyncio
    async def test_none_execute_write_result(self, mock_client):
        """Test handling None in execute_write results."""
        mock_client.execute_write.return_value = [None]

        manager = SchemaManager(mock_client)
        # This should not raise an error
        result = await manager.delete_schema(uuid4())

        assert result is False
