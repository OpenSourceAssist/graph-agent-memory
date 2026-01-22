"""Query builder utilities for dynamic Cypher generation with validated labels.

This module provides functions to build Cypher queries with dynamic entity labels
based on the POLE+O model (Person, Object, Location, Event, Organization).

Since Neo4j doesn't support parameterized labels in Cypher, we use query string
construction with strict validation against known POLE+O types to ensure safety.
"""

from typing import Set

# Valid POLE+O entity types
VALID_ENTITY_TYPES: Set[str] = {"PERSON", "OBJECT", "LOCATION", "EVENT", "ORGANIZATION"}

# Valid subtypes by entity type (from schema/models.py)
VALID_SUBTYPES: dict[str, Set[str]] = {
    "PERSON": {"INDIVIDUAL", "ALIAS", "PERSONA", "SUSPECT", "WITNESS", "VICTIM"},
    "OBJECT": {
        "VEHICLE",
        "PHONE",
        "EMAIL",
        "DOCUMENT",
        "DEVICE",
        "WEAPON",
        "MONEY",
        "DRUG",
        "EVIDENCE",
        "SOFTWARE",
        "PRODUCT",
    },
    "LOCATION": {
        "ADDRESS",
        "CITY",
        "REGION",
        "COUNTRY",
        "LANDMARK",
        "FACILITY",
        "COORDINATES",
        "GEOPOLITICAL",
        "GEOGRAPHIC",
    },
    "EVENT": {
        "INCIDENT",
        "MEETING",
        "TRANSACTION",
        "COMMUNICATION",
        "CRIME",
        "TRAVEL",
        "EMPLOYMENT",
        "OBSERVATION",
        "DATE",
        "TIME",
    },
    "ORGANIZATION": {
        "COMPANY",
        "NONPROFIT",
        "GOVERNMENT",
        "EDUCATIONAL",
        "CRIMINAL",
        "POLITICAL",
        "RELIGIOUS",
        "MILITARY",
        "GROUP",
    },
}


def validate_entity_type(entity_type: str) -> str | None:
    """Validate and normalize entity type.

    Args:
        entity_type: The entity type to validate

    Returns:
        Normalized (uppercase) entity type if valid, None if invalid
    """
    type_upper = entity_type.upper()
    return type_upper if type_upper in VALID_ENTITY_TYPES else None


def validate_subtype(entity_type: str, subtype: str) -> str | None:
    """Validate and normalize subtype for a given entity type.

    Args:
        entity_type: The parent entity type
        subtype: The subtype to validate

    Returns:
        Normalized (uppercase) subtype if valid for the entity type, None if invalid
    """
    type_upper = entity_type.upper()
    subtype_upper = subtype.upper()
    valid_subtypes = VALID_SUBTYPES.get(type_upper, set())
    return subtype_upper if subtype_upper in valid_subtypes else None


def build_label_set_clause(entity_type: str, subtype: str | None, node_var: str = "e") -> str:
    """Build SET clause to add type/subtype labels to a node.

    Args:
        entity_type: The entity type (e.g., "PERSON", "OBJECT")
        subtype: Optional subtype (e.g., "VEHICLE", "ADDRESS")
        node_var: The Cypher node variable name (default: "e")

    Returns:
        SET clause string (e.g., "SET e:PERSON, e:INDIVIDUAL") or empty string if no valid labels
    """
    labels_to_add = []

    validated_type = validate_entity_type(entity_type)
    if validated_type:
        labels_to_add.append(validated_type)

    if subtype and validated_type:
        validated_subtype = validate_subtype(entity_type, subtype)
        if validated_subtype:
            labels_to_add.append(validated_subtype)

    if not labels_to_add:
        return ""

    # Build: SET e:PERSON, e:INDIVIDUAL
    label_additions = ", ".join([f"{node_var}:{label}" for label in labels_to_add])
    return f"SET {label_additions}"


def build_create_entity_query(entity_type: str, subtype: str | None) -> str:
    """Build the CREATE_ENTITY query with dynamic type/subtype labels.

    The query MERGEs on :Entity with name+type properties for uniqueness,
    then adds type and subtype as additional labels.

    Args:
        entity_type: The entity type (e.g., "PERSON", "OBJECT")
        subtype: Optional subtype (e.g., "VEHICLE", "ADDRESS")

    Returns:
        Complete Cypher query string with dynamic labels

    Example:
        >>> query = build_create_entity_query("OBJECT", "VEHICLE")
        >>> # Returns query that creates (:Entity:OBJECT:VEHICLE {...})
    """
    label_set_clause = build_label_set_clause(entity_type, subtype)

    query = """MERGE (e:Entity {name: $name, type: $type})
ON CREATE SET
    e.id = $id,
    e.subtype = $subtype,
    e.canonical_name = $canonical_name,
    e.description = $description,
    e.embedding = $embedding,
    e.confidence = $confidence,
    e.created_at = datetime(),
    e.metadata = $metadata
ON MATCH SET
    e.subtype = COALESCE($subtype, e.subtype),
    e.canonical_name = COALESCE($canonical_name, e.canonical_name),
    e.description = COALESCE($description, e.description),
    e.embedding = COALESCE($embedding, e.embedding),
    e.updated_at = datetime()"""

    # Add label SET clause if we have valid labels
    if label_set_clause:
        query += f"\n{label_set_clause}"

    query += "\nRETURN e"

    return query
