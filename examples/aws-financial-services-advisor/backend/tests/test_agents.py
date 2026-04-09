"""Tests for bind_tool utility and agent wiring."""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.tools import bind_tool


class TestBindTool:
    """Test the bind_tool utility that hides neo4j_service from LLM signatures."""

    def test_bind_tool_removes_neo4j_service_from_signature(self):
        async def my_tool(customer_id: str, *, neo4j_service) -> dict:
            return {"id": customer_id}

        bound = bind_tool(my_tool, neo4j_service=MagicMock())
        sig = inspect.signature(bound)
        param_names = list(sig.parameters.keys())
        assert "customer_id" in param_names
        assert "neo4j_service" not in param_names

    def test_bind_tool_preserves_function_name(self):
        async def verify_identity(customer_id: str, *, neo4j_service) -> dict:
            return {}

        bound = bind_tool(verify_identity, neo4j_service=MagicMock())
        assert bound.__name__ == "verify_identity"

    def test_bind_tool_preserves_docstring(self):
        async def verify_identity(customer_id: str, *, neo4j_service) -> dict:
            """Verify customer identity."""
            return {}

        bound = bind_tool(verify_identity, neo4j_service=MagicMock())
        assert "Verify customer identity" in bound.__doc__

    @pytest.mark.asyncio
    async def test_bind_tool_injects_neo4j_service(self):
        captured = {}

        async def my_tool(customer_id: str, *, neo4j_service) -> dict:
            captured["neo4j_service"] = neo4j_service
            return {"id": customer_id}

        mock_svc = MagicMock()
        bound = bind_tool(my_tool, neo4j_service=mock_svc)
        result = await bound("CUST-001")
        assert captured["neo4j_service"] is mock_svc
        assert result["id"] == "CUST-001"

    @pytest.mark.asyncio
    async def test_bind_tool_with_multiple_params(self):
        async def my_tool(customer_id: str, days: int = 90, *, neo4j_service) -> dict:
            return {"id": customer_id, "days": days}

        bound = bind_tool(my_tool, neo4j_service=MagicMock())
        sig = inspect.signature(bound)

        # Should have customer_id and days, but not neo4j_service
        param_names = list(sig.parameters.keys())
        assert param_names == ["customer_id", "days"]

        result = await bound("CUST-001", days=30)
        assert result["days"] == 30

    def test_bind_tool_signature_has_correct_defaults(self):
        async def my_tool(customer_id: str, days: int = 90, *, neo4j_service) -> dict:
            return {}

        bound = bind_tool(my_tool, neo4j_service=MagicMock())
        sig = inspect.signature(bound)
        assert sig.parameters["days"].default == 90


class TestAgentWiring:
    """Test supervisor agent creation and configuration."""

    def test_reset_supervisor_agent(self):
        from src.agents.supervisor import _supervisor_agent, reset_supervisor_agent

        reset_supervisor_agent()
        from src.agents.supervisor import _supervisor_agent as agent_after

        assert agent_after is None

    def test_supervisor_prompt_contains_key_terms(self):
        from src.agents.prompts import SUPERVISOR_SYSTEM_PROMPT

        prompt_lower = SUPERVISOR_SYSTEM_PROMPT.lower()
        assert any(term in prompt_lower for term in ["financial", "compliance", "delegate", "supervisor", "agent"])

    def test_kyc_prompt_exists(self):
        from src.agents.prompts import KYC_AGENT_SYSTEM_PROMPT

        assert len(KYC_AGENT_SYSTEM_PROMPT) > 50

    def test_aml_prompt_exists(self):
        from src.agents.prompts import AML_AGENT_SYSTEM_PROMPT

        assert len(AML_AGENT_SYSTEM_PROMPT) > 50

    def test_relationship_prompt_exists(self):
        from src.agents.prompts import RELATIONSHIP_AGENT_SYSTEM_PROMPT

        assert len(RELATIONSHIP_AGENT_SYSTEM_PROMPT) > 50

    def test_compliance_prompt_exists(self):
        from src.agents.prompts import COMPLIANCE_AGENT_SYSTEM_PROMPT

        assert len(COMPLIANCE_AGENT_SYSTEM_PROMPT) > 50
