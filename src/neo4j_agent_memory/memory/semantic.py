"""Semantic memory for entities, preferences, and facts."""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from neo4j_agent_memory.core.memory import BaseMemory, MemoryEntry
from neo4j_agent_memory.graph import queries


def _serialize_metadata(metadata: dict[str, Any] | None) -> str | None:
    """Serialize metadata dict to JSON string for Neo4j storage."""
    if metadata is None or metadata == {}:
        return None
    return json.dumps(metadata)


def _deserialize_metadata(metadata_str: str | None) -> dict[str, Any]:
    """Deserialize metadata from JSON string."""
    if metadata_str is None:
        return {}
    try:
        return json.loads(metadata_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def _to_python_datetime(neo4j_datetime) -> datetime:
    """Convert Neo4j DateTime to Python datetime."""
    if neo4j_datetime is None:
        return datetime.utcnow()
    if isinstance(neo4j_datetime, datetime):
        return neo4j_datetime
    # Neo4j DateTime has to_native() method
    try:
        return neo4j_datetime.to_native()
    except AttributeError:
        return datetime.utcnow()


if TYPE_CHECKING:
    from neo4j_agent_memory.embeddings.base import Embedder
    from neo4j_agent_memory.extraction.base import EntityExtractor
    from neo4j_agent_memory.graph.client import Neo4jClient
    from neo4j_agent_memory.resolution.base import EntityResolver


class EntityType(str, Enum):
    """Standard entity types."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    CONCEPT = "CONCEPT"
    EMOTION = "EMOTION"
    PREFERENCE = "PREFERENCE"
    FACT = "FACT"


class Entity(MemoryEntry):
    """An entity extracted from conversations or documents."""

    name: str = Field(description="Entity name")
    canonical_name: str | None = Field(default=None, description="Resolved canonical name")
    type: EntityType = Field(description="Entity type")
    description: str | None = Field(default=None, description="Entity description")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")
    source_id: UUID | None = Field(default=None, description="Source message/document ID")

    @property
    def display_name(self) -> str:
        """Get the display name (canonical if available)."""
        return self.canonical_name or self.name


class Relationship(MemoryEntry):
    """A relationship between entities with temporal bounds."""

    source_id: UUID = Field(description="Source entity ID")
    target_id: UUID = Field(description="Target entity ID")
    type: str = Field(description="Relationship type")
    description: str | None = Field(default=None, description="Relationship description")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    valid_from: datetime | None = Field(default=None, description="Start of validity")
    valid_until: datetime | None = Field(default=None, description="End of validity")


class Preference(MemoryEntry):
    """A user preference."""

    category: str = Field(description="Preference category")
    preference: str = Field(description="The preference statement")
    context: str | None = Field(default=None, description="When/where preference applies")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    linked_entities: list[UUID] = Field(default_factory=list, description="Linked entity IDs")


class Fact(MemoryEntry):
    """A declarative fact about the user or domain."""

    subject: str = Field(description="Fact subject")
    predicate: str = Field(description="Fact predicate/relationship")
    object: str = Field(description="Fact object")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    source_id: UUID | None = Field(default=None, description="Source message/document ID")
    valid_from: datetime | None = Field(default=None, description="Start of validity")
    valid_until: datetime | None = Field(default=None, description="End of validity")

    @property
    def as_triple(self) -> tuple[str, str, str]:
        """Return fact as (subject, predicate, object) triple."""
        return (self.subject, self.predicate, self.object)


class SemanticMemory(BaseMemory[Entity]):
    """
    Semantic/Declarative memory stores facts, preferences, and entities.

    Provides:
    - Entity storage with resolution/deduplication
    - User preferences with categories
    - Facts with temporal validity
    - Relationships between entities
    """

    def __init__(
        self,
        client: "Neo4jClient",
        embedder: "Embedder | None" = None,
        extractor: "EntityExtractor | None" = None,
        resolver: "EntityResolver | None" = None,
    ):
        """Initialize semantic memory."""
        super().__init__(client, embedder, extractor)
        self._resolver = resolver

    async def add(self, content: str, **kwargs: Any) -> Entity:
        """Add content as an entity."""
        name = kwargs.get("name", content)
        entity_type = kwargs.get("type", EntityType.CONCEPT)
        return await self.add_entity(name, entity_type, **kwargs)

    async def add_entity(
        self,
        name: str,
        entity_type: EntityType | str,
        *,
        description: str | None = None,
        resolve: bool = True,
        generate_embedding: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        """
        Add an entity with optional resolution.

        Args:
            name: Entity name
            entity_type: Entity type
            description: Optional description
            resolve: Whether to resolve against existing entities
            generate_embedding: Whether to generate embedding
            metadata: Optional metadata

        Returns:
            The created or resolved entity
        """
        # Normalize type
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type.upper())

        canonical_name = name
        confidence = 1.0

        # Resolve against existing entities
        if resolve and self._resolver is not None:
            existing = await self._get_existing_entity_names(entity_type)
            resolved = await self._resolver.resolve(
                name, entity_type.value, existing_entities=existing
            )
            canonical_name = resolved.canonical_name
            confidence = resolved.confidence

        # Generate embedding
        embedding = None
        if generate_embedding and self._embedder is not None:
            embedding = await self._embedder.embed(name)

        # Create entity
        entity = Entity(
            id=uuid4(),
            name=name,
            canonical_name=canonical_name,
            type=entity_type,
            description=description,
            embedding=embedding,
            confidence=confidence,
            metadata=metadata or {},
        )

        # Store entity
        await self._client.execute_write(
            queries.CREATE_ENTITY,
            {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.type.value,
                "canonical_name": entity.canonical_name,
                "description": entity.description,
                "embedding": entity.embedding,
                "confidence": entity.confidence,
                "metadata": _serialize_metadata(entity.metadata),
            },
        )

        return entity

    async def add_preference(
        self,
        category: str,
        preference: str,
        *,
        context: str | None = None,
        confidence: float = 1.0,
        generate_embedding: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> Preference:
        """
        Add a user preference.

        Args:
            category: Preference category (food, music, communication, etc.)
            preference: The preference statement
            context: When/where preference applies
            confidence: Confidence score
            generate_embedding: Whether to generate embedding
            metadata: Optional metadata

        Returns:
            The created preference
        """
        # Generate embedding
        embedding = None
        if generate_embedding and self._embedder is not None:
            text = f"{category}: {preference}"
            if context:
                text += f" ({context})"
            embedding = await self._embedder.embed(text)

        # Create preference
        pref = Preference(
            id=uuid4(),
            category=category,
            preference=preference,
            context=context,
            confidence=confidence,
            embedding=embedding,
            metadata=metadata or {},
        )

        # Store preference
        await self._client.execute_write(
            queries.CREATE_PREFERENCE,
            {
                "id": str(pref.id),
                "category": pref.category,
                "preference": pref.preference,
                "context": pref.context,
                "confidence": pref.confidence,
                "embedding": pref.embedding,
                "metadata": _serialize_metadata(pref.metadata),
            },
        )

        return pref

    async def add_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        *,
        confidence: float = 1.0,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        generate_embedding: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> Fact:
        """
        Add a declarative fact.

        Args:
            subject: Fact subject
            predicate: Fact predicate/relationship
            obj: Fact object
            confidence: Confidence score
            valid_from: Start of validity
            valid_until: End of validity
            generate_embedding: Whether to generate embedding
            metadata: Optional metadata

        Returns:
            The created fact
        """
        # Generate embedding
        embedding = None
        if generate_embedding and self._embedder is not None:
            text = f"{subject} {predicate} {obj}"
            embedding = await self._embedder.embed(text)

        # Create fact
        fact = Fact(
            id=uuid4(),
            subject=subject,
            predicate=predicate,
            object=obj,
            confidence=confidence,
            embedding=embedding,
            valid_from=valid_from,
            valid_until=valid_until,
            metadata=metadata or {},
        )

        # Store fact
        await self._client.execute_write(
            queries.CREATE_FACT,
            {
                "id": str(fact.id),
                "subject": fact.subject,
                "predicate": fact.predicate,
                "object": fact.object,
                "confidence": fact.confidence,
                "embedding": fact.embedding,
                "valid_from": fact.valid_from.isoformat() if fact.valid_from else None,
                "valid_until": fact.valid_until.isoformat() if fact.valid_until else None,
                "metadata": _serialize_metadata(fact.metadata),
            },
        )

        return fact

    async def add_relationship(
        self,
        source: Entity | UUID,
        target: Entity | UUID,
        relationship_type: str,
        *,
        description: str | None = None,
        confidence: float = 1.0,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
    ) -> Relationship:
        """
        Add a relationship between entities.

        Args:
            source: Source entity or ID
            target: Target entity or ID
            relationship_type: Type of relationship
            description: Optional description
            confidence: Confidence score
            valid_from: Start of validity
            valid_until: End of validity

        Returns:
            The created relationship
        """
        source_id = source.id if isinstance(source, Entity) else source
        target_id = target.id if isinstance(target, Entity) else target

        relationship = Relationship(
            id=uuid4(),
            source_id=source_id,
            target_id=target_id,
            type=relationship_type,
            description=description,
            confidence=confidence,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        await self._client.execute_write(
            queries.CREATE_ENTITY_RELATIONSHIP,
            {
                "id": str(relationship.id),
                "source_id": str(source_id),
                "target_id": str(target_id),
                "relation_type": relationship_type,
                "description": description,
                "confidence": confidence,
                "valid_from": valid_from.isoformat() if valid_from else None,
                "valid_until": valid_until.isoformat() if valid_until else None,
            },
        )

        return relationship

    async def get_entity_by_name(self, name: str) -> Entity | None:
        """
        Get an entity by name.

        Args:
            name: Entity name to search for (checks name, canonical_name, aliases)

        Returns:
            The entity if found, None otherwise
        """
        results = await self._client.execute_read(
            queries.GET_ENTITY_BY_NAME,
            {"name": name},
        )

        if not results:
            return None

        row = results[0]
        entity_data = dict(row["e"])

        return Entity(
            id=UUID(entity_data["id"]),
            name=entity_data["name"],
            canonical_name=entity_data.get("canonical_name"),
            type=EntityType(entity_data["type"]),
            description=entity_data.get("description"),
            embedding=entity_data.get("embedding"),
            confidence=entity_data.get("confidence", 1.0),
            created_at=_to_python_datetime(entity_data.get("created_at")),
            metadata=_deserialize_metadata(entity_data.get("metadata")),
        )

    async def search(self, query: str, **kwargs: Any) -> list[Entity]:
        """Search for entities."""
        return await self.search_entities(query, **kwargs)

    async def search_entities(
        self,
        query: str,
        *,
        entity_types: list[EntityType] | None = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[Entity]:
        """
        Search for entities by semantic similarity.

        Args:
            query: Search query
            entity_types: Optional filter by entity types
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of matching entities
        """
        if self._embedder is None:
            return []

        query_embedding = await self._embedder.embed(query)

        results = await self._client.execute_read(
            queries.SEARCH_ENTITIES_BY_EMBEDDING,
            {
                "embedding": query_embedding,
                "limit": limit,
                "threshold": threshold,
            },
        )

        entities = []
        for row in results:
            entity_data = dict(row["e"])
            entity_type = EntityType(entity_data["type"])

            # Filter by type if specified
            if entity_types and entity_type not in entity_types:
                continue

            entity = Entity(
                id=UUID(entity_data["id"]),
                name=entity_data["name"],
                canonical_name=entity_data.get("canonical_name"),
                type=entity_type,
                description=entity_data.get("description"),
                embedding=entity_data.get("embedding"),
                confidence=entity_data.get("confidence", 1.0),
                created_at=_to_python_datetime(entity_data.get("created_at")),
                metadata={
                    **_deserialize_metadata(entity_data.get("metadata")),
                    "similarity": row["score"],
                },
            )
            entities.append(entity)

        return entities

    async def search_preferences(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[Preference]:
        """
        Search for preferences.

        Args:
            query: Search query
            category: Optional filter by category
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of matching preferences
        """
        if self._embedder is None:
            # Fall back to category-based search
            if category:
                results = await self._client.execute_read(
                    queries.SEARCH_PREFERENCES_BY_CATEGORY,
                    {"category": category, "limit": limit},
                )
                return [self._parse_preference(dict(r["p"])) for r in results]
            return []

        query_embedding = await self._embedder.embed(query)

        results = await self._client.execute_read(
            queries.SEARCH_PREFERENCES_BY_EMBEDDING,
            {
                "embedding": query_embedding,
                "limit": limit,
                "threshold": threshold,
            },
        )

        preferences = []
        for row in results:
            pref_data = dict(row["p"])

            # Filter by category if specified
            if category and pref_data.get("category") != category:
                continue

            pref = self._parse_preference(pref_data)
            pref.metadata["similarity"] = row["score"]
            preferences.append(pref)

        return preferences

    async def get_related_entities(
        self,
        entity: Entity | UUID,
        *,
        relationship_types: list[str] | None = None,
        depth: int = 1,
    ) -> list[tuple[Entity, Relationship]]:
        """
        Get entities related to a given entity.

        Args:
            entity: Entity or ID to find relations for
            relationship_types: Optional filter by relationship types
            depth: Traversal depth

        Returns:
            List of (entity, relationship) tuples
        """
        entity_id = entity.id if isinstance(entity, Entity) else entity

        results = await self._client.execute_read(
            queries.GET_ENTITY_RELATIONSHIPS,
            {"entity_id": str(entity_id)},
        )

        related = []
        for row in results:
            # Neo4j relationship object has different access pattern
            rel = row["r"]
            # Get relationship properties - use dict() if available, else access via _properties
            if hasattr(rel, "_properties"):
                rel_data = dict(rel._properties)
            elif hasattr(rel, "items"):
                rel_data = dict(rel)
            else:
                # Fallback: create empty dict and get individual properties
                rel_data = {}
                for key in ["id", "type", "confidence", "description", "valid_from", "valid_until"]:
                    try:
                        val = rel.get(key) if hasattr(rel, "get") else getattr(rel, key, None)
                        if val is not None:
                            rel_data[key] = val
                    except Exception:
                        pass

            other_data = dict(row["other"])

            # Filter by relationship type
            rel_type = rel_data.get("type") or (rel.type if hasattr(rel, "type") else "RELATED_TO")
            if relationship_types and rel_type not in relationship_types:
                continue

            other_entity = Entity(
                id=UUID(other_data["id"]),
                name=other_data["name"],
                type=EntityType(other_data["type"]),
                canonical_name=other_data.get("canonical_name"),
                description=other_data.get("description"),
            )

            relationship = Relationship(
                id=UUID(rel_data.get("id", str(uuid4()))),
                source_id=entity_id,
                target_id=other_entity.id,
                type=rel_type,
                confidence=rel_data.get("confidence", 1.0),
            )

            related.append((other_entity, relationship))

        return related

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """
        Get semantic context for LLM prompts.

        Args:
            query: Query to find relevant context
            include_entities: Whether to include entities
            include_preferences: Whether to include preferences
            include_facts: Whether to include facts
            max_items: Maximum items per category

        Returns:
            Formatted context string
        """
        include_entities = kwargs.get("include_entities", True)
        include_preferences = kwargs.get("include_preferences", True)
        max_items = kwargs.get("max_items", 10)

        parts = []

        # Get relevant preferences
        if include_preferences:
            preferences = await self.search_preferences(query, limit=max_items)
            if preferences:
                parts.append("### User Preferences")
                for pref in preferences:
                    line = f"- [{pref.category}] {pref.preference}"
                    if pref.context:
                        line += f" (context: {pref.context})"
                    parts.append(line)

        # Get relevant entities
        if include_entities:
            entities = await self.search_entities(query, limit=max_items)
            if entities:
                parts.append("\n### Relevant Entities")
                for entity in entities:
                    line = f"- {entity.display_name} ({entity.type.value})"
                    if entity.description:
                        line += f": {entity.description}"
                    parts.append(line)

        return "\n".join(parts)

    async def _get_existing_entity_names(self, entity_type: EntityType) -> list[str]:
        """Get names of existing entities of a given type."""
        results = await self._client.execute_read(
            queries.SEARCH_ENTITIES_BY_TYPE,
            {"type": entity_type.value, "limit": 1000},
        )
        names = []
        for row in results:
            entity_data = dict(row["e"])
            names.append(entity_data["name"])
            if entity_data.get("canonical_name"):
                names.append(entity_data["canonical_name"])
        return list(set(names))

    async def get_preferences_by_category(
        self,
        category: str,
        *,
        limit: int = 100,
    ) -> list[Preference]:
        """
        Get all preferences in a category.

        Args:
            category: The preference category
            limit: Maximum results

        Returns:
            List of preferences in the category
        """
        results = await self._client.execute_read(
            queries.SEARCH_PREFERENCES_BY_CATEGORY,
            {"category": category, "limit": limit},
        )
        return [self._parse_preference(dict(r["p"])) for r in results]

    async def get_facts_about(
        self,
        subject: str,
        *,
        limit: int = 100,
    ) -> list[Fact]:
        """
        Get all facts about a subject.

        Args:
            subject: The fact subject
            limit: Maximum results

        Returns:
            List of facts about the subject
        """
        results = await self._client.execute_read(
            queries.GET_FACTS_BY_SUBJECT,
            {"subject": subject, "limit": limit},
        )
        return [self._parse_fact(dict(r["f"])) for r in results]

    async def search_facts(
        self,
        query: str,
        *,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> list[Fact]:
        """
        Search for facts by semantic similarity.

        Args:
            query: Search query
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of matching facts
        """
        if self._embedder is None:
            return []

        query_embedding = await self._embedder.embed(query)

        results = await self._client.execute_read(
            queries.SEARCH_FACTS_BY_EMBEDDING,
            {
                "embedding": query_embedding,
                "limit": limit,
                "threshold": threshold,
            },
        )

        facts = []
        for row in results:
            fact = self._parse_fact(dict(row["f"]))
            fact.metadata["similarity"] = row["score"]
            facts.append(fact)

        return facts

    async def get_entity_relationships(
        self,
        entity_name: str,
    ) -> list[tuple[Entity, Relationship]]:
        """
        Get relationships for an entity by name.

        Args:
            entity_name: Name of the entity

        Returns:
            List of (related_entity, relationship) tuples
        """
        # First get the entity
        entity = await self.get_entity_by_name(entity_name)
        if entity is None:
            return []

        return await self.get_related_entities(entity)

    def _parse_preference(self, data: dict[str, Any]) -> Preference:
        """Parse preference from database result."""
        return Preference(
            id=UUID(data["id"]),
            category=data["category"],
            preference=data["preference"],
            context=data.get("context"),
            confidence=data.get("confidence", 1.0),
            embedding=data.get("embedding"),
            created_at=_to_python_datetime(data.get("created_at")),
            metadata=_deserialize_metadata(data.get("metadata")),
        )

    def _parse_fact(self, data: dict[str, Any]) -> Fact:
        """Parse fact from database result."""
        return Fact(
            id=UUID(data["id"]),
            subject=data["subject"],
            predicate=data["predicate"],
            object=data["object"],
            confidence=data.get("confidence", 1.0),
            embedding=data.get("embedding"),
            valid_from=_to_python_datetime(data.get("valid_from"))
            if data.get("valid_from")
            else None,
            valid_until=_to_python_datetime(data.get("valid_until"))
            if data.get("valid_until")
            else None,
            created_at=_to_python_datetime(data.get("created_at")),
            metadata=_deserialize_metadata(data.get("metadata")),
        )
