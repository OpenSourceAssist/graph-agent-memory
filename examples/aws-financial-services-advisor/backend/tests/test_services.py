"""Tests for business logic services."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.customer import CustomerType, RiskLevel
from src.services.risk_service import RiskService, get_risk_service


class TestRiskService:
    """Tests for the risk calculation service."""

    def test_calculate_geographic_risk_low(self):
        """Test geographic risk calculation for low-risk jurisdiction."""
        service = RiskService()

        score, factors = service.calculate_geographic_risk("US")

        assert score >= 0.0
        assert score <= 50  # US should be low risk (not in high/medium lists)

    def test_calculate_geographic_risk_medium(self):
        """Test geographic risk calculation for medium-risk jurisdiction."""
        service = RiskService()

        score, factors = service.calculate_geographic_risk("PA")  # Panama

        assert score >= 25
        assert len(factors) > 0
        assert any("medium-risk" in f.lower() for f in factors)

    def test_calculate_geographic_risk_high(self):
        """Test geographic risk calculation for high-risk jurisdiction."""
        service = RiskService()

        # High-risk jurisdictions (sanctioned countries)
        score, factors = service.calculate_geographic_risk("KP")  # North Korea

        assert score >= 60
        assert any("high-risk" in f.lower() for f in factors)

    def test_calculate_geographic_risk_with_counterparties(self):
        """Test geographic risk with counterparty jurisdictions."""
        service = RiskService()

        score, factors = service.calculate_geographic_risk(
            primary_jurisdiction="US",
            counterparty_jurisdictions=["BVI", "KY"],
        )

        # Should increase risk due to offshore counterparties
        assert score > 0
        assert len(factors) > 0

    def test_calculate_customer_type_risk_individual(self):
        """Test customer type risk for individuals."""
        service = RiskService()

        score, factors = service.calculate_customer_type_risk("individual")

        assert score >= 0.0
        assert score <= 100

    def test_calculate_customer_type_risk_corporate(self):
        """Test customer type risk for corporations."""
        service = RiskService()

        corp_score, _ = service.calculate_customer_type_risk("corporate")
        individual_score, _ = service.calculate_customer_type_risk("individual")

        # Corporate typically higher risk than individual
        assert corp_score >= individual_score

    def test_calculate_customer_type_risk_trust(self):
        """Test customer type risk for trusts."""
        service = RiskService()

        score, factors = service.calculate_customer_type_risk("trust")

        # Trusts typically high risk due to opacity
        assert score >= 30

    def test_calculate_customer_type_risk_high_risk_industry(self):
        """Test customer type risk with high-risk industry."""
        service = RiskService()

        score, factors = service.calculate_customer_type_risk(
            customer_type="corporate",
            industry="gambling",
        )

        assert score >= 50
        assert any("high-risk industry" in f.lower() for f in factors)

    def test_calculate_customer_type_risk_complex_structure(self):
        """Test customer type risk with complex structure."""
        service = RiskService()

        complex_score, complex_factors = service.calculate_customer_type_risk(
            customer_type="corporate",
            has_complex_structure=True,
            has_nominee_shareholders=True,
        )

        simple_score, _ = service.calculate_customer_type_risk(
            customer_type="corporate",
        )

        assert complex_score > simple_score
        assert any("complex" in f.lower() or "nominee" in f.lower() for f in complex_factors)

    def test_calculate_transaction_risk_normal(self):
        """Test transaction risk with normal activity."""
        service = RiskService()

        score, factors = service.calculate_transaction_risk(
            avg_monthly_volume=10000,
            expected_monthly_volume=10000,
            cash_transaction_ratio=0.1,
            high_risk_jurisdiction_ratio=0.0,
        )

        assert score < 50  # Normal activity should be low risk

    def test_calculate_transaction_risk_high_volume(self):
        """Test transaction risk with high volume deviation."""
        service = RiskService()

        score, factors = service.calculate_transaction_risk(
            avg_monthly_volume=50000,
            expected_monthly_volume=10000,  # 5x expected
            cash_transaction_ratio=0.0,
            high_risk_jurisdiction_ratio=0.0,
        )

        assert score >= 30
        assert any("volume" in f.lower() for f in factors)

    def test_calculate_transaction_risk_high_cash(self):
        """Test transaction risk with high cash ratio."""
        service = RiskService()

        score, factors = service.calculate_transaction_risk(
            avg_monthly_volume=10000,
            expected_monthly_volume=10000,
            cash_transaction_ratio=0.6,  # 60% cash
            high_risk_jurisdiction_ratio=0.0,
        )

        assert score >= 20
        assert any("cash" in f.lower() for f in factors)

    def test_calculate_transaction_risk_structuring(self):
        """Test transaction risk with structuring indicators."""
        service = RiskService()

        score, factors = service.calculate_transaction_risk(
            avg_monthly_volume=10000,
            expected_monthly_volume=10000,
            cash_transaction_ratio=0.0,
            high_risk_jurisdiction_ratio=0.0,
            structuring_indicators=5,
        )

        assert score >= 30
        assert any("structuring" in f.lower() for f in factors)

    def test_calculate_network_risk_clean(self):
        """Test network risk with no risky connections."""
        service = RiskService()

        score, factors = service.calculate_network_risk(
            high_risk_connections=0,
            pep_connections=0,
            sanctioned_connections=0,
            total_connections=10,
        )

        assert score < 30

    def test_calculate_network_risk_sanctioned(self):
        """Test network risk with sanctioned connections."""
        service = RiskService()

        score, factors = service.calculate_network_risk(
            high_risk_connections=0,
            pep_connections=0,
            sanctioned_connections=1,
            total_connections=10,
        )

        assert score >= 80
        assert any("sanctioned" in f.lower() for f in factors)

    def test_calculate_network_risk_pep(self):
        """Test network risk with PEP connections."""
        service = RiskService()

        score, factors = service.calculate_network_risk(
            high_risk_connections=0,
            pep_connections=3,
            sanctioned_connections=0,
            total_connections=10,
        )

        assert score >= 30
        assert any("pep" in f.lower() for f in factors)

    def test_calculate_network_risk_shell_companies(self):
        """Test network risk with shell company connections."""
        service = RiskService()

        score, factors = service.calculate_network_risk(
            high_risk_connections=0,
            pep_connections=0,
            sanctioned_connections=0,
            shell_company_connections=3,
            total_connections=10,
        )

        assert score >= 40
        assert any("shell" in f.lower() for f in factors)

    def test_assess_customer_risk_overall(self):
        """Test comprehensive customer risk assessment."""
        service = RiskService()

        assessment = service.assess_customer_risk(
            customer_id="CUST-001",
            customer_type="corporate",
            jurisdiction="US",
            industry="technology",
        )

        assert assessment.customer_id == "CUST-001"
        assert assessment.risk_score >= 0
        assert assessment.risk_score <= 100
        assert assessment.overall_risk in [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        assert assessment.assessment_date is not None

    def test_assess_customer_risk_high_risk_profile(self):
        """Test risk assessment for high-risk customer profile."""
        service = RiskService()

        assessment = service.assess_customer_risk(
            customer_id="CUST-002",
            customer_type="trust",
            jurisdiction="BVI",
            industry="cryptocurrency",
            network_data={
                "high_risk_count": 5,
                "pep_count": 2,
                "sanctioned_count": 0,
                "shell_company_count": 1,
                "total_connections": 10,
            },
        )

        # High-risk profile should have elevated score
        assert assessment.risk_score >= 40
        assert assessment.overall_risk in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]

    def test_risk_recommendations_generated(self):
        """Test that risk recommendations are generated."""
        service = RiskService()

        assessment = service.assess_customer_risk(
            customer_id="CUST-001",
            customer_type="corporate",
            jurisdiction="US",
        )

        assert isinstance(assessment.recommendations, list)
        assert len(assessment.recommendations) > 0

    def test_risk_recommendations_for_high_risk(self):
        """Test recommendations for high-risk customer."""
        service = RiskService()

        assessment = service.assess_customer_risk(
            customer_id="CUST-002",
            customer_type="corporate",
            jurisdiction="KP",  # Sanctioned country
        )

        # Should recommend EDD for high-risk
        assert any(
            "due diligence" in r.lower() or "edd" in r.lower() for r in assessment.recommendations
        )

    def test_get_risk_service_singleton(self):
        """Test that get_risk_service returns singleton."""
        service1 = get_risk_service()
        service2 = get_risk_service()

        assert service1 is service2


class TestMemoryService:
    """Tests for the Neo4j Agent Memory service."""

    @pytest.mark.asyncio
    async def test_add_customer_to_graph(self, mock_memory_service):
        """Test adding a customer to the Context Graph."""
        entity_id = await mock_memory_service.add_customer(
            customer_id="CUST-001",
            name="Test Corp",
            customer_type="corporate",
            jurisdiction="US",
            risk_level="medium",
        )

        assert entity_id is not None
        mock_memory_service.add_customer.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_network(self, mock_memory_service):
        """Test retrieving customer network."""
        network = await mock_memory_service.get_customer_network(
            customer_id="CUST-001",
            depth=2,
        )

        assert "nodes" in network
        mock_memory_service.get_customer_network.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_entities(self, mock_memory_service):
        """Test entity search."""
        mock_memory_service.search_entities.return_value = [
            {"name": "Test Corp", "type": "organization", "score": 0.95}
        ]

        results = await mock_memory_service.search_entities(
            query="technology companies",
            entity_types=["organization"],
            limit=10,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_start_investigation_trace(self, mock_memory_service):
        """Test starting an investigation reasoning trace."""
        await mock_memory_service.start_investigation_trace(
            session_id="sess-001",
            investigation_id="INV-001",
            task="Investigate customer for suspicious activity",
        )

        mock_memory_service.start_investigation_trace.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_reasoning_step(self, mock_memory_service):
        """Test adding a reasoning step to the trace."""
        await mock_memory_service.add_reasoning_step(
            session_id="sess-001",
            step_type="analysis",
            content="Analyzed transaction patterns - no anomalies found",
            metadata={"agent": "aml_agent"},
        )

        mock_memory_service.add_reasoning_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_cleanup(self, mock_memory_service):
        """Test service cleanup on shutdown."""
        await mock_memory_service.close()

        mock_memory_service.close.assert_called_once()


class TestRiskLevelThresholds:
    """Tests for risk level threshold determination."""

    def test_low_risk_score(self):
        """Test low risk level for low score."""
        service = RiskService()

        # Score below 25 should be low risk
        assessment = service.assess_customer_risk(
            customer_id="CUST-LOW",
            customer_type="individual",
            jurisdiction="US",
        )

        # Low-risk profile
        if assessment.risk_score < 25:
            assert assessment.overall_risk == RiskLevel.LOW

    def test_critical_risk_for_sanctioned_jurisdiction(self):
        """Test critical risk for sanctioned jurisdiction."""
        service = RiskService()

        assessment = service.assess_customer_risk(
            customer_id="CUST-CRITICAL",
            customer_type="corporate",
            jurisdiction="KP",  # North Korea - sanctioned
            network_data={
                "sanctioned_count": 1,
                "total_connections": 5,
            },
        )

        # Should be high or critical risk
        assert assessment.overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert assessment.risk_score >= 50


class TestRiskServiceWeights:
    """Tests for risk component weighting."""

    def test_weights_sum_to_one(self):
        """Test that risk weights sum to 1.0."""
        service = RiskService()

        total_weight = sum(service.weights.values())

        assert abs(total_weight - 1.0) < 0.001

    def test_all_components_have_weights(self):
        """Test that all risk components have weights."""
        service = RiskService()

        expected_components = ["geographic", "customer_type", "transaction", "network"]

        for component in expected_components:
            assert component in service.weights
            assert service.weights[component] > 0
