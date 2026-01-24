"""Integration tests for location queries with session filtering."""

import pytest

from neo4j_agent_memory.memory.long_term import EntityType


@pytest.mark.integration
class TestGetLocations:
    """Test the get_locations() method on MemoryClient."""

    @pytest.mark.asyncio
    async def test_get_locations_returns_all(self, clean_memory_client):
        """Test get_locations returns all locations when no session filter."""
        # Add some location entities with coordinates
        await clean_memory_client.long_term.add_entity(
            name="New York City",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(40.7128, -74.0060),
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="San Francisco",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(37.7749, -122.4194),
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="Tokyo",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(35.6762, 139.6503),
            resolve=False,
            generate_embedding=False,
        )

        # Get all locations
        locations = await clean_memory_client.get_locations(
            has_coordinates=True,
            limit=100,
        )

        assert len(locations) == 3
        names = [loc["name"] for loc in locations]
        assert "New York City" in names
        assert "San Francisco" in names
        assert "Tokyo" in names

    @pytest.mark.asyncio
    async def test_get_locations_filters_by_coordinates(self, clean_memory_client):
        """Test get_locations filters by has_coordinates."""
        # Add location with coordinates
        await clean_memory_client.long_term.add_entity(
            name="Paris",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(48.8566, 2.3522),
            resolve=False,
            generate_embedding=False,
        )
        # Add location without coordinates
        await clean_memory_client.long_term.add_entity(
            name="Unknown Place",
            entity_type=EntityType.LOCATION,
            resolve=False,
            generate_embedding=False,
        )

        # Get only locations with coordinates
        locations_with_coords = await clean_memory_client.get_locations(
            has_coordinates=True,
            limit=100,
        )
        assert len(locations_with_coords) == 1
        assert locations_with_coords[0]["name"] == "Paris"

        # Get all locations (including those without coordinates)
        all_locations = await clean_memory_client.get_locations(
            has_coordinates=False,
            limit=100,
        )
        assert len(all_locations) == 2

    @pytest.mark.asyncio
    async def test_get_locations_filters_by_session_id(self, clean_memory_client):
        """Test get_locations filters by session_id."""
        # Create a conversation and add a message
        await clean_memory_client.short_term.add_message(
            session_id="session-1",
            role="user",
            content="Let's talk about London",
            extract_entities=False,
            generate_embedding=False,
        )
        msg1 = await clean_memory_client.short_term.add_message(
            session_id="session-1",
            role="assistant",
            content="London is a great city!",
            extract_entities=False,
            generate_embedding=False,
        )

        await clean_memory_client.short_term.add_message(
            session_id="session-2",
            role="user",
            content="Tell me about Berlin",
            extract_entities=False,
            generate_embedding=False,
        )
        msg2 = await clean_memory_client.short_term.add_message(
            session_id="session-2",
            role="assistant",
            content="Berlin is fascinating!",
            extract_entities=False,
            generate_embedding=False,
        )

        # Add location entities
        london, _ = await clean_memory_client.long_term.add_entity(
            name="London",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(51.5074, -0.1278),
            resolve=False,
            generate_embedding=False,
        )
        berlin, _ = await clean_memory_client.long_term.add_entity(
            name="Berlin",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(52.5200, 13.4050),
            resolve=False,
            generate_embedding=False,
        )

        # Link entities to messages (simulating extraction)
        await clean_memory_client.long_term.link_entity_to_message(
            london,
            msg1.id,
            confidence=0.9,
        )
        await clean_memory_client.long_term.link_entity_to_message(
            berlin,
            msg2.id,
            confidence=0.9,
        )

        # Get locations for session-1 only
        session1_locations = await clean_memory_client.get_locations(
            session_id="session-1",
            has_coordinates=True,
            limit=100,
        )
        assert len(session1_locations) == 1
        assert session1_locations[0]["name"] == "London"

        # Get locations for session-2 only
        session2_locations = await clean_memory_client.get_locations(
            session_id="session-2",
            has_coordinates=True,
            limit=100,
        )
        assert len(session2_locations) == 1
        assert session2_locations[0]["name"] == "Berlin"

    @pytest.mark.asyncio
    async def test_get_locations_returns_conversations_list(self, clean_memory_client):
        """Test get_locations includes conversations list for each location."""
        # Create conversations
        await clean_memory_client.short_term.add_message(
            session_id="conv-a",
            role="user",
            content="Visiting Rome",
            extract_entities=False,
            generate_embedding=False,
        )
        msg_a = await clean_memory_client.short_term.add_message(
            session_id="conv-a",
            role="assistant",
            content="Rome is wonderful!",
            extract_entities=False,
            generate_embedding=False,
        )

        await clean_memory_client.short_term.add_message(
            session_id="conv-b",
            role="user",
            content="I also love Rome",
            extract_entities=False,
            generate_embedding=False,
        )
        msg_b = await clean_memory_client.short_term.add_message(
            session_id="conv-b",
            role="assistant",
            content="Rome is amazing!",
            extract_entities=False,
            generate_embedding=False,
        )

        # Add Rome and link to both conversations
        rome, _ = await clean_memory_client.long_term.add_entity(
            name="Rome",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(41.9028, 12.4964),
            resolve=False,
            generate_embedding=False,
        )

        await clean_memory_client.long_term.link_entity_to_message(rome, msg_a.id, confidence=0.9)
        await clean_memory_client.long_term.link_entity_to_message(rome, msg_b.id, confidence=0.9)

        # Get locations (should include conversations list)
        locations = await clean_memory_client.get_locations(
            has_coordinates=True,
            limit=100,
        )

        assert len(locations) == 1
        rome_loc = locations[0]
        assert rome_loc["name"] == "Rome"
        assert "conversations" in rome_loc
        # Rome should be linked to both conversations
        session_ids = [c.get("session_id") for c in rome_loc["conversations"]]
        assert "conv-a" in session_ids
        assert "conv-b" in session_ids

    @pytest.mark.asyncio
    async def test_get_locations_respects_limit(self, clean_memory_client):
        """Test get_locations respects the limit parameter."""
        # Add multiple locations
        cities = [
            ("City1", 40.0, -74.0),
            ("City2", 41.0, -74.0),
            ("City3", 42.0, -74.0),
            ("City4", 43.0, -74.0),
            ("City5", 44.0, -74.0),
        ]

        for name, lat, lon in cities:
            await clean_memory_client.long_term.add_entity(
                name=name,
                entity_type=EntityType.LOCATION,
                subtype="CITY",
                coordinates=(lat, lon),
                resolve=False,
                generate_embedding=False,
            )

        # Get with limit
        locations = await clean_memory_client.get_locations(
            has_coordinates=True,
            limit=3,
        )

        assert len(locations) == 3


@pytest.mark.integration
class TestSearchLocationsNear:
    """Test session-scoped geospatial queries for locations near a point."""

    @pytest.mark.asyncio
    async def test_search_locations_near_basic(self, clean_memory_client):
        """Test basic search_locations_near without session filter."""
        # Add locations at known coordinates
        await clean_memory_client.long_term.add_entity(
            name="Manhattan",
            entity_type=EntityType.LOCATION,
            subtype="BOROUGH",
            coordinates=(40.7831, -73.9712),  # ~5km from reference
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="Brooklyn",
            entity_type=EntityType.LOCATION,
            subtype="BOROUGH",
            coordinates=(40.6782, -73.9442),  # ~10km from reference
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="Los Angeles",
            entity_type=EntityType.LOCATION,
            subtype="CITY",
            coordinates=(34.0522, -118.2437),  # Very far
            resolve=False,
            generate_embedding=False,
        )

        # Search near Times Square (40.7580, -73.9855)
        nearby = await clean_memory_client.long_term.search_locations_near(
            latitude=40.7580,
            longitude=-73.9855,
            radius_km=15.0,
            limit=10,
        )

        # Should find Manhattan and Brooklyn, not LA
        names = [loc.name for loc in nearby]
        assert "Manhattan" in names
        assert "Brooklyn" in names
        assert "Los Angeles" not in names

    @pytest.mark.asyncio
    async def test_search_locations_near_with_session_id(self, clean_memory_client):
        """Test search_locations_near with session_id filter."""
        # Create a conversation
        await clean_memory_client.short_term.add_message(
            session_id="nyc-session",
            role="user",
            content="Tell me about Manhattan",
            extract_entities=False,
            generate_embedding=False,
        )
        msg = await clean_memory_client.short_term.add_message(
            session_id="nyc-session",
            role="assistant",
            content="Manhattan is great!",
            extract_entities=False,
            generate_embedding=False,
        )

        # Add locations
        manhattan, _ = await clean_memory_client.long_term.add_entity(
            name="Manhattan",
            entity_type=EntityType.LOCATION,
            coordinates=(40.7831, -73.9712),
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="Queens",
            entity_type=EntityType.LOCATION,
            coordinates=(40.7282, -73.7949),  # Also near, but not linked to session
            resolve=False,
            generate_embedding=False,
        )

        # Link Manhattan to the conversation
        await clean_memory_client.long_term.link_entity_to_message(
            manhattan, msg.id, confidence=0.9
        )

        # Search near Times Square with session filter
        nearby = await clean_memory_client.long_term.search_locations_near(
            latitude=40.7580,
            longitude=-73.9855,
            radius_km=50.0,
            session_id="nyc-session",
            limit=10,
        )

        # Should only find Manhattan (linked to session), not Queens
        names = [loc.name for loc in nearby]
        assert "Manhattan" in names
        assert "Queens" not in names


@pytest.mark.integration
class TestSearchLocationsInBounds:
    """Test session-scoped geospatial queries for locations in bounding box."""

    @pytest.mark.asyncio
    async def test_search_locations_in_bounds_basic(self, clean_memory_client):
        """Test basic search_locations_in_bounds without session filter."""
        # Add locations
        await clean_memory_client.long_term.add_entity(
            name="Central Park",
            entity_type=EntityType.LOCATION,
            coordinates=(40.7829, -73.9654),  # Inside NYC bounds
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="Empire State",
            entity_type=EntityType.LOCATION,
            coordinates=(40.7484, -73.9857),  # Inside NYC bounds
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="Golden Gate",
            entity_type=EntityType.LOCATION,
            coordinates=(37.8199, -122.4783),  # Outside NYC bounds
            resolve=False,
            generate_embedding=False,
        )

        # Search in NYC bounding box
        in_bounds = await clean_memory_client.long_term.search_locations_in_bounding_box(
            min_lat=40.5,
            max_lat=41.0,
            min_lon=-74.5,
            max_lon=-73.5,
            limit=50,
        )

        names = [loc.name for loc in in_bounds]
        assert "Central Park" in names
        assert "Empire State" in names
        assert "Golden Gate" not in names

    @pytest.mark.asyncio
    async def test_search_locations_in_bounds_with_session_id(self, clean_memory_client):
        """Test search_locations_in_bounds with session_id filter."""
        # Create conversation
        await clean_memory_client.short_term.add_message(
            session_id="park-session",
            role="user",
            content="About Central Park",
            extract_entities=False,
            generate_embedding=False,
        )
        msg = await clean_memory_client.short_term.add_message(
            session_id="park-session",
            role="assistant",
            content="Central Park is iconic!",
            extract_entities=False,
            generate_embedding=False,
        )

        # Add locations
        central_park, _ = await clean_memory_client.long_term.add_entity(
            name="Central Park",
            entity_type=EntityType.LOCATION,
            coordinates=(40.7829, -73.9654),
            resolve=False,
            generate_embedding=False,
        )
        await clean_memory_client.long_term.add_entity(
            name="Bryant Park",
            entity_type=EntityType.LOCATION,
            coordinates=(40.7536, -73.9832),  # Also in bounds, not linked
            resolve=False,
            generate_embedding=False,
        )

        # Link Central Park to session
        await clean_memory_client.long_term.link_entity_to_message(
            central_park, msg.id, confidence=0.9
        )

        # Search in NYC bounds with session filter
        in_bounds = await clean_memory_client.long_term.search_locations_in_bounding_box(
            min_lat=40.5,
            max_lat=41.0,
            min_lon=-74.5,
            max_lon=-73.5,
            session_id="park-session",
            limit=50,
        )

        # Should only find Central Park
        names = [loc.name for loc in in_bounds]
        assert "Central Park" in names
        assert "Bryant Park" not in names


@pytest.mark.integration
class TestLocationQueryEdgeCases:
    """Test edge cases for location queries."""

    @pytest.mark.asyncio
    async def test_get_locations_empty_database(self, clean_memory_client):
        """Test get_locations returns empty list when no locations exist."""
        locations = await clean_memory_client.get_locations(
            has_coordinates=True,
            limit=100,
        )
        assert locations == []

    @pytest.mark.asyncio
    async def test_get_locations_nonexistent_session(self, clean_memory_client):
        """Test get_locations with non-existent session_id returns empty list."""
        # Add a location but don't link to any session
        await clean_memory_client.long_term.add_entity(
            name="Orphan Location",
            entity_type=EntityType.LOCATION,
            coordinates=(40.0, -74.0),
            resolve=False,
            generate_embedding=False,
        )

        locations = await clean_memory_client.get_locations(
            session_id="nonexistent-session",
            has_coordinates=True,
            limit=100,
        )
        assert locations == []

    @pytest.mark.asyncio
    async def test_search_locations_near_no_results(self, clean_memory_client):
        """Test search_locations_near returns empty when no locations in radius."""
        # Add location far from search point
        await clean_memory_client.long_term.add_entity(
            name="Far Away Place",
            entity_type=EntityType.LOCATION,
            coordinates=(0.0, 0.0),  # Equator
            resolve=False,
            generate_embedding=False,
        )

        # Search near North Pole
        nearby = await clean_memory_client.long_term.search_locations_near(
            latitude=89.0,
            longitude=0.0,
            radius_km=100.0,
            limit=10,
        )

        assert len(nearby) == 0

    @pytest.mark.asyncio
    async def test_location_subtype_returned(self, clean_memory_client):
        """Test that location subtype is returned in get_locations results."""
        await clean_memory_client.long_term.add_entity(
            name="France",
            entity_type=EntityType.LOCATION,
            subtype="COUNTRY",
            coordinates=(46.2276, 2.2137),
            resolve=False,
            generate_embedding=False,
        )

        locations = await clean_memory_client.get_locations(
            has_coordinates=True,
            limit=100,
        )

        assert len(locations) == 1
        assert locations[0]["name"] == "France"
        assert locations[0]["subtype"] == "COUNTRY"
