"""Alert API routes."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...models.alert import (
    Alert,
    AlertCreate,
    AlertSeverity,
    AlertStatus,
    AlertSummary,
    AlertType,
    AlertUpdate,
)
from ...tools.kyc_tools import SAMPLE_CUSTOMERS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])

# Sample alerts for demo
_alerts: dict[str, Alert] = {
    "ALERT-001": Alert(
        id="ALERT-001",
        customer_id="CUST-003",
        customer_name="Global Holdings Ltd",
        type=AlertType.AML,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.NEW,
        title="Structuring Pattern Detected",
        description="Multiple cash deposits just under $10,000 threshold detected over 4 consecutive days.",
        transaction_id="TXN-203,TXN-204,TXN-205,TXN-206",
        evidence=[
            "TXN-203: $9,500 cash deposit on 2024-01-20",
            "TXN-204: $9,500 cash deposit on 2024-01-21",
            "TXN-205: $9,500 cash deposit on 2024-01-22",
            "TXN-206: $9,500 cash deposit on 2024-01-23",
        ],
        requires_sar=True,
        auto_generated=True,
    ),
    "ALERT-002": Alert(
        id="ALERT-002",
        customer_id="CUST-003",
        customer_name="Global Holdings Ltd",
        type=AlertType.NETWORK,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.NEW,
        title="Shell Company Indicators",
        description="Customer network shows multiple connections to entities with shell company characteristics.",
        evidence=[
            "Connected to Shell Corp - Cayman (no employees, nominee directors)",
            "Connected to Anonymous Trust - Seychelles (opaque structure)",
            "BVI jurisdiction with nominee director services",
        ],
        requires_sar=False,
        auto_generated=True,
    ),
    "ALERT-003": Alert(
        id="ALERT-003",
        customer_id="CUST-002",
        customer_name="Maria Garcia",
        type=AlertType.TRANSACTION,
        severity=AlertSeverity.MEDIUM,
        status=AlertStatus.ACKNOWLEDGED,
        title="Rapid Wire Movement",
        description="Funds received and moved within 24-48 hours with minimal change.",
        evidence=[
            "Pattern of receive-and-send within 2 days",
            "Consistent 2-4% reduction (possible fees/commission)",
            "Multiple counterparties in high-risk jurisdictions",
        ],
        requires_sar=False,
        auto_generated=True,
        acknowledged_at=datetime.now(),
    ),
}


@router.get("", response_model=list[Alert])
async def list_alerts(
    status: AlertStatus | None = Query(None, description="Filter by status"),
    severity: AlertSeverity | None = Query(None, description="Filter by severity"),
    type: AlertType | None = Query(None, description="Filter by type"),
    customer_id: str | None = Query(None, description="Filter by customer"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[Alert]:
    """List alerts with optional filtering."""
    alerts = list(_alerts.values())

    if status:
        alerts = [a for a in alerts if a.status == status]
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    if type:
        alerts = [a for a in alerts if a.type == type]
    if customer_id:
        alerts = [a for a in alerts if a.customer_id == customer_id]

    # Sort by severity (CRITICAL first) then by created_at
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(
        key=lambda x: (severity_order.get(x.severity, 4), x.created_at), reverse=False
    )

    return alerts[offset : offset + limit]


@router.get("/summary", response_model=AlertSummary)
async def get_alert_summary() -> AlertSummary:
    """Get summary statistics for alerts."""
    alerts = list(_alerts.values())

    by_severity = {}
    by_status = {}
    by_type = {}
    critical_unresolved = 0
    high_unresolved = 0

    for alert in alerts:
        # By severity
        sev = alert.severity.value
        by_severity[sev] = by_severity.get(sev, 0) + 1

        # By status
        stat = alert.status.value
        by_status[stat] = by_status.get(stat, 0) + 1

        # By type
        t = alert.type.value
        by_type[t] = by_type.get(t, 0) + 1

        # Unresolved counts
        if alert.status not in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]:
            if alert.severity == AlertSeverity.CRITICAL:
                critical_unresolved += 1
            elif alert.severity == AlertSeverity.HIGH:
                high_unresolved += 1

    return AlertSummary(
        total=len(alerts),
        by_severity=by_severity,
        by_status=by_status,
        by_type=by_type,
        critical_unresolved=critical_unresolved,
        high_unresolved=high_unresolved,
    )


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str) -> Alert:
    """Get a specific alert."""
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return _alerts[alert_id]


@router.post("", response_model=Alert)
async def create_alert(request: AlertCreate) -> Alert:
    """Create a new alert."""
    if request.customer_id not in SAMPLE_CUSTOMERS:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {request.customer_id} not found",
        )

    alert_id = f"ALERT-{uuid.uuid4().hex[:6].upper()}"

    customer = SAMPLE_CUSTOMERS[request.customer_id]

    alert = Alert(
        id=alert_id,
        customer_id=request.customer_id,
        customer_name=customer.get("name"),
        type=request.type,
        severity=request.severity,
        status=AlertStatus.NEW,
        title=request.title,
        description=request.description,
        transaction_id=request.transaction_id,
        evidence=request.evidence,
        requires_sar=request.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH],
        auto_generated=False,
    )

    _alerts[alert_id] = alert
    logger.info(f"Created alert {alert_id}")

    return alert


@router.patch("/{alert_id}", response_model=Alert)
async def update_alert(alert_id: str, update: AlertUpdate) -> Alert:
    """Update an alert."""
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert = _alerts[alert_id]

    if update.status:
        alert.status = update.status
        if update.status == AlertStatus.ACKNOWLEDGED:
            alert.acknowledged_at = datetime.now()
        elif update.status in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]:
            alert.resolved_at = datetime.now()

    if update.severity:
        alert.severity = update.severity

    if update.assigned_to:
        alert.assigned_to = update.assigned_to

    if update.notes:
        alert.notes.append(
            {
                "timestamp": datetime.now().isoformat(),
                "note": update.notes,
            }
        )

    if update.resolution_notes:
        alert.resolution_notes = update.resolution_notes

    return alert
