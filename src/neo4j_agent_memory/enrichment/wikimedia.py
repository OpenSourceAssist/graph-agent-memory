"""Wikimedia API enrichment provider.

Uses the Wikipedia REST API to fetch:
- Page summaries
- Descriptions
- Wikidata IDs
- Images
- Related links

API Documentation: https://en.wikipedia.org/api/rest_v1/
Rate Limit: Be respectful, use User-Agent header (max ~2 req/sec recommended)
"""

import asyncio
import logging
import time
from typing import Any

from neo4j_agent_memory.enrichment.base import EnrichmentResult, EnrichmentStatus

logger = logging.getLogger(__name__)


class WikimediaProvider:
    """Enrichment provider using Wikipedia/Wikimedia APIs.

    Fetches entity information from Wikipedia including summaries, descriptions,
    Wikidata IDs, and thumbnail images.

    Example:
        provider = WikimediaProvider()
        result = await provider.enrich("Albert Einstein", "PERSON")
        print(result.description)  # "German-born theoretical physicist"
        print(result.wikipedia_url)  # "https://en.wikipedia.org/wiki/Albert_Einstein"
    """

    BASE_URL = "https://{lang}.wikipedia.org/api/rest_v1"

    # Entity types this provider works well for
    SUPPORTED_TYPES = ["PERSON", "ORGANIZATION", "LOCATION", "EVENT", "OBJECT", "CONCEPT"]

    def __init__(
        self,
        *,
        user_agent: str = "neo4j-agent-memory/1.0",
        rate_limit: float = 0.5,  # Max 2 requests/sec
        timeout: float = 10.0,
        language: str = "en",
    ):
        """
        Initialize Wikimedia enrichment provider.

        Args:
            user_agent: User-Agent header (required by Wikimedia ToS)
            rate_limit: Minimum seconds between requests (default 0.5)
            timeout: Request timeout in seconds
            language: Default language for Wikipedia (e.g., "en", "de", "fr")
        """
        self._user_agent = user_agent
        self._rate_limit = rate_limit
        self._timeout = timeout
        self._language = language
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return "wikimedia"

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
        language: str | None = None,
    ) -> EnrichmentResult:
        """
        Fetch Wikipedia summary and metadata for entity.

        Args:
            entity_name: Name of the entity to look up
            entity_type: Entity type (PERSON, ORGANIZATION, etc.)
            context: Optional disambiguating context
            language: Language code (defaults to provider's language)

        Returns:
            EnrichmentResult with Wikipedia data or error status
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

        lang = language or self._language
        await self._rate_limit_wait()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                # Try direct page lookup first
                page_title = entity_name.replace(" ", "_")
                summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{page_title}"

                response = await client.get(
                    summary_url,
                    headers={"User-Agent": self._user_agent},
                    follow_redirects=True,
                )

                if response.status_code == 404:
                    # Page not found - try search API for fuzzy matching
                    return await self._search_and_enrich(
                        client, entity_name, entity_type, lang, context
                    )

                if response.status_code == 429:
                    return EnrichmentResult(
                        entity_name=entity_name,
                        entity_type=entity_type,
                        provider=self.name,
                        status=EnrichmentStatus.RATE_LIMITED,
                        error_message="Rate limited by Wikipedia API",
                    )

                response.raise_for_status()
                data = response.json()

                return self._parse_summary_response(data, entity_name, entity_type, lang)

        except Exception as e:
            if "httpx" in str(type(e).__module__):
                # HTTP-related error
                logger.warning(f"Wikipedia HTTP error for '{entity_name}': {e}")
            else:
                logger.warning(f"Wikipedia enrichment error for '{entity_name}': {e}")
            return EnrichmentResult(
                entity_name=entity_name,
                entity_type=entity_type,
                provider=self.name,
                status=EnrichmentStatus.ERROR,
                error_message=str(e),
            )

    async def _search_and_enrich(
        self,
        client: Any,  # httpx.AsyncClient
        entity_name: str,
        entity_type: str,
        language: str,
        context: str | None = None,
    ) -> EnrichmentResult:
        """Search Wikipedia and enrich with best match."""
        # Build search query with optional context
        search_query = entity_name
        if context:
            search_query = f"{entity_name} {context}"

        search_url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_query,
            "format": "json",
            "srlimit": 1,
        }

        await self._rate_limit_wait()

        response = await client.get(
            search_url,
            params=params,
            headers={"User-Agent": self._user_agent},
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("query", {}).get("search", [])
        if not results:
            return EnrichmentResult(
                entity_name=entity_name,
                entity_type=entity_type,
                provider=self.name,
                status=EnrichmentStatus.NOT_FOUND,
            )

        # Get summary for best match
        title = results[0]["title"]
        await self._rate_limit_wait()

        page_title = title.replace(" ", "_")
        summary_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{page_title}"
        response = await client.get(
            summary_url,
            headers={"User-Agent": self._user_agent},
            follow_redirects=True,
        )
        response.raise_for_status()

        return self._parse_summary_response(response.json(), entity_name, entity_type, language)

    def _parse_summary_response(
        self,
        data: dict[str, Any],
        entity_name: str,
        entity_type: str,
        language: str,
    ) -> EnrichmentResult:
        """Parse Wikipedia summary API response."""
        # Check if this is a disambiguation page
        if data.get("type") == "disambiguation":
            return EnrichmentResult(
                entity_name=entity_name,
                entity_type=entity_type,
                provider=self.name,
                status=EnrichmentStatus.NOT_FOUND,
                error_message="Wikipedia returned disambiguation page - need more context",
            )

        # Calculate confidence based on title match
        title = data.get("title", "")
        confidence = 0.9 if title.lower() == entity_name.lower() else 0.7

        # Extract thumbnail URL
        thumbnail = data.get("thumbnail", {})
        image_url = thumbnail.get("source") if thumbnail else None

        # Build content URLs
        content_urls = data.get("content_urls", {})
        desktop_urls = content_urls.get("desktop", {})
        wikipedia_url = desktop_urls.get("page")

        return EnrichmentResult(
            entity_name=entity_name,
            entity_type=entity_type,
            provider=self.name,
            status=EnrichmentStatus.SUCCESS,
            description=data.get("description"),
            summary=data.get("extract"),
            wikipedia_url=wikipedia_url,
            wikidata_id=data.get("wikibase_item"),
            image_url=image_url,
            source_url=wikipedia_url,
            metadata={
                "title": title,
                "pageid": data.get("pageid"),
                "lang": language,
                "type": data.get("type"),
                "coordinates": data.get("coordinates"),
                "originalimage": data.get("originalimage", {}).get("source"),
            },
            confidence=confidence,
        )
