"""Tests for nams/short_term.py — NamsShortTermMemory.

Endpoint shapes verified against the live NAMS OpenAPI spec.
"""

from __future__ import annotations

import json

import pytest
import respx

from neo4j_agent_memory.core.exceptions import NotSupportedError
from neo4j_agent_memory.core.protocols import ShortTermProtocol
from neo4j_agent_memory.memory.short_term import (
    Conversation,
    Message,
    MessageRole,
)
from neo4j_agent_memory.nams import HttpTransport, NamsShortTermMemory, StaticApiKeyAuth


@pytest.fixture
async def transport(nams_config):
    auth = StaticApiKeyAuth.from_config(nams_config)
    t = HttpTransport.from_config(nams_config, auth=auth)
    async with t:
        yield t


@pytest.fixture
def short_term(transport) -> NamsShortTermMemory:
    return NamsShortTermMemory(transport)


# NAMS uses camelCase end-to-end; createdAt is absent on POST responses.
SAMPLE_MESSAGE = {
    "id": "00000000-0000-0000-0000-000000000001",
    "conversationId": "00000000-0000-0000-0000-000000000aaa",
    "content": "hi",
    "role": "user",
}

SAMPLE_MESSAGE_WITH_TIMESTAMP = {
    **SAMPLE_MESSAGE,
    "createdAt": "2026-05-17T12:00:00Z",
}

SAMPLE_CONVERSATION = {
    "id": "00000000-0000-0000-0000-000000000aaa",
    "userId": "alice",
    "workspaceId": "ws-1",
    "createdAt": "2026-05-17T11:00:00Z",
    "updatedAt": "2026-05-17T11:30:00Z",
}


class TestProtocolConformance:
    def test_satisfies_short_term_protocol(self, short_term):
        assert isinstance(short_term, ShortTermProtocol)


class TestAddMessage:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.post(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/messages"
        ).respond(201, json=SAMPLE_MESSAGE)
        msg = await short_term.add_message("00000000-0000-0000-0000-0000000c1d00", "user", "hi")
        assert isinstance(msg, Message)
        assert msg.role == MessageRole.USER
        assert msg.content == "hi"
        body = json.loads(route.calls[0].request.content)
        assert body == {"content": "hi", "role": "user"}

    @respx.mock
    async def test_bolt_only_kwargs_dropped(self, short_term):
        route = respx.post(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/messages"
        ).respond(201, json=SAMPLE_MESSAGE)
        await short_term.add_message(
            "00000000-0000-0000-0000-0000000c1d00",
            "user",
            "hi",
            metadata={"src": "x"},
            user_identifier="alice",
            extract_entities=True,
        )
        body = json.loads(route.calls[0].request.content)
        # NAMS spec accepts only content + role.
        assert body == {"content": "hi", "role": "user"}


class TestGetConversation:
    """get_conversation does 2 HTTP calls: header + messages."""

    @respx.mock
    async def test_assembles_header_and_messages(self, short_term):
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00"
        ).respond(200, json=SAMPLE_CONVERSATION)
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/messages"
        ).respond(200, json={"messages": [SAMPLE_MESSAGE_WITH_TIMESTAMP]})

        conv = await short_term.get_conversation("00000000-0000-0000-0000-0000000c1d00")
        assert isinstance(conv, Conversation)
        assert len(conv.messages) == 1
        assert conv.messages[0].content == "hi"

    @respx.mock
    async def test_with_limit(self, short_term):
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00"
        ).respond(200, json=SAMPLE_CONVERSATION)
        route = respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/messages"
        ).respond(200, json={"messages": []})
        await short_term.get_conversation("00000000-0000-0000-0000-0000000c1d00", limit=20)
        assert route.calls[0].request.url.params["limit"] == "20"

    @respx.mock
    async def test_handles_bare_list_messages_response(self, short_term):
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00"
        ).respond(200, json=SAMPLE_CONVERSATION)
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/messages"
        ).respond(200, json=[SAMPLE_MESSAGE_WITH_TIMESTAMP])
        conv = await short_term.get_conversation("00000000-0000-0000-0000-0000000c1d00")
        assert len(conv.messages) == 1


class TestSearchMessages:
    @respx.mock
    async def test_scoped_to_conversation(self, short_term):
        route = respx.post(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/search"
        ).respond(200, json={"messages": [SAMPLE_MESSAGE_WITH_TIMESTAMP], "searchType": "vector"})
        msgs = await short_term.search_messages(
            "hello", session_id="00000000-0000-0000-0000-0000000c1d00", limit=5
        )
        assert len(msgs) == 1
        body = json.loads(route.calls[0].request.content)
        assert body == {"query": "hello", "limit": 5}

    async def test_requires_session_id(self, short_term):
        with pytest.raises(ValueError, match="session_id"):
            await short_term.search_messages("hello")

    @respx.mock
    async def test_empty_results(self, short_term):
        respx.post(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/search"
        ).respond(200, json={"messages": [], "searchType": "vector"})
        msgs = await short_term.search_messages(
            "nothing", session_id="00000000-0000-0000-0000-0000000c1d00"
        )
        assert msgs == []


class TestListSessions:
    async def test_raises_not_supported(self, short_term):
        with pytest.raises(NotSupportedError) as exc_info:
            await short_term.list_sessions(limit=50)
        assert "list_sessions" in exc_info.value.method


class TestDeleteMessage:
    async def test_raises_not_supported(self, short_term):
        with pytest.raises(NotSupportedError):
            await short_term.delete_message("msg-id")


class TestClearSession:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.delete(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00"
        ).respond(204)
        result = await short_term.clear_session("00000000-0000-0000-0000-0000000c1d00")
        assert result is None
        assert route.called


class TestGetContext:
    @respx.mock
    async def test_assembles_three_tier(self, short_term):
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/context"
        ).respond(
            200,
            json={
                "reflections": [{"content": "user prefers home cooking"}],
                "observations": [{"content": "loves italian"}],
                "recentMessages": [{"role": "user", "content": "hi"}],
            },
        )
        ctx = await short_term.get_context(
            "query", session_id="00000000-0000-0000-0000-0000000c1d00"
        )
        assert "Reflections" in ctx
        assert "user prefers home cooking" in ctx
        assert "Observations" in ctx
        assert "Recent Messages" in ctx

    async def test_requires_session_id(self, short_term):
        with pytest.raises(ValueError, match="session_id"):
            await short_term.get_context("query")


class TestGetConversationSummary:
    async def test_raises_not_supported(self, short_term):
        with pytest.raises(NotSupportedError):
            await short_term.get_conversation_summary("00000000-0000-0000-0000-0000000c1d00")


class TestCreateConversation:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.post("https://memory.test/v1/conversations").respond(
            201,
            json={
                "id": "00000000-0000-0000-0000-0000000c1d00",
                "userId": "alice",
                "workspaceId": "ws",
            },
        )
        conv = await short_term.create_conversation("my-session", user_identifier="alice")
        assert isinstance(conv, Conversation)
        body = json.loads(route.calls[0].request.content)
        # NAMS accepts only {userId, metadata}.
        assert body == {"userId": "alice"}

    @respx.mock
    async def test_ignores_title_kwarg(self, short_term):
        """title is bolt-side concept — NAMS spec does not accept it."""
        route = respx.post("https://memory.test/v1/conversations").respond(
            201,
            json={
                "id": "00000000-0000-0000-0000-0000000c1d00",
                "userId": "alice",
                "workspaceId": "ws",
            },
        )
        await short_term.create_conversation("session", title="ignored", user_identifier="alice")
        body = json.loads(route.calls[0].request.content)
        assert "title" not in body


class TestListConversations:
    @respx.mock
    async def test_with_envelope(self, short_term):
        respx.get("https://memory.test/v1/conversations").respond(
            200, json={"conversations": [SAMPLE_CONVERSATION]}
        )
        convs = await short_term.list_conversations()
        assert len(convs) == 1

    @respx.mock
    async def test_with_bare_list(self, short_term):
        respx.get("https://memory.test/v1/conversations").respond(200, json=[SAMPLE_CONVERSATION])
        convs = await short_term.list_conversations()
        assert len(convs) == 1


class TestBulkAddMessages:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.post(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/messages/bulk"
        ).respond(
            201,
            json={"messages": [SAMPLE_MESSAGE, SAMPLE_MESSAGE]},
        )
        msgs = await short_term.bulk_add_messages(
            "00000000-0000-0000-0000-0000000c1d00",
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        )
        assert len(msgs) == 2
        body = json.loads(route.calls[0].request.content)
        assert body == {
            "messages": [
                {"content": "hi", "role": "user"},
                {"content": "hello", "role": "assistant"},
            ]
        }


class TestGetObservations:
    @respx.mock
    async def test_with_envelope(self, short_term):
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/observations"
        ).respond(200, json={"observations": [{"content": "user likes Italian food"}]})
        obs = await short_term.get_observations("00000000-0000-0000-0000-0000000c1d00", limit=20)
        assert len(obs) == 1


class TestGetReflections:
    @respx.mock
    async def test_with_envelope(self, short_term):
        respx.get(
            "https://memory.test/v1/conversations/00000000-0000-0000-0000-0000000c1d00/reflections"
        ).respond(200, json={"reflections": [{"content": "user prefers cooking at home"}]})
        refs = await short_term.get_reflections("00000000-0000-0000-0000-0000000c1d00")
        assert len(refs) == 1


class TestBridgeRouting:
    """Bridge protocol = ``POST /<snake_case_method>`` (no path templating)."""

    @respx.mock
    async def test_add_message_bridge_path(self, bridge_config):
        auth = StaticApiKeyAuth.from_config(bridge_config)
        route = respx.post("https://memory.test/add_message").respond(201, json=SAMPLE_MESSAGE)
        async with HttpTransport.from_config(bridge_config, auth=auth) as t:
            st = NamsShortTermMemory(t)
            await st.add_message("00000000-0000-0000-0000-0000000c1d00", "user", "hi")
        assert route.called
