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

# Live NAMS doesn't inline messages in GET /conversations/{id} — messages
# are fetched separately. This spec is used by ``get_conversation`` to
# back-fill the ``messages`` list when the conversation header response
# arrives without them.
_SPEC_LIST_CONVERSATION_MESSAGES = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{session_id}/messages",
    bridge_method="list_conversation_messages",
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


def _conversation_with_defaults(
    payload: dict[str, Any] | None,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Inject defaults the bolt Pydantic ``Conversation`` model expects.

    NAMS's ``Conversation`` responses are minimal — observed shape is
    ``{"id": "<uuid>"}`` with no ``session_id`` or ``created_at``. The
    bolt-side Pydantic ``Conversation`` model requires both. This helper
    fills the gaps with caller-supplied or sensible defaults so
    ``payload_to_model`` succeeds.

    The injected ``session_id`` is the value the caller passed when
    invoking the NAMS method — keeping the user-facing semantics
    consistent across backends.
    """
    from datetime import datetime, timezone

    data = dict(payload or {})
    if "session_id" not in data and session_id is not None:
        data["session_id"] = session_id
    if "created_at" not in data:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
    if "messages" not in data:
        data["messages"] = []
    if "metadata" not in data:
        data["metadata"] = {}
    return data


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
        """Return the conversation + its messages.

        Live NAMS splits this across two endpoints — ``GET /conversations/{id}``
        returns header-only data (no inline messages), and
        ``GET /conversations/{id}/messages`` returns the message list.
        This method does both calls and reassembles them client-side so
        the user-facing contract matches the SPEC (single call → full
        Conversation with messages).
        """
        params: dict[str, Any] = {}
        if (limit := kwargs.get("limit")) is not None:
            params["limit"] = limit
        raw_header = await self._transport.request(
            _SPEC_GET_CONVERSATION,
            path_params={"session_id": session_id},
            params=params or None,
        )
        # Detect whether NAMS embedded messages inline (some deployments may).
        # We check the raw response *before* default-injection, since the
        # helper synthesizes ``messages: []`` when absent.
        has_inline_messages = isinstance(raw_header, dict) and raw_header.get("messages")
        payload = _conversation_with_defaults(raw_header, session_id=session_id)

        if not has_inline_messages:
            # Back-fill messages from the dedicated endpoint. Best-effort:
            # if the messages endpoint isn't supported (404 / NotSupported),
            # fall through with the empty list rather than failing the
            # whole call.
            from neo4j_agent_memory.core.exceptions import (
                MemoryError as _ME,
            )
            from neo4j_agent_memory.core.exceptions import (
                NotSupportedError as _NSE,
            )

            try:
                msgs_payload = await self._transport.request(
                    _SPEC_LIST_CONVERSATION_MESSAGES,
                    path_params={"session_id": session_id},
                    params=params or None,
                )
                if isinstance(msgs_payload, list):
                    payload["messages"] = msgs_payload
                elif isinstance(msgs_payload, dict) and "messages" in msgs_payload:
                    # Some servers wrap the list in an envelope.
                    payload["messages"] = msgs_payload["messages"]
            except (_ME, _NSE):
                pass  # Endpoint not available; fall through with [].
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
        payload = await self._transport.request(_SPEC_LIST_SESSIONS, params=params or None)
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
        max_messages = kwargs.get("max_messages")
        if max_messages is None:
            max_messages = kwargs.get("max_items")
        body = _drop_none(
            {
                "query": query,
                "session_id": kwargs.get("session_id"),
                "max_messages": max_messages,
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
        """Explicitly create a conversation node (no initial messages).

        NAMS responds with a minimal body — typically ``{"id": "<uuid>"}``
        — without echoing the supplied ``session_id``. We inject the
        caller's ``session_id`` into the payload before Pydantic parsing
        so the returned :class:`Conversation` has the field populated
        (matching bolt semantics).
        """
        body = _drop_none(
            {
                "session_id": session_id,
                "title": kwargs.get("title"),
                "userId": kwargs.get("user_identifier"),
                "metadata": kwargs.get("metadata"),
            }
        )
        payload = await self._transport.request(_SPEC_CREATE_CONVERSATION, json=body)
        payload = _conversation_with_defaults(payload, session_id=session_id)
        return payload_to_model(payload, Conversation)

    async def list_conversations(self, **kwargs: Any) -> list[Conversation]:
        """List conversations; bolt filters by ``user_identifier``.

        NAMS may return Conversation items without ``session_id``;
        we inject a placeholder per item (the item's own ``id`` if
        the session_id field is missing) so Pydantic parsing succeeds.
        """
        params = _drop_none(
            {
                "userId": kwargs.get("user_identifier"),
                "limit": kwargs.get("limit"),
            }
        )
        payload = await self._transport.request(_SPEC_LIST_CONVERSATIONS, params=params or None)
        items = payload or []
        out: list[Conversation] = []
        for item in items:
            if isinstance(item, dict):
                # If session_id is absent, fall back to the item's id so the
                # Pydantic model can be constructed. Callers can match
                # conversations by ``conv.id`` instead of by session_id.
                fallback_session = item.get("session_id") or item.get("id")
                normalized = _conversation_with_defaults(item, session_id=fallback_session)
                out.append(payload_to_model(normalized, Conversation))
        return out

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
