"""Pydantic payload models used by structured LLM extraction.

These mirror the public :class:`~neo4j_agent_memory.extraction.base.ExtractedEntity`,
:class:`~neo4j_agent_memory.extraction.base.ExtractedRelation`, and
:class:`~neo4j_agent_memory.extraction.base.ExtractedPreference` classes,
but are lean extraction-time payloads suitable for
:meth:`~neo4j_agent_memory.llm.protocol.StructuredExtractor.complete_structured`.

Keeping them separate from the public ``Extracted*`` classes avoids
forcing the LLM to invent values for downstream-only fields like
``start_pos``, ``end_pos``, ``extractor``, or ``attributes``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EntityPayload(BaseModel):
    """An entity payload from LLM structured extraction."""

    name: str = Field(description="Entity name, as it appears in the text.")
    type: str = Field(
        description=(
            "Entity type. One of the allowed types (PERSON, OBJECT, "
            "LOCATION, EVENT, ORGANIZATION for POLE+O, or as configured)."
        )
    )
    subtype: str | None = Field(
        default=None,
        description=(
            "Optional subtype (e.g., VEHICLE for OBJECT, ADDRESS for LOCATION). "
            "Use null when no specific subtype applies."
        ),
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the extraction (0.0 to 1.0).",
    )


class RelationPayload(BaseModel):
    """A relation payload from LLM structured extraction."""

    source: str = Field(description="Source entity name (must match an extracted entity).")
    target: str = Field(description="Target entity name (must match an extracted entity).")
    relation_type: str = Field(
        description=("Relationship type (WORKS_AT, LIVES_IN, OWNS, KNOWS, FOUNDED, etc.).")
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PreferencePayload(BaseModel):
    """A preference payload from LLM structured extraction."""

    category: str = Field(
        description="Preference category (food, music, communication, style, technology, etc.)."
    )
    preference: str = Field(description="The preference statement.")
    context: str | None = Field(
        default=None, description="Optional context for when/where the preference applies."
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractionPayload(BaseModel):
    """Top-level payload for LLM structured extraction."""

    entities: list[EntityPayload] = Field(default_factory=list)
    relations: list[RelationPayload] = Field(default_factory=list)
    preferences: list[PreferencePayload] = Field(default_factory=list)


__all__ = [
    "EntityPayload",
    "RelationPayload",
    "PreferencePayload",
    "ExtractionPayload",
]
