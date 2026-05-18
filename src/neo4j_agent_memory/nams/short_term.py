"""NAMS implementation of :class:`ShortTermProtocol`.

Endpoint mappings verified against the live NAMS OpenAPI spec at
``https://memory.neo4jlabs.com/openapi.json`` (as of v0.4 development).

NAMS conventions to remember
============================

* **camelCase** end-to-end: ``userId``, ``conversationId``, ``createdAt``,
  ``toolName``, ``stepId``, ``durationMs``. The bolt-side Pydantic models
  use snake_case; this module translates at the boundary.
* **No "session" concept** — NAMS only has conversations identified by
  UUIDs. The Protocol's ``session_id`` parameter is treated as a
  conversation UUID (typically the one returned from
  ``create_conversation``).
* **Conversation create** accepts only ``{userId?, metadata?}`` —
  ``session_id`` and ``title`` from our caller are not in the NAMS body.
* **Conversation GET** returns header-only (``id, userId, workspaceId,
  createdAt, updatedAt``) — messages live at the separate
  ``/conversations/{id}/messages`` endpoint.
* **Search messages** is scoped to a conversation:
  ``POST /v1/conversations/{id}/search``, not a global ``/messages/search``.
* **Bulk add** uses path ``/messages/bulk`` (slash, not the
  ``:bulk`` verb suffix some SPECs use).

Methods that don't exist on NAMS raise :class:`NotSupportedError`:
``list_sessions``, ``delete_message``, ``get_conversation_summary``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.memory.short_term import (
    Conversation,
    ConversationSummary,
    Message,
    SessionInfo,
)
from neo4j_agent_memory.nams._serialization import payload_to_model, snakeize_keys
from neo4j_agent_memory.nams.endpoints import EndpointSpec

if TYPE_CHECKING:
    from neo4j_agent_memory.nams.transport import HttpTransport


# -----------------------------------------------------------------------------
# Endpoint registry — verified against live NAMS OpenAPI spec.
# -----------------------------------------------------------------------------

_SPEC_CREATE_CONVERSATION = EndpointSpec(
    rest_method="POST", rest_path="/conversations", bridge_method="create_conversation"
)

_SPEC_LIST_CONVERSATIONS = EndpointSpec(
    rest_method="GET", rest_path="/conversations", bridge_method="list_conversations"
)

_SPEC_GET_CONVERSATION = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{conversation_id}",
    bridge_method="get_conversation",
)

_SPEC_DELETE_CONVERSATION = EndpointSpec(
    rest_method="DELETE",
    rest_path="/conversations/{conversation_id}",
    bridge_method="delete_conversation",
)

_SPEC_ADD_MESSAGE = EndpointSpec(
    rest_method="POST",
    rest_path="/conversations/{conversation_id}/messages",
    bridge_method="add_message",
)

_SPEC_LIST_MESSAGES = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{conversation_id}/messages",
    bridge_method="list_messages",
)

_SPEC_BULK_ADD_MESSAGES = EndpointSpec(
    rest_method="POST",
    rest_path="/conversations/{conversation_id}/messages/bulk",
    bridge_method="bulk_add_messages",
)

_SPEC_SEARCH_MESSAGES = EndpointSpec(
    rest_method="POST",
    rest_path="/conversations/{conversation_id}/search",
    bridge_method="search_messages",
)

_SPEC_GET_CONTEXT = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{conversation_id}/context",
    bridge_method="get_context",
)

_SPEC_GET_OBSERVATIONS = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{conversation_id}/observations",
    bridge_method="get_observations",
)

_SPEC_GET_REFLECTIONS = EndpointSpec(
    rest_method="GET",
    rest_path="/conversations/{conversation_id}/reflections",
    bridge_method="get_reflections",
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    """Strip ``None`` values — NAMS treats absent fields as 'default'."""
    return {k: v for k, v in d.items() if v is not None}


def _coerce_uuid_str(value: UUID | str) -> str:
    return str(value)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Map NAMS Message response → bolt Pydantic shape.

    NAMS shape: ``{id, conversationId, content, role[, createdAt, tokenCount, score]}``.
    The ``createdAt`` field is absent on POST responses but present on
    list/search responses; we default to now-UTC when absent.
    """
    raw = snakeize_keys(payload) if isinstance(payload, dict) else {}
    data: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
    if "created_at" not in data:
        data["created_at"] = _now_utc_iso()
    if "metadata" not in data:
        data["metadata"] = {}
    return data


def _normalize_conversation(
    payload: dict[str, Any] | None,
    *,
    session_id: str | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Map NAMS Conversation response → bolt Pydantic shape.

    NAMS returns ``{id, userId, workspaceId, createdAt, updatedAt}`` from
    GET, and only ``{id, userId, workspaceId}`` from create. The bolt
    Pydantic ``Conversation`` model requires ``id``, ``session_id``, and
    ``created_at``. We synthesize ``session_id`` from the caller-supplied
    value (which is typically the NAMS conversation UUID).
    """
    data = snakeize_keys(payload) if isinstance(payload, dict) else {}
    if "session_id" not in data:
        data["session_id"] = session_id or data.get("id") or "unknown"
    if "created_at" not in data:
        data["created_at"] = _now_utc_iso()
    if "metadata" not in data:
        data["metadata"] = {}
    data["messages"] = [_normalize_message(m) for m in (messages or [])]
    return data


# -----------------------------------------------------------------------------
# NamsShortTermMemory
# -----------------------------------------------------------------------------


class NamsShortTermMemory:
    """Short-term memory backed by the NAMS HTTP service.

    The Protocol's ``session_id`` parameter on every method maps to the
    NAMS *conversation UUID* — usually the one returned from
    :meth:`create_conversation`. Pre-create your conversation, hold onto
    the UUID, and pass it as ``session_id`` to subsequent methods.
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
        """Append a message to a NAMS conversation.

        Per verified spec, NAMS accepts only ``{content, role}`` — other
        kwargs (``metadata``, ``user_identifier``, ``conversation_id``,
        bolt-only knobs) are silently dropped.
        """
        body = {"content": content, "role": role}
        payload = await self._transport.request(
            _SPEC_ADD_MESSAGE,
            path_params={"conversation_id": session_id},
            json=body,
        )
        return payload_to_model(_normalize_message(payload or {}), Message)

    async def get_conversation(self, session_id: str, **kwargs: Any) -> Conversation:
        """Return the conversation + its messages.

        NAMS splits this across two endpoints — ``GET /conversations/{id}``
        returns header data and ``GET /conversations/{id}/messages``
        returns the message list (envelope ``{"messages": [...]}``).
        We assemble them client-side so the user-facing contract matches
        the Protocol (single call → full :class:`Conversation`).
        """
        limit = kwargs.get("limit")
        header = await self._transport.request(
            _SPEC_GET_CONVERSATION,
            path_params={"conversation_id": session_id},
        )

        params = _drop_none({"limit": limit})
        msgs_payload = await self._transport.request(
            _SPEC_LIST_MESSAGES,
            path_params={"conversation_id": session_id},
            params=params or None,
        )
        if isinstance(msgs_payload, dict) and "messages" in msgs_payload:
            messages = msgs_payload["messages"]
        elif isinstance(msgs_payload, list):
            messages = msgs_payload
        else:
            messages = []

        return payload_to_model(
            _normalize_conversation(header, session_id=session_id, messages=messages),
            Conversation,
        )

    async def search_messages(self, query: str, **kwargs: Any) -> list[Message]:
        """Vector/keyword search across messages within a conversation.

        Per verified spec, NAMS's search is **conversation-scoped** —
        ``POST /v1/conversations/{id}/search``. A ``session_id`` kwarg
        is required; if absent, the call raises.
        """
        session_id = kwargs.get("session_id")
        if not session_id:
            raise ValueError(
                "search_messages requires session_id on NAMS — the API is "
                "conversation-scoped (POST /v1/conversations/{id}/search). "
                "Pass session_id=... to scope the search."
            )
        body = _drop_none({"query": query, "limit": kwargs.get("limit")})
        payload = await self._transport.request(
            _SPEC_SEARCH_MESSAGES,
            path_params={"conversation_id": session_id},
            json=body,
        )
        # Response: {"messages": [...], "searchType": "vector"|"text"}
        items: list[Any]
        if isinstance(payload, dict):
            items = payload.get("messages") or []
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return [payload_to_model(_normalize_message(m), Message) for m in items]

    async def list_sessions(self, **kwargs: Any) -> list[SessionInfo]:
        """Not supported on NAMS — use :meth:`list_conversations`."""
        raise NotSupportedError(
            backend="nams",
            method="ShortTermMemory.list_sessions",
            message="NAMS does not expose a sessions endpoint.",
            workaround="Use client.short_term.list_conversations() instead.",
        )

    # ------------------------------------------------------------------ Silver

    async def delete_message(self, message_id: UUID | str) -> bool:
        """Not supported on NAMS — individual messages can't be deleted."""
        raise NotSupportedError(
            backend="nams",
            method="ShortTermMemory.delete_message",
            message="NAMS does not expose a message-delete endpoint.",
            workaround="Use clear_session(session_id) to clear an entire conversation.",
        )

    async def clear_session(self, session_id: str) -> None:
        """Delete the entire conversation (NAMS ``DELETE /conversations/{id}``)."""
        await self._transport.request(
            _SPEC_DELETE_CONVERSATION,
            path_params={"conversation_id": session_id},
        )

    async def get_context(self, query: str, **kwargs: Any) -> str:
        """Return three-tier context (reflections + observations + recent messages).

        Per verified spec, NAMS exposes
        ``GET /v1/conversations/{id}/context`` (no query body — the
        endpoint always returns the same three-tier view). The ``query``
        argument is currently unused server-side; we keep it on the
        Protocol surface for parity with bolt.

        Returns a formatted text block assembled client-side from the
        three response sections.
        """
        session_id = kwargs.get("session_id")
        if not session_id:
            raise ValueError(
                "get_context requires session_id on NAMS — the context "
                "endpoint is conversation-scoped "
                "(GET /v1/conversations/{id}/context)."
            )
        payload = await self._transport.request(
            _SPEC_GET_CONTEXT,
            path_params={"conversation_id": session_id},
        )
        if not isinstance(payload, dict):
            return ""
        parts: list[str] = []
        reflections = payload.get("reflections") or []
        observations = payload.get("observations") or []
        recent = payload.get("recentMessages") or payload.get("recent_messages") or []
        if reflections:
            parts.append("## Reflections\n" + "\n".join(r.get("content", "") for r in reflections))
        if observations:
            parts.append(
                "## Observations\n" + "\n".join(o.get("content", "") for o in observations)
            )
        if recent:
            parts.append(
                "## Recent Messages\n"
                + "\n".join(f"[{m.get('role', '?')}] {m.get('content', '')}" for m in recent)
            )
        return "\n\n".join(parts)

    async def get_conversation_summary(self, session_id: str, **kwargs: Any) -> ConversationSummary:
        """Not supported on NAMS — no dedicated summary endpoint.

        Use the configured ``llm`` provider to summarize
        ``get_conversation(session_id).messages`` client-side instead.
        """
        raise NotSupportedError(
            backend="nams",
            method="ShortTermMemory.get_conversation_summary",
            message="NAMS does not expose a conversation-summary endpoint.",
            workaround=(
                "Fetch the conversation with get_conversation(session_id), "
                "then summarize client-side with the configured llm provider."
            ),
        )

    # -------------------------------------------------------------------- Gold

    async def create_conversation(self, session_id: str, **kwargs: Any) -> Conversation:
        """Create a new conversation on NAMS.

        Per verified spec, NAMS accepts ``{userId?, metadata?}`` only —
        no ``session_id`` or ``title`` in the body (those are
        client-side concepts). The ``session_id`` argument is used to
        populate the returned ``Conversation.session_id`` field for
        Pydantic compatibility.
        """
        body = _drop_none(
            {
                "userId": kwargs.get("user_identifier"),
                "metadata": kwargs.get("metadata"),
            }
        )
        payload = await self._transport.request(_SPEC_CREATE_CONVERSATION, json=body)
        return payload_to_model(
            _normalize_conversation(payload, session_id=session_id),
            Conversation,
        )

    async def list_conversations(self, **kwargs: Any) -> list[Conversation]:
        """List conversations (NAMS workspace-scoped via API key)."""
        params = _drop_none(
            {
                "userId": kwargs.get("user_identifier"),
                "limit": kwargs.get("limit"),
            }
        )
        payload = await self._transport.request(_SPEC_LIST_CONVERSATIONS, params=params or None)
        items: list[Any]
        if isinstance(payload, dict) and "conversations" in payload:
            items = payload["conversations"]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return [
            payload_to_model(
                _normalize_conversation(item, session_id=(item or {}).get("id")),
                Conversation,
            )
            for item in items
            if isinstance(item, dict)
        ]

    # ---------------------------------------------------------------- Platinum

    async def bulk_add_messages(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[Message]:
        """Bulk-insert messages (max 100 per call per NAMS spec).

        Request: ``{"messages": [{"content", "role"}, ...]}``.
        Response: ``{"messages": [...]}``.
        """
        # Strip any extra kwargs each message might carry (bolt-only fields).
        clean_batch = [{"content": m["content"], "role": m["role"]} for m in messages]
        body = {"messages": clean_batch}
        payload = await self._transport.request(
            _SPEC_BULK_ADD_MESSAGES,
            path_params={"conversation_id": session_id},
            json=body,
        )
        items: list[Any]
        if isinstance(payload, dict) and "messages" in payload:
            items = payload["messages"]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return [payload_to_model(_normalize_message(m), Message) for m in items]

    async def get_observations(self, session_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Return inline observations extracted from a conversation."""
        payload = await self._transport.request(
            _SPEC_GET_OBSERVATIONS,
            path_params={"conversation_id": session_id},
        )
        if isinstance(payload, dict) and "observations" in payload:
            return list(payload["observations"])
        if isinstance(payload, list):
            return list(payload)
        return []

    async def get_reflections(self, session_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Return LLM-generated reflections for a conversation."""
        payload = await self._transport.request(
            _SPEC_GET_REFLECTIONS,
            path_params={"conversation_id": session_id},
        )
        if isinstance(payload, dict) and "reflections" in payload:
            return list(payload["reflections"])
        if isinstance(payload, list):
            return list(payload)
        return []


__all__ = ["NamsShortTermMemory"]
