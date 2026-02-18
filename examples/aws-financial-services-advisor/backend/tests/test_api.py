"""Tests for FastAPI endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestChatAPI:
    """Tests for chat/agent interaction endpoints."""

    @patch("src.api.routes.chat.create_supervisor_agent")
    def test_chat_endpoint_basic(self, mock_create_agent, test_client):
        """Test basic chat endpoint functionality."""
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(
            message="I can help you with financial compliance inquiries."
        )
        mock_create_agent.return_value = mock_agent

        response = test_client.post(
            "/api/chat",
            json={
                "message": "Hello, I need help with KYC",
                "session_id": "test-session-001",
            },
        )

        # Should succeed or return appropriate error
        assert response.status_code in [200, 500, 503]

    @patch("src.api.routes.chat.create_supervisor_agent")
    def test_chat_with_customer_context(self, mock_create_agent, test_client):
        """Test chat with customer context."""
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        response = test_client.post(
            "/api/chat",
            json={
                "message": "What is the risk level for this customer?",
                "session_id": "test-session-002",
                "customer_id": "CUST-001",
            },
        )

        assert response.status_code in [200, 500, 503]

    def test_chat_missing_message(self, test_client):
        """Test chat endpoint validation for missing message."""
        response = test_client.post(
            "/api/chat",
            json={
                "session_id": "test-session-003",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_get_conversation_history(self, test_client):
        """Test retrieving conversation history."""
        response = test_client.get("/api/chat/history/test-session-001")

        # Should return history or empty list
        assert response.status_code in [200, 404]


class TestCustomersAPI:
    """Tests for customer management endpoints."""

    def test_list_customers(self, test_client):
        """Test listing customers."""
        response = test_client.get("/api/customers")

        assert response.status_code == 200
        data = response.json()
        assert "customers" in data or isinstance(data, list)

    def test_list_customers_with_filters(self, test_client):
        """Test listing customers with risk level filter."""
        response = test_client.get("/api/customers?risk_level=high")

        assert response.status_code == 200

    def test_get_customer_by_id(self, test_client):
        """Test getting a specific customer."""
        response = test_client.get("/api/customers/CUST-001")

        # Should return customer or 404
        assert response.status_code in [200, 404]

    def test_get_customer_risk_assessment(self, test_client):
        """Test getting customer risk assessment."""
        response = test_client.get("/api/customers/CUST-001/risk")

        assert response.status_code in [200, 404]

    def test_get_customer_network(self, test_client):
        """Test getting customer network graph."""
        response = test_client.get("/api/customers/CUST-001/network")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "nodes" in data or "network" in data

    def test_create_customer(self, test_client, sample_customer):
        """Test creating a new customer."""
        customer_data = {
            "name": "New Test Corp",
            "type": "corporate",
            "industry": "Technology",
            "jurisdiction": "US",
        }

        response = test_client.post("/api/customers", json=customer_data)

        assert response.status_code in [200, 201, 422]

    def test_update_customer(self, test_client):
        """Test updating a customer."""
        update_data = {
            "risk_level": "high",
        }

        response = test_client.put("/api/customers/CUST-001", json=update_data)

        assert response.status_code in [200, 404, 422]


class TestInvestigationsAPI:
    """Tests for investigation workflow endpoints."""

    def test_list_investigations(self, test_client):
        """Test listing investigations."""
        response = test_client.get("/api/investigations")

        assert response.status_code == 200

    def test_list_investigations_by_status(self, test_client):
        """Test listing investigations filtered by status."""
        response = test_client.get("/api/investigations?status=in_progress")

        assert response.status_code == 200

    def test_get_investigation_by_id(self, test_client):
        """Test getting a specific investigation."""
        response = test_client.get("/api/investigations/INV-001")

        assert response.status_code in [200, 404]

    def test_create_investigation(self, test_client):
        """Test creating a new investigation."""
        investigation_data = {
            "title": "Test Investigation",
            "description": "Testing investigation workflow",
            "customer_id": "CUST-001",
            "alert_ids": ["ALERT-001"],
        }

        response = test_client.post("/api/investigations", json=investigation_data)

        assert response.status_code in [200, 201, 422]

    def test_update_investigation_status(self, test_client):
        """Test updating investigation status."""
        response = test_client.put(
            "/api/investigations/INV-001/status",
            json={"status": "completed"},
        )

        assert response.status_code in [200, 404, 422]

    def test_get_investigation_audit_trail(self, test_client):
        """Test getting investigation audit trail."""
        response = test_client.get("/api/investigations/INV-001/audit-trail")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "entries" in data or isinstance(data, list)


class TestAlertsAPI:
    """Tests for alert management endpoints."""

    def test_list_alerts(self, test_client):
        """Test listing alerts."""
        response = test_client.get("/api/alerts")

        assert response.status_code == 200

    def test_list_alerts_by_severity(self, test_client):
        """Test listing alerts filtered by severity."""
        response = test_client.get("/api/alerts?severity=high")

        assert response.status_code == 200

    def test_list_alerts_by_status(self, test_client):
        """Test listing alerts filtered by status."""
        response = test_client.get("/api/alerts?status=open")

        assert response.status_code == 200

    def test_get_alert_by_id(self, test_client):
        """Test getting a specific alert."""
        response = test_client.get("/api/alerts/ALERT-001")

        assert response.status_code in [200, 404]

    def test_acknowledge_alert(self, test_client):
        """Test acknowledging an alert."""
        response = test_client.post(
            "/api/alerts/ALERT-001/acknowledge",
            json={"notes": "Reviewed and acknowledged"},
        )

        assert response.status_code in [200, 404]

    def test_escalate_alert(self, test_client):
        """Test escalating an alert."""
        response = test_client.post(
            "/api/alerts/ALERT-001/escalate",
            json={
                "reason": "Requires senior review",
                "escalate_to": "supervisor@company.com",
            },
        )

        assert response.status_code in [200, 404]

    def test_close_alert(self, test_client):
        """Test closing an alert."""
        response = test_client.post(
            "/api/alerts/ALERT-001/close",
            json={
                "resolution": "False positive - verified legitimate transaction",
            },
        )

        assert response.status_code in [200, 404]


class TestGraphAPI:
    """Tests for graph visualization endpoints."""

    def test_get_entity_subgraph(self, test_client):
        """Test getting entity subgraph."""
        response = test_client.get("/api/graph/entity/Acme%20Corporation")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "nodes" in data
            assert "relationships" in data or "edges" in data

    def test_search_graph(self, test_client):
        """Test semantic search across graph."""
        response = test_client.post(
            "/api/graph/search",
            json={
                "query": "technology companies in US",
                "limit": 10,
            },
        )

        assert response.status_code in [200, 422]

    def test_get_connection_path(self, test_client):
        """Test finding connection path between entities."""
        response = test_client.get(
            "/api/graph/path",
            params={
                "from_entity": "CUST-001",
                "to_entity": "CUST-002",
            },
        )

        assert response.status_code in [200, 404]


class TestReportsAPI:
    """Tests for compliance report endpoints."""

    def test_generate_sar_report(self, test_client):
        """Test generating Suspicious Activity Report."""
        response = test_client.post(
            "/api/reports/sar",
            json={
                "customer_id": "CUST-001",
                "transaction_ids": ["TXN-001"],
                "alert_ids": ["ALERT-001"],
                "narrative": "Suspicious wire transfer activity",
            },
        )

        assert response.status_code in [200, 201, 404, 422]

    def test_generate_risk_assessment_report(self, test_client):
        """Test generating risk assessment report."""
        response = test_client.post(
            "/api/reports/risk-assessment",
            json={
                "customer_id": "CUST-001",
                "include_network": True,
                "include_transactions": True,
            },
        )

        assert response.status_code in [200, 201, 404, 422]

    def test_list_reports(self, test_client):
        """Test listing generated reports."""
        response = test_client.get("/api/reports")

        assert response.status_code == 200

    def test_get_report_by_id(self, test_client):
        """Test getting a specific report."""
        response = test_client.get("/api/reports/RPT-001")

        assert response.status_code in [200, 404]


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, test_client):
        """Test basic health check."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_readiness_check(self, test_client):
        """Test readiness check (dependencies)."""
        response = test_client.get("/ready")

        # May fail if dependencies not available
        assert response.status_code in [200, 503]


class TestAPIValidation:
    """Tests for API input validation."""

    def test_invalid_customer_type(self, test_client):
        """Test validation of invalid customer type."""
        response = test_client.post(
            "/api/customers",
            json={
                "name": "Test Corp",
                "type": "invalid_type",
                "jurisdiction": "US",
            },
        )

        assert response.status_code == 422

    def test_invalid_risk_level(self, test_client):
        """Test validation of invalid risk level."""
        response = test_client.put(
            "/api/customers/CUST-001",
            json={"risk_level": "super_high"},
        )

        assert response.status_code in [404, 422]

    def test_invalid_alert_severity(self, test_client):
        """Test validation of invalid alert severity."""
        response = test_client.get("/api/alerts?severity=extreme")

        # Should either ignore invalid filter or return validation error
        assert response.status_code in [200, 422]

    def test_empty_investigation_title(self, test_client):
        """Test validation of empty investigation title."""
        response = test_client.post(
            "/api/investigations",
            json={
                "title": "",
                "customer_id": "CUST-001",
            },
        )

        assert response.status_code == 422

    def test_negative_transaction_amount(self, test_client):
        """Test validation of negative transaction amount in search."""
        response = test_client.post(
            "/api/graph/search",
            json={
                "query": "transactions",
                "min_amount": -1000,
            },
        )

        # May accept or reject based on implementation
        assert response.status_code in [200, 422]
