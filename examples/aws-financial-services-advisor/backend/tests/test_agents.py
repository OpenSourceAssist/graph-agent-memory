"""Tests for Strands Agent configurations and behaviors."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAgentPrompts:
    """Tests for agent system prompts."""

    def test_supervisor_prompt_contains_required_elements(self):
        """Test that supervisor prompt has required context."""
        from src.agents.prompts import SUPERVISOR_SYSTEM_PROMPT

        # Check for key elements in the prompt
        assert "financial" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "compliance" in SUPERVISOR_SYSTEM_PROMPT.lower()
        assert "delegate" in SUPERVISOR_SYSTEM_PROMPT.lower()

    def test_kyc_prompt_contains_required_elements(self):
        """Test that KYC agent prompt has required context."""
        from src.agents.prompts import KYC_AGENT_SYSTEM_PROMPT

        assert "kyc" in KYC_AGENT_SYSTEM_PROMPT.lower()
        assert (
            "identity" in KYC_AGENT_SYSTEM_PROMPT.lower()
            or "customer" in KYC_AGENT_SYSTEM_PROMPT.lower()
        )

    def test_aml_prompt_contains_required_elements(self):
        """Test that AML agent prompt has required context."""
        from src.agents.prompts import AML_AGENT_SYSTEM_PROMPT

        prompt_lower = AML_AGENT_SYSTEM_PROMPT.lower()
        assert (
            "aml" in prompt_lower
            or "anti-money" in prompt_lower
            or "transaction" in prompt_lower
        )

    def test_relationship_prompt_contains_required_elements(self):
        """Test that relationship agent prompt has required context."""
        from src.agents.prompts import RELATIONSHIP_AGENT_SYSTEM_PROMPT

        prompt_lower = RELATIONSHIP_AGENT_SYSTEM_PROMPT.lower()
        assert (
            "relationship" in prompt_lower
            or "network" in prompt_lower
            or "connection" in prompt_lower
        )

    def test_compliance_prompt_contains_required_elements(self):
        """Test that compliance agent prompt has required context."""
        from src.agents.prompts import COMPLIANCE_AGENT_SYSTEM_PROMPT

        prompt_lower = COMPLIANCE_AGENT_SYSTEM_PROMPT.lower()
        assert "compliance" in prompt_lower or "regulatory" in prompt_lower


class TestAgentCreation:
    """Tests for agent factory functions."""

    @patch("src.agents.supervisor.BedrockModel")
    @patch("src.agents.supervisor.context_graph_tools")
    def test_create_supervisor_agent(self, mock_tools, mock_model):
        """Test supervisor agent creation."""
        from src.agents.supervisor import create_supervisor_agent

        mock_tools.return_value = []
        mock_model.return_value = MagicMock()

        agent = create_supervisor_agent()

        assert agent is not None
        # Verify agent has tools configured
        assert hasattr(agent, "tools") or mock_tools.called

    @patch("src.agents.kyc_agent.BedrockModel")
    @patch("src.agents.kyc_agent.context_graph_tools")
    def test_create_kyc_agent(self, mock_tools, mock_model):
        """Test KYC agent creation."""
        from src.agents.kyc_agent import create_kyc_agent

        mock_tools.return_value = []
        mock_model.return_value = MagicMock()

        agent = create_kyc_agent()

        assert agent is not None

    @patch("src.agents.aml_agent.BedrockModel")
    @patch("src.agents.aml_agent.context_graph_tools")
    def test_create_aml_agent(self, mock_tools, mock_model):
        """Test AML agent creation."""
        from src.agents.aml_agent import create_aml_agent

        mock_tools.return_value = []
        mock_model.return_value = MagicMock()

        agent = create_aml_agent()

        assert agent is not None

    @patch("src.agents.relationship_agent.BedrockModel")
    @patch("src.agents.relationship_agent.context_graph_tools")
    def test_create_relationship_agent(self, mock_tools, mock_model):
        """Test relationship agent creation."""
        from src.agents.relationship_agent import create_relationship_agent

        mock_tools.return_value = []
        mock_model.return_value = MagicMock()

        agent = create_relationship_agent()

        assert agent is not None

    @patch("src.agents.compliance_agent.BedrockModel")
    @patch("src.agents.compliance_agent.context_graph_tools")
    def test_create_compliance_agent(self, mock_tools, mock_model):
        """Test compliance agent creation."""
        from src.agents.compliance_agent import create_compliance_agent

        mock_tools.return_value = []
        mock_model.return_value = MagicMock()

        agent = create_compliance_agent()

        assert agent is not None


class TestAgentToolConfiguration:
    """Tests for verifying agents have correct tools configured."""

    def test_kyc_agent_has_required_tools(self):
        """Test that KYC agent has all required tools."""
        from src.agents import kyc_agent

        # Check that the module has the expected tool functions
        required_tools = [
            "verify_identity",
            "check_documents",
            "assess_customer_risk",
            "check_adverse_media",
        ]

        for tool_name in required_tools:
            assert hasattr(kyc_agent, tool_name), f"KYC agent missing tool: {tool_name}"

    def test_aml_agent_has_required_tools(self):
        """Test that AML agent has all required tools."""
        from src.agents import aml_agent

        required_tools = [
            "scan_transactions",
            "detect_patterns",
            "flag_suspicious",
            "analyze_velocity",
        ]

        for tool_name in required_tools:
            assert hasattr(aml_agent, tool_name), f"AML agent missing tool: {tool_name}"

    def test_relationship_agent_has_required_tools(self):
        """Test that relationship agent has all required tools."""
        from src.agents import relationship_agent

        required_tools = [
            "find_connections",
            "analyze_network_risk",
            "detect_shell_companies",
            "map_beneficial_ownership",
        ]

        for tool_name in required_tools:
            assert hasattr(relationship_agent, tool_name), (
                f"Relationship agent missing tool: {tool_name}"
            )

    def test_compliance_agent_has_required_tools(self):
        """Test that compliance agent has all required tools."""
        from src.agents import compliance_agent

        required_tools = [
            "check_sanctions",
            "verify_pep",
            "generate_report",
            "assess_regulatory_requirements",
        ]

        for tool_name in required_tools:
            assert hasattr(compliance_agent, tool_name), (
                f"Compliance agent missing tool: {tool_name}"
            )

    def test_supervisor_has_delegation_tools(self):
        """Test that supervisor agent has delegation tools."""
        from src.agents import supervisor

        required_tools = [
            "delegate_to_kyc_agent",
            "delegate_to_aml_agent",
            "delegate_to_relationship_agent",
            "delegate_to_compliance_agent",
            "summarize_investigation",
        ]

        for tool_name in required_tools:
            assert hasattr(supervisor, tool_name), (
                f"Supervisor missing tool: {tool_name}"
            )


class TestAgentIntegration:
    """Integration tests for multi-agent workflows."""

    @pytest.mark.asyncio
    async def test_investigation_workflow_sequence(self):
        """Test that investigation workflow follows correct sequence."""
        # This test verifies the workflow logic without calling actual LLMs
        from src.agents.supervisor import (
            delegate_to_aml_agent,
            delegate_to_compliance_agent,
            delegate_to_kyc_agent,
            delegate_to_relationship_agent,
            summarize_investigation,
        )

        # Step 1: KYC
        kyc_result = delegate_to_kyc_agent(
            customer_id="CUST-001",
            task="Verify customer",
        )
        assert kyc_result["status"] in ["completed", "delegated", "pending"]

        # Step 2: AML
        aml_result = delegate_to_aml_agent(
            customer_id="CUST-001",
            task="Scan transactions",
        )
        assert aml_result["status"] in ["completed", "delegated", "pending"]

        # Step 3: Relationship
        rel_result = delegate_to_relationship_agent(
            entity_name="Test Corp",
            task="Analyze network",
        )
        assert rel_result["status"] in ["completed", "delegated", "pending"]

        # Step 4: Compliance
        comp_result = delegate_to_compliance_agent(
            customer_id="CUST-001",
            task="Generate report",
        )
        assert comp_result["status"] in ["completed", "delegated", "pending"]

        # Step 5: Summarize
        summary = summarize_investigation(
            investigation_id="INV-001",
            findings=[
                kyc_result,
                aml_result,
                rel_result,
                comp_result,
            ],
        )
        assert "summary" in summary
        assert "recommendations" in summary

    def test_tool_return_types_are_serializable(self):
        """Test that all tool return types can be JSON serialized."""
        import json

        from src.agents.aml_agent import detect_patterns, scan_transactions
        from src.agents.compliance_agent import check_sanctions, verify_pep
        from src.agents.kyc_agent import assess_customer_risk, verify_identity
        from src.agents.relationship_agent import analyze_network_risk, find_connections

        tools_to_test = [
            (verify_identity, {"customer_id": "CUST-001", "document_type": "passport"}),
            (
                assess_customer_risk,
                {"customer_id": "CUST-001", "include_network_analysis": False},
            ),
            (scan_transactions, {"account_id": "ACC-001", "lookback_days": 30}),
            (
                detect_patterns,
                {"customer_id": "CUST-001", "pattern_types": ["structuring"]},
            ),
            (
                check_sanctions,
                {"entity_name": "Test Corp", "entity_type": "organization"},
            ),
            (verify_pep, {"person_name": "John Smith", "country": "US"}),
            (
                find_connections,
                {
                    "entity_name": "Test Corp",
                    "entity_type": "organization",
                    "max_depth": 2,
                },
            ),
            (analyze_network_risk, {"customer_id": "CUST-001", "depth": 2}),
        ]

        for tool_func, kwargs in tools_to_test:
            result = tool_func(**kwargs)
            # Should not raise an exception
            serialized = json.dumps(result)
            # Should be able to deserialize back
            deserialized = json.loads(serialized)
            assert deserialized == result, (
                f"Tool {tool_func.__name__} result not serializable"
            )
