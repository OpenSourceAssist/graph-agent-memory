"""NAMS implementation of :class:`ShortTermProtocol`.

Translates Protocol method calls into NAMS HTTP requests via
:class:`HttpTransport`. Each method has an associated :class:`EndpointSpec`
declared as a module-level constant.

The endpoint mappings are inferred from the SPEC plus REST conventions;
entries marked ``TODO(nams-spec)`` need verification against the live
TCK reference implementation before v0.4 ships.

Tolerant ``**kwargs`` — bolt-only knobs (``extract_entities``,
``extract_relations``, ``generate_embedding``, ``extraction_mode``,
``explicit_mentions``) are accepted and ignored, per decision #4 of the
plan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from neo4j_agent_memory.memory.short_term import (
    Conversation,
    ConversationSummary,
    Message,
    SessionInfo,
)
from neo4j_agent_memory.nams._serialization import payload_to_model
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


# -----------------------------------------------------------------------------
# Endpoint registry (REST path + bridge method per Protocol method).
# Inferred from plan §G; ⚠️ entries need TCK-spec verification.
# -----------------------------------------------------------------------------

_SPEC_ADD_MESSAGE = EndpointSpec(
    rest_method="POST",
    rest_path="/conversations/{session_id}/messages",
    bridge_method="add_message",
)

_SPEC_GET_CONVERSATION = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{session_id}",
    bridge_method="get_conversation",
)

_SPEC_SEARCH_MESSAGES = EndpointSpec(
    rest_method="POST",
    rest_path="/messages/search",
    bridge_method="search_messages",
)

_SPEC_LIST_SESSIONS = EndpointSpec(
    rest_method="GET",
    rest_path="/sessions",
    bridge_method="list_sessions",
)

_SPEC_DELETE_MESSAGE = EndpointSpec(
    rest_method="DELETE",
    rest_path="/messages/{message_id}",
    bridge_method="delete_message",
)

_SPEC_CLEAR_SESSION = EndpointSpec(
    rest_method="DELETE",
    rest_path="/conversations/{session_id}",
    bridge_method="clear_session",
)

# TODO(nams-spec): verify ``/context`` shape against live SPEC.
_SPEC_GET_CONTEXT = EndpointSpec(
    rest_method="POST",
    rest_path="/context",
    bridge_method="get_context",
)

# TODO(nams-spec): verify summary route exists; may be client-side LLM only.
_SPEC_GET_CONVERSATION_SUMMARY = EndpointSpec(
    rest_method="POST",
    rest_path="/conversations/{session_id}/summary",
    bridge_method="get_conversation_summary",
)

_SPEC_CREATE_CONVERSATION = EndpointSpec(
    rest_method="POST",
    rest_path="/conversations",
    bridge_method="create_conversation",
)

_SPEC_LIST_CONVERSATIONS = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations",
    bridge_method="list_conversations",
)

# TODO(nams-spec): verify bulk shape; some SPECs use :bulk verb suffix.
_SPEC_BULK_ADD_MESSAGES = EndpointSpec(
    rest_method="POST",
    rest_path="/conversations/{session_id}/messages:bulk",
    bridge_method="bulk_add_messages",
)

# TODO(nams-spec): verify observation/reflection routes.
_SPEC_GET_OBSERVATIONS = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{session_id}/observations",
    bridge_method="get_observations",
)

_SPEC_GET_REFLECTIONS = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{session_id}/reflections",
    bridge_method="get_reflections",
)


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    """Strip ``None`` values from a dict — NAMS treats absent fields as 'default'."""
    return {k: v for k, v in d.items() if v is not None}


def _coerce_uuid_str(value: UUID | str) -> str:
    """Accept either a UUID or a stringified UUID; return canonical string form."""
    return str(value)


class NamsShortTermMemory:
    """Short-term memory backed by the NAMS HTTP service.

    Drop-in for :class:`ShortTermMemory` (bolt) where the
    :class:`ShortTermProtocol` contract overlaps. Bolt-only methods like
    ``add_messages_batch`` / ``extract_entities_from_session`` are not
    available — use the Protocol surface for portable code.
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    # ------------------------------------------------------------------ Bronze

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Append a message; returns the stored :class:`Message`.

        Known kwargs:

        * ``metadata`` (``dict``) — passthrough
        * ``user_identifier`` (``str``) — sent as ``userId``
        * ``conversation_id`` (UUID/str) — passthrough as ``conversation_id``

        Other kwargs (bolt-only: ``extract_entities``, ``extract_relations``,
        ``generate_embedding``, ``extraction_mode``, ``explicit_mentions``)
        are silently ignored — NAMS handles these server-side.
        """
        body = _drop_none(
            {
                "role": role,
                "content": content,
                "metadata": kwargs.get("metadata"),
                "userId": kwargs.get("user_identifier"),
                "conversation_id": (
                    _coerce_uuid_str(kwargs["conversation_id"])
                    if kwargs.get("conversation_id") is not None
                    else None
                ),
            }
        )
        payload = await self._transport.request(
            _SPEC_ADD_MESSAGE,
            path_params={"session_id": session_id},
            json=body,
        )
        return payload_to_model(payload, Message)

    async def get_conversation(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> Conversation:
        """Return the conversation + its messages."""
        params: dict[str, Any] = {}
        if (limit := kwargs.get("limit")) is not None:
            params["limit"] = limit
        payload = await self._transport.request(
            _SPEC_GET_CONVERSATION,
            path_params={"session_id": session_id},
            params=params or None,
        )
        return payload_to_model(payload, Conversation)

    async def search_messages(
        self,
        query: str,
        **kwargs: Any,
    ) -> list[Message]:
        """Vector/keyword search across messages."""
        body = _drop_none(
            {
                "query": query,
                "session_id": kwargs.get("session_id"),
                "limit": kwargs.get("limit"),
                "threshold": kwargs.get("threshold"),
            }
        )
        payload = await self._transport.request(_SPEC_SEARCH_MESSAGES, json=body)
        return [payload_to_model(item, Message) for item in (payload or [])]

    async def list_sessions(self, **kwargs: Any) -> list[SessionInfo]:
        """List sessions known to the backend."""
        params = _drop_none(
            {
                "limit": kwargs.get("limit"),
                "offset": kwargs.get("offset"),
                "order_by": kwargs.get("order_by"),
            }
        )
        payload = await self._transport.request(
            _SPEC_LIST_SESSIONS, params=params or None
        )
        return [payload_to_model(item, SessionInfo) for item in (payload or [])]

    # ------------------------------------------------------------------ Silver

    async def delete_message(self, message_id: UUID | str) -> bool:
        """Delete a message. Returns True if deleted."""
        payload = await self._transport.request(
            _SPEC_DELETE_MESSAGE,
            path_params={"message_id": _coerce_uuid_str(message_id)},
        )
        # Some servers respond 204 (None) — treat as success.
        if payload is None:
            return True
        if isinstance(payload, dict):
            return bool(payload.get("deleted", True))
        return True

    async def clear_session(self, session_id: str) -> None:
        """Delete every message in a session."""
        await self._transport.request(
            _SPEC_CLEAR_SESSION,
            path_params={"session_id": session_id},
        )

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """Return assembled context text for a query (NAMS Platinum get_context)."""
        body = _drop_none(
            {
                "query": query,
                "session_id": kwargs.get("session_id"),
                "max_messages": kwargs.get("max_messages") or kwargs.get("max_items"),
                "include_short_term": kwargs.get("include_short_term"),
                "include_long_term": kwargs.get("include_long_term"),
                "include_reasoning": kwargs.get("include_reasoning"),
            }
        )
        payload = await self._transport.request(_SPEC_GET_CONTEXT, json=body)
        # SPEC: ``get_context`` returns either a string or
        # ``{"context": "...", "recent_messages": [...], ...}``. Be tolerant.
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            return str(payload.get("context") or payload.get("text") or "")
        return ""

    async def get_conversation_summary(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> ConversationSummary:
        """Generate or fetch a conversation summary.

        TODO(nams-spec): the SPEC may not expose this — NAMS could return
        404. Callers that hit a 404 should fall back to client-side
        summarization via the configured LLM provider (decision #20).
        """
        body = _drop_none(
            {
                "max_messages": kwargs.get("max_messages"),
                "max_tokens": kwargs.get("max_tokens"),
            }
        )
        payload = await self._transport.request(
            _SPEC_GET_CONVERSATION_SUMMARY,
            path_params={"session_id": session_id},
            json=body or None,
        )
        return payload_to_model(payload, ConversationSummary)

    # -------------------------------------------------------------------- Gold

    async def create_conversation(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> Conversation:
        """Explicitly create a conversation node (no initial messages)."""
        body = _drop_none(
            {
                "session_id": session_id,
                "title": kwargs.get("title"),
                "userId": kwargs.get("user_identifier"),
                "metadata": kwargs.get("metadata"),
            }
        )
        payload = await self._transport.request(_SPEC_CREATE_CONVERSATION, json=body)
        return payload_to_model(payload, Conversation)

    async def list_conversations(self, **kwargs: Any) -> list[Conversation]:
        """List conversations; bolt filters by ``user_identifier``."""
        params = _drop_none(
            {
                "userId": kwargs.get("user_identifier"),
                "limit": kwargs.get("limit"),
            }
        )
        payload = await self._transport.request(
            _SPEC_LIST_CONVERSATIONS, params=params or None
        )
        return [payload_to_model(item, Conversation) for item in (payload or [])]

    # ---------------------------------------------------------------- Platinum

    async def bulk_add_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[Message]:
        """Bulk-insert messages (max 100 per call per SPEC)."""
        body: dict[str, Any] = {"messages": messages}
        if (user_identifier := kwargs.get("user_identifier")) is not None:
            body["userId"] = user_identifier
        payload = await self._transport.request(
            _SPEC_BULK_ADD_MESSAGES,
            path_params={"session_id": session_id},
            json=body,
        )
        return [payload_to_model(item, Message) for item in (payload or [])]

    async def get_observations(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Return inline observations extracted from the session.

        Server-managed (NAMS Platinum). Concrete observation shape is
        not yet a Pydantic model; returns raw dicts to avoid premature
        schema lock-in.
        """
        params = _drop_none({"limit": kwargs.get("limit")})
        payload = await self._transport.request(
            _SPEC_GET_OBSERVATIONS,
            path_params={"session_id": session_id},
            params=params or None,
        )
        return list(payload or [])

    async def get_reflections(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Return LLM-generated reflections for the session."""
        params = _drop_none({"limit": kwargs.get("limit")})
        payload = await self._transport.request(
            _SPEC_GET_REFLECTIONS,
            path_params={"session_id": session_id},
            params=params or None,
        )
        return list(payload or [])


__all__ = ["NamsShortTermMemory"]
