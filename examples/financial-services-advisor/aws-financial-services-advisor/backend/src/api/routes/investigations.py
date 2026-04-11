"""Investigation API routes.

Investigations are persisted to Neo4j via Neo4jDomainService.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ...services.memory_service import get_memory_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/investigations", tags=["investigations"])

# Trace ID mapping (kept in memory since traces are in Neo4j reasoning layer)
_traces: dict[str, str] = {}


def _get_neo4j_service(request: Request):
    svc = getattr(request.app.state, "neo4j_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Neo4j service not available")
    return svc


class InvestigationCreateRequest(BaseModel):
    customer_id: str
    title: str
    description: str = ""
    trigger: str = ""
    priority: str = "MEDIUM"


class StartInvestigationRequest(BaseModel):
    run_kyc: bool = Field(default=True)
    run_aml: bool = Field(default=True)
    run_relationship: bool = Field(default=True)
    run_compliance: bool = Field(default=True)
    time_period_days: int = Field(default=90)


class CompleteInvestigationRequest(BaseModel):
    conclusion: str
    recommended_actions: list[str] = Field(default_factory=list)
    file_sar: bool = False


@router.get("")
async def list_investigations(
    request: Request,
    status: str | None = Query(None),
    customer_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """List all investigations from Neo4j."""
    neo4j_service = _get_neo4j_service(request)
    return await neo4j_service.list_investigations(
        status=status, customer_id=customer_id, limit=limit,
    )


@router.post("", status_code=201)
async def create_investigation(
    body: InvestigationCreateRequest,
    request: Request,
) -> dict[str, Any]:
    """Create a new investigation persisted to Neo4j."""
    neo4j_service = _get_neo4j_service(request)

    customer = await neo4j_service.get_customer(body.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {body.customer_id} not found")

    investigation_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    investigation = await neo4j_service.create_investigation({
        "id": investigation_id,
        "customer_id": body.customer_id,
        "title": body.title,
        "description": body.description,
        "trigger": body.trigger,
        "priority": body.priority,
    })

    # Initialize reasoning trace
    try:
        memory_service = get_memory_service()
        trace_id = await memory_service.start_investigation_trace(
            session_id=f"session-{investigation_id}",
            task=f"Investigation: {body.title}",
        )
        _traces[investigation_id] = trace_id
    except Exception as e:
        logger.error(f"Failed to create trace: {e}")

    return investigation


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: str, request: Request) -> dict[str, Any]:
    """Get investigation details."""
    neo4j_service = _get_neo4j_service(request)
    inv = await neo4j_service.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


@router.post("/{investigation_id}/start")
async def start_investigation(
    investigation_id: str,
    body: StartInvestigationRequest,
    request: Request,
) -> dict[str, Any]:
    """Start a multi-agent investigation."""
    neo4j_service = _get_neo4j_service(request)

    inv = await neo4j_service.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    await neo4j_service.update_investigation(investigation_id, {"status": "IN_PROGRESS"})

    try:
        from ...agents import get_supervisor_agent

        supervisor = get_supervisor_agent(neo4j_service)

        agents_to_run = []
        if body.run_kyc:
            agents_to_run.append("KYC verification")
        if body.run_aml:
            agents_to_run.append("AML transaction analysis")
        if body.run_relationship:
            agents_to_run.append("relationship network analysis")
        if body.run_compliance:
            agents_to_run.append("compliance screening")

        prompt = f"""Investigate customer {inv.get('customer_id', 'unknown')}.
Title: {inv.get('title', '')}
Perform: {', '.join(agents_to_run)}
Period: Last {body.time_period_days} days"""

        result = supervisor(prompt)
        response_text = str(result)

        await neo4j_service.update_investigation(investigation_id, {
            "status": "COMPLETED",
            "summary": response_text[:2000],
        })

        if investigation_id in _traces:
            memory_service = get_memory_service()
            await memory_service.add_reasoning_step(
                trace_id=_traces[investigation_id],
                agent="supervisor",
                action="conduct_investigation",
                reasoning=f"Agents: {', '.join(agents_to_run)}",
                result={"response_length": len(response_text)},
            )

        return {
            "investigation_id": investigation_id,
            "status": "COMPLETED",
            "agents_invoked": agents_to_run,
            "preliminary_response": response_text[:1000],
        }

    except Exception as e:
        logger.error(f"Investigation error: {e}")
        await neo4j_service.update_investigation(investigation_id, {"status": "PENDING"})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}/audit-trail")
async def get_audit_trail(investigation_id: str, request: Request) -> dict[str, Any]:
    """Get reasoning audit trail."""
    neo4j_service = _get_neo4j_service(request)
    inv = await neo4j_service.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if investigation_id not in _traces:
        return {"investigation_id": investigation_id, "trace_available": False}

    try:
        memory_service = get_memory_service()
        trace = await memory_service.get_investigation_trace(trace_id=_traces[investigation_id])
        return {"investigation_id": investigation_id, "trace_available": True, "trace": trace}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{investigation_id}/complete")
async def complete_investigation(
    investigation_id: str,
    body: CompleteInvestigationRequest,
    request: Request,
) -> dict[str, Any]:
    """Complete an investigation with conclusion."""
    neo4j_service = _get_neo4j_service(request)
    inv = await neo4j_service.get_investigation(investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    updated = await neo4j_service.update_investigation(investigation_id, {
        "status": "COMPLETED",
        "conclusion": body.conclusion,
    })

    if investigation_id in _traces:
        try:
            memory_service = get_memory_service()
            await memory_service.complete_investigation_trace(
                trace_id=_traces[investigation_id],
                conclusion=body.conclusion,
                success=True,
            )
        except Exception as e:
            logger.error(f"Error completing trace: {e}")

    return updated or inv
