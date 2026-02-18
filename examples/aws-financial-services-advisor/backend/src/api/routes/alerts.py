"""Alert API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...models import (
    Alert,
    AlertAcknowledge,
    AlertClose,
    AlertCreate,
    AlertSeverity,
    AlertStatus,
    AlertSummary,
    AlertType,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])

# In-memory store for demo purposes
_alerts: dict[str, Alert] = {}


class AlertListResponse(BaseModel):
    """Response for alert list endpoint."""

    alerts: list[Alert]
    total: int
    page: int
    page_size: int


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: AlertStatus | None = Query(None, description="Filter by status"),
    severity: AlertSeverity | None = Query(None, description="Filter by severity"),
    alert_type: AlertType | None = Query(None, description="Filter by type"),
    customer_id: str | None = Query(None, description="Filter by customer"),
) -> AlertListResponse:
    """List all alerts with optional filtering.

    Args:
        page: Page number for pagination
        page_size: Number of items per page
        status: Optional status filter
        severity: Optional severity filter
        alert_type: Optional type filter
        customer_id: Optional customer filter

    Returns:
        Paginated list of alerts
    """
    alerts = list(_alerts.values())

    # Apply filters
    if status:
        alerts = [a for a in alerts if a.status == status]

    if severity:
        alerts = [a for a in alerts if a.severity == severity]

    if alert_type:
        alerts = [a for a in alerts if a.type == alert_type]

    if customer_id:
        alerts = [a for a in alerts if a.customer_id == customer_id]

    # Sort by created_at descending (newest first)
    alerts.sort(key=lambda x: x.created_at, reverse=True)

    # Pagination
    total = len(alerts)
    start = (page - 1) * page_size
    end = start + page_size
    page_alerts = alerts[start:end]

    return AlertListResponse(
        alerts=page_alerts,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=Alert, status_code=201)
async def create_alert(request: AlertCreate) -> Alert:
    """Create a new compliance alert.

    Alerts are typically created by agent tools when suspicious activity
    is detected. This endpoint allows manual alert creation as well.

    Args:
        request: Alert creation data

    Returns:
        Created alert
    """
    alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"

    alert = Alert(
        id=alert_id,
        **request.model_dump(),
    )

    _alerts[alert_id] = alert
    logger.info(f"Created alert {alert_id}: {alert.title}")

    return alert


@router.get("/summary", response_model=AlertSummary)
async def get_alert_summary() -> AlertSummary:
    """Get summary statistics for alerts.

    Provides an overview of alert counts by status, severity, and type.

    Returns:
        Alert summary statistics
    """
    alerts = list(_alerts.values())

    by_status = {}
    by_severity = {}
    by_type = {}

    for alert in alerts:
        by_status[alert.status.value] = by_status.get(alert.status.value, 0) + 1
        by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
        by_type[alert.type.value] = by_type.get(alert.type.value, 0) + 1

    # Calculate average resolution time for closed alerts
    closed_alerts = [a for a in alerts if a.resolved_at and a.created_at]
    avg_resolution_time = None
    if closed_alerts:
        total_hours = sum(
            (a.resolved_at - a.created_at).total_seconds() / 3600 for a in closed_alerts
        )
        avg_resolution_time = total_hours / len(closed_alerts)

    # Find oldest unresolved alert
    unresolved = [
        a
        for a in alerts
        if a.status not in (AlertStatus.CLOSED, AlertStatus.FALSE_POSITIVE)
    ]
    oldest_unresolved = None
    if unresolved:
        oldest_unresolved = min(a.created_at for a in unresolved)

    return AlertSummary(
        total_count=len(alerts),
        by_status=by_status,
        by_severity=by_severity,
        by_type=by_type,
        avg_resolution_time_hours=avg_resolution_time,
        oldest_unresolved=oldest_unresolved,
    )


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str) -> Alert:
    """Get alert details by ID.

    Args:
        alert_id: The alert identifier

    Returns:
        Alert details
    """
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    return _alerts[alert_id]


@router.post("/{alert_id}/acknowledge", response_model=Alert)
async def acknowledge_alert(alert_id: str, request: AlertAcknowledge) -> Alert:
    """Acknowledge an alert and assign for review.

    Args:
        alert_id: The alert identifier
        request: Acknowledgment details

    Returns:
        Updated alert
    """
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = _alerts[alert_id]
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.assigned_to = request.analyst_id
    alert.updated_at = datetime.utcnow()

    _alerts[alert_id] = alert
    logger.info(f"Alert {alert_id} acknowledged by {request.analyst_id}")

    return alert


@router.post("/{alert_id}/escalate", response_model=Alert)
async def escalate_alert(
    alert_id: str,
    reason: str = Query(..., description="Reason for escalation"),
    escalate_to: str = Query(..., description="Escalation target"),
) -> Alert:
    """Escalate an alert for senior review.

    Args:
        alert_id: The alert identifier
        reason: Reason for escalation
        escalate_to: Who to escalate to

    Returns:
        Updated alert
    """
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = _alerts[alert_id]
    alert.status = AlertStatus.ESCALATED
    alert.updated_at = datetime.utcnow()

    # Store escalation info in metadata
    if "escalation_history" not in alert.metadata:
        alert.metadata["escalation_history"] = []

    alert.metadata["escalation_history"].append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "escalated_to": escalate_to,
        }
    )

    _alerts[alert_id] = alert
    logger.info(f"Alert {alert_id} escalated to {escalate_to}")

    return alert


@router.post("/{alert_id}/close", response_model=Alert)
async def close_alert(alert_id: str, request: AlertClose) -> Alert:
    """Close an alert with resolution notes.

    Args:
        alert_id: The alert identifier
        request: Closure details

    Returns:
        Closed alert
    """
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = _alerts[alert_id]
    alert.status = (
        AlertStatus.FALSE_POSITIVE if request.is_false_positive else AlertStatus.CLOSED
    )
    alert.resolution = request.resolution
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = request.analyst_id
    alert.updated_at = datetime.utcnow()

    _alerts[alert_id] = alert
    logger.info(f"Alert {alert_id} closed by {request.analyst_id}")

    return alert


@router.post("/{alert_id}/link-investigation", response_model=Alert)
async def link_investigation(
    alert_id: str,
    investigation_id: str = Query(..., description="Investigation ID to link"),
) -> Alert:
    """Link an alert to an investigation.

    Args:
        alert_id: The alert identifier
        investigation_id: The investigation to link

    Returns:
        Updated alert
    """
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert = _alerts[alert_id]
    alert.investigation_id = investigation_id
    alert.status = AlertStatus.UNDER_REVIEW
    alert.updated_at = datetime.utcnow()

    _alerts[alert_id] = alert
    logger.info(f"Alert {alert_id} linked to investigation {investigation_id}")

    return alert


@router.get("/customer/{customer_id}", response_model=list[Alert])
async def get_customer_alerts(
    customer_id: str,
    include_closed: bool = Query(False, description="Include closed alerts"),
) -> list[Alert]:
    """Get all alerts for a specific customer.

    Args:
        customer_id: The customer identifier
        include_closed: Whether to include closed alerts

    Returns:
        List of customer alerts
    """
    alerts = [a for a in _alerts.values() if a.customer_id == customer_id]

    if not include_closed:
        alerts = [
            a
            for a in alerts
            if a.status not in (AlertStatus.CLOSED, AlertStatus.FALSE_POSITIVE)
        ]

    # Sort by severity (critical first) then by created_at
    severity_order = {
        AlertSeverity.CRITICAL: 0,
        AlertSeverity.HIGH: 1,
        AlertSeverity.MEDIUM: 2,
        AlertSeverity.LOW: 3,
    }
    alerts.sort(
        key=lambda x: (severity_order.get(x.severity, 99), -x.created_at.timestamp())
    )

    return alerts
