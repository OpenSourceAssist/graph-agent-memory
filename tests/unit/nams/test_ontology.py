"""Unit tests for nams/ontology.py — NamsOntology accessor + models.

Endpoint shapes and payloads verified empirically against the staging
deployment (the ontology surface is absent from the OpenAPI spec).
"""

from __future__ import annotations

import json

import pytest
import respx
from pydantic import SecretStr

from neo4j_agent_memory.config.settings import NamsConfig
from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.nams import (
    ActiveOntology,
    HttpTransport,
    NamsOntology,
    Ontology,
    OntologyDocument,
    OntologySummary,
    OntologyVersion,
    StaticApiKeyAuth,
)
from neo4j_agent_memory.nams._unsupported import _NamsUnsupported

BASE = "https://memory.test/v1"

DOC = {
    "domain": {"id": "legal-clone", "name": "Legal (clone)", "tagline": "t", "emoji": "⚖️"},
    "entity_types": [
        {
            "label": "Case",
            "pole_type": "EVENT",
            "subtype": "CASE",
            "color": "#fff",
            "icon": "gavel",
            "properties": [
                {"name": "docket", "type": "string", "unique": True, "required": True},
                {"name": "status", "type": "string", "enum": ["open", "closed"]},
            ],
        }
    ],
    "relationships": [{"type": "FILED_BY", "source": "Case", "target": "Person"}],
}

SUMMARY = {
    "id": "ont_1",
    "name": "legal-clone",
    "display_name": "Legal (clone)",
    "description": "d",
    "emoji": "⚖️",
    "tagline": "t",
    "is_system": False,
    "current_revision": 2,
    "is_active": True,
}


def _version(revision=1, mode="permissive", doc=DOC):
    return {
        "id": f"ov_{revision}",
        "ontology_id": "ont_1",
        "revision": revision,
        "validation_mode": mode,
        "schema_json": json.dumps(doc),
        "schema_hash": "abc",
        "created_at": "2026-05-29T00:00:00Z",
        "message": "msg",
    }


@pytest.fixture
async def transport(nams_config):
    auth = StaticApiKeyAuth.from_config(nams_config)
    async with HttpTransport.from_config(nams_config, auth=auth) as t:
        yield t


@pytest.fixture
def ontology(transport) -> NamsOntology:
    return NamsOntology(transport)


class TestList:
    @respx.mock
    async def test_list_parses_summaries(self, ontology):
        respx.get(f"{BASE}/ontologies").respond(200, json={"ontologies": [SUMMARY]})
        result = await ontology.list()
        assert len(result) == 1
        assert isinstance(result[0], OntologySummary)
        assert result[0].name == "legal-clone"
        assert result[0].current_revision == 2
        assert result[0].is_active is True


class TestGet:
    @respx.mock
    async def test_get_parses_record_and_versions(self, ontology):
        respx.get(f"{BASE}/ontologies/ont_1").respond(
            200, json={"record": {"id": "ont_1", "name": "legal-clone"}, "versions": [_version(1)]}
        )
        result = await ontology.get("ont_1")
        assert isinstance(result, Ontology)
        assert result.record.id == "ont_1"
        assert len(result.versions) == 1
        # schema_json double-encoding is parsed into a typed document
        assert result.versions[0].document.entity_types[0].label == "Case"
        assert result.versions[0].document.entity_types[0].properties[0].unique is True


class TestGetActive:
    @respx.mock
    async def test_get_active_composes_validation_mode(self, ontology):
        respx.get(f"{BASE}/ontologies/active").respond(
            200, json={"ontology": DOC, "version": None}
        )
        respx.get(f"{BASE}/ontologies").respond(200, json={"ontologies": [SUMMARY]})
        respx.get(f"{BASE}/ontologies/ont_1").respond(
            200,
            json={"record": {"id": "ont_1", "name": "legal-clone"},
                  "versions": [_version(1, "permissive"), _version(2, "strict")]},
        )
        active = await ontology.get_active()
        assert isinstance(active, ActiveOntology)
        assert active.document.domain.id == "legal-clone"
        # current_revision=2 on the summary -> picks the strict version
        assert active.validation_mode == "strict"
        assert active.revision == 2
        assert active.version_id == "ov_2"
        assert active.ontology_id == "ont_1"


class TestWriteOps:
    @respx.mock
    async def test_clone_returns_version(self, ontology):
        respx.post(f"{BASE}/ontologies/legal/clone").respond(201, json=_version(1))
        v = await ontology.clone("legal")
        assert isinstance(v, OntologyVersion)
        assert v.ontology_id == "ont_1"
        assert v.document.domain.id == "legal-clone"

    @respx.mock
    async def test_create_wraps_ontology_key(self, ontology):
        route = respx.post(f"{BASE}/ontologies").respond(201, json=_version(1))
        doc = OntologyDocument.model_validate(DOC)
        await ontology.create("legal-clone", doc, validation_mode="strict")
        body = json.loads(route.calls.last.request.content)
        assert "ontology" in body
        assert body["ontology"]["domain"]["id"] == "legal-clone"
        assert body["validation_mode"] == "strict"

    @respx.mock
    async def test_update_wraps_ontology_key_and_bumps_revision(self, ontology):
        route = respx.put(f"{BASE}/ontologies/ont_1").respond(200, json=_version(2, "strict"))
        v = await ontology.update("ont_1", OntologyDocument.model_validate(DOC))
        body = json.loads(route.calls.last.request.content)
        assert "ontology" in body  # update uses the same wrapper as create
        assert v.revision == 2

    @respx.mock
    async def test_activate_posts_version_id(self, ontology):
        route = respx.post(f"{BASE}/ontologies/active").respond(200, json=_version(2, "strict"))
        await ontology.activate("ov_2")
        body = json.loads(route.calls.last.request.content)
        assert body == {"version_id": "ov_2"}

    @respx.mock
    async def test_delete(self, ontology):
        route = respx.delete(f"{BASE}/ontologies/ont_1").respond(204)
        await ontology.delete("ont_1")
        assert route.called


class TestModelResilience:
    def test_null_collections_coerced(self):
        doc = OntologyDocument.model_validate(
            {"domain": {"id": "x", "name": "X"}, "entity_types": None, "relationships": None}
        )
        assert doc.entity_types == []
        assert doc.relationships == []

    def test_extra_fields_ignored(self):
        s = OntologySummary.model_validate({**SUMMARY, "unknown_future_field": 123})
        assert s.name == "legal-clone"


class TestBackendGuards:
    @respx.mock
    async def test_bridge_transport_raises_not_supported(self):
        config = NamsConfig(
            endpoint="https://memory.test", api_key=SecretStr("k"),  # bridge shape (no /vN)
            transport_mode="bridge", validate_on_connect=False,
        )
        async with HttpTransport.from_config(
            config, auth=StaticApiKeyAuth.from_config(config)
        ) as t:
            with pytest.raises(NotSupportedError, match="REST"):
                await NamsOntology(t).list()

    async def test_bolt_sentinel_raises(self):
        # On bolt, client.ontology is a sentinel that raises on method call.
        sentinel = _NamsUnsupported(
            accessor="ontology", message="NAMS capability.",
            workaround="SchemaModel.CUSTOM",
        )
        with pytest.raises(NotSupportedError, match="ontology"):
            await sentinel.list()
