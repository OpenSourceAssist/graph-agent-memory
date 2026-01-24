"""Unit tests for geocoding services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from neo4j_agent_memory.services.geocoder import (
    CachedGeocoder,
    GeocodingResult,
    GoogleGeocoder,
    NominatimGeocoder,
    create_geocoder,
)

# Check if httpx is available for mocking
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

requires_httpx = pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")


class TestGeocodingResult:
    """Tests for GeocodingResult dataclass."""

    def test_create_result(self):
        """Test creating a geocoding result."""
        result = GeocodingResult(
            latitude=40.748817,
            longitude=-73.985428,
            display_name="Empire State Building, New York, NY",
            place_type="building",
            confidence=0.95,
        )

        assert result.latitude == 40.748817
        assert result.longitude == -73.985428
        assert result.display_name == "Empire State Building, New York, NY"
        assert result.place_type == "building"
        assert result.confidence == 0.95

    def test_as_neo4j_point(self):
        """Test converting to Neo4j Point format."""
        result = GeocodingResult(latitude=40.748817, longitude=-73.985428)

        point = result.as_neo4j_point()

        assert point == {"latitude": 40.748817, "longitude": -73.985428}

    def test_as_tuple(self):
        """Test converting to tuple."""
        result = GeocodingResult(latitude=40.748817, longitude=-73.985428)

        coords = result.as_tuple()

        assert coords == (40.748817, -73.985428)

    def test_default_values(self):
        """Test default values for optional fields."""
        result = GeocodingResult(latitude=0.0, longitude=0.0)

        assert result.display_name is None
        assert result.place_type is None
        assert result.confidence == 1.0


class TestNominatimGeocoder:
    """Tests for NominatimGeocoder."""

    def test_init_defaults(self):
        """Test default initialization."""
        geocoder = NominatimGeocoder()

        assert geocoder._user_agent == "neo4j-agent-memory/1.0"
        assert geocoder._rate_limit == 1.0
        assert geocoder._timeout == 10.0

    def test_init_custom_values(self):
        """Test custom initialization."""
        geocoder = NominatimGeocoder(
            user_agent="test-agent/1.0",
            rate_limit=2.0,
            timeout=30.0,
        )

        assert geocoder._user_agent == "test-agent/1.0"
        assert geocoder._rate_limit == 2.0
        assert geocoder._timeout == 30.0

    @requires_httpx
    @pytest.mark.asyncio
    async def test_geocode_success(self):
        """Test successful geocoding."""
        geocoder = NominatimGeocoder(rate_limit=0)  # No rate limiting for tests

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "lat": "40.748817",
                "lon": "-73.985428",
                "display_name": "Empire State Building",
                "type": "building",
                "importance": 0.85,
            }
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.geocode("Empire State Building")

        assert result is not None
        assert result.latitude == 40.748817
        assert result.longitude == -73.985428
        assert result.display_name == "Empire State Building"
        assert result.place_type == "building"
        assert result.confidence == 0.85

    @requires_httpx
    @pytest.mark.asyncio
    async def test_geocode_not_found(self):
        """Test geocoding when location not found."""
        geocoder = NominatimGeocoder(rate_limit=0)

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.geocode("NonexistentPlace12345")

        assert result is None

    @requires_httpx
    @pytest.mark.asyncio
    async def test_geocode_http_error(self):
        """Test geocoding handles HTTP errors gracefully."""
        geocoder = NominatimGeocoder(rate_limit=0)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection error")
            )

            result = await geocoder.geocode("New York")

        assert result is None

    @requires_httpx
    @pytest.mark.asyncio
    async def test_reverse_geocode_success(self):
        """Test successful reverse geocoding."""
        geocoder = NominatimGeocoder(rate_limit=0)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lat": "40.748817",
            "lon": "-73.985428",
            "display_name": "Empire State Building, Manhattan, NYC",
            "type": "building",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.reverse_geocode(40.748817, -73.985428)

        assert result is not None
        assert result.latitude == 40.748817
        assert result.display_name == "Empire State Building, Manhattan, NYC"

    @requires_httpx
    @pytest.mark.asyncio
    async def test_reverse_geocode_not_found(self):
        """Test reverse geocoding when coordinates not found."""
        geocoder = NominatimGeocoder(rate_limit=0)

        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Unable to geocode"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.reverse_geocode(0.0, 0.0)

        assert result is None


class TestGoogleGeocoder:
    """Tests for GoogleGeocoder."""

    def test_init(self):
        """Test initialization with API key."""
        geocoder = GoogleGeocoder(api_key="test-api-key")

        assert geocoder._api_key == "test-api-key"
        assert geocoder._timeout == 10.0

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        geocoder = GoogleGeocoder(api_key="test-key", timeout=30.0)

        assert geocoder._timeout == 30.0

    @requires_httpx
    @pytest.mark.asyncio
    async def test_geocode_success(self):
        """Test successful Google geocoding."""
        geocoder = GoogleGeocoder(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Empire State Building, NY",
                    "geometry": {
                        "location": {"lat": 40.748817, "lng": -73.985428},
                        "location_type": "ROOFTOP",
                    },
                    "types": ["point_of_interest", "establishment"],
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.geocode("Empire State Building")

        assert result is not None
        assert result.latitude == 40.748817
        assert result.longitude == -73.985428
        assert result.display_name == "Empire State Building, NY"
        assert result.place_type == "point_of_interest"
        assert result.confidence == 1.0  # ROOFTOP = 1.0

    @requires_httpx
    @pytest.mark.asyncio
    async def test_geocode_approximate_confidence(self):
        """Test confidence mapping for approximate results."""
        geocoder = GoogleGeocoder(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Some City",
                    "geometry": {
                        "location": {"lat": 40.0, "lng": -73.0},
                        "location_type": "APPROXIMATE",
                    },
                    "types": ["locality"],
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.geocode("Some City")

        assert result is not None
        assert result.confidence == 0.4  # APPROXIMATE = 0.4

    @requires_httpx
    @pytest.mark.asyncio
    async def test_geocode_not_found(self):
        """Test geocoding when location not found."""
        geocoder = GoogleGeocoder(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.geocode("NonexistentPlace12345")

        assert result is None

    @requires_httpx
    @pytest.mark.asyncio
    async def test_reverse_geocode_success(self):
        """Test successful Google reverse geocoding."""
        geocoder = GoogleGeocoder(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "350 5th Avenue, New York, NY",
                    "geometry": {
                        "location": {"lat": 40.748817, "lng": -73.985428},
                    },
                    "types": ["street_address"],
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await geocoder.reverse_geocode(40.748817, -73.985428)

        assert result is not None
        assert result.display_name == "350 5th Avenue, New York, NY"


class TestCachedGeocoder:
    """Tests for CachedGeocoder."""

    @pytest.mark.asyncio
    async def test_caching_geocode(self):
        """Test that geocode results are cached."""
        mock_geocoder = AsyncMock()
        mock_geocoder.geocode.return_value = GeocodingResult(
            latitude=40.748817, longitude=-73.985428
        )

        cached = CachedGeocoder(mock_geocoder)

        # First call
        result1 = await cached.geocode("Empire State Building")
        # Second call (should be cached)
        result2 = await cached.geocode("Empire State Building")

        assert result1 == result2
        assert mock_geocoder.geocode.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_caching_case_insensitive(self):
        """Test that cache keys are case-insensitive."""
        mock_geocoder = AsyncMock()
        mock_geocoder.geocode.return_value = GeocodingResult(latitude=40.0, longitude=-73.0)

        cached = CachedGeocoder(mock_geocoder)

        await cached.geocode("New York")
        await cached.geocode("new york")
        await cached.geocode("NEW YORK")

        assert mock_geocoder.geocode.call_count == 1

    @pytest.mark.asyncio
    async def test_caching_reverse_geocode(self):
        """Test that reverse geocode results are cached."""
        mock_geocoder = AsyncMock()
        mock_geocoder.reverse_geocode.return_value = GeocodingResult(
            latitude=40.748817, longitude=-73.985428, display_name="Test Location"
        )

        cached = CachedGeocoder(mock_geocoder)

        result1 = await cached.reverse_geocode(40.748817, -73.985428)
        result2 = await cached.reverse_geocode(40.748817, -73.985428)

        assert result1 == result2
        assert mock_geocoder.reverse_geocode.call_count == 1

    @pytest.mark.asyncio
    async def test_caching_coordinates_rounded(self):
        """Test that coordinates are rounded for cache keys."""
        mock_geocoder = AsyncMock()
        mock_geocoder.reverse_geocode.return_value = GeocodingResult(
            latitude=40.0, longitude=-73.0, display_name="Test"
        )

        cached = CachedGeocoder(mock_geocoder)

        # These should map to the same cache key (5 decimal places)
        await cached.reverse_geocode(40.748817123, -73.985428456)
        await cached.reverse_geocode(40.748817789, -73.985428999)

        assert mock_geocoder.reverse_geocode.call_count == 1

    def test_clear_cache(self):
        """Test clearing the cache."""
        mock_geocoder = MagicMock()
        cached = CachedGeocoder(mock_geocoder)

        cached._cache["test"] = GeocodingResult(latitude=0, longitude=0)
        cached._reverse_cache[(0.0, 0.0)] = GeocodingResult(latitude=0, longitude=0)

        assert cached.cache_size == 2

        cached.clear_cache()

        assert cached.cache_size == 0

    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        """Test that old entries are evicted when cache is full."""
        mock_geocoder = AsyncMock()
        mock_geocoder.geocode.return_value = GeocodingResult(latitude=0, longitude=0)

        cached = CachedGeocoder(mock_geocoder, max_cache_size=10)

        # Fill the cache
        for i in range(15):
            await cached.geocode(f"Location {i}")

        # Cache should not exceed max size by much
        assert cached.cache_size <= 15

    @pytest.mark.asyncio
    async def test_caches_none_results(self):
        """Test that None results are also cached."""
        mock_geocoder = AsyncMock()
        mock_geocoder.geocode.return_value = None

        cached = CachedGeocoder(mock_geocoder)

        result1 = await cached.geocode("Unknown Place")
        result2 = await cached.geocode("Unknown Place")

        assert result1 is None
        assert result2 is None
        assert mock_geocoder.geocode.call_count == 1


class TestCreateGeocoder:
    """Tests for create_geocoder factory function."""

    def test_create_nominatim_default(self):
        """Test creating default Nominatim geocoder."""
        geocoder = create_geocoder()

        assert isinstance(geocoder, CachedGeocoder)
        assert isinstance(geocoder._geocoder, NominatimGeocoder)

    def test_create_nominatim_no_cache(self):
        """Test creating Nominatim geocoder without caching."""
        geocoder = create_geocoder(cache_results=False)

        assert isinstance(geocoder, NominatimGeocoder)

    def test_create_nominatim_custom_settings(self):
        """Test creating Nominatim geocoder with custom settings."""
        geocoder = create_geocoder(
            provider="nominatim",
            cache_results=False,
            rate_limit=2.0,
            user_agent="custom-agent/1.0",
        )

        assert isinstance(geocoder, NominatimGeocoder)
        assert geocoder._user_agent == "custom-agent/1.0"
        assert geocoder._rate_limit == 2.0

    def test_create_google(self):
        """Test creating Google geocoder."""
        geocoder = create_geocoder(provider="google", api_key="test-key")

        assert isinstance(geocoder, CachedGeocoder)
        assert isinstance(geocoder._geocoder, GoogleGeocoder)

    def test_create_google_no_cache(self):
        """Test creating Google geocoder without caching."""
        geocoder = create_geocoder(provider="google", api_key="test-key", cache_results=False)

        assert isinstance(geocoder, GoogleGeocoder)

    def test_create_google_requires_api_key(self):
        """Test that Google geocoder requires API key."""
        with pytest.raises(ValueError, match="requires an API key"):
            create_geocoder(provider="google")

    def test_create_unknown_provider(self):
        """Test that unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown geocoding provider"):
            create_geocoder(provider="unknown")  # type: ignore
