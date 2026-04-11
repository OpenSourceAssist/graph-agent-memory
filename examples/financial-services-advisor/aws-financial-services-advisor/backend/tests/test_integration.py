"""Integration tests requiring a running Neo4j instance.

These tests load sample data and run real Cypher queries.
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Check if Neo4j is available
NEO4J_URI = os.getenv("NEO4J_URI", "")
HAS_NEO4J = bool(NEO4J_URI) and NEO4J_URI != "bolt://localhost:7687"

try:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "test-password")),
    )
    driver.verify_connectivity()
    driver.close()
    HAS_NEO4J = True
except Exception:
    HAS_NEO4J = False

pytestmark = pytest.mark.skipif(not HAS_NEO4J, reason="Neo4j not available")

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@pytest.fixture(scope="module")
def loaded_neo4j():
    """Load sample data into Neo4j once for the module."""
    # Run the load script
    result = subprocess.run(
        [sys.executable, str(DATA_DIR / "load_sample_data.py")],
        capture_output=True,
        text=True,
        cwd=str(DATA_DIR),
    )
    if result.returncode != 0:
        pytest.skip(f"Failed to load sample data: {result.stderr}")

    # Create Neo4jDomainService
    from neo4j_agent_memory import MemoryClient, MemorySettings
    from neo4j_agent_memory.config import Neo4jConfig

    import asyncio

    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "test-password"),
        ),
    )
    client = MemoryClient(settings)
    asyncio.get_event_loop().run_until_complete(client.connect())

    from src.services.neo4j_service import Neo4jDomainService

    svc = Neo4jDomainService(client.graph)
    yield svc

    asyncio.get_event_loop().run_until_complete(client.close())


@pytest.mark.integration
class TestCustomerQueries:
    @pytest.mark.asyncio
    async def test_get_customer_john_smith(self, loaded_neo4j):
        customer = await loaded_neo4j.get_customer("CUST-001")
        assert customer is not None
        assert customer["name"] == "John Smith"
        assert customer["type"] == "individual"

    @pytest.mark.asyncio
    async def test_get_customer_global_holdings(self, loaded_neo4j):
        customer = await loaded_neo4j.get_customer("CUST-003")
        assert customer is not None
        assert customer["name"] == "Global Holdings Ltd"
        assert customer["type"] == "corporate"

    @pytest.mark.asyncio
    async def test_list_customers(self, loaded_neo4j):
        customers = await loaded_neo4j.list_customers()
        assert len(customers) == 3


@pytest.mark.integration
class TestAMLPatterns:
    @pytest.mark.asyncio
    async def test_detect_structuring_cust003(self, loaded_neo4j):
        """CUST-003 has 4x $9,500 cash deposits (structuring)."""
        results = await loaded_neo4j.detect_structuring("CUST-003")
        assert len(results) == 4
        assert all(9000 <= r["amount"] < 10000 for r in results)

    @pytest.mark.asyncio
    async def test_no_structuring_cust001(self, loaded_neo4j):
        """CUST-001 (low-risk) should have no structuring."""
        results = await loaded_neo4j.detect_structuring("CUST-001")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_detect_rapid_movement_cust002(self, loaded_neo4j):
        """CUST-002 has wire_in/wire_out pairs within 2 days."""
        results = await loaded_neo4j.detect_rapid_movement("CUST-002")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_detect_layering_cust003(self, loaded_neo4j):
        """CUST-003 has transactions with offshore counterparties."""
        results = await loaded_neo4j.detect_layering("CUST-003")
        assert len(results) >= 1


@pytest.mark.integration
class TestNetworkAnalysis:
    @pytest.mark.asyncio
    async def test_find_connections_cust003(self, loaded_neo4j):
        result = await loaded_neo4j.find_connections("CUST-003")
        assert len(result["connections"]) >= 1

    @pytest.mark.asyncio
    async def test_detect_shell_companies_cust003(self, loaded_neo4j):
        shells = await loaded_neo4j.detect_shell_companies("CUST-003")
        assert len(shells) >= 1
        shell_names = [s["name"] for s in shells]
        assert any("Shell Corp" in name or "Anonymous Trust" in name for name in shell_names)

    @pytest.mark.asyncio
    async def test_network_risk_cust003_is_high(self, loaded_neo4j):
        result = await loaded_neo4j.get_network_risk("CUST-003")
        assert result["risk_level"] in ("HIGH", "CRITICAL")


@pytest.mark.integration
class TestSanctionsAndPEP:
    @pytest.mark.asyncio
    async def test_check_sanctions_exact_match(self, loaded_neo4j):
        results = await loaded_neo4j.check_sanctions("Ivan Petrov")
        assert len(results) >= 1
        assert any(r["match_type"] == "EXACT" for r in results)

    @pytest.mark.asyncio
    async def test_check_sanctions_no_match(self, loaded_neo4j):
        results = await loaded_neo4j.check_sanctions("Clean Person XYZ")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_check_pep_direct(self, loaded_neo4j):
        results = await loaded_neo4j.check_pep("Carlos Rodriguez")
        assert len(results) >= 1


@pytest.mark.integration
class TestGraphStats:
    @pytest.mark.asyncio
    async def test_graph_stats_not_empty(self, loaded_neo4j):
        stats = await loaded_neo4j.get_graph_stats()
        assert stats["total_nodes"] > 0
        assert stats["total_relationships"] > 0
        assert "Customer" in stats["nodes_by_label"]
