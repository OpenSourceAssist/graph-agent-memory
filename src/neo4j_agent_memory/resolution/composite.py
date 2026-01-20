"""Composite entity resolution using multiple strategies."""

import logging
from typing import TYPE_CHECKING

from neo4j_agent_memory.resolution.base import (
    BaseResolver,
    ResolutionMatch,
    ResolvedEntity,
)
from neo4j_agent_memory.resolution.exact import ExactMatchResolver
from neo4j_agent_memory.resolution.fuzzy import FuzzyMatchResolver

if TYPE_CHECKING:
    from neo4j_agent_memory.embeddings.base import Embedder

logger = logging.getLogger(__name__)


class CompositeResolver(BaseResolver):
    """
    Composite resolver that chains multiple resolution strategies.

    Tries resolvers in order: Exact -> Fuzzy -> Semantic
    Returns the first match that meets the threshold.

    Type-aware resolution ensures that entities of different types
    are never merged (e.g., PERSON "John" won't match LOCATION "John").
    """

    def __init__(
        self,
        *,
        embedder: "Embedder | None" = None,
        exact_threshold: float = 1.0,
        fuzzy_threshold: float = 0.85,
        semantic_threshold: float = 0.8,
        type_strict: bool = True,
    ):
        """
        Initialize composite resolver.

        Args:
            embedder: Optional embedder for semantic matching
            exact_threshold: Threshold for exact matching
            fuzzy_threshold: Threshold for fuzzy matching
            semantic_threshold: Threshold for semantic matching
            type_strict: If True, only match entities of the same type
        """
        self._embedder = embedder
        self._exact_threshold = exact_threshold
        self._fuzzy_threshold = fuzzy_threshold
        self._semantic_threshold = semantic_threshold
        self._type_strict = type_strict

        # Initialize resolvers
        self._exact_resolver = ExactMatchResolver()
        self._fuzzy_resolver: FuzzyMatchResolver | None = None
        self._semantic_resolver = None

        # Try to initialize fuzzy resolver
        try:
            self._fuzzy_resolver = FuzzyMatchResolver(threshold=fuzzy_threshold)
        except Exception:
            pass  # RapidFuzz not available

        # Initialize semantic resolver if embedder provided
        if embedder is not None:
            from neo4j_agent_memory.resolution.semantic import SemanticMatchResolver

            self._semantic_resolver = SemanticMatchResolver(embedder, threshold=semantic_threshold)

    async def resolve(
        self,
        entity_name: str,
        entity_type: str,
        *,
        existing_entities: list[str] | None = None,
        existing_entity_types: dict[str, str] | None = None,
    ) -> ResolvedEntity:
        """
        Resolve entity using chained strategies.

        Args:
            entity_name: Name of entity to resolve
            entity_type: Type of entity (PERSON, OBJECT, LOCATION, etc.)
            existing_entities: List of existing entity names to match against
            existing_entity_types: Optional mapping of entity names to their types
                                   for type-aware resolution

        Returns:
            ResolvedEntity with canonical name
        """
        if not existing_entities:
            return ResolvedEntity(
                original_name=entity_name,
                canonical_name=entity_name,
                entity_type=entity_type,
                confidence=1.0,
                match_type="none",
            )

        # Filter candidates by type if type-strict and type info available
        candidates = existing_entities
        if self._type_strict and existing_entity_types:
            candidates = [
                name
                for name in existing_entities
                if existing_entity_types.get(name, entity_type) == entity_type
            ]
            if not candidates:
                return ResolvedEntity(
                    original_name=entity_name,
                    canonical_name=entity_name,
                    entity_type=entity_type,
                    confidence=1.0,
                    match_type="none",
                )

        # Try exact match first
        result = await self._exact_resolver.resolve(
            entity_name, entity_type, existing_entities=candidates
        )
        if result.original_name != result.canonical_name:
            return result

        # Try fuzzy match
        if self._fuzzy_resolver is not None and self._fuzzy_resolver.is_available:
            result = await self._fuzzy_resolver.resolve(
                entity_name, entity_type, existing_entities=candidates
            )
            if result.original_name != result.canonical_name:
                return result

        # Try semantic match
        if self._semantic_resolver is not None:
            result = await self._semantic_resolver.resolve(
                entity_name, entity_type, existing_entities=candidates
            )
            if result.original_name != result.canonical_name:
                return result

        # No match found
        return ResolvedEntity(
            original_name=entity_name,
            canonical_name=entity_name,
            entity_type=entity_type,
            confidence=1.0,
            match_type="none",
        )

    async def find_matches(
        self,
        entity_name: str,
        entity_type: str,
        candidates: list[str],
        *,
        candidate_types: dict[str, str] | None = None,
    ) -> list[ResolutionMatch]:
        """
        Find matches from candidates using all strategies.

        Args:
            entity_name: Name of entity to match
            entity_type: Type of entity
            candidates: List of candidate entity names
            candidate_types: Optional mapping of candidate names to types

        Returns:
            List of matches sorted by similarity
        """
        # Filter by type if type-strict
        filtered_candidates = candidates
        if self._type_strict and candidate_types:
            filtered_candidates = [
                name for name in candidates if candidate_types.get(name, entity_type) == entity_type
            ]

        if not filtered_candidates:
            return []

        all_matches: dict[str, ResolutionMatch] = {}

        # Collect matches from all resolvers
        exact_matches = await self._exact_resolver.find_matches(
            entity_name, entity_type, filtered_candidates
        )
        for match in exact_matches:
            all_matches[match.entity2_name] = match

        if self._fuzzy_resolver is not None and self._fuzzy_resolver.is_available:
            fuzzy_matches = await self._fuzzy_resolver.find_matches(
                entity_name, entity_type, filtered_candidates
            )
            for match in fuzzy_matches:
                if match.entity2_name not in all_matches:
                    all_matches[match.entity2_name] = match

        if self._semantic_resolver is not None:
            semantic_matches = await self._semantic_resolver.find_matches(
                entity_name, entity_type, filtered_candidates
            )
            for match in semantic_matches:
                if match.entity2_name not in all_matches:
                    all_matches[match.entity2_name] = match

        # Sort by similarity score descending
        matches = list(all_matches.values())
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches

    async def resolve_batch(
        self,
        entities: list[tuple[str, str]],
    ) -> list[ResolvedEntity]:
        """
        Resolve multiple entities with cross-entity deduplication.

        Uses Union-Find to cluster similar entities together.
        Respects type constraints - entities of different types
        are never merged.

        Args:
            entities: List of (name, type) tuples

        Returns:
            List of resolved entities
        """
        if not entities:
            return []

        # First pass: resolve each entity
        results = []
        canonical_map: dict[str, str] = {}  # normalized_name -> canonical_name
        type_map: dict[str, str] = {}  # normalized_name -> entity_type

        for name, entity_type in entities:
            # Check if we've already seen a similar entity
            normalized = self._normalize(name)

            # Check for exact normalized match of same type
            if normalized in canonical_map and type_map.get(normalized) == entity_type:
                results.append(
                    ResolvedEntity(
                        original_name=name,
                        canonical_name=canonical_map[normalized],
                        entity_type=entity_type,
                        confidence=1.0,
                        match_type="batch",
                    )
                )
                continue

            # Build existing entities of same type for matching
            existing_same_type = [canonical_map[n] for n, t in type_map.items() if t == entity_type]

            if existing_same_type:
                result = await self.resolve(
                    name,
                    entity_type,
                    existing_entities=existing_same_type,
                )
            else:
                result = ResolvedEntity(
                    original_name=name,
                    canonical_name=name,
                    entity_type=entity_type,
                    confidence=1.0,
                    match_type="none",
                )

            if result.original_name != result.canonical_name:
                # Found a match
                canonical_map[normalized] = result.canonical_name
            else:
                # New entity
                canonical_map[normalized] = name

            type_map[normalized] = entity_type
            results.append(result)

        return results

    async def resolve_with_types(
        self,
        entities: list[tuple[str, str]],
        existing_entities: list[tuple[str, str]] | None = None,
    ) -> list[ResolvedEntity]:
        """
        Resolve entities with full type information.

        This is the preferred method when you have type information
        for existing entities.

        Args:
            entities: List of (name, type) tuples to resolve
            existing_entities: List of (name, type) tuples to match against

        Returns:
            List of resolved entities
        """
        if not entities:
            return []

        # Build type-aware lookup
        existing_by_type: dict[str, list[str]] = {}
        existing_types: dict[str, str] = {}

        if existing_entities:
            for name, etype in existing_entities:
                if etype not in existing_by_type:
                    existing_by_type[etype] = []
                existing_by_type[etype].append(name)
                existing_types[name] = etype

        results = []
        for name, entity_type in entities:
            # Only consider entities of the same type
            candidates = existing_by_type.get(entity_type, [])

            if candidates:
                result = await self.resolve(
                    name,
                    entity_type,
                    existing_entities=candidates,
                    existing_entity_types=existing_types,
                )
            else:
                result = ResolvedEntity(
                    original_name=name,
                    canonical_name=name,
                    entity_type=entity_type,
                    confidence=1.0,
                    match_type="none",
                )

            results.append(result)

            # Add to existing for subsequent resolutions
            if result.canonical_name not in existing_types:
                if entity_type not in existing_by_type:
                    existing_by_type[entity_type] = []
                existing_by_type[entity_type].append(result.canonical_name)
                existing_types[result.canonical_name] = entity_type

        return results
