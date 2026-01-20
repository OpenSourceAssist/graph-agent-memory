"""Base extraction classes and protocols."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """Entity extracted from text.

    Supports the POLE+O model (Person, Object, Location, Event, Organization)
    as well as custom entity types and subtypes.
    """

    name: str = Field(description="Entity name")
    type: str = Field(description="Entity type (PERSON, OBJECT, LOCATION, EVENT, ORGANIZATION)")
    subtype: str | None = Field(
        default=None, description="Entity subtype (e.g., VEHICLE for OBJECT, ADDRESS for LOCATION)"
    )
    start_pos: int | None = Field(default=None, description="Start position in text")
    end_pos: int | None = Field(default=None, description="End position in text")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    context: str | None = Field(default=None, description="Surrounding context")
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Additional attributes extracted for this entity"
    )
    extractor: str | None = Field(
        default=None, description="Name of the extractor that produced this entity"
    )

    @property
    def normalized_name(self) -> str:
        """Return normalized entity name (lowercase, stripped)."""
        return self.name.lower().strip()

    @property
    def full_type(self) -> str:
        """Return full type including subtype if present."""
        if self.subtype:
            return f"{self.type}:{self.subtype}"
        return self.type


class ExtractedRelation(BaseModel):
    """Relation extracted from text."""

    source: str = Field(description="Source entity name")
    target: str = Field(description="Target entity name")
    relation_type: str = Field(description="Type of relationship")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")

    @property
    def as_triple(self) -> tuple[str, str, str]:
        """Return relation as (source, relation, target) triple."""
        return (self.source, self.relation_type, self.target)


class ExtractedPreference(BaseModel):
    """Preference extracted from text."""

    category: str = Field(description="Preference category")
    preference: str = Field(description="The preference statement")
    context: str | None = Field(default=None, description="Context where preference applies")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")


class ExtractionResult(BaseModel):
    """Result of entity and relation extraction."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    preferences: list[ExtractedPreference] = Field(default_factory=list)
    source_text: str | None = Field(default=None, description="Original source text")

    @property
    def entity_count(self) -> int:
        """Return number of entities."""
        return len(self.entities)

    @property
    def relation_count(self) -> int:
        """Return number of relations."""
        return len(self.relations)

    @property
    def preference_count(self) -> int:
        """Return number of preferences."""
        return len(self.preferences)

    def entities_by_type(self) -> dict[str, list[ExtractedEntity]]:
        """Group entities by type."""
        result: dict[str, list[ExtractedEntity]] = {}
        for entity in self.entities:
            if entity.type not in result:
                result[entity.type] = []
            result[entity.type].append(entity)
        return result

    def get_entities_of_type(self, entity_type: str) -> list[ExtractedEntity]:
        """Get entities of a specific type."""
        return [e for e in self.entities if e.type.upper() == entity_type.upper()]


@runtime_checkable
class EntityExtractor(Protocol):
    """Protocol for entity extraction implementations."""

    async def extract(
        self,
        text: str,
        *,
        entity_types: list[str] | None = None,
        extract_relations: bool = True,
        extract_preferences: bool = True,
    ) -> ExtractionResult:
        """
        Extract entities and relations from text.

        Args:
            text: The text to extract from
            entity_types: Optional list of entity types to extract
            extract_relations: Whether to extract relations
            extract_preferences: Whether to extract preferences

        Returns:
            ExtractionResult containing entities, relations, and preferences
        """
        ...


class NoOpExtractor:
    """Extractor that does nothing (for when extraction is disabled)."""

    async def extract(
        self,
        text: str,
        *,
        entity_types: list[str] | None = None,
        extract_relations: bool = True,
        extract_preferences: bool = True,
    ) -> ExtractionResult:
        """Return empty extraction result."""
        return ExtractionResult(source_text=text)
