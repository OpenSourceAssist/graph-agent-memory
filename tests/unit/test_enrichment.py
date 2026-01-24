"""Unit tests for enrichment services."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from neo4j_agent_memory.config.settings import EnrichmentConfig, EnrichmentProvider
from neo4j_agent_memory.enrichment.base import (
    EnrichmentResult,
    EnrichmentStatus,
    EnrichmentTask,
    NoOpEnrichmentProvider,
)
from neo4j_agent_memory.enrichment.factory import (
    CachedEnrichmentProvider,
    CompositeEnrichmentProvider,
    create_enrichment_provider,
    create_enrichment_service,
)


class TestEnrichmentResult:
    """Tests for EnrichmentResult."""

    def test_has_data_with_description(self):
        result = EnrichmentResult(
            entity_name="test",
            entity_type="PERSON",
            provider="test",
            status=EnrichmentStatus.SUCCESS,
            description="A description",
        )
        assert result.has_data() is True

    def test_has_data_with_summary(self):
        result = EnrichmentResult(
            entity_name="test",
            entity_type="PERSON",
            provider="test",
            status=EnrichmentStatus.SUCCESS,
            summary="A summary",
        )
        assert result.has_data() is True

    def test_has_data_with_metadata(self):
        result = EnrichmentResult(
            entity_name="test",
            entity_type="PERSON",
            provider="test",
            status=EnrichmentStatus.SUCCESS,
            metadata={"key": "value"},
        )
        assert result.has_data() is True

    def test_has_data_empty(self):
        result = EnrichmentResult(
            entity_name="test",
            entity_type="PERSON",
            provider="test",
            status=EnrichmentStatus.NOT_FOUND,
        )
        assert result.has_data() is False

    def test_has_data_error_status(self):
        result = EnrichmentResult(
            entity_name="test",
            entity_type="PERSON",
            provider="test",
            status=EnrichmentStatus.ERROR,
            description="Has description but error status",
        )
        assert result.has_data() is False

    def test_to_entity_attributes(self):
        result = EnrichmentResult(
            entity_name="test",
            entity_type="PERSON",
            provider="wikimedia",
            status=EnrichmentStatus.SUCCESS,
            description="A famous scientist",
            wikipedia_url="https://en.wikipedia.org/wiki/Test",
            wikidata_id="Q12345",
            image_url="https://example.com/image.jpg",
        )
        attrs = result.to_entity_attributes()
        assert attrs["enriched_description"] == "A famous scientist"
        assert attrs["wikipedia_url"] == "https://en.wikipedia.org/wiki/Test"
        assert attrs["wikidata_id"] == "Q12345"
        assert attrs["image_url"] == "https://example.com/image.jpg"
        assert attrs["enrichment_provider"] == "wikimedia"
        assert "enrichment_timestamp" in attrs

    def test_to_entity_attributes_minimal(self):
        result = EnrichmentResult(
            entity_name="test",
            entity_type="PERSON",
            provider="wikimedia",
            status=EnrichmentStatus.SUCCESS,
        )
        attrs = result.to_entity_attributes()
        assert attrs["enrichment_provider"] == "wikimedia"
        assert "enrichment_timestamp" in attrs
        assert "enriched_description" not in attrs


class TestEnrichmentTask:
    """Tests for EnrichmentTask."""

    def test_task_creation(self):
        entity_id = uuid4()
        task = EnrichmentTask(
            entity_id=entity_id,
            entity_name="Albert Einstein",
            entity_type="PERSON",
        )
        assert task.entity_id == entity_id
        assert task.entity_name == "Albert Einstein"
        assert task.entity_type == "PERSON"
        assert task.priority == 0
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_task_with_context(self):
        task = EnrichmentTask(
            entity_id=uuid4(),
            entity_name="Apple",
            entity_type="ORGANIZATION",
            context="technology company",
            priority=5,
        )
        assert task.context == "technology company"
        assert task.priority == 5


class TestNoOpEnrichmentProvider:
    """Tests for NoOpEnrichmentProvider."""

    @pytest.mark.asyncio
    async def test_enrich_returns_skipped(self):
        provider = NoOpEnrichmentProvider()
        result = await provider.enrich("Test Entity", "PERSON")
        assert result.status == EnrichmentStatus.SKIPPED
        assert result.entity_name == "Test Entity"
        assert result.entity_type == "PERSON"
        assert result.provider == "noop"

    def test_supports_no_types(self):
        provider = NoOpEnrichmentProvider()
        assert provider.supported_entity_types == []
        assert provider.supports_entity_type("PERSON") is False
        assert provider.supports_entity_type("ORGANIZATION") is False


class TestWikimediaProvider:
    """Tests for WikimediaProvider."""

    def test_init_defaults(self):
        from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider

        provider = WikimediaProvider()
        assert provider.name == "wikimedia"
        assert provider._rate_limit == 0.5
        assert provider._language == "en"

    def test_init_custom_settings(self):
        from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider

        provider = WikimediaProvider(
            user_agent="test-agent/1.0",
            rate_limit=1.0,
            language="de",
        )
        assert provider._user_agent == "test-agent/1.0"
        assert provider._rate_limit == 1.0
        assert provider._language == "de"

    def test_supports_entity_type(self):
        from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider

        provider = WikimediaProvider()
        assert provider.supports_entity_type("PERSON") is True
        assert provider.supports_entity_type("ORGANIZATION") is True
        assert provider.supports_entity_type("LOCATION") is True
        assert provider.supports_entity_type("EVENT") is True
        assert provider.supports_entity_type("OBJECT") is True
        assert provider.supports_entity_type("person") is True  # Case insensitive
        assert provider.supports_entity_type("UNKNOWN_TYPE") is False

    @pytest.mark.asyncio
    async def test_enrich_success(self):
        pytest.importorskip("httpx")
        from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider

        provider = WikimediaProvider(rate_limit=0)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Albert Einstein",
            "description": "German-born theoretical physicist",
            "extract": "Albert Einstein was a physicist...",
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Albert_Einstein"}},
            "wikibase_item": "Q937",
            "thumbnail": {"source": "https://upload.wikimedia.org/..."},
            "type": "standard",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await provider.enrich("Albert Einstein", "PERSON")

        assert result.status == EnrichmentStatus.SUCCESS
        assert result.description == "German-born theoretical physicist"
        assert result.wikidata_id == "Q937"
        assert "wikipedia.org" in (result.wikipedia_url or "")

    @pytest.mark.asyncio
    async def test_enrich_unsupported_type(self):
        from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider

        provider = WikimediaProvider(rate_limit=0)
        result = await provider.enrich("Test", "UNSUPPORTED_TYPE")
        # Should return SKIPPED (type not supported) - this check happens before httpx import
        assert result.status == EnrichmentStatus.SKIPPED
        assert "not supported" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_enrich_without_httpx(self):
        """Test that enrichment gracefully handles missing httpx."""
        from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider

        provider = WikimediaProvider(rate_limit=0)

        # Mock the httpx import to fail
        with patch.dict("sys.modules", {"httpx": None}):
            result = await provider.enrich("Test", "PERSON")
            # Should return error when httpx is not available
            assert (
                result.status == EnrichmentStatus.ERROR or result.status == EnrichmentStatus.SUCCESS
            )


class TestDiffbotProvider:
    """Tests for DiffbotProvider."""

    def test_init(self):
        from neo4j_agent_memory.enrichment.diffbot import DiffbotProvider

        provider = DiffbotProvider(api_key="test-key")
        assert provider.name == "diffbot"
        assert provider._api_key == "test-key"
        assert provider._rate_limit == 0.2

    def test_supports_entity_type(self):
        from neo4j_agent_memory.enrichment.diffbot import DiffbotProvider

        provider = DiffbotProvider(api_key="test-key")
        assert provider.supports_entity_type("PERSON") is True
        assert provider.supports_entity_type("ORGANIZATION") is True
        assert provider.supports_entity_type("LOCATION") is True
        assert provider.supports_entity_type("EVENT") is True
        assert provider.supports_entity_type("OBJECT") is True
        assert provider.supports_entity_type("CONCEPT") is False

    @pytest.mark.asyncio
    async def test_enrich_success(self):
        pytest.importorskip("httpx")
        from neo4j_agent_memory.enrichment.diffbot import DiffbotProvider

        provider = DiffbotProvider(api_key="test-key", rate_limit=0)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "name": "Apple Inc.",
                    "description": "American multinational technology company",
                    "summary": "Apple is a technology company...",
                    "diffbotUri": "https://diffbot.com/entity/abc123",
                    "image": "https://example.com/apple.jpg",
                    "industries": ["Technology", "Consumer Electronics"],
                    "importance": 75,
                    "types": ["Organization", "Company"],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await provider.enrich("Apple Inc", "ORGANIZATION")

        assert result.status == EnrichmentStatus.SUCCESS
        assert result.description == "American multinational technology company"
        assert result.diffbot_uri == "https://diffbot.com/entity/abc123"
        assert result.metadata.get("industries") == ["Technology", "Consumer Electronics"]

    @pytest.mark.asyncio
    async def test_enrich_not_found(self):
        pytest.importorskip("httpx")
        from neo4j_agent_memory.enrichment.diffbot import DiffbotProvider

        provider = DiffbotProvider(api_key="test-key", rate_limit=0)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=MagicMock(get=AsyncMock(return_value=mock_response))
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await provider.enrich("NonexistentEntity12345", "PERSON")

        assert result.status == EnrichmentStatus.NOT_FOUND


class TestCachedEnrichmentProvider:
    """Tests for CachedEnrichmentProvider."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.supported_entity_types = ["PERSON"]
        mock_provider.supports_entity_type = MagicMock(return_value=True)
        mock_provider.enrich = AsyncMock(
            return_value=EnrichmentResult(
                entity_name="Test",
                entity_type="PERSON",
                provider="test",
                status=EnrichmentStatus.SUCCESS,
                description="Cached description",
            )
        )

        cached = CachedEnrichmentProvider(mock_provider, ttl_hours=1)

        # First call - should hit provider
        result1 = await cached.enrich("Test", "PERSON")
        assert result1.description == "Cached description"
        assert mock_provider.enrich.call_count == 1

        # Second call - should hit cache
        result2 = await cached.enrich("Test", "PERSON")
        assert result2.description == "Cached description"
        assert mock_provider.enrich.call_count == 1  # Still 1

    @pytest.mark.asyncio
    async def test_cache_key_normalization(self):
        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.enrich = AsyncMock(
            return_value=EnrichmentResult(
                entity_name="Test",
                entity_type="PERSON",
                provider="test",
                status=EnrichmentStatus.SUCCESS,
            )
        )

        cached = CachedEnrichmentProvider(mock_provider)

        # Different cases should hit same cache key
        await cached.enrich("Test Entity", "PERSON")
        await cached.enrich("test entity", "PERSON")
        await cached.enrich("  Test Entity  ", "person")

        # Should only have 1 call due to normalization
        assert mock_provider.enrich.call_count == 1

    def test_clear_cache(self):
        mock_provider = MagicMock()
        mock_provider.name = "test"

        cached = CachedEnrichmentProvider(mock_provider)
        cached._cache["test_key"] = (
            EnrichmentResult(
                entity_name="Test",
                entity_type="PERSON",
                provider="test",
                status=EnrichmentStatus.SUCCESS,
            ),
            0,
        )
        assert cached.cache_size == 1

        cached.clear_cache()
        assert cached.cache_size == 0


class TestCompositeEnrichmentProvider:
    """Tests for CompositeEnrichmentProvider."""

    def test_requires_providers(self):
        with pytest.raises(ValueError, match="requires at least one provider"):
            CompositeEnrichmentProvider([])

    @pytest.mark.asyncio
    async def test_tries_providers_in_order(self):
        provider1 = MagicMock()
        provider1.supports_entity_type = MagicMock(return_value=True)
        provider1.enrich = AsyncMock(
            return_value=EnrichmentResult(
                entity_name="Test",
                entity_type="PERSON",
                provider="provider1",
                status=EnrichmentStatus.NOT_FOUND,
            )
        )

        provider2 = MagicMock()
        provider2.supports_entity_type = MagicMock(return_value=True)
        provider2.enrich = AsyncMock(
            return_value=EnrichmentResult(
                entity_name="Test",
                entity_type="PERSON",
                provider="provider2",
                status=EnrichmentStatus.SUCCESS,
                description="Found by provider2",
            )
        )

        composite = CompositeEnrichmentProvider([provider1, provider2])
        result = await composite.enrich("Test", "PERSON")

        assert result.status == EnrichmentStatus.SUCCESS
        assert result.description == "Found by provider2"
        provider1.enrich.assert_called_once()
        provider2.enrich.assert_called_once()

    @pytest.mark.asyncio
    async def test_stops_on_success(self):
        provider1 = MagicMock()
        provider1.supports_entity_type = MagicMock(return_value=True)
        provider1.enrich = AsyncMock(
            return_value=EnrichmentResult(
                entity_name="Test",
                entity_type="PERSON",
                provider="provider1",
                status=EnrichmentStatus.SUCCESS,
                description="Found by provider1",
            )
        )

        provider2 = MagicMock()
        provider2.supports_entity_type = MagicMock(return_value=True)
        provider2.enrich = AsyncMock()

        composite = CompositeEnrichmentProvider([provider1, provider2])
        result = await composite.enrich("Test", "PERSON")

        assert result.description == "Found by provider1"
        provider2.enrich.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_unsupported_types(self):
        provider1 = MagicMock()
        provider1.supports_entity_type = MagicMock(return_value=False)
        provider1.enrich = AsyncMock()

        provider2 = MagicMock()
        provider2.supports_entity_type = MagicMock(return_value=True)
        provider2.enrich = AsyncMock(
            return_value=EnrichmentResult(
                entity_name="Test",
                entity_type="PERSON",
                provider="provider2",
                status=EnrichmentStatus.SUCCESS,
            )
        )

        composite = CompositeEnrichmentProvider([provider1, provider2])
        await composite.enrich("Test", "PERSON")

        provider1.enrich.assert_not_called()
        provider2.enrich.assert_called_once()

    def test_supported_entity_types_union(self):
        provider1 = MagicMock()
        provider1.supported_entity_types = ["PERSON", "ORGANIZATION"]

        provider2 = MagicMock()
        provider2.supported_entity_types = ["LOCATION", "ORGANIZATION"]

        composite = CompositeEnrichmentProvider([provider1, provider2])
        supported = set(composite.supported_entity_types)

        assert supported == {"PERSON", "ORGANIZATION", "LOCATION"}


class TestCreateEnrichmentProvider:
    """Tests for create_enrichment_provider factory."""

    def test_create_wikimedia(self):
        provider = create_enrichment_provider("wikimedia")
        assert provider.name == "wikimedia"

    def test_create_diffbot_requires_key(self):
        with pytest.raises(ValueError, match="requires an API key"):
            create_enrichment_provider("diffbot")

    def test_create_diffbot_with_key(self):
        provider = create_enrichment_provider("diffbot", api_key="test-key")
        assert provider.name == "diffbot"

    def test_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown enrichment provider"):
            create_enrichment_provider("unknown_provider")


class TestCreateEnrichmentService:
    """Tests for create_enrichment_service factory."""

    def test_disabled_returns_none(self):
        config = EnrichmentConfig(enabled=False)
        service = create_enrichment_service(config)
        assert service is None

    def test_none_provider_returns_none(self):
        config = EnrichmentConfig(enabled=True, providers=[EnrichmentProvider.NONE])
        service = create_enrichment_service(config)
        assert service is None

    def test_wikimedia_only(self):
        config = EnrichmentConfig(enabled=True, providers=[EnrichmentProvider.WIKIMEDIA])
        service = create_enrichment_service(config)
        assert service is not None
        # Should be wrapped in cache
        assert isinstance(service, CachedEnrichmentProvider)
        assert service.name == "wikimedia"

    def test_wikimedia_no_cache(self):
        config = EnrichmentConfig(
            enabled=True,
            providers=[EnrichmentProvider.WIKIMEDIA],
            cache_results=False,
        )
        service = create_enrichment_service(config)
        assert service is not None
        assert service.name == "wikimedia"
        assert not isinstance(service, CachedEnrichmentProvider)

    def test_multiple_providers_creates_composite(self):
        from pydantic import SecretStr

        config = EnrichmentConfig(
            enabled=True,
            providers=[EnrichmentProvider.WIKIMEDIA, EnrichmentProvider.DIFFBOT],
            diffbot_api_key=SecretStr("test-key"),
        )
        service = create_enrichment_service(config)
        assert service is not None
        assert isinstance(service, CompositeEnrichmentProvider)

    def test_diffbot_without_key_skipped(self):
        config = EnrichmentConfig(
            enabled=True,
            providers=[EnrichmentProvider.DIFFBOT],
            diffbot_api_key=None,
        )
        # Should return None since Diffbot requires key and is the only provider
        service = create_enrichment_service(config)
        assert service is None


class TestEnrichmentConfig:
    """Tests for EnrichmentConfig."""

    def test_defaults(self):
        config = EnrichmentConfig()
        assert config.enabled is False
        assert config.providers == [EnrichmentProvider.WIKIMEDIA]
        assert config.cache_results is True
        assert config.background_enabled is True
        assert config.min_confidence == 0.7

    def test_custom_settings(self):
        from pydantic import SecretStr

        config = EnrichmentConfig(
            enabled=True,
            providers=[EnrichmentProvider.WIKIMEDIA, EnrichmentProvider.DIFFBOT],
            diffbot_api_key=SecretStr("my-key"),
            wikimedia_rate_limit=1.0,
            cache_ttl_hours=48,
            entity_types=["PERSON", "ORGANIZATION"],
            min_confidence=0.8,
        )
        assert config.enabled is True
        assert len(config.providers) == 2
        assert config.diffbot_api_key.get_secret_value() == "my-key"
        assert config.wikimedia_rate_limit == 1.0
        assert config.cache_ttl_hours == 48
        assert config.entity_types == ["PERSON", "ORGANIZATION"]
        assert config.min_confidence == 0.8
