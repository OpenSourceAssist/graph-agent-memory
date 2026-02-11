"""Tests for the Financial Advisor Neo4j integration.

Covers:
- Neo4jDomainService (unit tests with mocked graph client)
- Tool functions (kyc, aml, relationship, compliance) with mocked Neo4jDomainService
- API route helpers (customers, alerts)
- Agent wiring (_bind_tool, agent creation)
- MemoryClient.graph property
- Structure validation (file existence, method signatures)

These are unit tests that do NOT require a running Neo4j instance.
All example app modules are loaded via importlib to avoid relative import issues.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
APP_DIR = EXAMPLES_DIR / "google-cloud-financial-advisor"
BACKEND_SRC = APP_DIR / "backend" / "src"


# ============================================================================
# Module loader — loads individual .py files without triggering __init__.py
# ============================================================================


def _setup_backend_package_hierarchy():
    """Register the backend src directory as a proper package hierarchy.

    This enables relative imports (e.g. `from ..services.neo4j_service import ...`)
    to resolve when loading individual modules from the example app.
    """
    src_dir = BACKEND_SRC
    # Register 'src' as the top-level package
    if "src" not in sys.modules:
        src_pkg = types.ModuleType("src")
        src_pkg.__path__ = [str(src_dir)]
        src_pkg.__package__ = "src"
        sys.modules["src"] = src_pkg

    # Register sub-packages
    sub_packages = [
        "services",
        "tools",
        "models",
        "agents",
        "api",
        "api.routes",
    ]
    for sub in sub_packages:
        full_name = f"src.{sub}"
        if full_name not in sys.modules:
            pkg = types.ModuleType(full_name)
            pkg.__path__ = [str(src_dir / sub.replace(".", "/"))]
            pkg.__package__ = full_name
            sys.modules[full_name] = pkg


def _load_module(name: str, filepath: Path, package: str | None = None) -> types.ModuleType:
    """Load a single Python file as a module with proper package context."""
    spec = importlib.util.spec_from_file_location(name, filepath, submodule_search_locations=[])
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {filepath}")
    mod = importlib.util.module_from_spec(spec)
    if package:
        mod.__package__ = package
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Set up the package hierarchy so relative imports work
_setup_backend_package_hierarchy()

# Pre-load neo4j_service.py (no problematic relative imports — only uses stdlib)
_neo4j_service_mod = _load_module(
    "src.services.neo4j_service",
    BACKEND_SRC / "services" / "neo4j_service.py",
    package="src.services",
)
Neo4jDomainService = _neo4j_service_mod.Neo4jDomainService


# ============================================================================
# Helpers
# ============================================================================


def _make_graph_client(**overrides) -> AsyncMock:
    """Create a mock Neo4j graph client (Neo4jClient)."""
    graph = AsyncMock()
    graph.execute_read = AsyncMock(return_value=[])
    graph.execute_write = AsyncMock(return_value=[])
    for key, val in overrides.items():
        setattr(graph, key, val)
    return graph


def _load_tool_module(filename: str) -> types.ModuleType:
    """Load a tool module with proper package context for relative imports."""
    basename = filename.replace(".py", "")
    mod_name = f"src.tools.{basename}"
    # Remove cached version if reloading
    sys.modules.pop(mod_name, None)
    return _load_module(mod_name, BACKEND_SRC / "tools" / filename, package="src.tools")


SAMPLE_CUSTOMER = {
    "id": "CUST-001",
    "name": "Alice Johnson",
    "type": "individual",
    "nationality": "US",
    "address": "123 Main St, New York, NY",
    "occupation": "Software Engineer",
    "employer": "Tech Corp",
    "jurisdiction": "US",
    "kyc_status": "verified",
    "risk_factors": [],
    "documents": [
        {"type": "passport", "status": "verified", "expiry_date": "2028-01-01"},
        {"type": "utility_bill", "status": "verified", "expiry_date": None},
    ],
}

SAMPLE_CUSTOMER_HIGH_RISK = {
    "id": "CUST-003",
    "name": "Global Holdings Ltd",
    "type": "corporate",
    "nationality": None,
    "jurisdiction": "KY",
    "business_type": "investment_holding",
    "kyc_status": "enhanced_review",
    "risk_factors": [
        "offshore_jurisdiction",
        "nominee_directors",
        "shell_company_indicators",
    ],
    "documents": [
        {"type": "certificate_of_incorporation", "status": "verified", "expiry_date": None},
        {"type": "register_of_directors", "status": "pending", "expiry_date": None},
    ],
}

SAMPLE_TRANSACTION = {
    "id": "TXN-001",
    "amount": 15000.0,
    "type": "wire_in",
    "counterparty": "Overseas Corp",
    "date": "2024-01-15",
    "description": "Wire transfer from overseas",
}

SAMPLE_ALERT = {
    "id": "ALERT-001",
    "type": "AML",
    "severity": "CRITICAL",
    "status": "NEW",
    "title": "Structuring Pattern Detected",
    "description": "Multiple cash deposits near threshold",
    "customer_id": "CUST-003",
    "customer_name": "Global Holdings Ltd",
    "evidence": ["TXN-010", "TXN-011"],
    "requires_sar": True,
    "auto_generated": True,
    "created_at": datetime(2024, 1, 15, 10, 30),
}


# ============================================================================
# Neo4jDomainService Tests
# ============================================================================


class TestNeo4jDomainService:
    """Unit tests for Neo4jDomainService with mocked graph client."""

    @pytest.fixture
    def graph(self):
        return _make_graph_client()

    @pytest.fixture
    def service(self, graph):
        return Neo4jDomainService(graph)

    # -- Customers -----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_customers_empty(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.list_customers()
        assert result == []
        graph.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_customers_returns_data(self, service, graph):
        graph.execute_read.return_value = [
            {"customer": SAMPLE_CUSTOMER},
            {"customer": SAMPLE_CUSTOMER_HIGH_RISK},
        ]
        result = await service.list_customers()
        assert len(result) == 2
        assert result[0]["name"] == "Alice Johnson"

    @pytest.mark.asyncio
    async def test_list_customers_with_type_filter(self, service, graph):
        graph.execute_read.return_value = [{"customer": SAMPLE_CUSTOMER}]
        await service.list_customers(customer_type="individual")
        call_args = graph.execute_read.call_args
        assert call_args[0][1]["type"] == "individual"

    @pytest.mark.asyncio
    async def test_get_customer_found(self, service, graph):
        graph.execute_read.return_value = [{"customer": SAMPLE_CUSTOMER}]
        result = await service.get_customer("CUST-001")
        assert result is not None
        assert result["name"] == "Alice Johnson"

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.get_customer("CUST-999")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_customer_documents(self, service, graph):
        graph.execute_read.return_value = [
            {"document": {"type": "passport", "status": "verified"}},
        ]
        result = await service.get_customer_documents("CUST-001")
        assert len(result) == 1
        assert result[0]["type"] == "passport"

    # -- Transactions --------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_transactions(self, service, graph):
        graph.execute_read.return_value = [{"transaction": SAMPLE_TRANSACTION}]
        result = await service.get_transactions("CUST-001")
        assert len(result) == 1
        assert result[0]["amount"] == 15000.0

    @pytest.mark.asyncio
    async def test_get_transactions_with_filters(self, service, graph):
        graph.execute_read.return_value = []
        await service.get_transactions("CUST-001", min_amount=5000.0, transaction_type="wire_in")
        call_args = graph.execute_read.call_args
        params = call_args[0][1]
        assert params["min_amount"] == 5000.0
        assert params["tx_type"] == "wire_in"

    @pytest.mark.asyncio
    async def test_get_transaction_stats_empty(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.get_transaction_stats("CUST-001")
        assert result["transaction_count"] == 0
        assert result["total_volume"] == 0

    @pytest.mark.asyncio
    async def test_get_transaction_stats(self, service, graph):
        graph.execute_read.return_value = [
            {
                "transaction_count": 5,
                "total_volume": 50000.0,
                "total_deposits": 30000.0,
                "total_withdrawals": 20000.0,
                "average_transaction": 10000.0,
                "counterparties": ["Corp A", "Corp B"],
                "transaction_types": ["wire_in", "wire_out"],
            }
        ]
        result = await service.get_transaction_stats("CUST-001")
        assert result["transaction_count"] == 5
        assert result["total_volume"] == 50000.0

    @pytest.mark.asyncio
    async def test_detect_structuring(self, service, graph):
        graph.execute_read.return_value = [
            {"transaction": {"id": "TXN-010", "amount": 9500}},
            {"transaction": {"id": "TXN-011", "amount": 9800}},
        ]
        result = await service.detect_structuring("CUST-003")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_detect_rapid_movement(self, service, graph):
        graph.execute_read.return_value = [
            {
                "inbound": {"id": "TXN-001", "amount": 50000},
                "outbound": {"id": "TXN-002", "amount": 48000},
                "retained": 2000,
            }
        ]
        result = await service.detect_rapid_movement("CUST-003")
        assert len(result) == 1
        assert result[0]["retained"] == 2000

    @pytest.mark.asyncio
    async def test_detect_layering(self, service, graph):
        graph.execute_read.return_value = [
            {"transaction": {"id": "TXN-005", "counterparty": "Cayman Fund"}},
        ]
        result = await service.detect_layering("CUST-003")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_velocity_metrics_empty(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.get_velocity_metrics("CUST-001")
        assert result["total_transactions"] == 0
        assert result["average_transaction"] == 0

    @pytest.mark.asyncio
    async def test_get_velocity_metrics(self, service, graph):
        graph.execute_read.return_value = [
            {"tx_type": "wire_in", "cnt": 3, "vol": 30000},
            {"tx_type": "cash_deposit", "cnt": 2, "vol": 19000},
        ]
        result = await service.get_velocity_metrics("CUST-001")
        assert result["total_transactions"] == 5
        assert result["total_volume"] == 49000
        assert result["transactions_by_type"]["wire_in"] == 3
        assert result["volume_by_type"]["cash_deposit"] == 19000

    # -- Network / Relationships ---------------------------------------------

    @pytest.mark.asyncio
    async def test_find_connections(self, service, graph):
        graph.execute_read.return_value = [
            {
                "entity": {"id": "ORG-001", "name": "Shell Corp"},
                "distance": 1,
                "rel_types": ["CONNECTED_TO"],
            }
        ]
        result = await service.find_connections("CUST-003")
        assert result["entity_id"] == "CUST-003"
        assert len(result["connections"]) == 1

    @pytest.mark.asyncio
    async def test_detect_shell_companies(self, service, graph):
        graph.execute_read.return_value = [
            {
                "org": {
                    "id": "ORG-001",
                    "name": "Shell Corp",
                    "jurisdiction": "KY",
                    "shell_indicators": ["no_employees", "po_box_address"],
                }
            }
        ]
        result = await service.detect_shell_companies("CUST-003")
        assert len(result) == 1
        assert result[0]["name"] == "Shell Corp"

    @pytest.mark.asyncio
    async def test_trace_ownership(self, service, graph):
        graph.execute_read.return_value = [
            {
                "owner": {"id": "CUST-003", "name": "Global Holdings", "type": "corporate"},
                "rel_types": ["OWNS"],
                "chain_length": 1,
            }
        ]
        result = await service.trace_ownership("ORG-001")
        assert result["entity_id"] == "ORG-001"
        assert len(result["ownership_chains"]) == 1
        assert result["ubo_identified"] is False

    @pytest.mark.asyncio
    async def test_trace_ownership_with_individual_ubo(self, service, graph):
        graph.execute_read.return_value = [
            {
                "owner": {"id": "CUST-001", "name": "Alice Johnson", "type": "individual"},
                "rel_types": ["OWNS"],
                "chain_length": 2,
            }
        ]
        result = await service.trace_ownership("ORG-001")
        assert result["ubo_identified"] is True

    @pytest.mark.asyncio
    async def test_get_network_risk_low(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.get_network_risk("CUST-001")
        assert result["network_risk_score"] == 0
        assert result["risk_level"] == "LOW"

    @pytest.mark.asyncio
    async def test_get_network_risk_high(self, service, graph):
        graph.execute_read.return_value = [
            {
                "entity": {
                    "id": "ORG-001",
                    "name": "Shell Corp KY",
                    "jurisdiction": "KY",
                    "shell_indicators": ["no_employees"],
                    "role": "nominee_services",
                }
            },
            {
                "entity": {
                    "id": "ORG-002",
                    "name": "BVI Holdings",
                    "jurisdiction": "BVI",
                    "shell_indicators": [],
                    "role": None,
                }
            },
        ]
        result = await service.get_network_risk("CUST-003")
        assert result["risk_level"] == "HIGH"
        assert result["network_risk_score"] == 65

    # -- Alerts --------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_alerts_empty(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.list_alerts()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_alerts(self, service, graph):
        graph.execute_read.return_value = [{"alert": SAMPLE_ALERT}]
        result = await service.list_alerts()
        assert len(result) == 1
        assert result[0]["severity"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_list_alerts_with_filters(self, service, graph):
        graph.execute_read.return_value = []
        await service.list_alerts(status="NEW", severity="CRITICAL", customer_id="CUST-003")
        call_args = graph.execute_read.call_args
        params = call_args[0][1]
        assert params["status"] == "NEW"
        assert params["severity"] == "CRITICAL"
        assert params["customer_id"] == "CUST-003"

    @pytest.mark.asyncio
    async def test_get_alert_found(self, service, graph):
        graph.execute_read.return_value = [{"alert": SAMPLE_ALERT}]
        result = await service.get_alert("ALERT-001")
        assert result is not None
        assert result["title"] == "Structuring Pattern Detected"

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.get_alert("ALERT-999")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_alert(self, service, graph):
        created = {**SAMPLE_ALERT, "id": "ALERT-NEW"}
        graph.execute_write.return_value = [{"alert": created}]
        result = await service.create_alert(
            {
                "id": "ALERT-NEW",
                "customer_id": "CUST-003",
                "type": "AML",
                "severity": "HIGH",
                "status": "NEW",
                "title": "Test Alert",
                "description": "Test",
            }
        )
        assert result["id"] == "ALERT-NEW"
        graph.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_alert(self, service, graph):
        updated = {**SAMPLE_ALERT, "status": "ACKNOWLEDGED"}
        graph.execute_write.return_value = [{"alert": updated}]
        result = await service.update_alert("ALERT-001", {"status": "ACKNOWLEDGED"})
        assert result is not None
        assert result["status"] == "ACKNOWLEDGED"

    @pytest.mark.asyncio
    async def test_update_alert_no_changes(self, service, graph):
        graph.execute_read.return_value = [{"alert": SAMPLE_ALERT}]
        result = await service.update_alert("ALERT-001", {"unknown_field": "value"})
        graph.execute_read.assert_called_once()
        graph.execute_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_alert_summary_empty(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.get_alert_summary()
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_get_alert_summary(self, service, graph):
        graph.execute_read.return_value = [
            {
                "total": 5,
                "critical": 2,
                "high": 1,
                "medium": 1,
                "low": 1,
                "new_count": 3,
                "acknowledged": 1,
                "investigating": 0,
                "escalated": 0,
                "resolved": 1,
                "critical_unresolved": 2,
                "high_unresolved": 1,
            }
        ]
        result = await service.get_alert_summary()
        assert result["total"] == 5
        assert result["by_severity"]["CRITICAL"] == 2
        assert result["by_status"]["NEW"] == 3
        assert result["critical_unresolved"] == 2

    # -- Sanctions -----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_check_sanctions_no_match(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.check_sanctions("John Smith")
        assert result == []

    @pytest.mark.asyncio
    async def test_check_sanctions_match(self, service, graph):
        graph.execute_read.return_value = [
            {
                "entity": {
                    "name": "Viktor Petrov",
                    "list": "OFAC SDN",
                    "reason": "Sanctions evasion",
                    "aliases": ["V. Petrov"],
                },
                "match_type": "EXACT",
                "confidence": 1.0,
            }
        ]
        result = await service.check_sanctions("Viktor Petrov")
        assert len(result) == 1
        assert result[0]["match_type"] == "EXACT"

    # -- PEP -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_check_pep_no_match(self, service, graph):
        graph.execute_read.return_value = []
        result = await service.check_pep("Random Person")
        assert result == []

    @pytest.mark.asyncio
    async def test_check_pep_direct_match(self, service, graph):
        graph.execute_read.return_value = [
            {
                "pep": {
                    "name": "Elena Rodriguez",
                    "position": "Finance Minister",
                    "country": "ES",
                    "tier": 1,
                },
                "match_type": "DIRECT_PEP",
                "confidence": 1.0,
            }
        ]
        result = await service.check_pep("Elena Rodriguez")
        assert len(result) >= 1
        assert result[0]["match_type"] == "DIRECT_PEP"

    # -- Graph stats ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_graph_stats(self, service, graph):
        graph.execute_read.side_effect = [
            [{"label": "Customer", "count": 3}, {"label": "Organization", "count": 6}],
            [{"type": "HAS_TRANSACTION", "count": 16}],
        ]
        result = await service.get_graph_stats()
        assert result["total_nodes"] == 9
        assert result["total_relationships"] == 16
        assert result["nodes_by_label"]["Customer"] == 3


# ============================================================================
# Tool function tests via source file validation
# ============================================================================


class TestToolFunctions:
    """Test tool function logic by loading modules directly with importlib.

    Each tool module does `from ..services.neo4j_service import Neo4jDomainService`
    We pre-register a stub so that import resolves.
    """

    @pytest.fixture
    def neo4j_service(self):
        svc = AsyncMock()
        svc.get_customer = AsyncMock(return_value=None)
        svc.get_customer_documents = AsyncMock(return_value=[])
        svc.get_transactions = AsyncMock(return_value=[])
        svc.detect_structuring = AsyncMock(return_value=[])
        svc.detect_rapid_movement = AsyncMock(return_value=[])
        svc.detect_layering = AsyncMock(return_value=[])
        svc.get_velocity_metrics = AsyncMock(
            return_value={
                "total_transactions": 0,
                "total_volume": 0,
                "average_transaction": 0,
                "transactions_by_type": {},
                "volume_by_type": {},
            }
        )
        svc.create_alert = AsyncMock(return_value={"id": "ALERT-NEW"})
        svc.check_sanctions = AsyncMock(return_value=[])
        svc.check_pep = AsyncMock(return_value=[])
        svc.find_connections = AsyncMock(return_value={"entity_id": "E1", "connections": []})
        svc.get_network_risk = AsyncMock(
            return_value={
                "network_risk_score": 0,
                "risk_level": "LOW",
                "risk_factors": [],
                "total_connections": 0,
            }
        )
        svc.detect_shell_companies = AsyncMock(return_value=[])
        svc.trace_ownership = AsyncMock(
            return_value={"entity_id": "E1", "ownership_chains": [], "ubo_identified": False}
        )
        svc._graph = AsyncMock()
        svc._graph.execute_read = AsyncMock(return_value=[])
        return svc

    # -- KYC tools -----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_identity_not_found(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        result = await mod.verify_identity("CUST-999", neo4j_service=neo4j_service)
        assert result["status"] == "NOT_FOUND"
        assert result["verified"] is False

    @pytest.mark.asyncio
    async def test_verify_identity_verified(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER
        result = await mod.verify_identity("CUST-001", neo4j_service=neo4j_service)
        assert result["status"] == "VERIFIED"
        assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_verify_identity_pending_corporate(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER_HIGH_RISK
        result = await mod.verify_identity("CUST-003", neo4j_service=neo4j_service)
        assert result["status"] == "PENDING"
        assert "register_of_directors" in result["missing_documents"]

    @pytest.mark.asyncio
    async def test_check_documents_all(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER
        result = await mod.check_documents("CUST-001", neo4j_service=neo4j_service)
        assert result["total_documents"] == 2

    @pytest.mark.asyncio
    async def test_check_documents_specific_type(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER
        result = await mod.check_documents(
            "CUST-001", document_type="passport", neo4j_service=neo4j_service
        )
        assert result["status"] == "VERIFIED"

    @pytest.mark.asyncio
    async def test_assess_customer_risk_low(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER
        result = await mod.assess_customer_risk("CUST-001", neo4j_service=neo4j_service)
        assert result["risk_level"] == "LOW"
        assert result["risk_score"] == 20

    @pytest.mark.asyncio
    async def test_assess_customer_risk_critical(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER_HIGH_RISK
        result = await mod.assess_customer_risk("CUST-003", neo4j_service=neo4j_service)
        assert result["risk_level"] == "CRITICAL"
        assert result["risk_score"] == 100

    @pytest.mark.asyncio
    async def test_check_adverse_media_no_hits(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER
        result = await mod.check_adverse_media("CUST-001", neo4j_service=neo4j_service)
        assert result["hits_found"] == 0

    @pytest.mark.asyncio
    async def test_check_adverse_media_with_hits(self, neo4j_service):
        mod = _load_tool_module("kyc_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER_HIGH_RISK
        result = await mod.check_adverse_media("CUST-003", neo4j_service=neo4j_service)
        assert result["hits_found"] == 1
        assert result["risk_indicator"] == "HIGH"

    # -- AML tools -----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_scan_transactions_no_data(self, neo4j_service):
        mod = _load_tool_module("aml_tools.py")
        result = await mod.scan_transactions("CUST-001", neo4j_service=neo4j_service)
        assert result["status"] == "NO_TRANSACTIONS"

    @pytest.mark.asyncio
    async def test_scan_transactions_with_data(self, neo4j_service):
        mod = _load_tool_module("aml_tools.py")
        neo4j_service.get_transactions.return_value = [
            {"id": "TXN-001", "amount": 10000, "type": "wire_in", "counterparty": "Corp A"},
            {"id": "TXN-002", "amount": 5000, "type": "wire_out", "counterparty": "Corp B"},
        ]
        result = await mod.scan_transactions("CUST-001", neo4j_service=neo4j_service)
        assert result["transaction_count"] == 2
        assert result["total_volume"] == 15000

    @pytest.mark.asyncio
    async def test_detect_patterns_structuring(self, neo4j_service):
        mod = _load_tool_module("aml_tools.py")
        neo4j_service.get_transactions.return_value = [
            {"id": "T1", "amount": 9500, "type": "cash_deposit"}
        ]
        neo4j_service.detect_structuring.return_value = [
            {"id": "TXN-010", "amount": 9500},
            {"id": "TXN-011", "amount": 9800},
        ]
        result = await mod.detect_patterns("CUST-003", neo4j_service=neo4j_service)
        assert any(p["pattern"] == "STRUCTURING" for p in result["patterns_detected"])

    @pytest.mark.asyncio
    async def test_flag_suspicious_transaction_success(self, neo4j_service):
        mod = _load_tool_module("aml_tools.py")
        neo4j_service._graph.execute_read.return_value = [
            {
                "customer_id": "CUST-003",
                "transaction": {"id": "TXN-010", "amount": 9500, "type": "cash_deposit"},
            }
        ]
        result = await mod.flag_suspicious_transaction(
            "TXN-010", "Structuring", severity="HIGH", neo4j_service=neo4j_service
        )
        assert result["status"] == "FLAGGED"

    @pytest.mark.asyncio
    async def test_analyze_velocity_no_data(self, neo4j_service):
        mod = _load_tool_module("aml_tools.py")
        result = await mod.analyze_velocity("CUST-001", neo4j_service=neo4j_service)
        assert result["status"] == "NO_DATA"

    # -- Compliance tools ----------------------------------------------------

    @pytest.mark.asyncio
    async def test_check_sanctions_clear(self, neo4j_service):
        mod = _load_tool_module("compliance_tools.py")
        result = await mod.check_sanctions("John Smith", neo4j_service=neo4j_service)
        assert result["screening_status"] == "CLEAR"

    @pytest.mark.asyncio
    async def test_check_sanctions_hit(self, neo4j_service):
        mod = _load_tool_module("compliance_tools.py")
        neo4j_service.check_sanctions.return_value = [
            {
                "entity": {"name": "Viktor Petrov", "list": "OFAC SDN", "reason": "test"},
                "match_type": "EXACT",
                "confidence": 1.0,
            }
        ]
        result = await mod.check_sanctions("Viktor Petrov", neo4j_service=neo4j_service)
        assert result["screening_status"] == "HIT"
        assert result["requires_escalation"] is True

    @pytest.mark.asyncio
    async def test_verify_pep_status_clear(self, neo4j_service):
        mod = _load_tool_module("compliance_tools.py")
        result = await mod.verify_pep_status("Random Person", neo4j_service=neo4j_service)
        assert result["pep_status"] == "CLEAR"

    @pytest.mark.asyncio
    async def test_generate_sar_report(self, neo4j_service):
        mod = _load_tool_module("compliance_tools.py")
        neo4j_service.get_customer.return_value = SAMPLE_CUSTOMER
        result = await mod.generate_sar_report(
            "CUST-001", "structuring", transaction_ids=["TXN-010"], neo4j_service=neo4j_service
        )
        assert result["status"] == "SAR_DRAFT_CREATED"

    @pytest.mark.asyncio
    async def test_assess_regulatory_requirements(self, neo4j_service):
        mod = _load_tool_module("compliance_tools.py")
        neo4j_service.get_customer.return_value = {**SAMPLE_CUSTOMER, "jurisdiction": "KY"}
        neo4j_service.get_transactions.return_value = [{"type": "cash_deposit"}]
        result = await mod.assess_regulatory_requirements("CUST-001", neo4j_service=neo4j_service)
        assert "US" in result["jurisdictions_analyzed"]

    # -- Relationship tools --------------------------------------------------

    @pytest.mark.asyncio
    async def test_find_connections_not_found(self, neo4j_service):
        mod = _load_tool_module("relationship_tools.py")
        result = await mod.find_connections("UNKNOWN", neo4j_service=neo4j_service)
        assert result["status"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_find_connections_found(self, neo4j_service):
        mod = _load_tool_module("relationship_tools.py")
        neo4j_service._graph.execute_read.return_value = [
            {"entity": {"id": "CUST-003", "name": "Global Holdings", "type": "corporate"}}
        ]
        neo4j_service.find_connections.return_value = {
            "entity_id": "CUST-003",
            "connections": [
                {
                    "entity": {
                        "id": "ORG-001",
                        "name": "Shell Corp",
                        "type": "org",
                        "jurisdiction": "KY",
                    },
                    "rel_types": ["CONNECTED_TO"],
                    "distance": 1,
                }
            ],
        }
        result = await mod.find_connections("CUST-003", neo4j_service=neo4j_service)
        assert result["connections_found"] == 1

    @pytest.mark.asyncio
    async def test_detect_shell_companies_entity_not_found(self, neo4j_service):
        mod = _load_tool_module("relationship_tools.py")
        result = await mod.detect_shell_companies("UNKNOWN", neo4j_service=neo4j_service)
        assert result["status"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_map_beneficial_ownership_not_found(self, neo4j_service):
        mod = _load_tool_module("relationship_tools.py")
        result = await mod.map_beneficial_ownership("UNKNOWN", neo4j_service=neo4j_service)
        assert result["status"] == "NOT_FOUND"


# ============================================================================
# Agent Wiring Tests (_bind_tool, agent creation)
# ============================================================================


class TestAgentWiring:
    """Test _bind_tool function — loaded directly from kyc_agent.py."""

    def _get_bind_tool(self):
        """Extract _bind_tool from kyc_agent.py without triggering ADK imports."""
        # Read the source and extract just the _bind_tool function
        source = (BACKEND_SRC / "agents" / "kyc_agent.py").read_text()
        # Build a minimal module with just _bind_tool
        code = """
import inspect
from functools import wraps

"""
        # Extract the function definition
        lines = source.split("\n")
        in_func = False
        func_lines = []
        for line in lines:
            if line.startswith("def _bind_tool("):
                in_func = True
            if in_func:
                func_lines.append(line)
                if line and not line[0].isspace() and len(func_lines) > 1:
                    # End of function (next top-level definition)
                    func_lines.pop()
                    break
        code += "\n".join(func_lines)

        ns: dict[str, Any] = {}
        exec(code, ns)
        return ns["_bind_tool"]

    def test_bind_tool_removes_neo4j_service_from_signature(self):
        _bind_tool = self._get_bind_tool()

        async def sample_tool(customer_id: str, *, neo4j_service: Any) -> dict:
            return {"customer_id": customer_id}

        bound = _bind_tool(sample_tool, MagicMock())
        sig = inspect.signature(bound)
        assert "neo4j_service" not in sig.parameters
        assert "customer_id" in sig.parameters

    def test_bind_tool_preserves_function_name(self):
        _bind_tool = self._get_bind_tool()

        async def verify_identity(customer_id: str, *, neo4j_service: Any) -> dict:
            return {}

        bound = _bind_tool(verify_identity, MagicMock())
        assert bound.__name__ == "verify_identity"

    @pytest.mark.asyncio
    async def test_bind_tool_passes_neo4j_service(self):
        _bind_tool = self._get_bind_tool()
        received = {}

        async def sample_tool(customer_id: str, *, neo4j_service: Any) -> dict:
            received["neo4j_service"] = neo4j_service
            received["customer_id"] = customer_id
            return {}

        mock_service = MagicMock()
        bound = _bind_tool(sample_tool, mock_service)
        await bound("CUST-001")

        assert received["neo4j_service"] is mock_service
        assert received["customer_id"] == "CUST-001"

    def test_bind_tool_handles_multiple_params(self):
        _bind_tool = self._get_bind_tool()

        async def multi_param(a: str, b: int = 5, c: bool = False, *, neo4j_service: Any) -> dict:
            return {}

        bound = _bind_tool(multi_param, MagicMock())
        sig = inspect.signature(bound)
        param_names = list(sig.parameters.keys())
        assert param_names == ["a", "b", "c"]


# ============================================================================
# API Route Helper Tests — loaded by parsing source directly
# ============================================================================


class TestCustomerRouteHelpers:
    """Test _compute_risk and _customer_from_dict from customers.py."""

    @pytest.fixture(autouse=True)
    def _load(self):
        """Load the helpers by exec'ing relevant code from customers.py."""
        # _compute_risk is a standalone function with no imports needed
        source = (BACKEND_SRC / "api" / "routes" / "customers.py").read_text()

        # Extract _compute_risk function
        lines = source.split("\n")
        func_lines = []
        in_func = False
        for line in lines:
            if line.startswith("def _compute_risk("):
                in_func = True
            elif in_func and line and not line[0].isspace() and line.strip():
                break
            if in_func:
                func_lines.append(line)

        code = "\n".join(func_lines)
        ns: dict[str, Any] = {}
        exec(code, ns)
        self._compute_risk = ns["_compute_risk"]

    def test_compute_risk_low(self):
        result = self._compute_risk(SAMPLE_CUSTOMER)
        assert result["risk_level"] == "LOW"
        assert result["risk_score"] == 20

    def test_compute_risk_critical(self):
        result = self._compute_risk(SAMPLE_CUSTOMER_HIGH_RISK)
        assert result["risk_level"] == "CRITICAL"
        assert result["risk_score"] == 100

    def test_compute_risk_no_risk_factors(self):
        cust = {"risk_factors": None, "documents": []}
        result = self._compute_risk(cust)
        assert result["risk_score"] == 20
        assert result["risk_level"] == "LOW"


class TestAlertRouteHelpers:
    """Test _to_python_datetime and _alert_from_dict from alerts.py."""

    @pytest.fixture(autouse=True)
    def _load(self):
        """Load the helpers by exec'ing relevant code from alerts.py."""
        source = (BACKEND_SRC / "api" / "routes" / "alerts.py").read_text()

        # Extract _to_python_datetime function
        lines = source.split("\n")

        # Find and extract _to_python_datetime
        to_dt_lines = []
        in_func = False
        for line in lines:
            if line.startswith("def _to_python_datetime("):
                in_func = True
            elif in_func and line and not line[0].isspace() and line.strip():
                break
            if in_func:
                to_dt_lines.append(line)

        code = "from datetime import datetime\n\n" + "\n".join(to_dt_lines)
        ns: dict[str, Any] = {}
        exec(code, ns)
        self._to_python_datetime = ns["_to_python_datetime"]

    def test_to_python_datetime_none(self):
        assert self._to_python_datetime(None) is None

    def test_to_python_datetime_with_python_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30)
        assert self._to_python_datetime(dt) == dt

    def test_to_python_datetime_with_neo4j_datetime(self):
        mock_neo4j_dt = MagicMock()
        expected = datetime(2024, 1, 15, 10, 30)
        mock_neo4j_dt.to_native.return_value = expected
        assert self._to_python_datetime(mock_neo4j_dt) == expected


# ============================================================================
# MemoryClient.graph Property Test
# ============================================================================


class TestMemoryClientGraphProperty:
    """Test the MemoryClient.graph property."""

    def test_graph_property_exists(self):
        from neo4j_agent_memory import MemoryClient

        assert hasattr(MemoryClient, "graph")

    def test_graph_property_raises_when_not_connected(self):
        from pydantic import SecretStr

        from neo4j_agent_memory import MemoryClient, MemorySettings
        from neo4j_agent_memory.config.settings import Neo4jConfig

        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri="bolt://localhost:7687",
                password=SecretStr("test"),
            ),
        )
        client = MemoryClient(settings)
        with pytest.raises(Exception, match="not connected"):
            _ = client.graph


# ============================================================================
# SSE Streaming Helper Tests
# ============================================================================


class TestSSEHelpers:
    """Test SSE helper functions from chat.py."""

    @pytest.fixture(autouse=True)
    def _load(self):
        """Extract _sse_event and _truncate_result from chat.py."""
        source = (BACKEND_SRC / "api" / "routes" / "chat.py").read_text()
        code = "import json\n\n"

        # Extract _sse_event
        lines = source.split("\n")
        for func_name in ("_sse_event", "_truncate_result"):
            in_func = False
            func_lines = []
            for line in lines:
                if line.startswith(f"def {func_name}("):
                    in_func = True
                elif in_func and line and not line[0].isspace() and line.strip():
                    break
                if in_func:
                    func_lines.append(line)
            code += "\n".join(func_lines) + "\n\n"

        ns: dict[str, Any] = {}
        exec(code, ns)
        self._sse_event = ns["_sse_event"]
        self._truncate_result = ns["_truncate_result"]

    def test_sse_event_format(self):
        result = self._sse_event("agent_start", {"agent": "kyc_agent"})
        assert result.startswith("event: agent_start\n")
        assert "data: " in result
        assert result.endswith("\n\n")
        import json

        data_line = result.split("\n")[1]
        data = json.loads(data_line.replace("data: ", ""))
        assert data["agent"] == "kyc_agent"

    def test_sse_event_types(self):
        for event_type in [
            "agent_start",
            "agent_complete",
            "agent_delegate",
            "tool_call",
            "tool_result",
            "memory_access",
            "thinking",
            "response",
            "trace_saved",
            "done",
            "error",
        ]:
            result = self._sse_event(event_type, {"test": True})
            assert result.startswith(f"event: {event_type}\n")

    def test_truncate_result_none(self):
        assert self._truncate_result(None) is None

    def test_truncate_result_string(self):
        result = self._truncate_result("hello")
        assert result == "hello"
        assert isinstance(result, str)

    def test_truncate_result_dict(self):
        result = self._truncate_result({"key": "value"})
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_truncate_result_list(self):
        result = self._truncate_result([1, 2, 3])
        assert isinstance(result, str)
        assert result == "[1, 2, 3]"

    def test_truncate_result_long_string(self):
        long_str = "x" * 600
        result = self._truncate_result(long_str, max_len=500)
        assert len(result) == 503  # 500 + "..."
        assert result.endswith("...")

    def test_truncate_result_long_dict(self):
        big_dict = {"key": "v" * 600}
        result = self._truncate_result(big_dict, max_len=500)
        assert isinstance(result, str)
        assert result.endswith("...")


# ============================================================================
# Structure Validation
# ============================================================================


class TestNewFileStructure:
    """Validate that all new files exist and have expected content."""

    @pytest.fixture
    def app_dir(self):
        return APP_DIR

    def test_neo4j_service_exists(self, app_dir):
        assert (app_dir / "backend" / "src" / "services" / "neo4j_service.py").exists()

    def test_sanctions_json_exists(self, app_dir):
        assert (app_dir / "data" / "sanctions.json").exists()

    def test_pep_json_exists(self, app_dir):
        assert (app_dir / "data" / "pep.json").exists()

    def test_alerts_json_exists(self, app_dir):
        assert (app_dir / "data" / "alerts.json").exists()

    def test_neo4j_service_has_expected_methods(self, app_dir):
        content = (app_dir / "backend" / "src" / "services" / "neo4j_service.py").read_text()
        expected = [
            "list_customers",
            "get_customer",
            "get_customer_documents",
            "get_transactions",
            "get_transaction_stats",
            "detect_structuring",
            "detect_rapid_movement",
            "detect_layering",
            "get_velocity_metrics",
            "find_connections",
            "detect_shell_companies",
            "trace_ownership",
            "get_network_risk",
            "list_alerts",
            "get_alert",
            "create_alert",
            "update_alert",
            "get_alert_summary",
            "check_sanctions",
            "check_pep",
            "get_graph_stats",
        ]
        for method in expected:
            assert f"async def {method}" in content, f"Missing method: {method}"

    def test_tools_use_neo4j_service_parameter(self, app_dir):
        for tool_file in [
            "kyc_tools.py",
            "aml_tools.py",
            "relationship_tools.py",
            "compliance_tools.py",
        ]:
            content = (app_dir / "backend" / "src" / "tools" / tool_file).read_text()
            assert "neo4j_service: Neo4jDomainService" in content, (
                f"{tool_file} missing neo4j_service param"
            )

    def test_agent_files_have_bind_tool(self, app_dir):
        for agent_file in [
            "kyc_agent.py",
            "aml_agent.py",
            "relationship_agent.py",
            "compliance_agent.py",
        ]:
            content = (app_dir / "backend" / "src" / "agents" / agent_file).read_text()
            assert "_bind_tool" in content, f"{agent_file} missing _bind_tool"

    def test_main_initializes_neo4j_service(self, app_dir):
        content = (app_dir / "backend" / "src" / "main.py").read_text()
        assert "Neo4jDomainService" in content
        assert "neo4j_service" in content

    def test_main_registers_traces_router(self, app_dir):
        content = (app_dir / "backend" / "src" / "main.py").read_text()
        assert "traces" in content, "main.py should import traces router"
        assert "traces.router" in content, "main.py should register traces.router"

    def test_routes_use_app_state(self, app_dir):
        for route_file in ["customers.py", "alerts.py"]:
            content = (app_dir / "backend" / "src" / "api" / "routes" / route_file).read_text()
            assert "_get_neo4j_service" in content, f"{route_file} missing _get_neo4j_service"

    def test_chat_has_both_endpoints(self, app_dir):
        content = (app_dir / "backend" / "src" / "api" / "routes" / "chat.py").read_text()
        assert "async def chat_stream" in content, "chat.py should have chat_stream"
        assert "async def chat(" in content, "chat.py should have original chat endpoint"
        assert "StreamingResponse" in content, "chat.py should use StreamingResponse"
        assert "text/event-stream" in content, "chat.py should use SSE content type"

    def test_chat_records_reasoning_traces(self, app_dir):
        content = (app_dir / "backend" / "src" / "api" / "routes" / "chat.py").read_text()
        assert "start_trace" in content, "chat.py should call start_trace"
        assert "add_step" in content, "chat.py should call add_step"
        assert "record_tool_call" in content, "chat.py should call record_tool_call"
        assert "complete_trace" in content, "chat.py should call complete_trace"
        assert "ToolCallStatus" in content, "chat.py should import ToolCallStatus"

    def test_chat_filters_internal_adk_functions(self, app_dir):
        content = (app_dir / "backend" / "src" / "api" / "routes" / "chat.py").read_text()
        assert "_internal_fns" in content, "chat.py should define _internal_fns set"
        assert '"transfer_to_agent"' in content, "Should filter transfer_to_agent"
        assert '"transfer"' in content, "Should filter transfer"

    def test_traces_route_has_endpoints(self, app_dir):
        content = (app_dir / "backend" / "src" / "api" / "routes" / "traces.py").read_text()
        assert "get_session_traces" in content, "traces.py should have get_session_traces"
        assert "get_trace_detail" in content, "traces.py should have get_trace_detail"
        assert "reasoning" in content, "traces.py should use reasoning layer"
        assert "list_traces" in content, "traces.py should call list_traces"
        assert "get_trace" in content, "traces.py should call get_trace"

    def test_routes_init_exports_traces(self, app_dir):
        content = (app_dir / "backend" / "src" / "api" / "routes" / "__init__.py").read_text()
        assert "traces" in content, "__init__.py should export traces module"

    def test_neo4j_service_uses_merge_for_alerts(self, app_dir):
        content = (app_dir / "backend" / "src" / "services" / "neo4j_service.py").read_text()
        assert "MERGE (a:Alert" in content, "create_alert should use MERGE"
        assert "ON CREATE SET" in content, "create_alert should use ON CREATE SET"
        assert "import uuid" in content, "Should import uuid for alert IDs"

    def test_neo4j_service_uses_where_not_and(self, app_dir):
        """Verify get_transactions uses WHERE (not AND) for optional filters."""
        content = (app_dir / "backend" / "src" / "services" / "neo4j_service.py").read_text()
        # The dynamic filter should use WHERE, not AND
        assert 'where_extra = ("WHERE "' in content, "get_transactions should use WHERE"

    def test_no_hardcoded_sample_data_in_tools(self, app_dir):
        for tool_file in [
            "kyc_tools.py",
            "aml_tools.py",
            "relationship_tools.py",
            "compliance_tools.py",
        ]:
            content = (app_dir / "backend" / "src" / "tools" / tool_file).read_text()
            assert "SAMPLE_CUSTOMERS" not in content, f"{tool_file} still has SAMPLE_CUSTOMERS"
            assert "SAMPLE_TRANSACTIONS" not in content, (
                f"{tool_file} still has SAMPLE_TRANSACTIONS"
            )
            assert "SAMPLE_NETWORK" not in content, f"{tool_file} still has SAMPLE_NETWORK"

    def test_no_hardcoded_sample_data_in_routes(self, app_dir):
        for route_file in ["customers.py", "alerts.py", "investigations.py"]:
            content = (app_dir / "backend" / "src" / "api" / "routes" / route_file).read_text()
            assert "SAMPLE_CUSTOMERS" not in content, f"{route_file} still has SAMPLE_CUSTOMERS"

    # -- Frontend structure --------------------------------------------------

    def test_frontend_has_agent_stream_hook(self):
        hook = APP_DIR / "frontend" / "src" / "hooks" / "useAgentStream.ts"
        assert hook.exists(), "useAgentStream.ts should exist"
        content = hook.read_text()
        assert "useAgentStream" in content, "Should export useAgentStream"
        assert "agentStates" in content, "Should track agentStates"
        assert "streamChatMessage" in content, "Should use streamChatMessage from api"

    def test_frontend_has_orchestration_view(self):
        comp = APP_DIR / "frontend" / "src" / "components" / "Chat" / "AgentOrchestrationView.tsx"
        assert comp.exists()
        content = comp.read_text()
        assert "framer-motion" in content or "motion" in content, "Should use framer-motion"
        assert "AnimatePresence" in content, "Should use AnimatePresence"

    def test_frontend_has_activity_timeline(self):
        comp = APP_DIR / "frontend" / "src" / "components" / "Chat" / "AgentActivityTimeline.tsx"
        assert comp.exists()
        content = comp.read_text()
        assert "Timeline" in content, "Should use Chakra Timeline"

    def test_frontend_has_tool_call_card(self):
        comp = APP_DIR / "frontend" / "src" / "components" / "Chat" / "ToolCallCard.tsx"
        assert comp.exists()
        content = comp.read_text()
        assert "formatValue" in content, "Should have formatValue helper"

    def test_frontend_has_memory_access_indicator(self):
        comp = APP_DIR / "frontend" / "src" / "components" / "Chat" / "MemoryAccessIndicator.tsx"
        assert comp.exists()

    def test_frontend_api_has_streaming(self):
        api = APP_DIR / "frontend" / "src" / "lib" / "api.ts"
        content = api.read_text()
        assert "streamChatMessage" in content, "api.ts should have streamChatMessage"
        assert "getSessionTraces" in content, "api.ts should have getSessionTraces"
        assert "AgentEvent" in content, "api.ts should define AgentEvent type"

    def test_frontend_package_has_framer_motion(self):
        pkg = APP_DIR / "frontend" / "package.json"
        content = pkg.read_text()
        assert "framer-motion" in content, "package.json should include framer-motion"
