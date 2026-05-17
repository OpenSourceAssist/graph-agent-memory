"""Tests for nams/long_term.py — NamsLongTermMemory."""

from __future__ import annotations

import json

import pytest
import respx

from neo4j_agent_memory.core.protocols import LongTermProtocol
from neo4j_agent_memory.memory.long_term import Entity, Fact, Preference, Relationship
from neo4j_agent_memory.nams import HttpTransport, NamsLongTermMemory, StaticApiKeyAuth

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


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
    "subtype": "INDIVIDUAL",
    "created_at": "2026-05-17T12:00:00Z",
    "metadata": {},
    "aliases": [],
    "attributes": {},
    "confidence": 0.95,
}

SAMPLE_PREFERENCE = {
    "id": "00000000-0000-0000-0000-00000000aaaa",
    "category": "food",
    "preference": "loves italian",
    "created_at": "2026-05-17T12:00:00Z",
    "metadata": {},
    "confidence": 1.0,
}

SAMPLE_FACT = {
    "id": "00000000-0000-0000-0000-00000000bbbb",
    "subject": "Alice",
    "predicate": "works_at",
    "object": "Acme",
    "created_at": "2026-05-17T12:00:00Z",
    "metadata": {},
    "confidence": 0.9,
}


# -----------------------------------------------------------------------------
# Protocol conformance
# -----------------------------------------------------------------------------


class TestProtocolConformance:
    def test_satisfies_long_term_protocol(self, long_term):
        assert isinstance(long_term, LongTermProtocol)


# -----------------------------------------------------------------------------
# Bronze — writes
# -----------------------------------------------------------------------------


class TestAddEntity:
    @respx.mock
    async def test_basic_returns_entity_only(self, long_term):
        """NAMS returns just Entity (no DeduplicationResult tuple)."""
        route = respx.post("https://memory.test/v1/entities").respond(200, json=SAMPLE_ENTITY)
        result = await long_term.add_entity("Alice", "PERSON", subtype="INDIVIDUAL")
        assert isinstance(result, Entity)
        assert result.name == "Alice"
        assert result.type == "PERSON"
        # Sanity: result is the Entity directly, not a tuple.
        assert not isinstance(result, tuple)
        body = json.loads(route.calls[0].request.content)
        assert body["name"] == "Alice"
        assert body["type"] == "PERSON"
        assert body["subtype"] == "INDIVIDUAL"

    @respx.mock
    async def test_bolt_only_kwargs_ignored(self, long_term):
        route = respx.post("https://memory.test/v1/entities").respond(200, json=SAMPLE_ENTITY)
        await long_term.add_entity(
            "Alice",
            "PERSON",
            # Bolt-only kwargs:
            deduplicate=True,
            geocode=True,
            enrich=True,
            resolve=False,
            generate_embedding=True,
        )
        body = json.loads(route.calls[0].request.content)
        for k in (
            "deduplicate",
            "geocode",
            "enrich",
            "resolve",
            "generate_embedding",
        ):
            assert k not in body


class TestAddPreference:
    @respx.mock
    async def test_basic(self, long_term):
        route = respx.post("https://memory.test/v1/preferences").respond(
            200, json=SAMPLE_PREFERENCE
        )
        pref = await long_term.add_preference("food", "loves italian", confidence=0.9)
        assert isinstance(pref, Preference)
        body = json.loads(route.calls[0].request.content)
        assert body == {
            "category": "food",
            "preference": "loves italian",
            "confidence": 0.9,
        }


class TestAddFact:
    @respx.mock
    async def test_basic(self, long_term):
        respx.post("https://memory.test/v1/facts").respond(200, json=SAMPLE_FACT)
        f = await long_term.add_fact("Alice", "works_at", "Acme")
        assert isinstance(f, Fact)
        assert f.as_triple == ("Alice", "works_at", "Acme")


class TestAddRelationship:
    @respx.mock
    async def test_basic(self, long_term):
        route = respx.post("https://memory.test/v1/relationships").respond(204)
        await long_term.add_relationship(
            "00000000-0000-0000-0000-000000000001",
            "WORKS_AT",
            "00000000-0000-0000-0000-000000000002",
            properties={"since": "2020"},
        )
        body = json.loads(route.calls[0].request.content)
        assert body["source_id"] == "00000000-0000-0000-0000-000000000001"
        assert body["target_id"] == "00000000-0000-0000-0000-000000000002"
        assert body["type"] == "WORKS_AT"
        assert body["properties"] == {"since": "2020"}


# -----------------------------------------------------------------------------
# Bronze — reads
# -----------------------------------------------------------------------------


class TestSearchEntities:
    @respx.mock
    async def test_basic(self, long_term):
        route = respx.post("https://memory.test/v1/entities/search").respond(
            200, json=[SAMPLE_ENTITY]
        )
        results = await long_term.search_entities("Alice", entity_type="PERSON", limit=5)
        assert len(results) == 1
        assert isinstance(results[0], Entity)
        body = json.loads(route.calls[0].request.content)
        # Accept both ``entity_type`` and ``type`` kwargs; NAMS sees ``type``.
        assert body == {"query": "Alice", "type": "PERSON", "limit": 5}


class TestSearchPreferences:
    @respx.mock
    async def test_basic(self, long_term):
        respx.post("https://memory.test/v1/preferences/search").respond(
            200, json=[SAMPLE_PREFERENCE]
        )
        results = await long_term.search_preferences("food", category="food")
        assert len(results) == 1
        assert isinstance(results[0], Preference)


class TestSearchFacts:
    @respx.mock
    async def test_basic(self, long_term):
        respx.post("https://memory.test/v1/facts/search").respond(200, json=[SAMPLE_FACT])
        results = await long_term.search_facts("Acme")
        assert len(results) == 1
        assert isinstance(results[0], Fact)


class TestGetEntityByName:
    @respx.mock
    async def test_returns_entity_when_found(self, long_term):
        respx.get("https://memory.test/v1/entities").respond(200, json=SAMPLE_ENTITY)
        e = await long_term.get_entity_by_name("Alice")
        assert isinstance(e, Entity)

    @respx.mock
    async def test_returns_none_on_404(self, long_term):
        respx.get("https://memory.test/v1/entities").respond(
            404, json={"error": "entity not found"}
        )
        assert await long_term.get_entity_by_name("Missing") is None

    @respx.mock
    async def test_returns_first_when_list(self, long_term):
        respx.get("https://memory.test/v1/entities").respond(200, json=[SAMPLE_ENTITY])
        e = await long_term.get_entity_by_name("Alice")
        assert isinstance(e, Entity)

    @respx.mock
    async def test_returns_none_on_empty_list(self, long_term):
        respx.get("https://memory.test/v1/entities").respond(200, json=[])
        assert await long_term.get_entity_by_name("Missing") is None


# -----------------------------------------------------------------------------
# Silver
# -----------------------------------------------------------------------------


class TestGetRelatedEntities:
    @respx.mock
    async def test_basic_list_response(self, long_term):
        route = respx.get(
            "https://memory.test/v1/entities/00000000-0000-0000-0000-000000000001/related"
        ).respond(200, json=[SAMPLE_ENTITY])
        related = await long_term.get_related_entities(
            "00000000-0000-0000-0000-000000000001", depth=2
        )
        assert len(related) == 1
        assert isinstance(related[0], Entity)
        assert route.calls[0].request.url.params["depth"] == "2"

    @respx.mock
    async def test_envelope_response_passes_through(self, long_term):
        """If NAMS returns ``{entities:[], relationships:[]}``, pass through as dict."""
        respx.get(
            "https://memory.test/v1/entities/00000000-0000-0000-0000-000000000001/related"
        ).respond(
            200,
            json={"entities": [SAMPLE_ENTITY], "relationships": []},
        )
        result = await long_term.get_related_entities("00000000-0000-0000-0000-000000000001")
        assert isinstance(result, dict)
        assert "entities" in result


class TestGetPreferencesFor:
    @respx.mock
    async def test_filters_by_category_and_user(self, long_term):
        route = respx.get("https://memory.test/v1/preferences").respond(
            200, json=[SAMPLE_PREFERENCE]
        )
        prefs = await long_term.get_preferences_for(category="food", user_identifier="alice")
        assert len(prefs) == 1
        assert route.calls[0].request.url.params["category"] == "food"
        assert route.calls[0].request.url.params["userId"] == "alice"


class TestSupersedePreference:
    @respx.mock
    async def test_basic(self, long_term):
        route = respx.post(
            "https://memory.test/v1/preferences/00000000-0000-0000-0000-000000000001/supersede"
        ).respond(204)
        await long_term.supersede_preference("00000000-0000-0000-0000-000000000001")
        assert route.called


class TestGetFactsAbout:
    @respx.mock
    async def test_basic(self, long_term):
        respx.get("https://memory.test/v1/entities/Alice/facts").respond(200, json=[SAMPLE_FACT])
        facts = await long_term.get_facts_about("Alice")
        assert len(facts) == 1
        assert isinstance(facts[0], Fact)


class TestGetEntityRelationships:
    @respx.mock
    async def test_basic(self, long_term):
        respx.get(
            "https://memory.test/v1/entities/00000000-0000-0000-0000-000000000001/relationships"
        ).respond(
            200,
            json=[
                {
                    "id": "00000000-0000-0000-0000-00000000cccc",
                    "source_id": "00000000-0000-0000-0000-000000000001",
                    "target_id": "00000000-0000-0000-0000-000000000002",
                    "type": "WORKS_AT",
                    "created_at": "2026-05-17T12:00:00Z",
                    "metadata": {},
                    "confidence": 1.0,
                    "attributes": {},
                }
            ],
        )
        rels = await long_term.get_entity_relationships("00000000-0000-0000-0000-000000000001")
        assert len(rels) == 1
        assert isinstance(rels[0], Relationship)


class TestGetContext:
    @respx.mock
    async def test_string_response(self, long_term):
        respx.post("https://memory.test/v1/long-term/context").respond(
            200, json="assembled long-term context"
        )
        ctx = await long_term.get_context("query")
        assert ctx == "assembled long-term context"

    @respx.mock
    async def test_dict_response(self, long_term):
        respx.post("https://memory.test/v1/long-term/context").respond(
            200, json={"context": "long-term"}
        )
        ctx = await long_term.get_context("query")
        assert ctx == "long-term"


# -----------------------------------------------------------------------------
# Gold + Platinum
# -----------------------------------------------------------------------------


class TestGetEntityProvenance:
    @respx.mock
    async def test_basic(self, long_term):
        respx.get(
            "https://memory.test/v1/entities/00000000-0000-0000-0000-000000000001/provenance"
        ).respond(
            200,
            json={"sources": [{"message_id": "m1"}], "extractors": []},
        )
        prov = await long_term.get_entity_provenance("00000000-0000-0000-0000-000000000001")
        assert "sources" in prov
        assert prov["sources"][0]["message_id"] == "m1"


class TestSetEntityFeedback:
    @respx.mock
    async def test_basic(self, long_term):
        route = respx.post(
            "https://memory.test/v1/entities/00000000-0000-0000-0000-000000000001/feedback"
        ).respond(204)
        await long_term.set_entity_feedback(
            "00000000-0000-0000-0000-000000000001",
            "positive",
            user_identifier="alice",
        )
        body = json.loads(route.calls[0].request.content)
        assert body == {"feedback": "positive", "userId": "alice"}


class TestGetEntityHistory:
    @respx.mock
    async def test_basic(self, long_term):
        respx.get(
            "https://memory.test/v1/entities/00000000-0000-0000-0000-000000000001/history"
        ).respond(
            200,
            json=[
                {"conversation_id": "c1", "mention_count": 3},
                {"conversation_id": "c2", "mention_count": 1},
            ],
        )
        history = await long_term.get_entity_history(
            "00000000-0000-0000-0000-000000000001", limit=10
        )
        assert len(history) == 2
        assert history[0]["mention_count"] == 3
