"""Tests for nams/short_term.py — NamsShortTermMemory.

Each test mocks one NAMS endpoint, exercises one Protocol method, and
asserts request URL/body shape + response parsing. Endpoint shapes are
the inferred mappings from plan §G — when the SPEC is verified these
expectations may shift.
"""

from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from neo4j_agent_memory.core.exceptions import MemoryError
from neo4j_agent_memory.core.protocols import ShortTermProtocol
from neo4j_agent_memory.memory.short_term import (
    Conversation,
    ConversationSummary,
    Message,
    MessageRole,
    SessionInfo,
)
from neo4j_agent_memory.nams import (
    HttpTransport,
    NamsShortTermMemory,
    StaticApiKeyAuth,
)

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
def short_term(transport) -> NamsShortTermMemory:
    return NamsShortTermMemory(transport)


# Useful canned responses
SAMPLE_MESSAGE = {
    "id": "00000000-0000-0000-0000-000000000001",
    "role": "user",
    "content": "hi",
    "created_at": "2026-05-17T12:00:00Z",
    "metadata": {},
}

SAMPLE_CONVERSATION = {
    "id": "00000000-0000-0000-0000-000000000aaa",
    "session_id": "s1",
    "title": "Test",
    "messages": [SAMPLE_MESSAGE],
    "created_at": "2026-05-17T11:00:00Z",
    "metadata": {},
}

SAMPLE_SESSION_INFO = {
    "session_id": "s1",
    "title": "Test",
    "created_at": "2026-05-17T11:00:00Z",
    "message_count": 5,
}


# -----------------------------------------------------------------------------
# Protocol conformance
# -----------------------------------------------------------------------------


class TestProtocolConformance:
    def test_satisfies_short_term_protocol(self, short_term):
        assert isinstance(short_term, ShortTermProtocol)


# -----------------------------------------------------------------------------
# Bronze tier
# -----------------------------------------------------------------------------


class TestAddMessage:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.post("https://memory.test/v1/conversations/s1/messages").respond(
            200, json=SAMPLE_MESSAGE
        )
        msg = await short_term.add_message("s1", "user", "hi")
        assert isinstance(msg, Message)
        assert msg.role == MessageRole.USER
        assert msg.content == "hi"
        # Verify body shape
        body = json.loads(route.calls[0].request.content)
        assert body == {"role": "user", "content": "hi"}

    @respx.mock
    async def test_with_metadata_and_user_identifier(self, short_term):
        route = respx.post("https://memory.test/v1/conversations/s1/messages").respond(
            200, json=SAMPLE_MESSAGE
        )
        await short_term.add_message(
            "s1",
            "user",
            "hi",
            metadata={"source": "test"},
            user_identifier="alice",
        )
        body = json.loads(route.calls[0].request.content)
        assert body["metadata"] == {"source": "test"}
        assert body["userId"] == "alice"

    @respx.mock
    async def test_bolt_only_kwargs_ignored(self, short_term):
        route = respx.post("https://memory.test/v1/conversations/s1/messages").respond(
            200, json=SAMPLE_MESSAGE
        )
        await short_term.add_message(
            "s1",
            "user",
            "hi",
            extract_entities=True,  # bolt-only — should be dropped
            extract_relations=True,
            generate_embedding=True,
        )
        body = json.loads(route.calls[0].request.content)
        assert "extract_entities" not in body
        assert "extract_relations" not in body
        assert "generate_embedding" not in body

    @respx.mock
    async def test_conversation_id_serialized(self, short_term):
        from uuid import UUID

        cid = UUID(int=42)
        route = respx.post("https://memory.test/v1/conversations/s1/messages").respond(
            200, json=SAMPLE_MESSAGE
        )
        await short_term.add_message("s1", "user", "hi", conversation_id=cid)
        body = json.loads(route.calls[0].request.content)
        assert body["conversation_id"] == str(cid)


class TestGetConversation:
    @respx.mock
    async def test_basic(self, short_term):
        respx.get("https://memory.test/v1/conversations/s1").respond(200, json=SAMPLE_CONVERSATION)
        conv = await short_term.get_conversation("s1")
        assert isinstance(conv, Conversation)
        assert conv.session_id == "s1"
        assert len(conv.messages) == 1

    @respx.mock
    async def test_with_limit(self, short_term):
        route = respx.get("https://memory.test/v1/conversations/s1").respond(
            200, json=SAMPLE_CONVERSATION
        )
        await short_term.get_conversation("s1", limit=20)
        assert route.calls[0].request.url.params["limit"] == "20"


class TestSearchMessages:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.post("https://memory.test/v1/messages/search").respond(
            200, json=[SAMPLE_MESSAGE]
        )
        msgs = await short_term.search_messages("hello", session_id="s1", limit=5)
        assert len(msgs) == 1
        assert isinstance(msgs[0], Message)
        body = json.loads(route.calls[0].request.content)
        assert body == {"query": "hello", "session_id": "s1", "limit": 5}

    @respx.mock
    async def test_empty_results(self, short_term):
        respx.post("https://memory.test/v1/messages/search").respond(200, json=[])
        msgs = await short_term.search_messages("nothing")
        assert msgs == []


class TestListSessions:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.get("https://memory.test/v1/sessions").respond(
            200, json=[SAMPLE_SESSION_INFO]
        )
        sessions = await short_term.list_sessions(limit=50)
        assert len(sessions) == 1
        assert isinstance(sessions[0], SessionInfo)
        assert sessions[0].session_id == "s1"
        assert route.calls[0].request.url.params["limit"] == "50"


# -----------------------------------------------------------------------------
# Silver tier
# -----------------------------------------------------------------------------


class TestDeleteMessage:
    @respx.mock
    async def test_returns_true_on_204(self, short_term):
        respx.delete(
            "https://memory.test/v1/messages/00000000-0000-0000-0000-000000000001"
        ).respond(204)
        assert await short_term.delete_message("00000000-0000-0000-0000-000000000001") is True

    @respx.mock
    async def test_returns_true_on_json_deleted(self, short_term):
        respx.delete(
            "https://memory.test/v1/messages/00000000-0000-0000-0000-000000000001"
        ).respond(200, json={"deleted": True})
        assert await short_term.delete_message("00000000-0000-0000-0000-000000000001") is True

    @respx.mock
    async def test_returns_false_when_server_says_so(self, short_term):
        respx.delete(
            "https://memory.test/v1/messages/00000000-0000-0000-0000-000000000001"
        ).respond(200, json={"deleted": False})
        assert await short_term.delete_message("00000000-0000-0000-0000-000000000001") is False


class TestClearSession:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.delete("https://memory.test/v1/conversations/s1").respond(204)
        result = await short_term.clear_session("s1")
        assert result is None
        assert route.called


class TestGetContext:
    @respx.mock
    async def test_string_response(self, short_term):
        respx.post("https://memory.test/v1/context").respond(200, json="assembled context")
        ctx = await short_term.get_context("query", session_id="s1")
        assert ctx == "assembled context"

    @respx.mock
    async def test_dict_response_with_context_key(self, short_term):
        respx.post("https://memory.test/v1/context").respond(
            200, json={"context": "assembled", "recent_messages": []}
        )
        ctx = await short_term.get_context("query")
        assert ctx == "assembled"

    @respx.mock
    async def test_dict_response_with_text_key_fallback(self, short_term):
        respx.post("https://memory.test/v1/context").respond(200, json={"text": "fallback"})
        ctx = await short_term.get_context("query")
        assert ctx == "fallback"


class TestGetConversationSummary:
    @respx.mock
    async def test_basic(self, short_term):
        respx.post("https://memory.test/v1/conversations/s1/summary").respond(
            200,
            json={
                "session_id": "s1",
                "summary": "talked about food",
                "message_count": 3,
                "key_entities": [],
                "key_topics": [],
                "generated_at": "2026-05-17T12:00:00Z",
            },
        )
        summary = await short_term.get_conversation_summary("s1")
        assert isinstance(summary, ConversationSummary)
        assert summary.summary == "talked about food"


# -----------------------------------------------------------------------------
# Gold tier
# -----------------------------------------------------------------------------


class TestCreateConversation:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.post("https://memory.test/v1/conversations").respond(
            200, json=SAMPLE_CONVERSATION
        )
        conv = await short_term.create_conversation("s1", title="My Chat", user_identifier="alice")
        assert isinstance(conv, Conversation)
        body = json.loads(route.calls[0].request.content)
        assert body == {"session_id": "s1", "title": "My Chat", "userId": "alice"}


class TestListConversations:
    @respx.mock
    async def test_filters_by_user(self, short_term):
        route = respx.get("https://memory.test/v1/conversations").respond(
            200, json=[SAMPLE_CONVERSATION]
        )
        convs = await short_term.list_conversations(user_identifier="alice", limit=10)
        assert len(convs) == 1
        assert route.calls[0].request.url.params["userId"] == "alice"
        assert route.calls[0].request.url.params["limit"] == "10"


# -----------------------------------------------------------------------------
# Platinum tier
# -----------------------------------------------------------------------------


class TestBulkAddMessages:
    @respx.mock
    async def test_basic(self, short_term):
        route = respx.post("https://memory.test/v1/conversations/s1/messages:bulk").respond(
            200, json=[SAMPLE_MESSAGE, SAMPLE_MESSAGE]
        )
        msgs = await short_term.bulk_add_messages(
            "s1",
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        )
        assert len(msgs) == 2
        assert all(isinstance(m, Message) for m in msgs)
        body = json.loads(route.calls[0].request.content)
        assert body == {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
        }


class TestGetObservations:
    @respx.mock
    async def test_basic(self, short_term):
        respx.get("https://memory.test/v1/conversations/s1/observations").respond(
            200, json=[{"text": "user likes Italian food"}]
        )
        obs = await short_term.get_observations("s1", limit=20)
        assert len(obs) == 1
        assert obs[0]["text"] == "user likes Italian food"

    @respx.mock
    async def test_empty(self, short_term):
        respx.get("https://memory.test/v1/conversations/s1/observations").respond(200, json=[])
        assert await short_term.get_observations("s1") == []


class TestGetReflections:
    @respx.mock
    async def test_basic(self, short_term):
        respx.get("https://memory.test/v1/conversations/s1/reflections").respond(
            200, json=[{"text": "user prefers cooking at home"}]
        )
        refs = await short_term.get_reflections("s1")
        assert len(refs) == 1


# -----------------------------------------------------------------------------
# Bridge protocol routing
# -----------------------------------------------------------------------------


class TestBridgeRouting:
    """Bridge protocol = ``POST /<snake_case_method>`` (no path templating)."""

    @respx.mock
    async def test_add_message_bridge_path(self, bridge_config):
        auth = StaticApiKeyAuth.from_config(bridge_config)
        route = respx.post("https://memory.test/add_message").respond(200, json=SAMPLE_MESSAGE)
        async with HttpTransport.from_config(bridge_config, auth=auth) as t:
            st = NamsShortTermMemory(t)
            await st.add_message("s1", "user", "hi")
        assert route.called

    @respx.mock
    async def test_list_sessions_bridge_path(self, bridge_config):
        auth = StaticApiKeyAuth.from_config(bridge_config)
        route = respx.post("https://memory.test/list_sessions").respond(
            200, json=[SAMPLE_SESSION_INFO]
        )
        async with HttpTransport.from_config(bridge_config, auth=auth) as t:
            st = NamsShortTermMemory(t)
            await st.list_sessions()
        assert route.called


# -----------------------------------------------------------------------------
# Error propagation
# -----------------------------------------------------------------------------


class TestErrorPropagation:
    @respx.mock
    async def test_session_not_found(self, short_term):
        respx.get("https://memory.test/v1/conversations/missing").respond(
            404, json={"error": "session not found"}
        )
        with pytest.raises(MemoryError, match="not found"):
            await short_term.get_conversation("missing")


def _unused_response_marker() -> Response:
    # Keeps the httpx import live for the file-level docstring lint.
    return Response(200)
