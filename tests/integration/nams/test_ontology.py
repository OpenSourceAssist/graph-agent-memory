"""Integration tests for the NAMS ontology surface (P2).

Exercises the live ontology lifecycle against the staging deployment:
list → clone → update (new revision) → activate → get_active → delete,
plus a strict-mode validation check.

These tests **mutate workspace-global active-ontology state**, so the
``restore_active_ontology`` fixture snapshots the active version before
each test and rebinds it afterward. Created ontologies are tracked and
deleted on teardown.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.nams import OntologyDocument

pytestmark = pytest.mark.integration

# A template unlikely to clash with other suites; its clone is "<name>-clone".
TEMPLATE = "conservation"
CLONE_NAME = f"{TEMPLATE}-clone"


@pytest.fixture
async def restore_active_ontology(nams_client: MemoryClient) -> AsyncIterator[None]:
    """Snapshot the active ontology version, restore it on teardown."""
    onto = nams_client.ontology
    before = await onto.get_active()
    prior_version_id = before.version_id
    yield
    # Best-effort cleanup: delete any test clone, restore prior active.
    for summary in await onto.list():
        if summary.name == CLONE_NAME and not summary.is_system:
            try:
                await onto.delete(summary.id)
            except Exception:  # noqa: BLE001 — best-effort teardown
                pass
    if prior_version_id:
        try:
            await onto.activate(prior_version_id)
        except Exception:  # noqa: BLE001
            pass


@pytest.fixture
async def fresh_clone(nams_client: MemoryClient, restore_active_ontology: None):
    """Delete any pre-existing clone, then clone TEMPLATE fresh."""
    onto = nams_client.ontology
    for summary in await onto.list():
        if summary.name == CLONE_NAME and not summary.is_system:
            await onto.delete(summary.id)
    return await onto.clone(TEMPLATE)


@pytest.mark.asyncio
async def test_list_includes_system_templates(nams_client: MemoryClient) -> None:
    catalog = await nams_client.ontology.list()
    names = {o.name for o in catalog}
    assert TEMPLATE in names
    assert "nams-default" in names
    # System templates are flagged.
    assert any(o.is_system for o in catalog)


@pytest.mark.asyncio
async def test_clone_returns_revision_1_version(fresh_clone) -> None:
    assert fresh_clone.revision == 1
    assert fresh_clone.ontology_id.startswith("ont_")
    assert fresh_clone.id.startswith("ov_")
    assert fresh_clone.document is not None
    assert len(fresh_clone.document.entity_types) > 0


@pytest.mark.asyncio
async def test_update_creates_new_revision_preserving_schema(
    nams_client: MemoryClient, fresh_clone
) -> None:
    onto = nams_client.ontology
    original_types = len(fresh_clone.document.entity_types)
    v2 = await onto.update(fresh_clone.ontology_id, fresh_clone.document)
    assert v2.revision == 2
    # The schema is preserved across the revision (regression: the body must
    # be wrapped under "ontology", else the service stores an empty schema).
    assert len(v2.document.entity_types) == original_types


@pytest.mark.asyncio
async def test_activate_and_get_active_surface_validation_mode(
    nams_client: MemoryClient, fresh_clone
) -> None:
    onto = nams_client.ontology
    strict = await onto.update(
        fresh_clone.ontology_id, fresh_clone.document, validation_mode="strict"
    )
    await onto.activate(strict.id)

    active = await onto.get_active()
    assert active.document.domain.id == CLONE_NAME
    assert active.validation_mode == "strict"
    assert active.revision == strict.revision
    assert active.version_id == strict.id


@pytest.mark.asyncio
async def test_create_from_document(
    nams_client: MemoryClient, restore_active_ontology: None
) -> None:
    onto = nams_client.ontology
    name = "itest-create-ontology"
    # clean any leftover
    for s in await onto.list():
        if s.name == name and not s.is_system:
            await onto.delete(s.id)
    doc = OntologyDocument.model_validate(
        {
            "domain": {"id": name, "name": "Integration Create", "description": "synthetic"},
            "entity_types": [
                {
                    "label": "Widget",
                    "pole_type": "OBJECT",
                    "properties": [{"name": "sku", "type": "string", "unique": True}],
                }
            ],
            "relationships": [],
        }
    )
    try:
        v = await onto.create(name, doc)
        assert v.revision == 1
        assert v.document.entity_types[0].label == "Widget"
    finally:
        for s in await onto.list():
            if s.name == name and not s.is_system:
                await onto.delete(s.id)
