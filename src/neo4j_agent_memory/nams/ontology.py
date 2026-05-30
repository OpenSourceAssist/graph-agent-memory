"""NAMS ontology surface — typed domain schemas extending POLE+O.

An *ontology* is a versioned, validated, typed schema for the knowledge
graph: entity types (each mapped onto a POLE+O ``pole_type``) with typed
properties (``required`` / ``unique`` / ``enum`` constraints) and typed
relationships. NAMS ships ~28 system templates and supports
workspace-owned ontologies with immutable revisions, activation, and a
per-version ``validation_mode`` (``permissive`` records non-conforming
writes; ``strict`` rejects them).

This module exposes :class:`NamsOntology` — the ``client.ontology``
accessor — plus the Pydantic models that hide the wire shape (notably the
double-encoded ``schema_json`` string the service returns, which we parse
into :class:`OntologyDocument`).

Contract note
=============

The ontology endpoints are **not** documented in the staging OpenAPI;
the routes and payloads below were verified empirically against the
development/staging deployment:

* ``GET    /ontologies``                          → list (summaries)
* ``GET    /ontologies/{id}``                      → ``{record, versions[]}``
* ``GET    /ontologies/active``                    → ``{ontology, version}``
* ``POST   /ontologies/{name}/clone``              → version (template name in path)
* ``POST   /ontologies``  body ``{ontology, validation_mode?}`` → version
* ``PUT    /ontologies/{id}``  body ``{ontology, validation_mode?}`` → new revision
* ``POST   /ontologies/active``  body ``{version_id}``          → version
* ``DELETE /ontologies/{id}``                       → 204
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


def _none_to_list(v: Any) -> Any:
    """Coerce a ``null`` collection to ``[]`` (the service emits null for empty)."""
    return [] if v is None else v


# -----------------------------------------------------------------------------
# Models — lenient (extra="ignore") so server additions don't break parsing.
# -----------------------------------------------------------------------------


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class PropertyDef(_Lenient):
    """A typed property on an entity type."""

    name: str
    type: str  # string | datetime | date | float | integer
    required: bool = False
    unique: bool = False
    enum: list[str] | None = None


class EntityTypeDef(_Lenient):
    """A typed entity in the ontology, mapped onto a POLE+O ``pole_type``."""

    label: str
    pole_type: str  # PERSON | ORGANIZATION | LOCATION | EVENT | OBJECT
    subtype: str | None = None
    color: str | None = None
    icon: str | None = None
    properties: Annotated[list[PropertyDef], BeforeValidator(_none_to_list)] = Field(
        default_factory=list
    )


class RelationshipDef(_Lenient):
    """A typed relationship between two entity labels."""

    type: str  # UPPER_SNAKE
    source: str
    target: str


class DomainInfo(_Lenient):
    """Display + identity metadata for an ontology."""

    id: str
    name: str
    description: str | None = None
    tagline: str | None = None
    emoji: str | None = None


class OntologyDocument(_Lenient):
    """The parsed schema body — domain + entity types + relationships."""

    domain: DomainInfo
    entity_types: Annotated[list[EntityTypeDef], BeforeValidator(_none_to_list)] = Field(
        default_factory=list
    )
    relationships: Annotated[list[RelationshipDef], BeforeValidator(_none_to_list)] = Field(
        default_factory=list
    )


class OntologySummary(_Lenient):
    """One row from ``list()`` — system templates + workspace-owned."""

    id: str
    name: str
    display_name: str | None = None
    description: str | None = None
    emoji: str | None = None
    tagline: str | None = None
    is_system: bool = False
    current_revision: int | None = None
    is_active: bool = False


class OntologyVersion(_Lenient):
    """An immutable ontology revision. ``document`` is the parsed schema.

    The field is named ``document`` (not ``schema``) to avoid shadowing
    Pydantic's reserved ``BaseModel.schema``.
    """

    id: str
    ontology_id: str
    revision: int
    validation_mode: str  # permissive | strict
    document: OntologyDocument | None = None
    schema_hash: str | None = None
    created_at: str | None = None
    message: str | None = None


class OntologyRecord(_Lenient):
    """Identity row for a workspace-owned or system ontology."""

    id: str
    name: str
    description: str | None = None
    workspace_id: str | None = None
    is_system: bool = False
    created_at: str | None = None


class Ontology(_Lenient):
    """A single ontology with its full revision history."""

    record: OntologyRecord
    versions: list[OntologyVersion] = Field(default_factory=list)


class ActiveOntology(_Lenient):
    """The currently-bound ontology, with version metadata composed in.

    ``validation_mode`` / ``revision`` / ``version_id`` are populated by a
    second lookup (the ``/ontologies/active`` response itself carries no
    version metadata).
    """

    document: OntologyDocument
    validation_mode: str | None = None
    revision: int | None = None
    ontology_id: str | None = None
    version_id: str | None = None


# -----------------------------------------------------------------------------
# Parsing helpers
# -----------------------------------------------------------------------------


def _parse_document(raw: Any) -> OntologyDocument | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return None
    if isinstance(raw, dict):
        return OntologyDocument.model_validate(raw)
    return None


def _parse_version(raw: dict[str, Any]) -> OntologyVersion:
    data = dict(raw)
    schema_json = data.pop("schema_json", None)
    doc = _parse_document(schema_json) if schema_json is not None else None
    return OntologyVersion.model_validate({**data, "document": doc})


# -----------------------------------------------------------------------------
# Endpoint specs (REST-only — ontology is a hosted-NAMS capability).
# -----------------------------------------------------------------------------

_SPEC_LIST = EndpointSpec(rest_method="GET", rest_path="/ontologies", bridge_method="list_ontologies")
_SPEC_GET = EndpointSpec(
    rest_method="GET", rest_path="/ontologies/{id}", bridge_method="get_ontology"
)
_SPEC_GET_ACTIVE = EndpointSpec(
    rest_method="GET", rest_path="/ontologies/active", bridge_method="get_active_ontology"
)
_SPEC_CLONE = EndpointSpec(
    rest_method="POST", rest_path="/ontologies/{name}/clone", bridge_method="clone_ontology"
)
_SPEC_CREATE = EndpointSpec(
    rest_method="POST", rest_path="/ontologies", bridge_method="create_ontology"
)
_SPEC_UPDATE = EndpointSpec(
    rest_method="PUT", rest_path="/ontologies/{id}", bridge_method="update_ontology"
)
_SPEC_ACTIVATE = EndpointSpec(
    rest_method="POST", rest_path="/ontologies/active", bridge_method="activate_ontology"
)
_SPEC_DELETE = EndpointSpec(
    rest_method="DELETE", rest_path="/ontologies/{id}", bridge_method="delete_ontology"
)


# -----------------------------------------------------------------------------
# Accessor
# -----------------------------------------------------------------------------


class NamsOntology:
    """``client.ontology`` — the NAMS ontology lifecycle.

    Lifecycle::

        v = await client.ontology.clone("healthcare")   # editable copy, rev 1
        # v = await client.ontology.update(v.ontology_id, schema=doc)  # -> rev 2
        await client.ontology.activate(v.id)             # bind the version
        active = await client.ontology.get_active()      # parsed body + mode

    From activation onward, server-side extraction validates entity writes
    against the active schema (``strict`` rejects non-conforming writes →
    :class:`ValidationError`).
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def _guard_rest(self) -> None:
        if self._transport.protocol != "rest":
            raise NotSupportedError(
                backend="nams",
                method="ontology",
                message="The ontology surface requires the REST transport (a /vN "
                "endpoint); it is not available over the TCK bridge.",
            )

    async def list(self) -> list[OntologySummary]:
        """List system templates + workspace-owned ontologies (active flagged)."""
        self._guard_rest()
        payload = await self._transport.request(_SPEC_LIST)
        items = payload.get("ontologies", []) if isinstance(payload, dict) else (payload or [])
        return [OntologySummary.model_validate(i) for i in items if isinstance(i, dict)]

    async def get(self, ontology_id: str) -> Ontology:
        """Return one ontology with its full revision history."""
        self._guard_rest()
        payload = await self._transport.request(_SPEC_GET, path_params={"id": ontology_id})
        payload = payload or {}
        record = payload.get("record") or {}
        versions = [_parse_version(v) for v in (payload.get("versions") or []) if isinstance(v, dict)]
        return Ontology(record=OntologyRecord.model_validate(record), versions=versions)

    async def get_active(self) -> ActiveOntology:
        """Return the active ontology's parsed body + composed version metadata.

        ``GET /ontologies/active`` returns the schema body but no version
        metadata, so we resolve the active ontology id (via the ``is_active``
        flag from :meth:`list`) and read its current version to surface
        ``validation_mode`` / ``revision`` / ``version_id``.
        """
        self._guard_rest()
        payload = await self._transport.request(_SPEC_GET_ACTIVE)
        payload = payload or {}
        body = payload.get("ontology") or payload
        document = _parse_document(body)
        if document is None:
            raise NotSupportedError(
                backend="nams",
                method="ontology.get_active",
                message="No active ontology bound for this workspace.",
            )

        active = ActiveOntology(document=document)
        # Compose version metadata via a second lookup.
        summaries = await self.list()
        match = next((s for s in summaries if s.is_active), None)
        if match is None:
            # Fall back to matching the active document's domain id to a name.
            match = next((s for s in summaries if s.name == document.domain.id), None)
        if match is not None:
            active.ontology_id = match.id
            detail = await self.get(match.id)
            current = _current_version(detail, match.current_revision)
            if current is not None:
                active.validation_mode = current.validation_mode
                active.revision = current.revision
                active.version_id = current.id
        return active

    async def clone(self, template_name: str) -> OntologyVersion:
        """Clone a system template into an editable workspace copy (revision 1)."""
        self._guard_rest()
        payload = await self._transport.request(
            _SPEC_CLONE, path_params={"name": template_name}
        )
        return _parse_version(payload or {})

    async def create(
        self,
        name: str,  # noqa: ARG002 — identity comes from schema.domain; kept for ergonomics/docs
        schema: OntologyDocument | dict[str, Any],
        *,
        validation_mode: str | None = None,
    ) -> OntologyVersion:
        """Create a new workspace ontology from a schema body (revision 1).

        ``name`` is accepted for API symmetry but the ontology's identity
        comes from ``schema.domain`` (NAMS reads ``domain.id`` / ``domain.name``).
        """
        self._guard_rest()
        doc = _as_document_dict(schema)
        body: dict[str, Any] = {"ontology": doc}
        if validation_mode is not None:
            body["validation_mode"] = validation_mode
        payload = await self._transport.request(_SPEC_CREATE, json=body)
        return _parse_version(payload or {})

    async def update(
        self,
        ontology_id: str,
        schema: OntologyDocument | dict[str, Any],
        *,
        validation_mode: str | None = None,
    ) -> OntologyVersion:
        """Create a new immutable revision (n+1) from an updated schema body."""
        self._guard_rest()
        body: dict[str, Any] = {"ontology": _as_document_dict(schema)}
        if validation_mode is not None:
            body["validation_mode"] = validation_mode
        payload = await self._transport.request(
            _SPEC_UPDATE, path_params={"id": ontology_id}, json=body
        )
        return _parse_version(payload or {})

    async def activate(self, version_id: str) -> OntologyVersion:
        """Bind a version; subsequent entity writes validate against it."""
        self._guard_rest()
        payload = await self._transport.request(
            _SPEC_ACTIVATE, json={"version_id": version_id}
        )
        return _parse_version(payload or {})

    async def delete(self, ontology_id: str) -> None:
        """Delete a workspace-owned ontology."""
        self._guard_rest()
        await self._transport.request(_SPEC_DELETE, path_params={"id": ontology_id})


def _current_version(ontology: Ontology, revision: int | None) -> OntologyVersion | None:
    if not ontology.versions:
        return None
    if revision is not None:
        for v in ontology.versions:
            if v.revision == revision:
                return v
    return max(ontology.versions, key=lambda v: v.revision)


def _as_document_dict(schema: OntologyDocument | dict[str, Any]) -> dict[str, Any]:
    if isinstance(schema, OntologyDocument):
        return schema.model_dump(exclude_none=True)
    return schema


__all__ = [
    "NamsOntology",
    "Ontology",
    "OntologySummary",
    "OntologyVersion",
    "OntologyRecord",
    "OntologyDocument",
    "ActiveOntology",
    "DomainInfo",
    "EntityTypeDef",
    "PropertyDef",
    "RelationshipDef",
]
