"""Supervisor Agent for orchestrating financial compliance investigations.

This agent coordinates multi-agent investigations by delegating tasks
to specialized agents (KYC, AML, Relationship, Compliance) and
synthesizing their findings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .aml_agent import create_aml_agent
from .compliance_agent import create_compliance_agent
from .kyc_agent import create_kyc_agent
from .prompts import SUPERVISOR_INSTRUCTION
from .relationship_agent import create_relationship_agent

if TYPE_CHECKING:
    from ..services.memory_service import FinancialMemoryService
    from ..services.neo4j_service import Neo4jDomainService

logger = logging.getLogger(__name__)

# Global supervisor instance
_supervisor_agent: LlmAgent | None = None
_memory_service: FinancialMemoryService | None = None
_neo4j_service: Neo4jDomainService | None = None


def create_supervisor_agent(
    memory_service: FinancialMemoryService | None = None,
    model: str = "gemini-2.5-flash",
    neo4j_service: Neo4jDomainService | None = None,
) -> LlmAgent:
    """Create the Supervisor Agent that orchestrates investigations.

    The supervisor uses Google ADK's sub_agents feature to delegate
    tasks to specialized agents for KYC, AML, relationship analysis,
    and compliance screening.

    Args:
        memory_service: Memory service for context graph access.
        model: The Gemini model to use.
        neo4j_service: Domain data service for Neo4j queries.

    Returns:
        Configured Supervisor Agent with sub-agents.
    """
    # Create specialized sub-agents, passing neo4j_service so their
    # tools can query domain data from Neo4j
    kyc_agent = create_kyc_agent(memory_service, model, neo4j_service=neo4j_service)
    aml_agent = create_aml_agent(memory_service, model, neo4j_service=neo4j_service)
    relationship_agent = create_relationship_agent(
        memory_service, model, neo4j_service=neo4j_service
    )
    compliance_agent = create_compliance_agent(memory_service, model, neo4j_service=neo4j_service)

    # Memory tools for the supervisor
    tools = []

    if memory_service:

        async def search_investigation_context(
            query: str,
            limit: int = 10,
        ) -> list[dict[str, Any]]:
            """Search the context graph for relevant investigation information.

            Use this to find prior investigations, known entities, or
            previously identified risks.

            Args:
                query: Search query for relevant context.
                limit: Maximum number of results.

            Returns:
                List of relevant memory entries.
            """
            return await memory_service.search_context(query, limit=limit)

        async def store_investigation_finding(
            content: str,
            customer_id: str | None = None,
            risk_level: str = "MEDIUM",
        ) -> str:
            """Store an investigation finding or conclusion.

            Use this to record important findings, risk assessments,
            or recommendations for the audit trail.

            Args:
                content: The finding to store.
                customer_id: Related customer ID.
                risk_level: Risk level (LOW/MEDIUM/HIGH/CRITICAL).

            Returns:
                Confirmation of storage.
            """
            return await memory_service.store_finding(
                content=content,
                category="investigation",
                metadata={
                    "customer_id": customer_id,
                    "risk_level": risk_level,
                    "source": "supervisor",
                },
            )

        async def get_conversation_history(
            session_id: str,
            limit: int = 20,
        ) -> list[dict[str, Any]]:
            """Get the conversation history for context.

            Args:
                session_id: The session identifier.
                limit: Maximum messages to retrieve.

            Returns:
                List of conversation messages.
            """
            entries = await memory_service.get_conversation_history(session_id, limit)
            return [{"content": e.content, "type": e.memory_type} for e in entries]

        tools.extend(
            [
                FunctionTool(search_investigation_context),
                FunctionTool(store_investigation_finding),
                FunctionTool(get_conversation_history),
            ]
        )

    # Create the supervisor with sub-agents
    supervisor = LlmAgent(
        name="financial_advisor_supervisor",
        model=model,
        description=(
            "Senior Financial Compliance Supervisor that orchestrates "
            "comprehensive investigations by coordinating KYC, AML, "
            "relationship analysis, and compliance screening."
        ),
        instruction=SUPERVISOR_INSTRUCTION,
        sub_agents=[kyc_agent, aml_agent, relationship_agent, compliance_agent],
        tools=tools,
    )

    logger.info("Supervisor Agent created with sub-agents")
    return supervisor


def get_supervisor_agent(
    memory_service: FinancialMemoryService | None = None,
    neo4j_service: Neo4jDomainService | None = None,
) -> LlmAgent:
    """Get or create the global Supervisor Agent instance.

    Args:
        memory_service: Memory service for context graph access.
            Required on first call.
        neo4j_service: Domain data service for Neo4j queries.

    Returns:
        Supervisor Agent instance.
    """
    global _supervisor_agent, _memory_service, _neo4j_service

    if (
        _supervisor_agent is None
        or (memory_service and memory_service != _memory_service)
        or (neo4j_service and neo4j_service != _neo4j_service)
    ):
        _memory_service = memory_service or _memory_service
        _neo4j_service = neo4j_service or _neo4j_service
        _supervisor_agent = create_supervisor_agent(_memory_service, neo4j_service=_neo4j_service)

    return _supervisor_agent


def reset_supervisor_agent() -> None:
    """Reset the global supervisor agent instance.

    Useful for testing or when memory service changes.
    """
    global _supervisor_agent, _memory_service, _neo4j_service
    _supervisor_agent = None
    _memory_service = None
    _neo4j_service = None
