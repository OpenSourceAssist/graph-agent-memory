"""Pytest configuration and shared fixtures for Financial Services Advisor tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from src.models.alert import Alert, AlertSeverity, AlertStatus, AlertType

# Import models
from src.models.customer import (
    Account,
    AccountType,
    Contact,
    Customer,
    CustomerType,
    RiskLevel,
)
from src.models.investigation import Investigation, InvestigationStatus
from src.models.transaction import (
    Beneficiary,
    Transaction,
    TransactionStatus,
    TransactionType,
)

# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_customer() -> Customer:
    """Create a sample customer for testing."""
    return Customer(
        id="CUST-001",
        name="Acme Corporation",
        type=CustomerType.CORPORATE,
        industry="Technology",
        jurisdiction="US",
        risk_level=RiskLevel.MEDIUM,
        contacts=[
            Contact(
                name="John Smith",
                role="CEO",
                email="john.smith@acme.com",
                phone="+1-555-0100",
                pep_status=False,
            )
        ],
        accounts=[
            Account(
                id="ACC-001",
                type=AccountType.BUSINESS_CHECKING,
                currency="USD",
                balance=150000.00,
                opened_date=datetime(2023, 1, 15, tzinfo=timezone.utc),
            )
        ],
        onboarding_date=datetime(2023, 1, 15, tzinfo=timezone.utc),
        last_review_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        next_review_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_high_risk_customer() -> Customer:
    """Create a high-risk customer for testing."""
    return Customer(
        id="CUST-002",
        name="Offshore Holdings Ltd",
        type=CustomerType.CORPORATE,
        industry="Finance",
        jurisdiction="BVI",
        risk_level=RiskLevel.HIGH,
        contacts=[
            Contact(
                name="Anonymous Director",
                role="Director",
                pep_status=True,
            )
        ],
        accounts=[
            Account(
                id="ACC-002",
                type=AccountType.INVESTMENT,
                currency="USD",
                balance=5000000.00,
                opened_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            )
        ],
        onboarding_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_transaction() -> Transaction:
    """Create a sample transaction for testing."""
    return Transaction(
        id="TXN-001",
        from_account="ACC-001",
        to_account="ACC-EXT-001",
        amount=50000.00,
        currency="USD",
        timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        type=TransactionType.WIRE_TRANSFER,
        status=TransactionStatus.COMPLETED,
        beneficiary=Beneficiary(
            name="Global Trade Ltd",
            account_number="****5678",
            bank_name="International Bank",
            jurisdiction="UK",
        ),
        reference="INV-2025-001",
        description="Payment for services",
    )


@pytest.fixture
def suspicious_transaction() -> Transaction:
    """Create a suspicious transaction for testing."""
    return Transaction(
        id="TXN-002",
        from_account="ACC-002",
        to_account="ACC-EXT-999",
        amount=9999.00,  # Just under reporting threshold
        currency="USD",
        timestamp=datetime(2025, 1, 20, 23, 55, 0, tzinfo=timezone.utc),
        type=TransactionType.WIRE_TRANSFER,
        status=TransactionStatus.COMPLETED,
        beneficiary=Beneficiary(
            name="Shell Corp BVI",
            jurisdiction="BVI",
        ),
    )


@pytest.fixture
def sample_alert() -> Alert:
    """Create a sample alert for testing."""
    return Alert(
        id="ALERT-001",
        type=AlertType.SUSPICIOUS_TRANSACTION,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title="Large wire transfer to high-risk jurisdiction",
        description="Customer CUST-001 initiated a $50,000 wire transfer to BVI",
        customer_id="CUST-001",
        transaction_id="TXN-001",
        created_at=datetime(2025, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
        risk_score=0.85,
        risk_factors=[
            "High-risk jurisdiction (BVI)",
            "Large transaction amount",
            "First transaction to this beneficiary",
        ],
    )


@pytest.fixture
def sample_investigation() -> Investigation:
    """Create a sample investigation for testing."""
    return Investigation(
        id="INV-001",
        title="Investigation of suspicious wire transfers",
        description="Review of multiple wire transfers to offshore jurisdictions",
        status=InvestigationStatus.IN_PROGRESS,
        customer_id="CUST-001",
        alert_ids=["ALERT-001"],
        assigned_to="analyst@company.com",
        created_at=datetime(2025, 1, 16, 9, 0, 0, tzinfo=timezone.utc),
        priority=1,
    )


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_memory_service():
    """Create a mock memory service."""
    service = AsyncMock()
    service.add_customer = AsyncMock(return_value="entity-123")
    service.get_customer_network = AsyncMock(
        return_value={
            "nodes": [
                {"id": "CUST-001", "label": "Customer", "name": "Acme Corporation"}
            ],
            "relationships": [],
        }
    )
    service.search_entities = AsyncMock(return_value=[])
    service.start_investigation_trace = AsyncMock()
    service.add_reasoning_step = AsyncMock()
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_risk_service():
    """Create a mock risk service."""
    from src.services.risk_service import RiskAssessment, RiskComponent

    service = MagicMock()
    service.calculate_customer_risk = MagicMock(
        return_value=RiskAssessment(
            overall_score=0.45,
            risk_level=RiskLevel.MEDIUM,
            components=[
                RiskComponent(
                    name="Geographic Risk",
                    score=0.3,
                    weight=0.25,
                    factors=["US jurisdiction - low risk"],
                ),
                RiskComponent(
                    name="Customer Type Risk",
                    score=0.5,
                    weight=0.20,
                    factors=["Corporate entity"],
                ),
            ],
            recommendations=["Schedule periodic review"],
            assessment_date=datetime.now(timezone.utc),
        )
    )
    return service


@pytest.fixture
def mock_bedrock_model():
    """Create a mock Bedrock model for agent testing."""
    model = MagicMock()
    model.converse = MagicMock(
        return_value={
            "output": {"message": {"content": [{"text": "Mock response"}]}},
            "stopReason": "end_turn",
        }
    )
    return model


# ============================================================================
# API Test Fixtures
# ============================================================================


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    from src.main import app

    # Override dependencies for testing
    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_client(test_client):
    """Create an authenticated test client."""
    # In a real implementation, this would include authentication headers
    test_client.headers["Authorization"] = "Bearer test-token"
    return test_client


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("NEO4J_DATABASE", "neo4j")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("BEDROCK_MODEL", "anthropic.claude-sonnet-4-20250514-v1:0")
    monkeypatch.setenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
