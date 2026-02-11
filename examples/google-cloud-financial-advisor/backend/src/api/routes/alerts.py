"""Alert API routes.

All alert data is queried from Neo4j via the Neo4jDomainService.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request

from ...models.alert import (
    Alert,
    AlertCreate,
    AlertSeverity,
    AlertStatus,
    AlertSummary,
    AlertType,
    AlertUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])


def _get_neo4j_service(request: Request):
    """Get Neo4jDomainService from app state."""
    svc = getattr(request.app.state, "neo4j_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="Neo4j service not available")
    return svc


def _to_python_datetime(val) -> datetime | None:
    """Convert a Neo4j DateTime or other value to a Python datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    # neo4j.time.DateTime has .to_native() -> python datetime
    if hasattr(val, "to_native"):
        return val.to_native()
    return None


def _alert_from_dict(data: dict) -> Alert:
    """Build an Alert response model from a Neo4j dict."""
    # Map Neo4j severity/status/type values to enums (handle case differences)
    severity_val = (data.get("severity") or "MEDIUM").upper()
    status_val = (data.get("status") or "new").lower()
    type_val = (data.get("type") or "aml").lower()

    return Alert(
        id=data.get("id", ""),
        customer_id=data.get("customer_id", ""),
        customer_name=data.get("customer_name"),
        type=AlertType(type_val) if type_val in AlertType._value2member_map_ else AlertType.AML,
        severity=AlertSeverity(severity_val),
        status=AlertStatus(status_val)
        if status_val in AlertStatus._value2member_map_
        else AlertStatus.NEW,
        title=data.get("title", ""),
        description=data.get("description", ""),
        transaction_id=data.get("transaction_id"),
        evidence=data.get("evidence") or [],
        requires_sar=data.get("requires_sar", False),
        auto_generated=data.get("auto_generated", False),
        created_at=_to_python_datetime(data.get("created_at")) or datetime.now(),
        acknowledged_at=_to_python_datetime(data.get("acknowledged_at")),
        resolved_at=_to_python_datetime(data.get("resolved_at")),
    )


@router.get("", response_model=list[Alert])
async def list_alerts(
    request: Request,
    status: AlertStatus | None = Query(None, description="Filter by status"),
    severity: AlertSeverity | None = Query(None, description="Filter by severity"),
    type: AlertType | None = Query(None, description="Filter by type"),
    customer_id: str | None = Query(None, description="Filter by customer"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[Alert]:
    """List alerts with optional filtering."""
    neo4j_service = _get_neo4j_service(request)

    rows = await neo4j_service.list_alerts(
        status=status.value.upper() if status else None,
        severity=severity.value if severity else None,
        alert_type=type.value if type else None,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )

    return [_alert_from_dict(r) for r in rows]


@router.get("/summary", response_model=AlertSummary)
async def get_alert_summary(request: Request) -> AlertSummary:
    """Get summary statistics for alerts."""
    neo4j_service = _get_neo4j_service(request)

    summary = await neo4j_service.get_alert_summary()

    return AlertSummary(
        total=summary.get("total", 0),
        by_severity=summary.get("by_severity", {}),
        by_status=summary.get("by_status", {}),
        by_type=summary.get("by_type", {}),
        critical_unresolved=summary.get("critical_unresolved", 0),
        high_unresolved=summary.get("high_unresolved", 0),
    )


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(request: Request, alert_id: str) -> Alert:
    """Get a specific alert."""
    neo4j_service = _get_neo4j_service(request)

    data = await neo4j_service.get_alert(alert_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return _alert_from_dict(data)


@router.post("", response_model=Alert)
async def create_alert(request: Request, body: AlertCreate) -> Alert:
    """Create a new alert."""
    neo4j_service = _get_neo4j_service(request)

    # Verify customer exists
    customer = await neo4j_service.get_customer(body.customer_id)
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {body.customer_id} not found",
        )

    alert_id = f"ALERT-{uuid.uuid4().hex[:6].upper()}"

    data = await neo4j_service.create_alert(
        {
            "id": alert_id,
            "customer_id": body.customer_id,
            "type": body.type.value.upper(),
            "severity": body.severity.value,
            "status": "NEW",
            "title": body.title,
            "description": body.description,
            "evidence": body.evidence,
            "requires_sar": body.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH],
            "auto_generated": False,
        }
    )

    logger.info(f"Created alert {alert_id}")
    return _alert_from_dict(data)


@router.patch("/{alert_id}", response_model=Alert)
async def update_alert(request: Request, alert_id: str, update: AlertUpdate) -> Alert:
    """Update an alert."""
    neo4j_service = _get_neo4j_service(request)

    existing = await neo4j_service.get_alert(alert_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    updates = {}
    if update.status:
        updates["status"] = update.status.value.upper()
    if update.severity:
        updates["severity"] = update.severity.value
    if update.assigned_to:
        updates["assigned_to"] = update.assigned_to
    if update.resolution_notes:
        updates["resolution_notes"] = update.resolution_notes

    if updates:
        data = await neo4j_service.update_alert(alert_id, updates)
    else:
        data = existing

    if not data:
        raise HTTPException(status_code=500, detail="Failed to update alert")

    return _alert_from_dict(data)
