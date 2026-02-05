"""KYC (Know Your Customer) tools for identity verification and due diligence.

These tools are used by the KYC Agent to perform customer verification tasks.
In a production environment, these would integrate with actual verification
services and databases.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Sample customer database (in production, this would be a real database)
SAMPLE_CUSTOMERS = {
    "CUST-001": {
        "id": "CUST-001",
        "name": "John Smith",
        "type": "individual",
        "date_of_birth": "1985-03-15",
        "nationality": "US",
        "address": "123 Main St, New York, NY 10001",
        "occupation": "Software Engineer",
        "employer": "Tech Corp Inc",
        "account_opened": "2020-01-15",
        "documents": {
            "passport": {"status": "verified", "expiry": "2028-03-15"},
            "utility_bill": {"status": "verified", "date": "2024-01-01"},
        },
        "risk_factors": [],
        "kyc_status": "approved",
    },
    "CUST-002": {
        "id": "CUST-002",
        "name": "Maria Garcia",
        "type": "individual",
        "date_of_birth": "1978-07-22",
        "nationality": "ES",
        "address": "456 Oak Ave, Miami, FL 33101",
        "occupation": "Import/Export Business Owner",
        "employer": "Garcia Trading LLC",
        "account_opened": "2019-06-20",
        "documents": {
            "passport": {"status": "verified", "expiry": "2026-07-22"},
            "utility_bill": {"status": "pending", "date": None},
        },
        "risk_factors": ["high_risk_business", "international_transactions"],
        "kyc_status": "enhanced_due_diligence",
    },
    "CUST-003": {
        "id": "CUST-003",
        "name": "Global Holdings Ltd",
        "type": "corporate",
        "incorporation_date": "2015-09-10",
        "jurisdiction": "BVI",
        "registered_address": "P.O. Box 123, Road Town, Tortola, BVI",
        "business_type": "Investment Holding",
        "directors": ["Nominee Director Services Ltd"],
        "account_opened": "2021-03-05",
        "documents": {
            "certificate_of_incorporation": {
                "status": "verified",
                "date": "2015-09-10",
            },
            "register_of_directors": {"status": "pending", "date": None},
            "proof_of_address": {"status": "missing", "date": None},
        },
        "risk_factors": [
            "offshore_jurisdiction",
            "nominee_directors",
            "shell_company_indicators",
        ],
        "kyc_status": "under_review",
    },
}


def verify_identity(customer_id: str) -> dict[str, Any]:
    """Verify customer identity against available records.

    Checks customer identity documents, personal information consistency,
    and verifies against known records.

    Args:
        customer_id: The customer identifier to verify.

    Returns:
        Identity verification results including status and findings.
    """
    logger.info(f"Verifying identity for customer {customer_id}")

    customer = SAMPLE_CUSTOMERS.get(customer_id)
    if not customer:
        return {
            "customer_id": customer_id,
            "status": "NOT_FOUND",
            "message": f"Customer {customer_id} not found in database",
            "verified": False,
            "timestamp": datetime.now().isoformat(),
        }

    # Check document status
    documents = customer.get("documents", {})
    verified_docs = sum(1 for d in documents.values() if d.get("status") == "verified")
    total_docs = len(documents)

    # Determine verification status
    if customer["type"] == "individual":
        required_docs = ["passport", "utility_bill"]
    else:
        required_docs = [
            "certificate_of_incorporation",
            "register_of_directors",
            "proof_of_address",
        ]

    missing_docs = [
        doc
        for doc in required_docs
        if doc not in documents or documents[doc].get("status") != "verified"
    ]

    status = "VERIFIED" if not missing_docs else "PENDING"

    return {
        "customer_id": customer_id,
        "customer_name": customer.get("name"),
        "customer_type": customer.get("type"),
        "status": status,
        "verified": status == "VERIFIED",
        "documents_verified": f"{verified_docs}/{total_docs}",
        "missing_documents": missing_docs,
        "risk_factors": customer.get("risk_factors", []),
        "kyc_status": customer.get("kyc_status"),
        "timestamp": datetime.now().isoformat(),
    }


def check_documents(
    customer_id: str,
    document_type: str | None = None,
) -> dict[str, Any]:
    """Check document status and validity for a customer.

    Reviews submitted documents for completeness, authenticity indicators,
    and expiration status.

    Args:
        customer_id: The customer identifier.
        document_type: Specific document to check (optional).

    Returns:
        Document verification results.
    """
    logger.info(f"Checking documents for customer {customer_id}")

    customer = SAMPLE_CUSTOMERS.get(customer_id)
    if not customer:
        return {
            "customer_id": customer_id,
            "status": "NOT_FOUND",
            "message": f"Customer {customer_id} not found",
            "timestamp": datetime.now().isoformat(),
        }

    documents = customer.get("documents", {})

    if document_type:
        if document_type not in documents:
            return {
                "customer_id": customer_id,
                "document_type": document_type,
                "status": "NOT_SUBMITTED",
                "message": f"Document '{document_type}' has not been submitted",
                "timestamp": datetime.now().isoformat(),
            }
        doc_info = documents[document_type]
        return {
            "customer_id": customer_id,
            "document_type": document_type,
            "status": doc_info.get("status", "unknown").upper(),
            "expiry_date": doc_info.get("expiry"),
            "submission_date": doc_info.get("date"),
            "timestamp": datetime.now().isoformat(),
        }

    # Return all documents
    doc_summary = []
    for doc_type, doc_info in documents.items():
        doc_summary.append(
            {
                "type": doc_type,
                "status": doc_info.get("status", "unknown").upper(),
                "expiry_date": doc_info.get("expiry"),
                "submission_date": doc_info.get("date"),
            }
        )

    return {
        "customer_id": customer_id,
        "customer_name": customer.get("name"),
        "total_documents": len(documents),
        "documents": doc_summary,
        "timestamp": datetime.now().isoformat(),
    }


def assess_customer_risk(customer_id: str) -> dict[str, Any]:
    """Assess overall KYC risk level for a customer.

    Evaluates customer risk based on profile, documents, jurisdiction,
    business type, and other factors.

    Args:
        customer_id: The customer identifier.

    Returns:
        Risk assessment with score and contributing factors.
    """
    logger.info(f"Assessing customer risk for {customer_id}")

    customer = SAMPLE_CUSTOMERS.get(customer_id)
    if not customer:
        return {
            "customer_id": customer_id,
            "status": "NOT_FOUND",
            "message": f"Customer {customer_id} not found",
            "timestamp": datetime.now().isoformat(),
        }

    # Calculate risk score based on factors
    base_score = 20  # Base risk
    risk_factors = customer.get("risk_factors", [])

    risk_weights = {
        "offshore_jurisdiction": 25,
        "nominee_directors": 20,
        "shell_company_indicators": 30,
        "high_risk_business": 15,
        "international_transactions": 10,
        "pep_connection": 25,
        "adverse_media": 20,
    }

    total_score = base_score
    contributing_factors = []

    for factor in risk_factors:
        weight = risk_weights.get(factor, 10)
        total_score += weight
        contributing_factors.append(
            {
                "factor": factor,
                "weight": weight,
                "description": factor.replace("_", " ").title(),
            }
        )

    # Check document status
    documents = customer.get("documents", {})
    pending_docs = sum(1 for d in documents.values() if d.get("status") != "verified")
    if pending_docs > 0:
        total_score += pending_docs * 5
        contributing_factors.append(
            {
                "factor": "incomplete_documentation",
                "weight": pending_docs * 5,
                "description": f"{pending_docs} documents pending verification",
            }
        )

    # Cap score at 100
    total_score = min(total_score, 100)

    # Determine risk level
    if total_score >= 75:
        risk_level = "CRITICAL"
    elif total_score >= 50:
        risk_level = "HIGH"
    elif total_score >= 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "customer_id": customer_id,
        "customer_name": customer.get("name"),
        "risk_score": total_score,
        "risk_level": risk_level,
        "contributing_factors": contributing_factors,
        "kyc_status": customer.get("kyc_status"),
        "recommendation": _get_risk_recommendation(risk_level),
        "timestamp": datetime.now().isoformat(),
    }


def check_adverse_media(
    customer_id: str,
    include_associates: bool = False,
) -> dict[str, Any]:
    """Screen customer for adverse media coverage.

    Searches news and media databases for negative coverage related
    to the customer.

    Args:
        customer_id: The customer identifier.
        include_associates: Whether to include associated entities.

    Returns:
        Adverse media screening results.
    """
    logger.info(f"Checking adverse media for customer {customer_id}")

    customer = SAMPLE_CUSTOMERS.get(customer_id)
    if not customer:
        return {
            "customer_id": customer_id,
            "status": "NOT_FOUND",
            "message": f"Customer {customer_id} not found",
            "timestamp": datetime.now().isoformat(),
        }

    # Sample adverse media results (in production, this would call a real service)
    adverse_media_database = {
        "CUST-003": [
            {
                "source": "Financial Times",
                "date": "2023-06-15",
                "headline": "BVI Shell Companies Under Scrutiny",
                "relevance": "MEDIUM",
                "category": "regulatory_concern",
            },
        ],
    }

    media_hits = adverse_media_database.get(customer_id, [])

    return {
        "customer_id": customer_id,
        "customer_name": customer.get("name"),
        "screening_status": "COMPLETED",
        "hits_found": len(media_hits),
        "media_hits": media_hits,
        "risk_indicator": "HIGH" if media_hits else "LOW",
        "include_associates": include_associates,
        "timestamp": datetime.now().isoformat(),
    }


def _get_risk_recommendation(risk_level: str) -> str:
    """Get recommendation based on risk level."""
    recommendations = {
        "CRITICAL": "Immediate escalation required. Consider account restriction pending investigation.",
        "HIGH": "Enhanced due diligence required. Senior review recommended.",
        "MEDIUM": "Standard enhanced monitoring. Periodic review required.",
        "LOW": "Standard monitoring procedures apply.",
    }
    return recommendations.get(risk_level, "Review required.")
