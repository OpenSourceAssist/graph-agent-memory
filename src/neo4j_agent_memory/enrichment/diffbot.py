"""Diffbot Knowledge Graph enrichment provider.

Uses the Diffbot Knowledge Graph API to fetch structured entity data.
Excellent for organizations, people, and products.

API Documentation: https://docs.diffbot.com/reference/introduction-to-the-knowledge-graph
Requires API key.
"""

import asyncio
import logging
import time
from typing import Any

from neo4j_agent_memory.enrichment.base import EnrichmentResult, EnrichmentStatus

logger = logging.getLogger(__name__)


class DiffbotProvider:
    """Enrichment provider using Diffbot Knowledge Graph API.

    Provides structured entity data from Diffbot's knowledge graph, including
    detailed metadata, related entities, and rich descriptions.

    Requires a Diffbot API key. Sign up at https://www.diffbot.com/

    Example:
        provider = DiffbotProvider(api_key="your-api-key")
        result = await provider.enrich("Apple Inc", "ORGANIZATION")
        print(result.description)
        print(result.metadata.get("industries"))
    """

    BASE_URL = "https://kg.diffbot.com/kg/v3"

    # Entity type mapping to Diffbot types
    TYPE_MAPPING = {
        "PERSON": "Person",
        "ORGANIZATION": "Organization",
        "LOCATION": "Place",
        "OBJECT": "Product",
        "EVENT": "Event",
    }

    SUPPORTED_TYPES = list(TYPE_MAPPING.keys())

    def __init__(
        self,
        api_key: str,
        *,
        rate_limit: float = 0.2,  # Diffbot allows ~5 req/sec
        timeout: float = 15.0,
    ):
        """
        Initialize Diffbot enrichment provider.

        Args:
            api_key: Diffbot API key
            rate_limit: Minimum seconds between requests (default 0.2)
            timeout: Request timeout in seconds
        """
        self._api_key = api_key
        self._rate_limit = rate_limit
        self._timeout = timeout
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return "diffbot"

    @property
    def supported_entity_types(self) -> list[str]:
        return self.SUPPORTED_TYPES

    def supports_entity_type(self, entity_type: str) -> bool:
        return entity_type.upper() in self.SUPPORTED_TYPES

    async def _rate_limit_wait(self) -> None:
        """Wait if needed to respect rate limit."""
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._rate_limit:
                await asyncio.sleep(self._rate_limit - elapsed)
            self._last_request_time = time.time()

    async def enrich(
        self,
        entity_name: str,
        entity_type: str,
        *,
        context: str | None = None,
        language: str = "en",
    ) -> EnrichmentResult:
        """
        Fetch Diffbot Knowledge Graph data for entity.

        Args:
            entity_name: Name of the entity to look up
            entity_type: Entity type (PERSON, ORGANIZATION, etc.)
            context: Optional disambiguating context
            language: Language code (currently unused by Diffbot)

        Returns:
            EnrichmentResult with Diffbot data or error status
        """
        # Check entity type first (before trying to import httpx)
        if not self.supports_entity_type(entity_type):
            return EnrichmentResult(
                entity_name=entity_name,
                entity_type=entity_type,
                provider=self.name,
                status=EnrichmentStatus.SKIPPED,
                error_message=f"Entity type {entity_type} not supported",
            )

        try:
            import httpx
        except ImportError:
            return EnrichmentResult(
                entity_name=entity_name,
                entity_type=entity_type,
                provider=self.name,
                status=EnrichmentStatus.ERROR,
                error_message="httpx required: pip install httpx",
            )

        await self._rate_limit_wait()

        try:
            diffbot_type = self.TYPE_MAPPING.get(entity_type.upper(), "")

            # Build Diffbot DQL query
            query = f'name:"{entity_name}"'
            if diffbot_type:
                query += f" type:{diffbot_type}"
            if context:
                query += f" {context}"

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/dql",
                    params={
                        "type": "query",
                        "token": self._api_key,
                        "query": query,
                        "size": 1,
                    },
                )

                if response.status_code == 401:
                    return EnrichmentResult(
                        entity_name=entity_name,
                        entity_type=entity_type,
                        provider=self.name,
                        status=EnrichmentStatus.ERROR,
                        error_message="Invalid Diffbot API key",
                    )

                if response.status_code == 429:
                    return EnrichmentResult(
                        entity_name=entity_name,
                        entity_type=entity_type,
                        provider=self.name,
                        status=EnrichmentStatus.RATE_LIMITED,
                        error_message="Rate limited by Diffbot API",
                    )

                response.raise_for_status()
                data = response.json()

                return self._parse_response(data, entity_name, entity_type)

        except Exception as e:
            if "httpx" in str(type(e).__module__):
                logger.warning(f"Diffbot HTTP error for '{entity_name}': {e}")
            else:
                logger.warning(f"Diffbot enrichment error for '{entity_name}': {e}")
            return EnrichmentResult(
                entity_name=entity_name,
                entity_type=entity_type,
                provider=self.name,
                status=EnrichmentStatus.ERROR,
                error_message=str(e),
            )

    def _parse_response(
        self,
        data: dict[str, Any],
        entity_name: str,
        entity_type: str,
    ) -> EnrichmentResult:
        """Parse Diffbot KG API response."""
        entities = data.get("data", [])

        if not entities:
            return EnrichmentResult(
                entity_name=entity_name,
                entity_type=entity_type,
                provider=self.name,
                status=EnrichmentStatus.NOT_FOUND,
            )

        entity = entities[0]

        # Extract description
        description = entity.get("description") or entity.get("summary")

        # Extract images
        images: list[str] = []
        if entity.get("image"):
            images.append(entity["image"])
        images.extend(entity.get("images", []))

        # Build related entities
        related: list[dict[str, Any]] = []
        relation_fields = [
            "employers",
            "subsidiaries",
            "founders",
            "locations",
            "parent",
            "children",
            "spouses",
            "affiliations",
        ]
        for rel_type in relation_fields:
            for item in entity.get(rel_type, []):
                if isinstance(item, dict):
                    related.append(
                        {
                            "name": item.get("name"),
                            "relation": rel_type,
                            "diffbot_uri": item.get("diffbotUri"),
                        }
                    )

        # Calculate confidence from Diffbot importance score
        importance = entity.get("importance", 0) or 0
        confidence = min(1.0, importance / 100 + 0.5)

        # Build comprehensive metadata
        metadata: dict[str, Any] = {
            "types": entity.get("types", []),
            "importance": importance,
            "nbIncomingEdges": entity.get("nbIncomingEdges"),
        }

        # Person-specific fields
        if entity_type.upper() == "PERSON":
            metadata.update(
                {
                    "birthDate": entity.get("birthDate"),
                    "deathDate": entity.get("deathDate"),
                    "gender": entity.get("gender"),
                    "nationalities": entity.get("nationalities", []),
                    "educations": entity.get("educations", []),
                    "employments": entity.get("employments", []),
                }
            )

        # Organization-specific fields
        if entity_type.upper() == "ORGANIZATION":
            metadata.update(
                {
                    "foundingDate": entity.get("foundingDate"),
                    "nbEmployees": entity.get("nbEmployees"),
                    "nbEmployeesMin": entity.get("nbEmployeesMin"),
                    "nbEmployeesMax": entity.get("nbEmployeesMax"),
                    "revenue": entity.get("revenue"),
                    "industries": entity.get("industries", []),
                    "categories": entity.get("categories", []),
                    "isPublic": entity.get("isPublic"),
                    "stock": entity.get("stock"),
                }
            )

        # Location-specific fields
        if entity_type.upper() == "LOCATION":
            metadata.update(
                {
                    "country": entity.get("country"),
                    "region": entity.get("region"),
                    "city": entity.get("city"),
                    "latitude": entity.get("latitude"),
                    "longitude": entity.get("longitude"),
                    "population": entity.get("population"),
                }
            )

        # Clean up None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return EnrichmentResult(
            entity_name=entity_name,
            entity_type=entity_type,
            provider=self.name,
            status=EnrichmentStatus.SUCCESS,
            description=description,
            summary=entity.get("summary"),
            diffbot_uri=entity.get("diffbotUri"),
            image_url=images[0] if images else None,
            images=images,
            related_entities=related,
            source_url=entity.get("origin") or entity.get("homepageUri"),
            metadata=metadata,
            confidence=confidence,
        )
