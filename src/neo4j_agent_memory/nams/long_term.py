"""NAMS implementation of :class:`LongTermProtocol`.

Endpoint mappings inferred from plan §G. Bolt-only deduplication
features (``find_potential_duplicates``, ``merge_duplicate_entities``,
``review_duplicate``, etc.) are NOT on this class — NAMS handles
deduplication server-side and exposes ``set_entity_feedback`` instead.
Same for geocoding, enrichment, and extractor provenance.

Note: :meth:`add_entity` returns just :class:`Entity` here (matching the
SPEC), unlike bolt's ``(Entity, DeduplicationResult)`` tuple. Portable
code that needs to support both should branch on the return type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from neo4j_agent_memory.memory.long_term import (
    Entity,
    Fact,
    Preference,
    Relationship,
)
from neo4j_agent_memory.nams._serialization import payload_to_model
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


# -----------------------------------------------------------------------------
# Endpoint registry
# -----------------------------------------------------------------------------

_SPEC_ADD_ENTITY = EndpointSpec(
    rest_method="POST", rest_path="/entities", bridge_method="add_entity"
)
_SPEC_ADD_PREFERENCE = EndpointSpec(
    rest_method="POST", rest_path="/preferences", bridge_method="add_preference"
)
_SPEC_ADD_FACT = EndpointSpec(
    rest_method="POST", rest_path="/facts", bridge_method="add_fact"
)
_SPEC_ADD_RELATIONSHIP = EndpointSpec(
    rest_method="POST", rest_path="/relationships", bridge_method="add_relationship"
)

_SPEC_SEARCH_ENTITIES = EndpointSpec(
    rest_method="POST", rest_path="/entities/search", bridge_method="search_entities"
)
_SPEC_SEARCH_PREFERENCES = EndpointSpec(
    rest_method="POST",
    rest_path="/preferences/search",
    bridge_method="search_preferences",
)
_SPEC_SEARCH_FACTS = EndpointSpec(
    rest_method="POST", rest_path="/facts/search", bridge_method="search_facts"
)

_SPEC_GET_ENTITY_BY_NAME = EndpointSpec(
    rest_method="GET", rest_path="/entities", bridge_method="get_entity_by_name"
)
_SPEC_GET_RELATED_ENTITIES = EndpointSpec(
    rest_method="GET",
    rest_path="/entities/{entity_id}/related",
    bridge_method="get_related_entities",
)
_SPEC_GET_PREFERENCES_FOR = EndpointSpec(
    rest_method="GET", rest_path="/preferences", bridge_method="get_preferences_for"
)
# TODO(nams-spec): verify supersede route shape.
_SPEC_SUPERSEDE_PREFERENCE = EndpointSpec(
    rest_method="POST",
    rest_path="/preferences/{preference_id}/supersede",
    bridge_method="supersede_preference",
)
_SPEC_GET_FACTS_ABOUT = EndpointSpec(
    rest_method="GET",
    rest_path="/entities/{entity_name}/facts",
    bridge_method="get_facts_about",
)
_SPEC_GET_ENTITY_RELATIONSHIPS = EndpointSpec(
    rest_method="GET",
    rest_path="/entities/{entity_id}/relationships",
    bridge_method="get_entity_relationships",
)
# TODO(nams-spec): verify long-term get_context shape vs short-term.
_SPEC_GET_CONTEXT = EndpointSpec(
    rest_method="POST",
    rest_path="/long-term/context",
    bridge_method="get_context",
)

_SPEC_GET_ENTITY_PROVENANCE = EndpointSpec(
    rest_method="GET",
    rest_path="/entities/{entity_id}/provenance",
    bridge_method="get_entity_provenance",
)
_SPEC_SET_ENTITY_FEEDBACK = EndpointSpec(
    rest_method="POST",
    rest_path="/entities/{entity_id}/feedback",
    bridge_method="set_entity_feedback",
)
_SPEC_GET_ENTITY_HISTORY = EndpointSpec(
    rest_method="GET",
    rest_path="/entities/{entity_id}/history",
    bridge_method="get_entity_history",
)


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _to_str(value: UUID | str) -> str:
    return str(value)


class NamsLongTermMemory:
    """Long-term memory backed by the NAMS HTTP service."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------ Bronze

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        **kwargs: Any,
    ) -> Entity:
        """Create or upsert an entity. Returns just :class:`Entity` (no dedup tuple)."""
        body = _drop_none(
            {
                "name": name,
                "type": entity_type,
                "subtype": kwargs.get("subtype"),
                "description": kwargs.get("description"),
                "aliases": kwargs.get("aliases"),
                "attributes": kwargs.get("attributes"),
                "confidence": kwargs.get("confidence"),
                "metadata": kwargs.get("metadata"),
                "userId": kwargs.get("user_identifier"),
            }
        )
        payload = await self._transport.request(_SPEC_ADD_ENTITY, json=body)
        return payload_to_model(payload, Entity)

    async def add_preference(
        self,
        category: str,
        preference: str,
        **kwargs: Any,
    ) -> Preference:
        """Record a user preference."""
        body = _drop_none(
            {
                "category": category,
                "preference": preference,
                "context": kwargs.get("context"),
                "confidence": kwargs.get("confidence"),
                "metadata": kwargs.get("metadata"),
                "userId": kwargs.get("user_identifier"),
                "applies_to": kwargs.get("applies_to"),
            }
        )
        payload = await self._transport.request(_SPEC_ADD_PREFERENCE, json=body)
        return payload_to_model(payload, Preference)

    async def add_fact(
        self,
        subject: str,
        predicate: str,
        object: str,  # noqa: A002 — SPEC name; shadows builtin
        **kwargs: Any,
    ) -> Fact:
        """Record a subject-predicate-object fact."""
        body = _drop_none(
            {
                "subject": subject,
                "predicate": predicate,
                "object": object,
                "confidence": kwargs.get("confidence"),
                "source_id": (
                    _to_str(kwargs["source_id"])
                    if kwargs.get("source_id") is not None
                    else None
                ),
                "valid_from": kwargs.get("valid_from"),
                "valid_until": kwargs.get("valid_until"),
                "metadata": kwargs.get("metadata"),
            }
        )
        payload = await self._transport.request(_SPEC_ADD_FACT, json=body)
        return payload_to_model(payload, Fact)

    async def add_relationship(
        self,
        source_id: UUID | str,
        relationship_type: str,
        target_id: UUID | str,
        **kwargs: Any,
    ) -> None:
        """Create a typed relationship between two entities."""
        body = _drop_none(
            {
                "source_id": _to_str(source_id),
                "target_id": _to_str(target_id),
                "type": relationship_type,
                "properties": kwargs.get("properties"),
            }
        )
        await self._transport.request(_SPEC_ADD_RELATIONSHIP, json=body)

    async def search_entities(self, query: str, **kwargs: Any) -> list[Entity]:
        """Vector/keyword search across entities."""
        body = _drop_none(
            {
                "query": query,
                "type": kwargs.get("entity_type") or kwargs.get("type"),
                "limit": kwargs.get("limit"),
                "threshold": kwargs.get("threshold"),
            }
        )
        payload = await self._transport.request(_SPEC_SEARCH_ENTITIES, json=body)
        return [payload_to_model(item, Entity) for item in (payload or [])]

    async def search_preferences(self, query: str, **kwargs: Any) -> list[Preference]:
        """Vector/keyword search across preferences."""
        body = _drop_none(
            {
                "query": query,
                "category": kwargs.get("category"),
                "limit": kwargs.get("limit"),
                "threshold": kwargs.get("threshold"),
            }
        )
        payload = await self._transport.request(_SPEC_SEARCH_PREFERENCES, json=body)
        return [payload_to_model(item, Preference) for item in (payload or [])]

    async def search_facts(self, query: str, **kwargs: Any) -> list[Fact]:
        """Vector/keyword search across facts."""
        body = _drop_none(
            {
                "query": query,
                "limit": kwargs.get("limit"),
                "threshold": kwargs.get("threshold"),
            }
        )
        payload = await self._transport.request(_SPEC_SEARCH_FACTS, json=body)
        return [payload_to_model(item, Fact) for item in (payload or [])]

    async def get_entity_by_name(self, name: str) -> Entity | None:
        """Look up an entity by exact (canonical) name.

        Returns ``None`` if the server reports 404 (mapped to
        :class:`MemoryError` with "not found" message by the transport).
        Other errors propagate.
        """
        from neo4j_agent_memory.core.exceptions import MemoryError as _ME

        try:
            payload = await self._transport.request(
                _SPEC_GET_ENTITY_BY_NAME,
                params={"name": name},
            )
        except _ME as e:
            if "not found" in str(e).lower():
                return None
            raise
        if payload is None:
            return None
        # NAMS may return a single object or a list (``GET /entities?name=``).
        if isinstance(payload, list):
            return payload_to_model(payload[0], Entity) if payload else None
        return payload_to_model(payload, Entity)

    # ------------------------------------------------------------------ Silver

    async def get_related_entities(
        self,
        entity_id: UUID | str,
        **kwargs: Any,
    ) -> Any:
        """Return entities related to ``entity_id`` (graph traversal)."""
        params = _drop_none(
            {
                "depth": kwargs.get("depth"),
                "limit": kwargs.get("limit"),
                "relationship_type": kwargs.get("relationship_type"),
            }
        )
        payload = await self._transport.request(
            _SPEC_GET_RELATED_ENTITIES,
            path_params={"entity_id": _to_str(entity_id)},
            params=params or None,
        )
        if payload is None:
            return []
        # NAMS may return a flat list of entities or a structured envelope
        # ``{"entities": [...], "relationships": [...]}``. Pass through dicts
        # untouched so callers can branch; convert plain lists.
        if isinstance(payload, list):
            return [payload_to_model(item, Entity) for item in payload]
        return payload

    async def get_preferences_for(self, **kwargs: Any) -> list[Preference]:
        """Return preferences filtered by category and/or user."""
        params = _drop_none(
            {
                "category": kwargs.get("category"),
                "userId": kwargs.get("user_identifier"),
                "active_only": kwargs.get("active_only"),
                "limit": kwargs.get("limit"),
            }
        )
        payload = await self._transport.request(
            _SPEC_GET_PREFERENCES_FOR, params=params or None
        )
        return [payload_to_model(item, Preference) for item in (payload or [])]

    async def supersede_preference(
        self,
        preference_id: UUID | str,
        **kwargs: Any,
    ) -> None:
        """Mark a preference as superseded (close its validity window)."""
        body = _drop_none(
            {
                "valid_until": kwargs.get("valid_until"),
            }
        )
        await self._transport.request(
            _SPEC_SUPERSEDE_PREFERENCE,
            path_params={"preference_id": _to_str(preference_id)},
            json=body or None,
        )

    async def get_facts_about(self, entity_name: str) -> list[Fact]:
        """Return facts where the entity is the subject."""
        payload = await self._transport.request(
            _SPEC_GET_FACTS_ABOUT,
            path_params={"entity_name": entity_name},
        )
        return [payload_to_model(item, Fact) for item in (payload or [])]

    async def get_entity_relationships(
        self,
        entity_id: UUID | str,
    ) -> list[Relationship]:
        """Return outgoing relationships from an entity."""
        payload = await self._transport.request(
            _SPEC_GET_ENTITY_RELATIONSHIPS,
            path_params={"entity_id": _to_str(entity_id)},
        )
        return [payload_to_model(item, Relationship) for item in (payload or [])]

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """Return assembled context text from long-term memory."""
        body = _drop_none(
            {
                "query": query,
                "max_items": kwargs.get("max_items"),
                "userId": kwargs.get("user_identifier"),
            }
        )
        payload = await self._transport.request(_SPEC_GET_CONTEXT, json=body)
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            return str(payload.get("context") or payload.get("text") or "")
        return ""

    # -------------------------------------------------------------------- Gold

    async def get_entity_provenance(
        self,
        entity_id: UUID | str,
    ) -> dict[str, Any]:
        """Return source messages + extractors that produced this entity."""
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
        """Record user feedback ('positive'/'negative') on an entity."""
        body = _drop_none(
            {
                "feedback": feedback,
                "userId": kwargs.get("user_identifier"),
            }
        )
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
        """Return the edit/mention history for an entity."""
        params = _drop_none({"limit": kwargs.get("limit")})
        payload = await self._transport.request(
            _SPEC_GET_ENTITY_HISTORY,
            path_params={"entity_id": _to_str(entity_id)},
            params=params or None,
        )
        return list(payload or [])


__all__ = ["NamsLongTermMemory"]
