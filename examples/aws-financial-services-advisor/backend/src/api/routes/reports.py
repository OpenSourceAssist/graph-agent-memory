"""Reports API routes for compliance reporting."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...models import (
    ReportFormat,
    ReportRequest,
    ReportStatus,
    RiskAssessmentReport,
    RiskFactor,
    SARReport,
)
from ...services.risk_service import get_risk_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

# In-memory store for demo purposes
_sar_reports: dict[str, SARReport] = {}
_risk_reports: dict[str, RiskAssessmentReport] = {}


class SARCreateRequest(BaseModel):
    """Request to create a SAR."""

    investigation_id: str = Field(..., description="Investigation ID")
    customer_id: str = Field(..., description="Subject customer ID")
    suspicious_activity_type: list[str] = Field(..., description="Types of activity")
    activity_start_date: datetime = Field(..., description="Activity start date")
    activity_end_date: datetime = Field(..., description="Activity end date")
    total_amount: float = Field(..., description="Total amount involved")
    currency: str = Field(default="USD", description="Currency")
    summary: str = Field(..., description="Executive summary")
    activity_description: str = Field(..., description="Detailed description")
    prepared_by: str = Field(..., description="Preparer ID")


class RiskReportCreateRequest(BaseModel):
    """Request to create a risk assessment report."""

    customer_id: str = Field(..., description="Customer ID")
    include_network: bool = Field(default=True, description="Include network analysis")
    include_transactions: bool = Field(
        default=True, description="Include transaction analysis"
    )
    prepared_by: str = Field(..., description="Preparer ID")


class ReportListResponse(BaseModel):
    """Response for report list endpoint."""

    reports: list[dict[str, Any]]
    total: int


@router.get("/sar", response_model=ReportListResponse)
async def list_sar_reports(
    status: ReportStatus | None = Query(None, description="Filter by status"),
    customer_id: str | None = Query(None, description="Filter by customer"),
) -> ReportListResponse:
    """List all SAR reports.

    Args:
        status: Optional status filter
        customer_id: Optional customer filter

    Returns:
        List of SAR reports
    """
    reports = list(_sar_reports.values())

    if status:
        reports = [r for r in reports if r.status == status]

    if customer_id:
        reports = [r for r in reports if r.customer_id == customer_id]

    # Sort by created_at descending
    reports.sort(key=lambda x: x.created_at, reverse=True)

    return ReportListResponse(
        reports=[
            {
                "id": r.id,
                "investigation_id": r.investigation_id,
                "customer_id": r.customer_id,
                "subject_name": r.subject_name,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
                "filed_at": r.filed_at.isoformat() if r.filed_at else None,
                "total_amount": r.total_amount_involved,
            }
            for r in reports
        ],
        total=len(reports),
    )


@router.post("/sar", response_model=SARReport, status_code=201)
async def create_sar_report(request: SARCreateRequest) -> SARReport:
    """Create a new Suspicious Activity Report.

    Args:
        request: SAR creation data

    Returns:
        Created SAR report
    """
    report_id = f"SAR-{uuid.uuid4().hex[:8].upper()}"

    # Get customer name from customers route (simplified)
    subject_name = f"Customer {request.customer_id}"

    report = SARReport(
        id=report_id,
        investigation_id=request.investigation_id,
        customer_id=request.customer_id,
        subject_name=subject_name,
        subject_type="entity",  # Simplified
        suspicious_activity_type=request.suspicious_activity_type,
        activity_date_range={
            "start": request.activity_start_date,
            "end": request.activity_end_date,
        },
        total_amount_involved=request.total_amount,
        currency=request.currency,
        summary=request.summary,
        activity_description=request.activity_description,
        subject_information={"customer_id": request.customer_id},
        account_information=[],
        transaction_summary=[],
        prepared_by=request.prepared_by,
    )

    _sar_reports[report_id] = report
    logger.info(f"Created SAR report {report_id}")

    return report


@router.get("/sar/{report_id}", response_model=SARReport)
async def get_sar_report(report_id: str) -> SARReport:
    """Get SAR report by ID.

    Args:
        report_id: Report identifier

    Returns:
        SAR report details
    """
    if report_id not in _sar_reports:
        raise HTTPException(status_code=404, detail="SAR report not found")

    return _sar_reports[report_id]


@router.post("/sar/{report_id}/submit")
async def submit_sar_report(
    report_id: str,
    reviewer_id: str = Query(..., description="Reviewer ID"),
    approver_id: str = Query(..., description="Approver ID"),
) -> dict[str, Any]:
    """Submit a SAR report for filing.

    Args:
        report_id: Report identifier
        reviewer_id: ID of reviewer
        approver_id: ID of approver

    Returns:
        Submission confirmation
    """
    if report_id not in _sar_reports:
        raise HTTPException(status_code=404, detail="SAR report not found")

    report = _sar_reports[report_id]
    report.status = ReportStatus.COMPLETED
    report.filed_at = datetime.utcnow()
    report.reviewed_by = reviewer_id
    report.approved_by = approver_id
    report.filing_reference = f"FINCEN-{uuid.uuid4().hex[:12].upper()}"

    _sar_reports[report_id] = report

    return {
        "report_id": report_id,
        "status": "submitted",
        "filing_reference": report.filing_reference,
        "filed_at": report.filed_at.isoformat(),
    }


@router.get("/risk-assessment", response_model=ReportListResponse)
async def list_risk_reports(
    customer_id: str | None = Query(None, description="Filter by customer"),
) -> ReportListResponse:
    """List all risk assessment reports.

    Args:
        customer_id: Optional customer filter

    Returns:
        List of risk assessment reports
    """
    reports = list(_risk_reports.values())

    if customer_id:
        reports = [r for r in reports if r.customer_id == customer_id]

    # Sort by created_at descending
    reports.sort(key=lambda x: x.created_at, reverse=True)

    return ReportListResponse(
        reports=[
            {
                "id": r.id,
                "customer_id": r.customer_id,
                "risk_score": r.overall_risk_score,
                "risk_level": r.overall_risk_level,
                "created_at": r.created_at.isoformat(),
                "valid_until": r.valid_until.isoformat() if r.valid_until else None,
            }
            for r in reports
        ],
        total=len(reports),
    )


@router.post("/risk-assessment", response_model=RiskAssessmentReport, status_code=201)
async def create_risk_report(request: RiskReportCreateRequest) -> RiskAssessmentReport:
    """Create a new risk assessment report for a customer.

    Args:
        request: Risk report creation data

    Returns:
        Created risk assessment report
    """
    report_id = f"RISK-{uuid.uuid4().hex[:8].upper()}"

    risk_service = get_risk_service()

    # Get risk assessment (simplified - would fetch real customer data)
    assessment = risk_service.assess_customer_risk(
        customer_id=request.customer_id,
        customer_type="corporate",  # Simplified
        jurisdiction="US",  # Simplified
    )

    # Build risk factors
    risk_factors = [
        RiskFactor(
            category="geographic",
            factor=factor,
            severity="medium",
            score=assessment.geographic_risk,
            description=factor,
            evidence=[],
        )
        for factor in assessment.risk_factors
        if "jurisdiction" in factor.lower()
    ]

    # Determine risk level string
    risk_level = assessment.overall_risk.value

    report = RiskAssessmentReport(
        id=report_id,
        customer_id=request.customer_id,
        status=ReportStatus.COMPLETED,
        valid_until=datetime.utcnow() + timedelta(days=365),
        overall_risk_score=assessment.risk_score,
        overall_risk_level=risk_level,
        identity_verification_score=85.0,  # Simplified
        geographic_risk_score=assessment.geographic_risk,
        product_risk_score=50.0,  # Simplified
        transaction_risk_score=assessment.transaction_risk,
        relationship_risk_score=assessment.network_risk,
        risk_factors=risk_factors,
        customer_profile={"customer_id": request.customer_id},
        transaction_analysis={"included": request.include_transactions},
        network_analysis={"included": request.include_network},
        regulatory_status={"compliant": True},
        risk_rating_recommendation=risk_level,
        enhanced_due_diligence_required=risk_level in ("high", "critical"),
        monitoring_recommendations=assessment.recommendations,
        action_items=assessment.recommendations[:3]
        if assessment.recommendations
        else [],
        prepared_by=request.prepared_by,
    )

    _risk_reports[report_id] = report
    logger.info(f"Created risk assessment report {report_id}")

    return report


@router.get("/risk-assessment/{report_id}", response_model=RiskAssessmentReport)
async def get_risk_report(report_id: str) -> RiskAssessmentReport:
    """Get risk assessment report by ID.

    Args:
        report_id: Report identifier

    Returns:
        Risk assessment report details
    """
    if report_id not in _risk_reports:
        raise HTTPException(status_code=404, detail="Risk report not found")

    return _risk_reports[report_id]


@router.post("/generate")
async def generate_report(request: ReportRequest) -> dict[str, Any]:
    """Generate a report based on request parameters.

    This endpoint triggers report generation using the compliance agent
    and returns the report metadata.

    Args:
        request: Report generation request

    Returns:
        Generated report metadata
    """
    try:
        from ...agents import get_compliance_agent

        compliance_agent = get_compliance_agent()

        # Build prompt for report generation
        prompt = f"""Generate a {request.report_type} report for customer {request.customer_id}.

Include the following:
- Network analysis: {request.include_network}
- Transaction analysis: {request.include_transactions}
- Date range: Last {request.date_range_days} days
- Output format: {request.format.value}

Provide a comprehensive report following regulatory requirements."""

        result = compliance_agent(prompt)

        return {
            "status": "generated",
            "customer_id": request.customer_id,
            "report_type": request.report_type,
            "format": request.format.value,
            "content_preview": str(result)[:500] + "..."
            if len(str(result)) > 500
            else str(result),
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_report_templates() -> list[dict[str, Any]]:
    """List available report templates.

    Returns:
        List of report templates with descriptions
    """
    return [
        {
            "id": "sar",
            "name": "Suspicious Activity Report (SAR)",
            "description": "Report for filing suspicious activity with FinCEN",
            "sections": [
                "subject_information",
                "suspicious_activity",
                "transaction_summary",
                "narrative",
            ],
            "regulatory_authority": "FinCEN",
        },
        {
            "id": "risk_assessment",
            "name": "Customer Risk Assessment",
            "description": "Comprehensive customer risk evaluation",
            "sections": [
                "customer_profile",
                "risk_scoring",
                "transaction_analysis",
                "network_analysis",
                "recommendations",
            ],
            "regulatory_authority": "Internal",
        },
        {
            "id": "edd",
            "name": "Enhanced Due Diligence Report",
            "description": "Detailed due diligence for high-risk customers",
            "sections": [
                "identity_verification",
                "source_of_wealth",
                "source_of_funds",
                "beneficial_ownership",
                "risk_factors",
            ],
            "regulatory_authority": "Various",
        },
        {
            "id": "periodic_review",
            "name": "Periodic Review Report",
            "description": "Regular customer review and monitoring summary",
            "sections": [
                "profile_changes",
                "transaction_summary",
                "alert_summary",
                "risk_update",
                "next_review_date",
            ],
            "regulatory_authority": "Internal",
        },
    ]
