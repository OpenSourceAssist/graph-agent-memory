"""Tests for FastAPI endpoints including SSE streaming and traces."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(mock_memory_service):
    """Create a TestClient with mocked services."""
    mock_neo4j_service = MagicMock()
    mock_supervisor = MagicMock()
    mock_supervisor.return_value = "Investigation complete. Risk level: MEDIUM."

    with patch("src.services.memory_service.get_memory_service", return_value=mock_memory_service), \
         patch("src.agents.supervisor.get_supervisor_agent", return_value=mock_supervisor), \
         patch("src.api.routes.chat.get_supervisor_agent", return_value=mock_supervisor), \
         patch("src.api.routes.chat.get_memory_service", return_value=mock_memory_service):

        from src.main import app

        app.state.neo4j_service = mock_neo4j_service
        yield TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoints:
    def test_root(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Financial Services Advisor"

    def test_health(self, app_client):
        response = app_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data

    def test_api_info(self, app_client):
        response = app_client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "supervisor" in data["agents"]
        assert "kyc" in data["agents"]
        assert "aml" in data["agents"]
        assert "memory_types" in data


class TestChatAPI:
    def test_chat_sync(self, app_client):
        response = app_client.post("/api/chat", json={
            "message": "Investigate CUST-001",
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert data["agent"] == "supervisor"

    def test_chat_with_customer_context(self, app_client):
        response = app_client.post("/api/chat", json={
            "message": "What is the risk level?",
            "customer_id": "CUST-003",
        })
        assert response.status_code == 200

    def test_chat_missing_message(self, app_client):
        response = app_client.post("/api/chat", json={})
        assert response.status_code == 422

    def test_chat_stream_returns_sse(self, app_client):
        response = app_client.post("/api/chat/stream", json={
            "message": "Investigate CUST-003",
        })
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass

        # Should have at least agent_start and done events
        event_types = set()
        for line in response.text.split("\n"):
            if line.startswith("event: "):
                event_types.add(line[7:].strip())

        assert "agent_start" in event_types or "response" in event_types or "done" in event_types

    def test_chat_history(self, app_client, mock_memory_service):
        mock_memory_service.get_conversation_history.return_value = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00"},
            {"role": "assistant", "content": "Hi", "timestamp": "2024-01-01T00:00:01"},
        ]

        with patch("src.api.routes.chat.get_memory_service", return_value=mock_memory_service):
            response = app_client.get("/api/chat/history/test-session")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_chat_search(self, app_client, mock_memory_service):
        mock_memory_service.search_conversations.return_value = [
            {"content": "money laundering", "role": "user", "metadata": {}},
        ]

        with patch("src.api.routes.chat.get_memory_service", return_value=mock_memory_service):
            response = app_client.post("/api/chat/search", json={
                "query": "money laundering",
            })
            assert response.status_code == 200


class TestTracesAPI:
    def test_get_session_traces(self, app_client, mock_memory_service):
        mock_reasoning = MagicMock()
        mock_reasoning.list_traces = AsyncMock(return_value=[])
        mock_memory_service.client.reasoning = mock_reasoning

        with patch("src.api.routes.traces.get_memory_service", return_value=mock_memory_service):
            response = app_client.get("/api/traces/test-session")
            assert response.status_code == 200
            assert response.json() == []

    def test_get_trace_detail_not_found(self, app_client, mock_memory_service):
        mock_reasoning = MagicMock()
        mock_reasoning.get_trace = AsyncMock(return_value=None)
        mock_memory_service.client.reasoning = mock_reasoning

        with patch("src.api.routes.traces.get_memory_service", return_value=mock_memory_service):
            response = app_client.get("/api/traces/detail/nonexistent-id")
            assert response.status_code == 404
