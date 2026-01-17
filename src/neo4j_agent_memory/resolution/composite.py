"""Composite entity resolution using multiple strategies."""

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


class CompositeResolver(BaseResolver):
    """
    Composite resolver that chains multiple resolution strategies.

    Tries resolvers in order: Exact -> Fuzzy -> Semantic
    Returns the first match that meets the threshold.
    """

    def __init__(
        self,
        *,
        embedder: "Embedder | None" = None,
        exact_threshold: float = 1.0,
        fuzzy_threshold: float = 0.85,
        semantic_threshold: float = 0.8,
    ):
        """
        Initialize composite resolver.

        Args:
            embedder: Optional embedder for semantic matching
            exact_threshold: Threshold for exact matching
            fuzzy_threshold: Threshold for fuzzy matching
            semantic_threshold: Threshold for semantic matching
        """
        self._embedder = embedder
        self._exact_threshold = exact_threshold
        self._fuzzy_threshold = fuzzy_threshold
        self._semantic_threshold = semantic_threshold

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
    ) -> ResolvedEntity:
        """Resolve entity using chained strategies."""
        if not existing_entities:
            return ResolvedEntity(
                original_name=entity_name,
                canonical_name=entity_name,
                entity_type=entity_type,
                confidence=1.0,
                match_type="none",
            )

        # Try exact match first
        result = await self._exact_resolver.resolve(
            entity_name, entity_type, existing_entities=existing_entities
        )
        if result.original_name != result.canonical_name:
            return result

        # Try fuzzy match
        if self._fuzzy_resolver is not None and self._fuzzy_resolver.is_available:
            result = await self._fuzzy_resolver.resolve(
                entity_name, entity_type, existing_entities=existing_entities
            )
            if result.original_name != result.canonical_name:
                return result

        # Try semantic match
        if self._semantic_resolver is not None:
            result = await self._semantic_resolver.resolve(
                entity_name, entity_type, existing_entities=existing_entities
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
    ) -> list[ResolutionMatch]:
        """Find matches from candidates using all strategies."""
        all_matches: dict[str, ResolutionMatch] = {}

        # Collect matches from all resolvers
        exact_matches = await self._exact_resolver.find_matches(
            entity_name, entity_type, candidates
        )
        for match in exact_matches:
            all_matches[match.entity2_name] = match

        if self._fuzzy_resolver is not None and self._fuzzy_resolver.is_available:
            fuzzy_matches = await self._fuzzy_resolver.find_matches(
                entity_name, entity_type, candidates
            )
            for match in fuzzy_matches:
                if match.entity2_name not in all_matches:
                    all_matches[match.entity2_name] = match

        if self._semantic_resolver is not None:
            semantic_matches = await self._semantic_resolver.find_matches(
                entity_name, entity_type, candidates
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
        """
        if not entities:
            return []

        # First pass: resolve each entity
        results = []
        canonical_map: dict[str, str] = {}

        for name, entity_type in entities:
            # Check if we've already seen a similar entity
            normalized = self._normalize(name)
            if normalized in canonical_map:
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

            # Resolve against already seen entities
            existing = list(canonical_map.values())
            result = await self.resolve(name, entity_type, existing_entities=existing)

            if result.original_name != result.canonical_name:
                # Found a match
                canonical_map[normalized] = result.canonical_name
            else:
                # New entity
                canonical_map[normalized] = name

            results.append(result)

        return results
