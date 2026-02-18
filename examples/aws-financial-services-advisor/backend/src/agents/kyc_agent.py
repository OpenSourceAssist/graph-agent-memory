"""KYC Agent for customer identity verification and due diligence."""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from ..config import get_settings
from .prompts import KYC_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Global agent instance
_kyc_agent: Agent | None = None


@tool
def verify_identity(
    customer_id: str,
    document_type: str = "passport",
    document_number: str | None = None,
) -> dict[str, Any]:
    """Verify a customer's identity using provided documentation.

    Use this tool when onboarding a new customer or refreshing KYC information.
    Checks identity documents against authoritative sources and validates authenticity.

    Args:
        customer_id: The unique customer identifier
        document_type: Type of document (passport, drivers_license, national_id)
        document_number: Document number if available

    Returns:
        Verification result with confidence score and any discrepancies
    """
    logger.info(f"Verifying identity for customer {customer_id} using {document_type}")

    # Simulated verification - in production, integrate with identity verification APIs
    verification_checks = {
        "document_authenticity": random.choice([True, True, True, False]),
        "photo_match": random.choice([True, True, True, False]),
        "data_consistency": random.choice([True, True, False]),
        "expiry_valid": True,
        "issuing_authority_verified": random.choice([True, True, False]),
    }

    passed_checks = sum(verification_checks.values())
    total_checks = len(verification_checks)
    confidence_score = (passed_checks / total_checks) * 100

    discrepancies = [
        check for check, passed in verification_checks.items() if not passed
    ]

    if confidence_score >= 80:
        status = "verified"
    elif confidence_score >= 60:
        status = "partial"
    else:
        status = "unverified"

    return {
        "customer_id": customer_id,
        "document_type": document_type,
        "verification_status": status,
        "confidence_score": round(confidence_score, 2),
        "checks_performed": verification_checks,
        "discrepancies": discrepancies,
        "verification_timestamp": datetime.utcnow().isoformat(),
        "requires_manual_review": status != "verified",
        "next_steps": (
            ["Complete verification"]
            if status == "verified"
            else ["Manual document review required", "Request additional documentation"]
        ),
    }


@tool
def check_documents(
    customer_id: str,
    document_types: list[str] | None = None,
) -> dict[str, Any]:
    """Validate KYC documents for authenticity and completeness.

    Use this tool to check that all required documents are present and valid.

    Args:
        customer_id: The unique customer identifier
        document_types: List of document types to check (defaults to standard set)

    Returns:
        Document validation results with status for each document
    """
    logger.info(f"Checking documents for customer {customer_id}")

    if document_types is None:
        document_types = [
            "identity_document",
            "proof_of_address",
            "source_of_funds",
        ]

    document_results = {}
    for doc_type in document_types:
        # Simulated document check
        is_present = random.choice([True, True, True, False])
        is_valid = random.choice([True, True, False]) if is_present else False
        is_current = random.choice([True, True, False]) if is_valid else False

        document_results[doc_type] = {
            "present": is_present,
            "valid": is_valid,
            "current": is_current,
            "issues": [],
        }

        if not is_present:
            document_results[doc_type]["issues"].append("Document not on file")
        elif not is_valid:
            document_results[doc_type]["issues"].append("Document failed validation")
        elif not is_current:
            document_results[doc_type]["issues"].append("Document expired or outdated")

    complete_count = sum(
        1
        for r in document_results.values()
        if r["present"] and r["valid"] and r["current"]
    )
    completeness_score = (complete_count / len(document_types)) * 100

    return {
        "customer_id": customer_id,
        "documents_checked": document_results,
        "completeness_score": round(completeness_score, 2),
        "all_documents_valid": completeness_score == 100,
        "missing_documents": [
            doc for doc, result in document_results.items() if not result["present"]
        ],
        "invalid_documents": [
            doc
            for doc, result in document_results.items()
            if result["present"] and not result["valid"]
        ],
        "expired_documents": [
            doc
            for doc, result in document_results.items()
            if result["valid"] and not result["current"]
        ],
        "check_timestamp": datetime.utcnow().isoformat(),
    }


@tool
def assess_customer_risk(
    customer_id: str,
    customer_type: str = "individual",
    jurisdiction: str = "US",
    industry: str | None = None,
    include_network_analysis: bool = True,
) -> dict[str, Any]:
    """Calculate risk score for a customer based on their profile and connections.

    Use this tool to evaluate customer risk during onboarding or periodic reviews.
    Considers transaction patterns, geographic risk, and network relationships.

    Args:
        customer_id: The unique customer identifier
        customer_type: Type of customer (individual, corporate, trust)
        jurisdiction: Customer's primary jurisdiction
        industry: Industry sector (for corporate customers)
        include_network_analysis: Whether to analyze connected entities

    Returns:
        Risk assessment with score, factors, and recommendations
    """
    logger.info(f"Assessing risk for customer {customer_id}")

    # Import risk service
    from ..services.risk_service import get_risk_service

    risk_service = get_risk_service()

    # Simulated data - in production, fetch from database/graph
    transaction_data = {
        "avg_monthly_volume": random.uniform(10000, 500000),
        "expected_monthly_volume": random.uniform(50000, 200000),
        "cash_ratio": random.uniform(0, 0.4),
        "high_risk_ratio": random.uniform(0, 0.2),
        "structuring_count": random.randint(0, 3),
        "rapid_movement_count": random.randint(0, 5),
    }

    network_data = {
        "high_risk_count": random.randint(0, 3),
        "pep_count": random.randint(0, 2),
        "sanctioned_count": 0,  # Usually 0 unless flagged
        "shell_company_count": random.randint(0, 2),
        "total_connections": random.randint(5, 20),
    }

    risk_assessment = risk_service.assess_customer_risk(
        customer_id=customer_id,
        customer_type=customer_type,
        jurisdiction=jurisdiction,
        industry=industry,
        transaction_data=transaction_data,
        network_data=network_data if include_network_analysis else None,
    )

    return {
        "customer_id": customer_id,
        "risk_level": risk_assessment.overall_risk.value,
        "risk_score": risk_assessment.risk_score,
        "component_scores": {
            "geographic": risk_assessment.geographic_risk,
            "customer_type": risk_assessment.customer_type_risk,
            "transaction": risk_assessment.transaction_risk,
            "network": risk_assessment.network_risk,
        },
        "risk_factors": risk_assessment.risk_factors,
        "recommendations": risk_assessment.recommendations,
        "assessment_date": risk_assessment.assessment_date.isoformat(),
        "requires_edd": risk_assessment.overall_risk.value in ("high", "critical"),
    }


@tool
def check_adverse_media(
    customer_name: str,
    customer_id: str | None = None,
    include_associates: bool = False,
) -> dict[str, Any]:
    """Screen for negative news and media mentions about a customer.

    Use this tool to identify adverse media that may indicate reputational
    or compliance risk.

    Args:
        customer_name: Name to search for
        customer_id: Optional customer ID for record linking
        include_associates: Whether to also search for known associates

    Returns:
        Media screening results with categorized findings
    """
    logger.info(f"Checking adverse media for {customer_name}")

    # Simulated adverse media check - in production, integrate with news APIs
    has_adverse_media = random.choice([False, False, False, True])

    if has_adverse_media:
        media_categories = [
            "financial_crime",
            "fraud",
            "corruption",
            "litigation",
            "regulatory",
        ]
        selected_categories = random.sample(media_categories, k=random.randint(1, 2))

        articles = [
            {
                "title": f"Sample article about {customer_name}",
                "source": random.choice(["Reuters", "Bloomberg", "WSJ", "Local News"]),
                "date": "2024-06-15",
                "category": cat,
                "relevance_score": random.uniform(0.6, 0.95),
                "summary": f"Article discussing {cat.replace('_', ' ')} concerns",
            }
            for cat in selected_categories
        ]
        risk_level = "high" if "financial_crime" in selected_categories else "medium"
    else:
        articles = []
        selected_categories = []
        risk_level = "low"

    return {
        "customer_name": customer_name,
        "customer_id": customer_id,
        "screening_date": datetime.utcnow().isoformat(),
        "adverse_media_found": has_adverse_media,
        "article_count": len(articles),
        "categories": selected_categories,
        "articles": articles,
        "risk_level": risk_level,
        "recommendation": (
            "Review flagged articles and assess impact"
            if has_adverse_media
            else "No adverse media concerns identified"
        ),
        "next_review_date": "2025-01-15",
    }


def create_kyc_agent() -> Agent:
    """Create the KYC Agent for identity verification.

    Returns:
        Configured Strands Agent for KYC operations
    """
    settings = get_settings()

    kyc_tools = [
        verify_identity,
        check_documents,
        assess_customer_risk,
        check_adverse_media,
    ]

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock.model_id,
            region_name=settings.aws.region,
        ),
        tools=kyc_tools,
        system_prompt=KYC_AGENT_SYSTEM_PROMPT,
    )


def get_kyc_agent() -> Agent:
    """Get or create the global KYC Agent instance.

    Returns:
        KYC Agent instance
    """
    global _kyc_agent
    if _kyc_agent is None:
        _kyc_agent = create_kyc_agent()
    return _kyc_agent
