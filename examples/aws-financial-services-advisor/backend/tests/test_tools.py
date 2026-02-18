"""Tests for custom Strands tool functions."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.models.customer import RiskLevel


class TestKYCTools:
    """Tests for KYC-related tools."""

    def test_verify_identity_valid_document(self):
        """Test identity verification with valid document."""
        from src.agents.kyc_agent import verify_identity

        # The tool returns a mock verification result
        result = verify_identity(
            customer_id="CUST-001",
            document_type="passport",
        )

        assert result["status"] == "verified"
        assert "confidence_score" in result
        assert result["confidence_score"] >= 0.0
        assert result["confidence_score"] <= 1.0
        assert "document_type" in result
        assert result["document_type"] == "passport"

    def test_verify_identity_invalid_document_type(self):
        """Test identity verification with unusual document type."""
        from src.agents.kyc_agent import verify_identity

        result = verify_identity(
            customer_id="CUST-001",
            document_type="unknown_doc",
        )

        # Should still return a result, possibly with lower confidence
        assert "status" in result

    def test_check_documents_completeness(self):
        """Test document completeness check."""
        from src.agents.kyc_agent import check_documents

        result = check_documents(
            customer_id="CUST-001",
            document_types=["passport", "proof_of_address", "bank_statement"],
        )

        assert "completeness" in result
        assert "missing_documents" in result
        assert "documents_verified" in result
        assert isinstance(result["documents_verified"], list)

    def test_assess_customer_risk_basic(self):
        """Test basic customer risk assessment."""
        from src.agents.kyc_agent import assess_customer_risk

        result = assess_customer_risk(
            customer_id="CUST-001",
            include_network_analysis=False,
        )

        assert "risk_score" in result
        assert "risk_level" in result
        assert "factors" in result
        assert isinstance(result["factors"], list)
        assert result["risk_score"] >= 0.0
        assert result["risk_score"] <= 1.0

    def test_assess_customer_risk_with_network(self):
        """Test customer risk assessment with network analysis."""
        from src.agents.kyc_agent import assess_customer_risk

        result = assess_customer_risk(
            customer_id="CUST-001",
            include_network_analysis=True,
        )

        assert "risk_score" in result
        assert "network_risk" in result or "factors" in result

    def test_check_adverse_media(self):
        """Test adverse media screening."""
        from src.agents.kyc_agent import check_adverse_media

        result = check_adverse_media(
            entity_name="Acme Corporation",
            entity_type="organization",
        )

        assert "hits" in result
        assert "risk_indicators" in result
        assert isinstance(result["hits"], list)


class TestAMLTools:
    """Tests for AML-related tools."""

    def test_scan_transactions_by_account(self):
        """Test transaction scanning by account."""
        from src.agents.aml_agent import scan_transactions

        result = scan_transactions(
            account_id="ACC-001",
            lookback_days=30,
        )

        assert "transactions_analyzed" in result
        assert "suspicious_count" in result
        assert "alerts" in result
        assert isinstance(result["alerts"], list)

    def test_scan_transactions_by_customer(self):
        """Test transaction scanning by customer."""
        from src.agents.aml_agent import scan_transactions

        result = scan_transactions(
            customer_id="CUST-001",
            lookback_days=90,
        )

        assert "transactions_analyzed" in result

    def test_detect_patterns_structuring(self):
        """Test pattern detection for structuring."""
        from src.agents.aml_agent import detect_patterns

        result = detect_patterns(
            customer_id="CUST-001",
            pattern_types=["structuring", "layering"],
        )

        assert "patterns_detected" in result
        assert isinstance(result["patterns_detected"], list)
        for pattern in result["patterns_detected"]:
            assert "type" in pattern
            assert "confidence" in pattern

    def test_flag_suspicious_activity(self):
        """Test flagging suspicious activity."""
        from src.agents.aml_agent import flag_suspicious

        result = flag_suspicious(
            transaction_id="TXN-001",
            reason="Large wire transfer to high-risk jurisdiction",
            severity="high",
        )

        assert "alert_id" in result
        assert "status" in result
        assert result["status"] == "flagged"

    def test_analyze_velocity(self):
        """Test transaction velocity analysis."""
        from src.agents.aml_agent import analyze_velocity

        result = analyze_velocity(
            account_id="ACC-001",
            time_window_hours=24,
        )

        assert "transaction_count" in result
        assert "total_volume" in result
        assert "velocity_score" in result
        assert "anomalies" in result


class TestComplianceTools:
    """Tests for compliance-related tools."""

    def test_check_sanctions_clean(self):
        """Test sanctions check for clean entity."""
        from src.agents.compliance_agent import check_sanctions

        result = check_sanctions(
            entity_name="Acme Corporation",
            entity_type="organization",
            jurisdictions=["US", "EU"],
        )

        assert "matched" in result
        assert "lists_checked" in result
        assert isinstance(result["lists_checked"], list)

    def test_check_sanctions_with_match(self):
        """Test sanctions check behavior (may or may not match)."""
        from src.agents.compliance_agent import check_sanctions

        result = check_sanctions(
            entity_name="Test Sanctioned Entity",
            entity_type="organization",
        )

        assert "matched" in result
        assert isinstance(result["matched"], bool)

    def test_verify_pep_status(self):
        """Test PEP (Politically Exposed Person) verification."""
        from src.agents.compliance_agent import verify_pep

        result = verify_pep(
            person_name="John Smith",
            country="US",
        )

        assert "is_pep" in result
        assert "pep_level" in result
        assert "associations" in result

    def test_generate_compliance_report(self):
        """Test compliance report generation."""
        from src.agents.compliance_agent import generate_report

        result = generate_report(
            customer_id="CUST-001",
            report_type="kyc_review",
            include_recommendations=True,
        )

        assert "report_id" in result
        assert "summary" in result
        assert "findings" in result
        assert "recommendations" in result

    def test_assess_regulatory_requirements(self):
        """Test regulatory requirements assessment."""
        from src.agents.compliance_agent import assess_regulatory_requirements

        result = assess_regulatory_requirements(
            customer_id="CUST-001",
            jurisdictions=["US", "EU"],
        )

        assert "requirements" in result
        assert isinstance(result["requirements"], list)
        assert "compliance_gaps" in result


class TestRelationshipTools:
    """Tests for relationship analysis tools."""

    def test_find_connections_basic(self):
        """Test finding entity connections."""
        from src.agents.relationship_agent import find_connections

        result = find_connections(
            entity_name="Acme Corporation",
            entity_type="organization",
            max_depth=2,
        )

        assert "connections" in result
        assert isinstance(result["connections"], list)
        assert "total_found" in result

    def test_analyze_network_risk(self):
        """Test network risk analysis."""
        from src.agents.relationship_agent import analyze_network_risk

        result = analyze_network_risk(
            customer_id="CUST-001",
            depth=2,
        )

        assert "network_risk_score" in result
        assert "high_risk_connections" in result
        assert "risk_factors" in result

    def test_detect_shell_companies(self):
        """Test shell company detection."""
        from src.agents.relationship_agent import detect_shell_companies

        result = detect_shell_companies(
            customer_id="CUST-001",
            threshold=0.7,
        )

        assert "potential_shells" in result
        assert isinstance(result["potential_shells"], list)
        assert "analysis_summary" in result

    def test_map_beneficial_ownership(self):
        """Test beneficial ownership mapping."""
        from src.agents.relationship_agent import map_beneficial_ownership

        result = map_beneficial_ownership(
            organization_name="Acme Corporation",
            include_indirect=True,
        )

        assert "beneficial_owners" in result
        assert isinstance(result["beneficial_owners"], list)
        assert "ownership_structure" in result


class TestSupervisorTools:
    """Tests for supervisor delegation tools."""

    def test_delegate_to_kyc_agent(self):
        """Test delegation to KYC agent."""
        from src.agents.supervisor import delegate_to_kyc_agent

        result = delegate_to_kyc_agent(
            customer_id="CUST-001",
            task="Verify customer identity and documents",
            context="New customer onboarding",
        )

        assert "status" in result
        assert "agent" in result
        assert result["agent"] == "kyc_agent"

    def test_delegate_to_aml_agent(self):
        """Test delegation to AML agent."""
        from src.agents.supervisor import delegate_to_aml_agent

        result = delegate_to_aml_agent(
            customer_id="CUST-001",
            task="Scan recent transactions for suspicious patterns",
        )

        assert "status" in result
        assert "agent" in result
        assert result["agent"] == "aml_agent"

    def test_delegate_to_relationship_agent(self):
        """Test delegation to relationship agent."""
        from src.agents.supervisor import delegate_to_relationship_agent

        result = delegate_to_relationship_agent(
            entity_name="Acme Corporation",
            task="Analyze network connections",
        )

        assert "status" in result
        assert "agent" in result
        assert result["agent"] == "relationship_agent"

    def test_delegate_to_compliance_agent(self):
        """Test delegation to compliance agent."""
        from src.agents.supervisor import delegate_to_compliance_agent

        result = delegate_to_compliance_agent(
            customer_id="CUST-001",
            task="Generate compliance report",
        )

        assert "status" in result
        assert "agent" in result
        assert result["agent"] == "compliance_agent"

    def test_summarize_investigation(self):
        """Test investigation summarization."""
        from src.agents.supervisor import summarize_investigation

        findings = [
            {"source": "kyc", "result": "Identity verified"},
            {"source": "aml", "result": "No suspicious patterns"},
            {"source": "compliance", "result": "All requirements met"},
        ]

        result = summarize_investigation(
            investigation_id="INV-001",
            findings=findings,
        )

        assert "summary" in result
        assert "risk_assessment" in result
        assert "recommendations" in result
