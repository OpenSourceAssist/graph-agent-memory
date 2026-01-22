"""Tests for query builder utilities."""

import pytest

from neo4j_agent_memory.graph.query_builder import (
    VALID_ENTITY_TYPES,
    VALID_SUBTYPES,
    build_create_entity_query,
    build_label_set_clause,
    validate_entity_type,
    validate_subtype,
)


class TestValidateEntityType:
    """Tests for validate_entity_type function."""

    def test_valid_types(self):
        """Test validation of valid POLE+O entity types."""
        assert validate_entity_type("PERSON") == "PERSON"
        assert validate_entity_type("OBJECT") == "OBJECT"
        assert validate_entity_type("LOCATION") == "LOCATION"
        assert validate_entity_type("EVENT") == "EVENT"
        assert validate_entity_type("ORGANIZATION") == "ORGANIZATION"

    def test_case_insensitive(self):
        """Test that validation is case-insensitive."""
        assert validate_entity_type("person") == "PERSON"
        assert validate_entity_type("Person") == "PERSON"
        assert validate_entity_type("PERSON") == "PERSON"
        assert validate_entity_type("object") == "OBJECT"
        assert validate_entity_type("Location") == "LOCATION"

    def test_invalid_types(self):
        """Test that invalid types return None."""
        assert validate_entity_type("INVALID") is None
        assert validate_entity_type("CUSTOM") is None
        assert validate_entity_type("") is None
        assert validate_entity_type("CONCEPT") is None  # Legacy type, not in POLE+O
        assert validate_entity_type("FOO") is None


class TestValidateSubtype:
    """Tests for validate_subtype function."""

    def test_valid_person_subtypes(self):
        """Test validation of valid PERSON subtypes."""
        assert validate_subtype("PERSON", "INDIVIDUAL") == "INDIVIDUAL"
        assert validate_subtype("PERSON", "ALIAS") == "ALIAS"
        assert validate_subtype("PERSON", "PERSONA") == "PERSONA"
        assert validate_subtype("PERSON", "SUSPECT") == "SUSPECT"
        assert validate_subtype("PERSON", "WITNESS") == "WITNESS"
        assert validate_subtype("PERSON", "VICTIM") == "VICTIM"

    def test_valid_object_subtypes(self):
        """Test validation of valid OBJECT subtypes."""
        assert validate_subtype("OBJECT", "VEHICLE") == "VEHICLE"
        assert validate_subtype("OBJECT", "PHONE") == "PHONE"
        assert validate_subtype("OBJECT", "EMAIL") == "EMAIL"
        assert validate_subtype("OBJECT", "DOCUMENT") == "DOCUMENT"
        assert validate_subtype("OBJECT", "DEVICE") == "DEVICE"
        assert validate_subtype("OBJECT", "WEAPON") == "WEAPON"

    def test_valid_location_subtypes(self):
        """Test validation of valid LOCATION subtypes."""
        assert validate_subtype("LOCATION", "ADDRESS") == "ADDRESS"
        assert validate_subtype("LOCATION", "CITY") == "CITY"
        assert validate_subtype("LOCATION", "COUNTRY") == "COUNTRY"
        assert validate_subtype("LOCATION", "LANDMARK") == "LANDMARK"
        assert validate_subtype("LOCATION", "FACILITY") == "FACILITY"

    def test_valid_event_subtypes(self):
        """Test validation of valid EVENT subtypes."""
        assert validate_subtype("EVENT", "INCIDENT") == "INCIDENT"
        assert validate_subtype("EVENT", "MEETING") == "MEETING"
        assert validate_subtype("EVENT", "TRANSACTION") == "TRANSACTION"
        assert validate_subtype("EVENT", "COMMUNICATION") == "COMMUNICATION"

    def test_valid_organization_subtypes(self):
        """Test validation of valid ORGANIZATION subtypes."""
        assert validate_subtype("ORGANIZATION", "COMPANY") == "COMPANY"
        assert validate_subtype("ORGANIZATION", "NONPROFIT") == "NONPROFIT"
        assert validate_subtype("ORGANIZATION", "GOVERNMENT") == "GOVERNMENT"
        assert validate_subtype("ORGANIZATION", "EDUCATIONAL") == "EDUCATIONAL"

    def test_case_insensitive(self):
        """Test that subtype validation is case-insensitive."""
        assert validate_subtype("PERSON", "individual") == "INDIVIDUAL"
        assert validate_subtype("person", "INDIVIDUAL") == "INDIVIDUAL"
        assert validate_subtype("Object", "vehicle") == "VEHICLE"

    def test_invalid_subtype_for_type(self):
        """Test that subtypes invalid for a type return None."""
        # VEHICLE is valid for OBJECT, not for PERSON
        assert validate_subtype("PERSON", "VEHICLE") is None
        # ADDRESS is valid for LOCATION, not for OBJECT
        assert validate_subtype("OBJECT", "ADDRESS") is None
        # COMPANY is valid for ORGANIZATION, not for EVENT
        assert validate_subtype("EVENT", "COMPANY") is None

    def test_completely_invalid_subtype(self):
        """Test that completely invalid subtypes return None."""
        assert validate_subtype("PERSON", "INVALID") is None
        assert validate_subtype("OBJECT", "FOOBAR") is None
        assert validate_subtype("LOCATION", "") is None

    def test_invalid_entity_type(self):
        """Test that invalid entity types return None for any subtype."""
        assert validate_subtype("INVALID", "VEHICLE") is None
        assert validate_subtype("CUSTOM", "ADDRESS") is None


class TestBuildLabelSetClause:
    """Tests for build_label_set_clause function."""

    def test_type_only(self):
        """Test building clause with type only (no subtype)."""
        clause = build_label_set_clause("PERSON", None)
        assert clause == "SET e:PERSON"

        clause = build_label_set_clause("OBJECT", None)
        assert clause == "SET e:OBJECT"

        clause = build_label_set_clause("LOCATION", None)
        assert clause == "SET e:LOCATION"

    def test_type_and_subtype(self):
        """Test building clause with both type and subtype."""
        clause = build_label_set_clause("OBJECT", "VEHICLE")
        assert "SET" in clause
        assert "e:OBJECT" in clause
        assert "e:VEHICLE" in clause

        clause = build_label_set_clause("PERSON", "INDIVIDUAL")
        assert "e:PERSON" in clause
        assert "e:INDIVIDUAL" in clause

        clause = build_label_set_clause("LOCATION", "ADDRESS")
        assert "e:LOCATION" in clause
        assert "e:ADDRESS" in clause

    def test_custom_node_variable(self):
        """Test building clause with custom node variable."""
        clause = build_label_set_clause("PERSON", None, node_var="n")
        assert clause == "SET n:PERSON"

        clause = build_label_set_clause("OBJECT", "VEHICLE", node_var="entity")
        assert "entity:OBJECT" in clause
        assert "entity:VEHICLE" in clause

    def test_invalid_type_returns_empty(self):
        """Test that invalid type returns empty string."""
        clause = build_label_set_clause("INVALID", None)
        assert clause == ""

        clause = build_label_set_clause("CUSTOM", "SUBTYPE")
        assert clause == ""

    def test_invalid_subtype_only_includes_type(self):
        """Test that invalid subtype still includes valid type."""
        clause = build_label_set_clause("PERSON", "INVALID_SUBTYPE")
        assert clause == "SET e:PERSON"
        assert "INVALID_SUBTYPE" not in clause

    def test_case_insensitive(self):
        """Test that clause building is case-insensitive."""
        clause = build_label_set_clause("person", "individual")
        assert "e:PERSON" in clause
        assert "e:INDIVIDUAL" in clause


class TestBuildCreateEntityQuery:
    """Tests for build_create_entity_query function."""

    def test_query_contains_merge(self):
        """Test that generated query contains MERGE clause."""
        query = build_create_entity_query("PERSON", None)
        assert "MERGE (e:Entity" in query
        assert "{name: $name, type: $type}" in query

    def test_query_contains_on_create_set(self):
        """Test that generated query contains ON CREATE SET."""
        query = build_create_entity_query("PERSON", None)
        assert "ON CREATE SET" in query
        assert "e.id = $id" in query
        assert "e.subtype = $subtype" in query
        assert "e.created_at = datetime()" in query

    def test_query_contains_on_match_set(self):
        """Test that generated query contains ON MATCH SET."""
        query = build_create_entity_query("PERSON", None)
        assert "ON MATCH SET" in query
        assert "e.updated_at = datetime()" in query

    def test_query_contains_return(self):
        """Test that generated query ends with RETURN."""
        query = build_create_entity_query("PERSON", None)
        assert query.strip().endswith("RETURN e")

    def test_query_includes_type_label(self):
        """Test that query includes type as label."""
        query = build_create_entity_query("PERSON", None)
        assert "SET e:PERSON" in query

        query = build_create_entity_query("OBJECT", None)
        assert "SET e:OBJECT" in query

        query = build_create_entity_query("ORGANIZATION", None)
        assert "SET e:ORGANIZATION" in query

    def test_query_includes_subtype_label(self):
        """Test that query includes subtype as label when valid."""
        query = build_create_entity_query("OBJECT", "VEHICLE")
        assert "e:OBJECT" in query
        assert "e:VEHICLE" in query

        query = build_create_entity_query("PERSON", "INDIVIDUAL")
        assert "e:PERSON" in query
        assert "e:INDIVIDUAL" in query

        query = build_create_entity_query("LOCATION", "ADDRESS")
        assert "e:LOCATION" in query
        assert "e:ADDRESS" in query

    def test_query_with_invalid_type_no_label_set(self):
        """Test that invalid type doesn't add label SET clause."""
        query = build_create_entity_query("INVALID", None)
        # Should still have valid query structure
        assert "MERGE (e:Entity" in query
        assert "RETURN e" in query
        # But no SET clause for labels (only ON CREATE/MATCH SET)
        lines = query.strip().split("\n")
        # The only SET should be within ON CREATE SET and ON MATCH SET
        set_lines = [l for l in lines if l.strip().startswith("SET e:")]
        assert len(set_lines) == 0

    def test_query_with_invalid_subtype_only_type_label(self):
        """Test that invalid subtype still adds type label."""
        query = build_create_entity_query("PERSON", "INVALID_SUBTYPE")
        assert "SET e:PERSON" in query
        assert "INVALID_SUBTYPE" not in query

    def test_all_pole_o_types(self):
        """Test query generation for all POLE+O types."""
        for entity_type in VALID_ENTITY_TYPES:
            query = build_create_entity_query(entity_type, None)
            assert f"SET e:{entity_type}" in query

    def test_sample_subtypes_for_each_type(self):
        """Test query generation for sample subtypes of each type."""
        test_cases = [
            ("PERSON", "INDIVIDUAL"),
            ("OBJECT", "VEHICLE"),
            ("LOCATION", "ADDRESS"),
            ("EVENT", "MEETING"),
            ("ORGANIZATION", "COMPANY"),
        ]
        for entity_type, subtype in test_cases:
            query = build_create_entity_query(entity_type, subtype)
            assert f"e:{entity_type}" in query
            assert f"e:{subtype}" in query


class TestValidSubtypesConsistency:
    """Tests to ensure VALID_SUBTYPES matches schema/models.py."""

    def test_all_pole_o_types_have_subtypes(self):
        """Test that all POLE+O types have subtype definitions."""
        for entity_type in VALID_ENTITY_TYPES:
            assert entity_type in VALID_SUBTYPES
            assert len(VALID_SUBTYPES[entity_type]) > 0

    def test_person_subtypes_complete(self):
        """Test that PERSON subtypes include expected values."""
        expected = {"INDIVIDUAL", "ALIAS", "PERSONA", "SUSPECT", "WITNESS", "VICTIM"}
        assert expected.issubset(VALID_SUBTYPES["PERSON"])

    def test_object_subtypes_complete(self):
        """Test that OBJECT subtypes include expected values."""
        expected = {"VEHICLE", "PHONE", "EMAIL", "DOCUMENT", "DEVICE", "WEAPON"}
        assert expected.issubset(VALID_SUBTYPES["OBJECT"])

    def test_location_subtypes_complete(self):
        """Test that LOCATION subtypes include expected values."""
        expected = {"ADDRESS", "CITY", "REGION", "COUNTRY", "LANDMARK", "FACILITY"}
        assert expected.issubset(VALID_SUBTYPES["LOCATION"])

    def test_event_subtypes_complete(self):
        """Test that EVENT subtypes include expected values."""
        expected = {"INCIDENT", "MEETING", "TRANSACTION", "COMMUNICATION"}
        assert expected.issubset(VALID_SUBTYPES["EVENT"])

    def test_organization_subtypes_complete(self):
        """Test that ORGANIZATION subtypes include expected values."""
        expected = {"COMPANY", "NONPROFIT", "GOVERNMENT", "EDUCATIONAL"}
        assert expected.issubset(VALID_SUBTYPES["ORGANIZATION"])
