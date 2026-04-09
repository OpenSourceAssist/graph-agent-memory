"""Supervisor Agent for orchestrating financial compliance investigations.

Uses AWS Strands Agents with Neo4j-backed tools via the bind_tool pattern.
The supervisor delegates to specialized sub-agents (KYC, AML, Relationship,
Compliance) which all query real data from Neo4j.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from ..config import get_settings
from ..services.neo4j_service import Neo4jDomainService
from ..tools import bind_tool
from ..tools.aml_tools import analyze_velocity, detect_patterns, flag_suspicious_transaction, scan_transactions
from ..tools.compliance_tools import (
    assess_regulatory_requirements,
    check_sanctions,
    generate_sar_report,
    verify_pep_status,
)
from ..tools.kyc_tools import assess_customer_risk, check_adverse_media, check_documents, verify_identity
from ..tools.relationship_tools import (
    analyze_network_risk,
    detect_shell_companies,
    find_connections,
    map_beneficial_ownership,
)
from .prompts import SUPERVISOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Global agent instance
_supervisor_agent: Agent | None = None


def _truncate(value: Any, max_len: int = 500) -> str:
    """Truncate a value to a string for logging/SSE."""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, default=str)
    else:
        text = str(value)
    return text[:max_len] + "..." if len(text) > max_len else text


def _create_sub_agent(
    name: str,
    system_prompt: str,
    tools: list,
    settings=None,
) -> Agent:
    """Create a sub-agent with Bedrock model."""
    if settings is None:
        settings = get_settings()
    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock.model_id,
            region_name=settings.aws.region,
        ),
        tools=tools,
        system_prompt=system_prompt,
    )


def create_supervisor_agent(neo4j_service: Neo4jDomainService) -> Agent:
    """Create the Supervisor Agent that orchestrates investigations.

    Args:
        neo4j_service: Neo4jDomainService for domain data queries

    Returns:
        Configured Strands Agent for supervision
    """
    settings = get_settings()

    # Import sub-agent prompts
    from .prompts import (
        AML_AGENT_SYSTEM_PROMPT as AML_SYSTEM_PROMPT,
        COMPLIANCE_AGENT_SYSTEM_PROMPT as COMPLIANCE_SYSTEM_PROMPT,
        KYC_AGENT_SYSTEM_PROMPT as KYC_SYSTEM_PROMPT,
        RELATIONSHIP_AGENT_SYSTEM_PROMPT as RELATIONSHIP_SYSTEM_PROMPT,
    )

    # Create bound tools for each sub-agent
    kyc_tools = [
        bind_tool(verify_identity, neo4j_service),
        bind_tool(check_documents, neo4j_service),
        bind_tool(assess_customer_risk, neo4j_service),
        bind_tool(check_adverse_media, neo4j_service),
    ]

    aml_tools = [
        bind_tool(scan_transactions, neo4j_service),
        bind_tool(detect_patterns, neo4j_service),
        bind_tool(flag_suspicious_transaction, neo4j_service),
        bind_tool(analyze_velocity, neo4j_service),
    ]

    relationship_tools = [
        bind_tool(find_connections, neo4j_service),
        bind_tool(analyze_network_risk, neo4j_service),
        bind_tool(detect_shell_companies, neo4j_service),
        bind_tool(map_beneficial_ownership, neo4j_service),
    ]

    compliance_tools = [
        bind_tool(check_sanctions, neo4j_service),
        bind_tool(verify_pep_status, neo4j_service),
        bind_tool(generate_sar_report, neo4j_service),
        bind_tool(assess_regulatory_requirements, neo4j_service),
    ]

    # Create sub-agents
    kyc_agent = _create_sub_agent("kyc", KYC_SYSTEM_PROMPT, kyc_tools, settings)
    aml_agent = _create_sub_agent("aml", AML_SYSTEM_PROMPT, aml_tools, settings)
    relationship_agent = _create_sub_agent(
        "relationship", RELATIONSHIP_SYSTEM_PROMPT, relationship_tools, settings
    )
    compliance_agent = _create_sub_agent(
        "compliance", COMPLIANCE_SYSTEM_PROMPT, compliance_tools, settings
    )

    # Delegation tools for the supervisor
    @tool
    def delegate_to_kyc_agent(
        customer_id: str,
        task: str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Delegate a KYC task to the KYC Agent.

        Use this tool when you need to verify customer identity, check documents,
        or perform customer due diligence.

        Args:
            customer_id: The customer identifier to investigate
            task: Specific KYC task to perform
            context: Additional context for the task
        """
        prompt = f"Perform KYC task for customer {customer_id}: {task}"
        if context:
            prompt += f"\nContext: {context}"
        result = kyc_agent(prompt)
        return {
            "agent": "kyc",
            "customer_id": customer_id,
            "task": task,
            "findings": _truncate(str(result), 2000),
            "status": "completed",
        }

    @tool
    def delegate_to_aml_agent(
        customer_id: str,
        task: str,
        time_period_days: int = 90,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Delegate an AML task to the AML Agent.

        Use this tool when you need to analyze transactions, detect suspicious
        patterns, or investigate potential money laundering activity.

        Args:
            customer_id: The customer identifier to investigate
            task: Specific AML task to perform
            time_period_days: Number of days of history to analyze
            context: Additional context for the task
        """
        prompt = f"Perform AML task for customer {customer_id}: {task}. Time period: last {time_period_days} days."
        if context:
            prompt += f"\nContext: {context}"
        result = aml_agent(prompt)
        return {
            "agent": "aml",
            "customer_id": customer_id,
            "task": task,
            "findings": _truncate(str(result), 2000),
            "status": "completed",
        }

    @tool
    def delegate_to_relationship_agent(
        customer_id: str,
        task: str,
        depth: int = 2,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Delegate a relationship analysis task to the Relationship Agent.

        Use this tool when you need to analyze customer networks, find connections,
        or trace beneficial ownership.

        Args:
            customer_id: The customer identifier to investigate
            task: Specific relationship task to perform
            depth: Network traversal depth (1-3)
            context: Additional context for the task
        """
        prompt = f"Analyze relationships for {customer_id}: {task}. Network depth: {depth} hops."
        if context:
            prompt += f"\nContext: {context}"
        result = relationship_agent(prompt)
        return {
            "agent": "relationship",
            "customer_id": customer_id,
            "task": task,
            "findings": _truncate(str(result), 2000),
            "status": "completed",
        }

    @tool
    def delegate_to_compliance_agent(
        customer_id: str,
        task: str,
        report_type: str | None = None,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Delegate a compliance task to the Compliance Agent.

        Use this tool for sanctions screening, PEP checks, or report generation.

        Args:
            customer_id: The customer identifier to check
            task: Specific compliance task to perform
            report_type: Type of report to generate if applicable
            context: Additional context for the task
        """
        prompt = f"Perform compliance task for customer {customer_id}: {task}."
        if report_type:
            prompt += f" Report type: {report_type}."
        if context:
            prompt += f"\nContext: {context}"
        result = compliance_agent(prompt)
        return {
            "agent": "compliance",
            "customer_id": customer_id,
            "task": task,
            "findings": _truncate(str(result), 2000),
            "status": "completed",
        }

    @tool
    def summarize_investigation(
        customer_id: str,
        kyc_findings: str | None = None,
        aml_findings: str | None = None,
        relationship_findings: str | None = None,
        compliance_findings: str | None = None,
    ) -> dict[str, Any]:
        """Synthesize findings from all agents into a comprehensive investigation summary.

        Args:
            customer_id: The customer under investigation
            kyc_findings: Findings from KYC agent
            aml_findings: Findings from AML agent
            relationship_findings: Findings from Relationship agent
            compliance_findings: Findings from Compliance agent
        """
        combined = ""
        if kyc_findings:
            combined += f"## KYC Findings\n{kyc_findings}\n\n"
        if aml_findings:
            combined += f"## AML Findings\n{aml_findings}\n\n"
        if relationship_findings:
            combined += f"## Relationship Analysis\n{relationship_findings}\n\n"
        if compliance_findings:
            combined += f"## Compliance Findings\n{compliance_findings}\n\n"

        lower = combined.lower()
        if "critical" in lower or "sanctions" in lower:
            overall_risk = "CRITICAL"
        elif "high" in lower or "suspicious" in lower:
            overall_risk = "HIGH"
        else:
            overall_risk = "MEDIUM"

        return {
            "customer_id": customer_id,
            "overall_risk": overall_risk,
            "summary": combined,
            "agents_consulted": [
                name
                for name, f in [
                    ("kyc", kyc_findings),
                    ("aml", aml_findings),
                    ("relationship", relationship_findings),
                    ("compliance", compliance_findings),
                ]
                if f
            ],
            "status": "synthesized",
        }

    # Combine all tools
    all_tools = [
        delegate_to_kyc_agent,
        delegate_to_aml_agent,
        delegate_to_relationship_agent,
        delegate_to_compliance_agent,
        summarize_investigation,
    ]

    # Optionally add context graph memory tools
    try:
        from neo4j_agent_memory.integrations.strands import StrandsConfig, context_graph_tools

        config = StrandsConfig.from_env()
        memory_tools = context_graph_tools(**config.to_dict())
        all_tools.extend(memory_tools)
    except Exception as e:
        logger.warning(f"Could not load context graph tools: {e}")

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock.model_id,
            region_name=settings.aws.region,
        ),
        tools=all_tools,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
    )


def get_supervisor_agent(neo4j_service: Neo4jDomainService) -> Agent:
    """Get or create the global Supervisor Agent instance."""
    global _supervisor_agent
    if _supervisor_agent is None:
        _supervisor_agent = create_supervisor_agent(neo4j_service)
    return _supervisor_agent


def reset_supervisor_agent() -> None:
    """Reset the global supervisor agent (for lifespan cleanup)."""
    global _supervisor_agent
    _supervisor_agent = None
