"""Tests for nams/long_term.py — NamsLongTermMemory.

Endpoint shapes verified against the live NAMS OpenAPI spec.

NAMS provides entity endpoints only. Preferences, facts, and
relationship writes raise :class:`NotSupportedError`.
"""

from __future__ import annotations

import json

import pytest
import respx

from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.core.protocols import LongTermProtocol
from neo4j_agent_memory.memory.long_term import Entity, Relationship
from neo4j_agent_memory.nams import HttpTransport, NamsLongTermMemory, StaticApiKeyAuth


@pytest.fixture
async def transport(nams_config):
    auth = StaticApiKeyAuth.from_config(nams_config)
    t = HttpTransport.from_config(nams_config, auth=auth)
    async with t:
        yield t


@pytest.fixture
def long_term(transport) -> NamsLongTermMemory:
    return NamsLongTermMemory(transport)


SAMPLE_ENTITY = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "Alice",
    "type": "PERSON",
    "description": "Test entity",
    "confidence": 0.95,
    "sourceStage": "extraction",
    "createdAt": "2026-05-17T12:00:00Z",
    "updatedAt": "2026-05-17T12:00:00Z",
}


class TestProtocolConformance:
    def test_satisfies_long_term_protocol(self, long_term):
        assert isinstance(long_term, LongTermProtocol)


class TestAddEntity:
    @respx.mock
    async def test_basic_returns_entity_only(self, long_term):
        route = respx.post("https://memory.test/v1/entities").respond(201, json=SAMPLE_ENTITY)
        entity = await long_term.add_entity("Alice", "PERSON", description="Test entity")
        assert isinstance(entity, Entity)
        assert entity.name == "Alice"
        assert entity.type == "PERSON"
        body = json.loads(route.calls[0].request.content)
        assert body == {"name": "Alice", "type": "PERSON", "description": "Test entity"}

    @respx.mock
    async def test_bolt_only_kwargs_dropped(self, long_term):
        route = respx.post("https://memory.test/v1/entities").respond(201, json=SAMPLE_ENTITY)
        await long_term.add_entity(
            "Alice",
            "PERSON",
            subtype="INDIVIDUAL",
            aliases=["Al"],
            attributes={"role": "lead"},
            confidence=0.8,
            deduplicate=True,
            geocode=True,
        )
        body = json.loads(route.calls[0].request.content)
        # NAMS accepts only name/type/description.
        for k in ("subtype", "aliases", "attributes", "confidence", "deduplicate", "geocode"):
            assert k not in body


class TestSearchEntities:
    @respx.mock
    async def test_with_envelope(self, long_term):
        route = respx.post("https://memory.test/v1/entities/search").respond(
            200, json={"entities": [SAMPLE_ENTITY], "searchType": "vector"}
        )
        results = await long_term.search_entities("Alice", entity_type="PERSON", limit=5)
        assert len(results) == 1
        assert isinstance(results[0], Entity)
        body = json.loads(route.calls[0].request.content)
        assert body == {"query": "Alice", "type": "PERSON", "limit": 5}


class TestGetEntityByName:
    @respx.mock
    async def test_uses_search_internally(self, long_term):
        respx.post("https://memory.test/v1/entities/search").respond(
            200, json={"entities": [SAMPLE_ENTITY], "searchType": "vector"}
        )
        result = await long_term.get_entity_by_name("Alice")
        assert result is not None
        assert result.name == "Alice"

    @respx.mock
    async def test_returns_none_when_no_match(self, long_term):
        respx.post("https://memory.test/v1/entities/search").respond(
            200, json={"entities": [], "searchType": "vector"}
        )
        result = await long_term.get_entity_by_name("Missing")
        assert result is None

    @respx.mock
    async def test_returns_none_when_only_inexact_matches(self, long_term):
        """Search returns hits but none with exact name match."""
        respx.post("https://memory.test/v1/entities/search").respond(
            200,
            json={
                "entities": [{**SAMPLE_ENTITY, "name": "Alice Different"}],
                "searchType": "vector",
            },
        )
        result = await long_term.get_entity_by_name("Alice")
        assert result is None


class TestSetEntityFeedback:
    @respx.mock
    async def test_positive_maps_to_user_score_and_confirmed(self, long_term):
        route = respx.put("https://memory.test/v1/entities/eid/feedback").respond(
            200, json={"id": "eid", "updated": True}
        )
        await long_term.set_entity_feedback("eid", "positive")
        body = json.loads(route.calls[0].request.content)
        assert body == {"userScore": 1.0, "confirmed": True}

    @respx.mock
    async def test_negative_maps_to_zero_and_false(self, long_term):
        route = respx.put("https://memory.test/v1/entities/eid/feedback").respond(
            200, json={"id": "eid", "updated": True}
        )
        await long_term.set_entity_feedback("eid", "negative")
        body = json.loads(route.calls[0].request.content)
        assert body == {"userScore": 0.0, "confirmed": False}

    @respx.mock
    async def test_explicit_user_score_kwarg(self, long_term):
        route = respx.put("https://memory.test/v1/entities/eid/feedback").respond(
            200, json={"id": "eid", "updated": True}
        )
        await long_term.set_entity_feedback("eid", "", user_score=0.75, confirmed=True)
        body = json.loads(route.calls[0].request.content)
        assert body == {"userScore": 0.75, "confirmed": True}


class TestGetEntityHistory:
    @respx.mock
    async def test_returns_mentions(self, long_term):
        respx.get("https://memory.test/v1/entities/eid/history").respond(
            200,
            json={
                "entityId": "eid",
                "mentions": [{"conversationId": "c1", "mentionCount": 3}],
            },
        )
        history = await long_term.get_entity_history("eid")
        assert len(history) == 1


class TestGetEntityProvenance:
    """Entity provenance lives under /v1/reasoning/provenance/{entityId}."""

    @respx.mock
    async def test_basic(self, long_term):
        respx.get("https://memory.test/v1/reasoning/provenance/eid").respond(
            200,
            json={"entityId": "eid", "steps": [{"id": "s1", "reasoning": "..."}]},
        )
        prov = await long_term.get_entity_provenance("eid")
        assert "steps" in prov
        assert len(prov["steps"]) == 1


class TestNotSupportedMethods:
    """Preferences, facts, relationships, related-entities, get_facts_about
    have no NAMS endpoints — all raise NotSupportedError."""

    async def test_add_preference(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.add_preference("food", "italian")

    async def test_search_preferences(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.search_preferences("food")

    async def test_get_preferences_for(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.get_preferences_for(category="food")

    async def test_supersede_preference(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.supersede_preference("pref-id")

    async def test_add_fact(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.add_fact("Alice", "works_at", "Acme")

    async def test_search_facts(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.search_facts("Acme")

    async def test_get_facts_about(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.get_facts_about("Alice")

    async def test_add_relationship(self, long_term):
        with pytest.raises(NotSupportedError):
            await long_term.add_relationship(
                "00000000-0000-0000-0000-0000000000e1",
                "WORKS_AT",
                "00000000-0000-0000-0000-0000000000e2",
            )


class TestGetEntityRelationships:
    @respx.mock
    async def test_returns_inline_relationships(self, long_term):
        """NAMS GET /v1/entities/{id} returns relationships inline."""
        respx.get("https://memory.test/v1/entities/00000000-0000-0000-0000-0000000000e1").respond(
            200,
            json={
                **SAMPLE_ENTITY,
                "relationships": [
                    {
                        "relType": "WORKS_AT",
                        "targetId": "00000000-0000-0000-0000-0000000000e2",
                        "targetName": "Acme",
                        "targetType": "ORGANIZATION",
                    }
                ],
            },
        )
        rels = await long_term.get_entity_relationships("00000000-0000-0000-0000-0000000000e1")
        assert len(rels) == 1
        assert isinstance(rels[0], Relationship)
        assert rels[0].type == "WORKS_AT"
        assert str(rels[0].target_id) == "00000000-0000-0000-0000-0000000000e2"

    @respx.mock
    async def test_empty_when_no_relationships(self, long_term):
        respx.get("https://memory.test/v1/entities/00000000-0000-0000-0000-0000000000e1").respond(
            200, json=SAMPLE_ENTITY
        )
        rels = await long_term.get_entity_relationships("00000000-0000-0000-0000-0000000000e1")
        assert rels == []


class TestGetRelatedEntities:
    @respx.mock
    async def test_returns_relationships_as_dicts(self, long_term):
        respx.get("https://memory.test/v1/entities/00000000-0000-0000-0000-0000000000e1").respond(
            200,
            json={
                **SAMPLE_ENTITY,
                "relationships": [
                    {
                        "relType": "KNOWS",
                        "targetId": "00000000-0000-0000-0000-0000000000e2",
                        "targetName": "Bob",
                        "targetType": "PERSON",
                    },
                ],
            },
        )
        related = await long_term.get_related_entities("00000000-0000-0000-0000-0000000000e1")
        assert isinstance(related, list)
        assert len(related) == 1


class TestGetContext:
    async def test_returns_empty_string(self, long_term):
        # NAMS doesn't expose long-term context. Returns "".
        result = await long_term.get_context("anything")
        assert result == ""
