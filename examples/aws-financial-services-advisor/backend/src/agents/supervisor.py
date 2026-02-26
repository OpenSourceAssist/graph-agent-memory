"""Supervisor Agent for orchestrating financial compliance investigations."""

from __future__ import annotations

import logging
from typing import Any

from neo4j_agent_memory.integrations.strands import StrandsConfig, context_graph_tools
from strands import Agent, tool
from strands.models import BedrockModel

from ..config import get_settings
from .prompts import SUPERVISOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Global agent instance
_supervisor_agent: Agent | None = None


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
        task: Specific KYC task to perform (e.g., "verify identity", "check documents")
        context: Additional context for the task

    Returns:
        KYC agent findings including verification status and risk factors
    """
    from .kyc_agent import get_kyc_agent

    logger.info(f"Delegating KYC task for customer {customer_id}: {task}")

    kyc_agent = get_kyc_agent()

    prompt = f"""Perform the following KYC task for customer {customer_id}:

Task: {task}

{"Context: " + context if context else ""}

Provide a structured assessment including:
1. Verification steps taken
2. Findings and any discrepancies
3. Risk factors identified
4. Confidence score
5. Recommendations
"""

    result = kyc_agent(prompt)

    return {
        "agent": "kyc",
        "customer_id": customer_id,
        "task": task,
        "findings": str(result),
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

    Use this tool when you need to analyze transactions, detect suspicious patterns,
    or investigate potential money laundering activity.

    Args:
        customer_id: The customer identifier to investigate
        task: Specific AML task (e.g., "scan transactions", "detect patterns")
        time_period_days: Number of days of history to analyze
        context: Additional context for the task

    Returns:
        AML agent findings including patterns detected and risk assessment
    """
    from .aml_agent import get_aml_agent

    logger.info(f"Delegating AML task for customer {customer_id}: {task}")

    aml_agent = get_aml_agent()

    prompt = f"""Perform the following AML task for customer {customer_id}:

Task: {task}
Time Period: Last {time_period_days} days

{"Context: " + context if context else ""}

Provide a structured assessment including:
1. Transaction analysis summary
2. Patterns detected with confidence scores
3. Specific suspicious transactions
4. Risk rating
5. Recommended actions
"""

    result = aml_agent(prompt)

    return {
        "agent": "aml",
        "customer_id": customer_id,
        "task": task,
        "time_period_days": time_period_days,
        "findings": str(result),
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
        task: Specific task (e.g., "find connections", "trace ownership")
        depth: Network traversal depth (1-3 recommended)
        context: Additional context for the task

    Returns:
        Relationship agent findings including network analysis and risk assessment
    """
    from .relationship_agent import get_relationship_agent

    logger.info(f"Delegating relationship task for customer {customer_id}: {task}")

    relationship_agent = get_relationship_agent()

    prompt = f"""Perform the following relationship analysis for customer {customer_id}:

Task: {task}
Network Depth: {depth} hops

{"Context: " + context if context else ""}

Provide a structured assessment including:
1. Network structure summary
2. Key relationships of concern
3. Beneficial ownership chain (if applicable)
4. Network risk score
5. Areas requiring further investigation
"""

    result = relationship_agent(prompt)

    return {
        "agent": "relationship",
        "customer_id": customer_id,
        "task": task,
        "depth": depth,
        "findings": str(result),
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
        task: Specific compliance task (e.g., "sanctions screen", "generate SAR")
        report_type: Type of report to generate if applicable
        context: Additional context for the task

    Returns:
        Compliance agent findings including screening results and recommendations
    """
    from .compliance_agent import get_compliance_agent

    logger.info(f"Delegating compliance task for customer {customer_id}: {task}")

    compliance_agent = get_compliance_agent()

    prompt = f"""Perform the following compliance task for customer {customer_id}:

Task: {task}
{"Report Type: " + report_type if report_type else ""}

{"Context: " + context if context else ""}

Provide a structured assessment including:
1. Screening results
2. Match details (if any)
3. Regulatory implications
4. Required actions
5. Report status (if generating)
"""

    result = compliance_agent(prompt)

    return {
        "agent": "compliance",
        "customer_id": customer_id,
        "task": task,
        "report_type": report_type,
        "findings": str(result),
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

    Use this tool after gathering findings from specialized agents to create
    a unified assessment with recommendations.

    Args:
        customer_id: The customer under investigation
        kyc_findings: Findings from KYC agent
        aml_findings: Findings from AML agent
        relationship_findings: Findings from Relationship agent
        compliance_findings: Findings from Compliance agent

    Returns:
        Comprehensive investigation summary with risk assessment and recommendations
    """
    findings_parts = []

    if kyc_findings:
        findings_parts.append(f"## KYC Findings\n{kyc_findings}")
    if aml_findings:
        findings_parts.append(f"## AML Findings\n{aml_findings}")
    if relationship_findings:
        findings_parts.append(f"## Relationship Analysis\n{relationship_findings}")
    if compliance_findings:
        findings_parts.append(f"## Compliance Findings\n{compliance_findings}")

    combined = "\n\n".join(findings_parts)

    # Determine overall risk level based on findings
    risk_indicators = []
    if "critical" in combined.lower() or "sanctions" in combined.lower():
        risk_indicators.append("critical")
    if "high" in combined.lower() or "suspicious" in combined.lower():
        risk_indicators.append("high")
    if "pep" in combined.lower():
        risk_indicators.append("pep_exposure")

    if "critical" in risk_indicators:
        overall_risk = "CRITICAL"
        urgency = "IMMEDIATE ACTION REQUIRED"
    elif "high" in risk_indicators:
        overall_risk = "HIGH"
        urgency = "Priority review required"
    else:
        overall_risk = "MEDIUM"
        urgency = "Standard review timeline"

    return {
        "customer_id": customer_id,
        "overall_risk": overall_risk,
        "urgency": urgency,
        "summary": combined,
        "risk_indicators": risk_indicators,
        "agents_consulted": [
            "kyc" if kyc_findings else None,
            "aml" if aml_findings else None,
            "relationship" if relationship_findings else None,
            "compliance" if compliance_findings else None,
        ],
        "status": "synthesized",
    }


def create_supervisor_agent() -> Agent:
    """Create the Supervisor Agent that orchestrates investigations.

    Returns:
        Configured Strands Agent for supervision
    """
    settings = get_settings()

    # Load Context Graph tools from neo4j-agent-memory
    config = StrandsConfig.from_env()
    memory_tools = context_graph_tools(**config.to_dict())

    # Delegation and synthesis tools
    delegation_tools = [
        delegate_to_kyc_agent,
        delegate_to_aml_agent,
        delegate_to_relationship_agent,
        delegate_to_compliance_agent,
        summarize_investigation,
    ]

    # Combine all tools
    all_tools = memory_tools + delegation_tools

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock.model_id,
            region_name=settings.aws.region,
        ),
        tools=all_tools,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
    )


def get_supervisor_agent() -> Agent:
    """Get or create the global Supervisor Agent instance.

    Returns:
        Supervisor Agent instance
    """
    global _supervisor_agent
    if _supervisor_agent is None:
        _supervisor_agent = create_supervisor_agent()
    return _supervisor_agent
