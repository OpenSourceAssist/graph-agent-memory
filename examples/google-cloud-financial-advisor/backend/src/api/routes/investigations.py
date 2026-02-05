"""Investigation API routes."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from ...agents.supervisor import get_supervisor_agent
from ...models.investigation import (
    AgentFinding,
    AuditTrailEntry,
    Investigation,
    InvestigationCreate,
    InvestigationStatus,
    InvestigationType,
)
from ...services.memory_service import FinancialMemoryService, get_memory_service
from ...tools.kyc_tools import SAMPLE_CUSTOMERS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/investigations", tags=["investigations"])

# In-memory storage for demo
_investigations: dict[str, Investigation] = {}
session_service = InMemorySessionService()


async def get_initialized_memory_service() -> FinancialMemoryService:
    """Get the initialized memory service."""
    service = get_memory_service()
    if not service._initialized:
        await service.initialize()
    return service


@router.get("", response_model=list[Investigation])
async def list_investigations(
    status: InvestigationStatus | None = Query(None),
    customer_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[Investigation]:
    """List all investigations with optional filtering."""
    investigations = list(_investigations.values())

    if status:
        investigations = [i for i in investigations if i.status == status]
    if customer_id:
        investigations = [i for i in investigations if i.customer_id == customer_id]

    # Sort by created_at descending
    investigations.sort(key=lambda x: x.created_at, reverse=True)

    return investigations[offset : offset + limit]


@router.post("", response_model=Investigation)
async def create_investigation(
    request: InvestigationCreate,
) -> Investigation:
    """Create a new investigation."""
    if request.customer_id not in SAMPLE_CUSTOMERS:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {request.customer_id} not found",
        )

    investigation_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    session_id = f"inv-session-{investigation_id}"

    investigation = Investigation(
        id=investigation_id,
        customer_id=request.customer_id,
        type=request.type,
        reason=request.reason,
        priority=request.priority,
        assigned_to=request.assigned_to,
        status=InvestigationStatus.PENDING,
        session_id=session_id,
        audit_trail=[
            AuditTrailEntry(
                action="CREATED",
                details=f"Investigation created: {request.reason}",
            )
        ],
    )

    _investigations[investigation_id] = investigation
    logger.info(f"Created investigation {investigation_id}")

    return investigation


@router.get("/{investigation_id}", response_model=Investigation)
async def get_investigation(investigation_id: str) -> Investigation:
    """Get a specific investigation."""
    if investigation_id not in _investigations:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation {investigation_id} not found",
        )
    return _investigations[investigation_id]


@router.post("/{investigation_id}/start")
async def start_investigation(
    investigation_id: str,
    memory_service: FinancialMemoryService = Depends(get_initialized_memory_service),
) -> dict[str, Any]:
    """Start a multi-agent investigation.

    This triggers the supervisor agent to orchestrate the investigation
    by delegating to KYC, AML, Relationship, and Compliance agents.
    """
    if investigation_id not in _investigations:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation {investigation_id} not found",
        )

    investigation = _investigations[investigation_id]

    if investigation.status not in [
        InvestigationStatus.PENDING,
        InvestigationStatus.IN_PROGRESS,
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Investigation is {investigation.status}, cannot start",
        )

    start_time = time.time()

    # Update status
    investigation.status = InvestigationStatus.IN_PROGRESS
    investigation.started_at = datetime.now()
    investigation.audit_trail.append(
        AuditTrailEntry(
            action="STARTED",
            details="Multi-agent investigation initiated",
        )
    )

    try:
        # Get the supervisor agent
        supervisor = get_supervisor_agent(memory_service)

        # Create session
        session = session_service.create_session(
            app_name="financial_advisor",
            user_id="investigator",
            session_id=investigation.session_id,
        )

        # Build investigation prompt
        prompt = f"""Conduct a comprehensive {investigation.type.value} investigation for customer {investigation.customer_id}.

Reason for investigation: {investigation.reason}
Priority: {investigation.priority}

Please:
1. Delegate appropriate tasks to specialized agents (KYC, AML, Relationship, Compliance)
2. Gather and analyze all findings
3. Assess overall risk level
4. Provide specific recommendations
5. Document all steps for the audit trail

Begin the investigation now."""

        # Create runner and execute
        runner = Runner(
            agent=supervisor,
            app_name="financial_advisor",
            session_service=session_service,
        )

        # Run the investigation
        result = await runner.run_async(
            user_id="investigator",
            session_id=investigation.session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            ),
        )

        # Extract results
        response_text = ""
        agents_consulted = set()
        tool_calls = []

        for event in result.events:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text
            if hasattr(event, "agent_name"):
                agents_consulted.add(event.agent_name)
            if hasattr(event, "tool_calls"):
                for tc in event.tool_calls:
                    tool_calls.append(
                        {
                            "tool": tc.name,
                            "agent": getattr(event, "agent_name", "unknown"),
                        }
                    )
                    investigation.audit_trail.append(
                        AuditTrailEntry(
                            action="TOOL_CALL",
                            agent=getattr(event, "agent_name", None),
                            tool_used=tc.name,
                            details=f"Called {tc.name}",
                        )
                    )

        # Parse risk level from response
        risk_level = "MEDIUM"
        if "CRITICAL" in response_text.upper():
            risk_level = "CRITICAL"
        elif "HIGH" in response_text.upper():
            risk_level = "HIGH"
        elif "LOW" in response_text.upper():
            risk_level = "LOW"

        # Update investigation
        investigation.status = InvestigationStatus.COMPLETED
        investigation.completed_at = datetime.now()
        investigation.overall_risk_level = risk_level
        investigation.summary = response_text[:2000]  # Truncate if too long
        investigation.agents_consulted = list(agents_consulted)

        investigation.audit_trail.append(
            AuditTrailEntry(
                action="COMPLETED",
                details=f"Investigation completed. Risk level: {risk_level}",
            )
        )

        duration = time.time() - start_time

        return {
            "investigation_id": investigation_id,
            "status": investigation.status,
            "overall_risk_level": risk_level,
            "summary": investigation.summary,
            "agents_consulted": list(agents_consulted),
            "tool_calls_count": len(tool_calls),
            "duration_seconds": round(duration, 2),
        }

    except Exception as e:
        logger.error(f"Investigation error: {e}", exc_info=True)

        investigation.audit_trail.append(
            AuditTrailEntry(
                action="ERROR",
                details=str(e),
            )
        )

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}/audit-trail", response_model=list[AuditTrailEntry])
async def get_audit_trail(investigation_id: str) -> list[AuditTrailEntry]:
    """Get the audit trail for an investigation."""
    if investigation_id not in _investigations:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation {investigation_id} not found",
        )

    return _investigations[investigation_id].audit_trail
