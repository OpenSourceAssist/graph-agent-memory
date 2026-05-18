"""NAMS implementation of :class:`LongTermProtocol`.

Endpoint mappings verified against the live NAMS OpenAPI spec.

NAMS provides first-class **Entity** endpoints only. Preferences,
facts, and entity relationships are NOT exposed as dedicated REST
endpoints — those features must go through the Cypher console
(``client.query.cypher``) or are out of scope on NAMS entirely.

Methods that raise :class:`NotSupportedError`:

* ``add_preference``, ``search_preferences``, ``get_preferences_for``,
  ``supersede_preference``
* ``add_fact``, ``search_facts``, ``get_facts_about``
* ``add_relationship``, ``get_entity_relationships``,
  ``get_related_entities``

NAMS-specific endpoint shapes vs. our Protocol:

* Entity create body is ``{name, type, description?}`` — no subtype,
  aliases, attributes, confidence (those are bolt-only).
* Entity search returns ``{"entities": [...], "searchType": ...}``
  envelope.
* Entity feedback is **PUT** not POST, body
  ``{userScore?, confirmed?}`` (no free-form ``feedback`` string).
* Entity provenance lives under ``/v1/reasoning/provenance/{entityId}``
  (not ``/v1/entities/{id}/provenance``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.memory.long_term import (
    Entity,
    Fact,
    Preference,
    Relationship,
)
from neo4j_agent_memory.nams._serialization import payload_to_model, snakeize_keys
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


# -----------------------------------------------------------------------------
# Endpoint registry — verified against live NAMS OpenAPI spec.
# -----------------------------------------------------------------------------

_SPEC_LIST_ENTITIES = EndpointSpec(
    rest_method="GET", rest_path="/entities", bridge_method="list_entities"
)
_SPEC_ADD_ENTITY = EndpointSpec(
    rest_method="POST", rest_path="/entities", bridge_method="add_entity"
)
_SPEC_GET_ENTITY = EndpointSpec(
    rest_method="GET", rest_path="/entities/{entity_id}", bridge_method="get_entity"
)
_SPEC_UPDATE_ENTITY = EndpointSpec(
    rest_method="PUT", rest_path="/entities/{entity_id}", bridge_method="update_entity"
)
_SPEC_DELETE_ENTITY = EndpointSpec(
    rest_method="DELETE", rest_path="/entities/{entity_id}", bridge_method="delete_entity"
)
_SPEC_SET_ENTITY_FEEDBACK = EndpointSpec(
    rest_method="PUT",  # NAMS uses PUT for feedback
    rest_path="/entities/{entity_id}/feedback",
    bridge_method="set_entity_feedback",
)
_SPEC_GET_ENTITY_HISTORY = EndpointSpec(
    rest_method="GET",
    rest_path="/entities/{entity_id}/history",
    bridge_method="get_entity_history",
)
_SPEC_MERGE_ENTITIES = EndpointSpec(
    rest_method="POST",
    rest_path="/entities/{entity_id}/merge",
    bridge_method="merge_entities",
)
_SPEC_ENTITY_GRAPH = EndpointSpec(
    rest_method="GET", rest_path="/entities/graph", bridge_method="entity_graph"
)
_SPEC_SEARCH_ENTITIES = EndpointSpec(
    rest_method="POST", rest_path="/entities/search", bridge_method="search_entities"
)

# Entity provenance is under the reasoning namespace per verified spec.
_SPEC_GET_ENTITY_PROVENANCE = EndpointSpec(
    rest_method="GET",
    rest_path="/reasoning/provenance/{entity_id}",
    bridge_method="get_entity_provenance",
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _to_str(value: UUID | str) -> str:
    return str(value)


def _normalize_entity(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Map NAMS Entity response → bolt Pydantic shape.

    NAMS Entity fields: ``id, name, type, description, confidence,
    sourceStage, createdAt, updatedAt`` (camelCase). The bolt Entity
    model adds ``aliases``, ``attributes``, ``subtype`` which NAMS
    doesn't provide — we default them so Pydantic parsing succeeds.
    """
    from datetime import datetime, timezone

    data = snakeize_keys(payload) if isinstance(payload, dict) else {}
    if "created_at" not in data:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
    if "metadata" not in data:
        data["metadata"] = {}
    if "aliases" not in data:
        data["aliases"] = []
    if "attributes" not in data:
        data["attributes"] = {}
    return data


# -----------------------------------------------------------------------------
# NamsLongTermMemory
# -----------------------------------------------------------------------------


class NamsLongTermMemory:
    """Long-term memory backed by the NAMS HTTP service.

    Provides entity operations only (NAMS exposes no first-class
    preference / fact / relationship endpoints). Other Protocol methods
    raise :class:`NotSupportedError`.
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------ Bronze

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        **kwargs: Any,
    ) -> Entity:
        """Create an entity on NAMS.

        NAMS accepts only ``{name, type, description?}`` per spec.
        Bolt-only kwargs (``subtype``, ``aliases``, ``attributes``,
        ``confidence``, ``deduplicate``, ``geocode``, ``enrich``, etc.)
        are silently dropped.
        """
        body = _drop_none(
            {
                "name": name,
                "type": entity_type,
                "description": kwargs.get("description"),
            }
        )
        payload = await self._transport.request(_SPEC_ADD_ENTITY, json=body)
        return payload_to_model(_normalize_entity(payload), Entity)

    async def add_preference(self, category: str, preference: str, **kwargs: Any) -> Preference:
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.add_preference",
            message="NAMS does not expose a preferences endpoint.",
            workaround=(
                "Store preferences via client.query.cypher with an explicit "
                "MERGE (:Preference {category, value}) — but note NAMS is "
                "read-only for Cypher. For full preference support, use bolt."
            ),
        )

    async def add_fact(self, subject: str, predicate: str, object: str, **kwargs: Any) -> Fact:  # noqa: A002
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.add_fact",
            message="NAMS does not expose a facts endpoint.",
            workaround="For full facts support, use the bolt backend.",
        )

    async def add_relationship(
        self,
        source_id: UUID | str,
        relationship_type: str,
        target_id: UUID | str,
        **kwargs: Any,
    ) -> None:
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.add_relationship",
            message=(
                "NAMS does not expose a relationships endpoint. Relationships "
                "are accessible read-only via get_entity(id) which inlines "
                "them in the response."
            ),
            workaround="For write-side relationship support, use the bolt backend.",
        )

    async def search_entities(self, query: str, **kwargs: Any) -> list[Entity]:
        """Vector/keyword search across entities.

        NAMS response: ``{"entities": [...], "searchType": "vector"|"text"}``.
        """
        body = _drop_none(
            {
                "query": query,
                "type": kwargs.get("entity_type") or kwargs.get("type"),
                "limit": kwargs.get("limit"),
            }
        )
        payload = await self._transport.request(_SPEC_SEARCH_ENTITIES, json=body)
        items: list[Any]
        if isinstance(payload, dict) and "entities" in payload:
            items = payload["entities"]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return [payload_to_model(_normalize_entity(item), Entity) for item in items]

    async def search_preferences(self, query: str, **kwargs: Any) -> list[Preference]:
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.search_preferences",
            message="NAMS does not expose a preferences endpoint.",
        )

    async def search_facts(self, query: str, **kwargs: Any) -> list[Fact]:
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.search_facts",
            message="NAMS does not expose a facts endpoint.",
        )

    async def get_entity_by_name(self, name: str) -> Entity | None:
        """Look up an entity by name.

        NAMS doesn't expose a ``GET /entities?name=`` filter — we use
        ``POST /entities/search`` with the name as the query and return
        the first hit whose name matches exactly. Returns ``None`` if
        no match is found.
        """
        results = await self.search_entities(name, limit=20)
        for e in results:
            if e.name == name:
                return e
        return None

    # ------------------------------------------------------------------ Silver

    async def get_related_entities(self, entity_id: UUID | str, **kwargs: Any) -> Any:
        """Return entities related to ``entity_id``.

        NAMS exposes inline relationships on ``GET /entities/{id}`` —
        we fetch the entity and return the ``relationships`` array.
        Each relationship has ``{relType, targetId, targetName, targetType}``.
        """
        payload = await self._transport.request(
            _SPEC_GET_ENTITY,
            path_params={"entity_id": _to_str(entity_id)},
        )
        if not isinstance(payload, dict):
            return []
        # camelCase → snake_case for the wrapper, but keep relationships verbatim
        # for the caller — they're identifying refs, not full Entity objects.
        rels = payload.get("relationships") or []
        return list(rels)

    async def get_preferences_for(self, **kwargs: Any) -> list[Preference]:
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.get_preferences_for",
            message="NAMS does not expose a preferences endpoint.",
        )

    async def supersede_preference(self, preference_id: UUID | str, **kwargs: Any) -> None:
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.supersede_preference",
            message="NAMS does not expose a preferences endpoint.",
        )

    async def get_facts_about(self, entity_name: str) -> list[Fact]:
        raise NotSupportedError(
            backend="nams",
            method="LongTermMemory.get_facts_about",
            message="NAMS does not expose a facts endpoint.",
        )

    async def get_entity_relationships(self, entity_id: UUID | str) -> list[Relationship]:
        """Return relationships from an entity (inline on NAMS).

        NAMS returns relationships inline on ``GET /v1/entities/{id}``
        with shape ``{relType, targetId, targetName, targetType}``.
        These don't carry full :class:`Relationship` fields
        (``source_id``, ``confidence``, ``valid_from``, etc.), so we
        synthesize what we can — the result is a list of
        :class:`Relationship` with bolt-flavored field names where
        the source field is the entity_id parameter.
        """
        from datetime import datetime, timezone

        payload = await self._transport.request(
            _SPEC_GET_ENTITY,
            path_params={"entity_id": _to_str(entity_id)},
        )
        if not isinstance(payload, dict):
            return []
        rels = payload.get("relationships") or []
        now_iso = datetime.now(timezone.utc).isoformat()
        out: list[Relationship] = []
        for r in rels:
            if not isinstance(r, dict):
                continue
            from uuid import uuid4

            normalized = {
                "id": str(uuid4()),
                "source_id": _to_str(entity_id),
                "target_id": r.get("targetId") or r.get("target_id") or "",
                "type": r.get("relType") or r.get("rel_type") or r.get("type") or "RELATED_TO",
                "created_at": now_iso,
                "metadata": {},
                "attributes": {
                    "target_name": r.get("targetName") or r.get("target_name"),
                    "target_type": r.get("targetType") or r.get("target_type"),
                },
            }
            out.append(payload_to_model(normalized, Relationship))
        return out

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """Long-term context — not exposed by NAMS as a dedicated endpoint.

        Returns an empty string. Use ``client.long_term.search_entities``
        and ``client.short_term.get_context`` to assemble context yourself,
        or use the bolt backend.
        """
        return ""

    # -------------------------------------------------------------------- Gold

    async def get_entity_provenance(self, entity_id: UUID | str) -> dict[str, Any]:
        """Return source-of-truth provenance for an entity.

        Per verified spec, this is under the reasoning namespace:
        ``GET /v1/reasoning/provenance/{entityId}``. Response:
        ``{entityId, steps: [...]}``.
        """
        payload = await self._transport.request(
            _SPEC_GET_ENTITY_PROVENANCE,
            path_params={"entity_id": _to_str(entity_id)},
        )
        return dict(payload or {})

    # ---------------------------------------------------------------- Platinum

    async def set_entity_feedback(
        self,
        entity_id: UUID | str,
        feedback: str,
        **kwargs: Any,
    ) -> None:
        """Record feedback on an entity.

        Per verified spec, NAMS uses **PUT** (not POST) at
        ``/v1/entities/{id}/feedback`` with body
        ``{userScore?, confirmed?}``. There is no free-form
        ``feedback`` string field — we map the Protocol's
        ``feedback`` parameter to ``userScore``:

        * ``"positive"`` → ``userScore=1.0, confirmed=True``
        * ``"negative"`` → ``userScore=0.0, confirmed=False``
        * float-stringed (e.g. ``"0.75"``) → ``userScore=<float>``

        Pass ``user_score=`` and ``confirmed=`` kwargs to override.
        """
        # Priority: explicit kwargs > derived from feedback string.
        user_score: float | None = kwargs.get("user_score")
        confirmed: bool | None = kwargs.get("confirmed")

        if user_score is None and confirmed is None:
            # Derive from feedback string.
            feedback_lc = (feedback or "").lower()
            if feedback_lc == "positive":
                user_score, confirmed = 1.0, True
            elif feedback_lc == "negative":
                user_score, confirmed = 0.0, False
            else:
                try:
                    user_score = float(feedback)
                except (TypeError, ValueError):
                    pass

        body = _drop_none({"userScore": user_score, "confirmed": confirmed})
        await self._transport.request(
            _SPEC_SET_ENTITY_FEEDBACK,
            path_params={"entity_id": _to_str(entity_id)},
            json=body,
        )

    async def get_entity_history(
        self,
        entity_id: UUID | str,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Return mention/edit history for an entity.

        NAMS response: ``{entityId, mentions: [...]}``. We return the
        ``mentions`` array.
        """
        payload = await self._transport.request(
            _SPEC_GET_ENTITY_HISTORY,
            path_params={"entity_id": _to_str(entity_id)},
        )
        if isinstance(payload, dict) and "mentions" in payload:
            return list(payload["mentions"])
        return []


__all__ = ["NamsLongTermMemory"]
