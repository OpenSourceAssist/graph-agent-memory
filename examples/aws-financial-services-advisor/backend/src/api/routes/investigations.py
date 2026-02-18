"""Investigation API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...models import (
    Investigation,
    InvestigationAuditTrail,
    InvestigationCreate,
    InvestigationStatus,
    InvestigationWorkflow,
)
from ...services.memory_service import get_memory_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/investigations", tags=["investigations"])

# In-memory store for demo purposes
_investigations: dict[str, Investigation] = {}
_traces: dict[str, str] = {}  # investigation_id -> trace_id mapping


class InvestigationSummary(BaseModel):
    """Condensed investigation information."""

    id: str
    customer_id: str
    title: str
    status: InvestigationStatus
    priority: str
    created_at: datetime
    findings_count: int


class InvestigationListResponse(BaseModel):
    """Response for investigation list endpoint."""

    investigations: list[InvestigationSummary]
    total: int
    page: int
    page_size: int


class StartInvestigationRequest(BaseModel):
    """Request to start/run an investigation."""

    run_kyc: bool = Field(default=True, description="Run KYC agent")
    run_aml: bool = Field(default=True, description="Run AML agent")
    run_relationship: bool = Field(
        default=True, description="Run relationship analysis"
    )
    run_compliance: bool = Field(default=True, description="Run compliance checks")
    time_period_days: int = Field(default=90, description="Analysis period in days")


class CompleteInvestigationRequest(BaseModel):
    """Request to complete an investigation."""

    conclusion: str = Field(..., description="Investigation conclusion")
    recommended_actions: list[str] = Field(
        default_factory=list, description="Recommended follow-up actions"
    )
    file_sar: bool = Field(default=False, description="Whether to file SAR")


@router.get("", response_model=InvestigationListResponse)
async def list_investigations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: InvestigationStatus | None = Query(None, description="Filter by status"),
    customer_id: str | None = Query(None, description="Filter by customer"),
) -> InvestigationListResponse:
    """List all investigations with optional filtering.

    Args:
        page: Page number for pagination
        page_size: Number of items per page
        status: Optional status filter
        customer_id: Optional customer filter

    Returns:
        Paginated list of investigations
    """
    investigations = list(_investigations.values())

    # Apply filters
    if status:
        investigations = [i for i in investigations if i.status == status]

    if customer_id:
        investigations = [i for i in investigations if i.customer_id == customer_id]

    # Sort by created_at descending
    investigations.sort(key=lambda x: x.created_at, reverse=True)

    # Pagination
    total = len(investigations)
    start = (page - 1) * page_size
    end = start + page_size
    page_investigations = investigations[start:end]

    return InvestigationListResponse(
        investigations=[
            InvestigationSummary(
                id=inv.id,
                customer_id=inv.customer_id,
                title=inv.title,
                status=inv.status,
                priority=inv.priority,
                created_at=inv.created_at,
                findings_count=len(inv.findings),
            )
            for inv in page_investigations
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=Investigation, status_code=201)
async def create_investigation(request: InvestigationCreate) -> Investigation:
    """Create a new investigation.

    This creates an investigation record and initializes a reasoning trace
    in the Context Graph for audit purposes.

    Args:
        request: Investigation creation data

    Returns:
        Created investigation
    """
    investigation_id = f"INV-{uuid.uuid4().hex[:8].upper()}"

    investigation = Investigation(
        id=investigation_id,
        **request.model_dump(),
    )

    _investigations[investigation_id] = investigation

    # Initialize reasoning trace
    try:
        memory_service = get_memory_service()
        session_id = f"session-{investigation_id}"
        trace_id = await memory_service.start_investigation_trace(
            session_id=session_id,
            investigation_id=investigation_id,
            task=f"Investigation: {investigation.title}",
        )
        _traces[investigation_id] = trace_id
        logger.info(f"Created investigation {investigation_id} with trace {trace_id}")
    except Exception as e:
        logger.error(f"Failed to create trace: {e}")

    return investigation


@router.get("/{investigation_id}", response_model=Investigation)
async def get_investigation(investigation_id: str) -> Investigation:
    """Get investigation details by ID.

    Args:
        investigation_id: The investigation identifier

    Returns:
        Investigation details with all findings
    """
    if investigation_id not in _investigations:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return _investigations[investigation_id]


@router.put("/{investigation_id}/status")
async def update_investigation_status(
    investigation_id: str,
    status: InvestigationStatus,
) -> Investigation:
    """Update investigation status.

    Args:
        investigation_id: The investigation identifier
        status: New status

    Returns:
        Updated investigation
    """
    if investigation_id not in _investigations:
        raise HTTPException(status_code=404, detail="Investigation not found")

    investigation = _investigations[investigation_id]
    investigation.status = status
    investigation.updated_at = datetime.utcnow()

    if status == InvestigationStatus.IN_PROGRESS and not investigation.started_at:
        investigation.started_at = datetime.utcnow()

    _investigations[investigation_id] = investigation
    return investigation


@router.post("/{investigation_id}/start")
async def start_investigation(
    investigation_id: str,
    request: StartInvestigationRequest,
) -> dict[str, Any]:
    """Start running an investigation with the multi-agent system.

    This triggers the supervisor agent to coordinate specialized agents
    for a comprehensive customer investigation.

    Args:
        investigation_id: The investigation identifier
        request: Configuration for which agents to run

    Returns:
        Investigation progress update
    """
    if investigation_id not in _investigations:
        raise HTTPException(status_code=404, detail="Investigation not found")

    investigation = _investigations[investigation_id]

    # Update status
    investigation.status = InvestigationStatus.IN_PROGRESS
    investigation.started_at = datetime.utcnow()
    investigation.updated_at = datetime.utcnow()

    try:
        from ...agents import get_supervisor_agent

        supervisor = get_supervisor_agent()

        # Build investigation prompt
        agents_to_run = []
        if request.run_kyc:
            agents_to_run.append("KYC verification")
        if request.run_aml:
            agents_to_run.append("AML transaction analysis")
        if request.run_relationship:
            agents_to_run.append("relationship network analysis")
        if request.run_compliance:
            agents_to_run.append("compliance screening")

        prompt = f"""Conduct a comprehensive investigation for customer {investigation.customer_id}.

Investigation ID: {investigation_id}
Investigation Title: {investigation.title}
Trigger: {investigation.trigger}
Description: {investigation.description}

Please perform the following analyses:
{chr(10).join(f"- {agent}" for agent in agents_to_run)}

Analysis period: Last {request.time_period_days} days

Coordinate with specialized agents and synthesize findings into a comprehensive report."""

        # Run investigation asynchronously (simplified for demo)
        result = supervisor(prompt)

        # Record reasoning step
        if investigation_id in _traces:
            memory_service = get_memory_service()
            session_id = f"session-{investigation_id}"
            await memory_service.add_reasoning_step(
                session_id=session_id,
                trace_id=_traces[investigation_id],
                agent="supervisor",
                action="conduct_investigation",
                reasoning=f"Running investigation with agents: {', '.join(agents_to_run)}",
                result={"response_length": len(str(result))},
            )

        return {
            "investigation_id": investigation_id,
            "status": "in_progress",
            "agents_invoked": agents_to_run,
            "preliminary_response": str(result)[:1000] + "..."
            if len(str(result)) > 1000
            else str(result),
        }

    except Exception as e:
        logger.error(f"Investigation error: {e}")
        investigation.status = InvestigationStatus.AWAITING_INFO
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}/audit-trail")
async def get_audit_trail(investigation_id: str) -> dict[str, Any]:
    """Get the reasoning audit trail for an investigation.

    Returns the complete trace of agent actions and reasoning
    for regulatory compliance and explainability.

    Args:
        investigation_id: The investigation identifier

    Returns:
        Complete audit trail with agent reasoning
    """
    if investigation_id not in _investigations:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if investigation_id not in _traces:
        return {
            "investigation_id": investigation_id,
            "trace_available": False,
            "message": "No reasoning trace found for this investigation",
        }

    try:
        memory_service = get_memory_service()
        session_id = f"session-{investigation_id}"
        trace = await memory_service.get_investigation_trace(
            session_id=session_id,
            trace_id=_traces[investigation_id],
        )

        return {
            "investigation_id": investigation_id,
            "trace_available": True,
            "trace": trace,
        }

    except Exception as e:
        logger.error(f"Error fetching audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{investigation_id}/complete")
async def complete_investigation(
    investigation_id: str,
    request: CompleteInvestigationRequest,
) -> Investigation:
    """Complete an investigation with conclusion and recommendations.

    Args:
        investigation_id: The investigation identifier
        request: Completion details

    Returns:
        Completed investigation
    """
    if investigation_id not in _investigations:
        raise HTTPException(status_code=404, detail="Investigation not found")

    investigation = _investigations[investigation_id]
    investigation.status = InvestigationStatus.COMPLETED
    investigation.completed_at = datetime.utcnow()
    investigation.updated_at = datetime.utcnow()
    investigation.conclusion = request.conclusion
    investigation.recommended_actions = request.recommended_actions
    investigation.sar_filed = request.file_sar

    # Complete reasoning trace
    if investigation_id in _traces:
        try:
            memory_service = get_memory_service()
            session_id = f"session-{investigation_id}"
            await memory_service.complete_investigation_trace(
                session_id=session_id,
                trace_id=_traces[investigation_id],
                conclusion=request.conclusion,
                success=True,
            )
        except Exception as e:
            logger.error(f"Error completing trace: {e}")

    _investigations[investigation_id] = investigation
    return investigation


@router.get("/{investigation_id}/workflow", response_model=InvestigationWorkflow)
async def get_investigation_workflow(investigation_id: str) -> InvestigationWorkflow:
    """Get the workflow state for an investigation.

    Shows which steps have been completed, are in progress,
    or are pending.

    Args:
        investigation_id: The investigation identifier

    Returns:
        Workflow state
    """
    if investigation_id not in _investigations:
        raise HTTPException(status_code=404, detail="Investigation not found")

    investigation = _investigations[investigation_id]

    # Determine workflow state based on findings
    all_steps = [
        "kyc_verification",
        "aml_analysis",
        "relationship_mapping",
        "compliance_check",
    ]
    agents_found = set(f.agent for f in investigation.findings)

    completed = [s for s in all_steps if any(a in s for a in agents_found)]
    pending = [s for s in all_steps if s not in completed]

    current_step = pending[0] if pending else "complete"
    if investigation.status == InvestigationStatus.COMPLETED:
        current_step = "complete"

    return InvestigationWorkflow(
        investigation_id=investigation_id,
        current_step=current_step,
        completed_steps=completed,
        pending_steps=pending,
        agent_assignments={
            "kyc_verification": "kyc",
            "aml_analysis": "aml",
            "relationship_mapping": "relationship",
            "compliance_check": "compliance",
        },
        step_results={},
    )
