"""Compliance tools for sanctions screening, PEP verification, and reporting.

These tools are used by the Compliance Agent to perform regulatory checks
and prepare required reports.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Sample sanctions list (in production, this would use real sanctions APIs)
SAMPLE_SANCTIONS_LIST = {
    "entities": [
        {
            "name": "Sanctioned Corp Ltd",
            "list": "OFAC SDN",
            "reason": "Narcotics trafficking",
            "added": "2020-01-15",
        },
        {
            "name": "Bad Actor Holdings",
            "list": "EU Consolidated",
            "reason": "Human rights violations",
            "added": "2021-03-22",
        },
        {
            "name": "Ivan Petrov",
            "list": "OFAC SDN",
            "reason": "Russian sanctions",
            "added": "2022-02-28",
        },
    ],
    "aliases": {
        "Sanctioned Corp Ltd": ["Sanctioned Corp", "SC Ltd"],
        "Ivan Petrov": ["I. Petrov", "Petrov Ivan"],
    },
}

# Sample PEP database
SAMPLE_PEP_DATABASE = {
    "peps": [
        {
            "name": "Carlos Rodriguez",
            "position": "Minister of Finance",
            "country": "MX",
            "tier": 1,
        },
        {
            "name": "Elena Volkov",
            "position": "Former Deputy Prime Minister",
            "country": "RU",
            "tier": 1,
        },
        {
            "name": "James Wilson",
            "position": "State Senator",
            "country": "US",
            "tier": 2,
        },
    ],
    "pep_relatives": [
        {"name": "Maria Rodriguez", "relation": "spouse", "pep": "Carlos Rodriguez"},
    ],
}


def check_sanctions(
    entity_name: str,
    lists: list[str] | None = None,
    include_aliases: bool = True,
) -> dict[str, Any]:
    """Screen an entity against sanctions lists.

    Checks the entity name against OFAC, EU, UN, and other
    sanctions lists for potential matches.

    Args:
        entity_name: Name of the entity to screen.
        lists: Specific lists to check (default: all).
        include_aliases: Whether to check known aliases.

    Returns:
        Sanctions screening results with match details.
    """
    logger.info(f"Checking sanctions for: {entity_name}")

    matches = []
    entity_lower = entity_name.lower()

    # Check direct matches
    for sanctioned in SAMPLE_SANCTIONS_LIST["entities"]:
        if sanctioned["name"].lower() == entity_lower:
            matches.append(
                {
                    "match_type": "EXACT",
                    "sanctioned_name": sanctioned["name"],
                    "list": sanctioned["list"],
                    "reason": sanctioned["reason"],
                    "date_added": sanctioned["added"],
                    "confidence": 1.0,
                }
            )
        elif (
            entity_lower in sanctioned["name"].lower()
            or sanctioned["name"].lower() in entity_lower
        ):
            matches.append(
                {
                    "match_type": "PARTIAL",
                    "sanctioned_name": sanctioned["name"],
                    "list": sanctioned["list"],
                    "reason": sanctioned["reason"],
                    "date_added": sanctioned["added"],
                    "confidence": 0.7,
                }
            )

    # Check aliases if enabled
    if include_aliases:
        for sanctioned_name, aliases in SAMPLE_SANCTIONS_LIST["aliases"].items():
            for alias in aliases:
                if alias.lower() == entity_lower:
                    # Find the original entry
                    for sanctioned in SAMPLE_SANCTIONS_LIST["entities"]:
                        if sanctioned["name"] == sanctioned_name:
                            matches.append(
                                {
                                    "match_type": "ALIAS",
                                    "matched_alias": alias,
                                    "sanctioned_name": sanctioned_name,
                                    "list": sanctioned["list"],
                                    "reason": sanctioned["reason"],
                                    "date_added": sanctioned["added"],
                                    "confidence": 0.95,
                                }
                            )
                            break

    # Determine status
    if matches:
        has_exact = any(m["match_type"] == "EXACT" for m in matches)
        status = "HIT" if has_exact else "POTENTIAL_MATCH"
        risk_level = "CRITICAL" if has_exact else "HIGH"
    else:
        status = "CLEAR"
        risk_level = "LOW"

    return {
        "entity_name": entity_name,
        "screening_status": status,
        "lists_checked": lists or ["OFAC SDN", "EU Consolidated", "UN Sanctions"],
        "matches_found": len(matches),
        "matches": matches,
        "risk_level": risk_level,
        "include_aliases": include_aliases,
        "requires_escalation": status == "HIT",
        "timestamp": datetime.now().isoformat(),
    }


def verify_pep_status(
    person_name: str,
    include_relatives: bool = True,
    include_associates: bool = False,
) -> dict[str, Any]:
    """Verify if a person is a Politically Exposed Person.

    Checks against PEP databases including current and former
    political figures, and optionally their relatives.

    Args:
        person_name: Name of the person to verify.
        include_relatives: Check for relatives of PEPs.
        include_associates: Check for close associates.

    Returns:
        PEP verification results with match details.
    """
    logger.info(f"Verifying PEP status for: {person_name}")

    person_lower = person_name.lower()
    matches = []

    # Check direct PEP matches
    for pep in SAMPLE_PEP_DATABASE["peps"]:
        if pep["name"].lower() == person_lower:
            matches.append(
                {
                    "match_type": "DIRECT_PEP",
                    "name": pep["name"],
                    "position": pep["position"],
                    "country": pep["country"],
                    "tier": pep["tier"],
                    "confidence": 1.0,
                }
            )
        elif person_lower in pep["name"].lower() or pep["name"].lower() in person_lower:
            matches.append(
                {
                    "match_type": "POTENTIAL_PEP",
                    "name": pep["name"],
                    "position": pep["position"],
                    "country": pep["country"],
                    "tier": pep["tier"],
                    "confidence": 0.7,
                }
            )

    # Check PEP relatives if enabled
    if include_relatives:
        for relative in SAMPLE_PEP_DATABASE["pep_relatives"]:
            if relative["name"].lower() == person_lower:
                matches.append(
                    {
                        "match_type": "PEP_RELATIVE",
                        "name": relative["name"],
                        "relation": relative["relation"],
                        "related_pep": relative["pep"],
                        "confidence": 0.95,
                    }
                )

    # Determine status
    if matches:
        has_direct = any(m["match_type"] == "DIRECT_PEP" for m in matches)
        is_pep = has_direct or any(m["match_type"] == "POTENTIAL_PEP" for m in matches)
        status = (
            "PEP_CONFIRMED" if has_direct else "PEP_ASSOCIATED" if matches else "CLEAR"
        )
        risk_level = "HIGH" if is_pep else "MEDIUM"
    else:
        status = "CLEAR"
        risk_level = "LOW"

    return {
        "person_name": person_name,
        "pep_status": status,
        "is_pep": status in ["PEP_CONFIRMED", "PEP_ASSOCIATED"],
        "matches_found": len(matches),
        "matches": matches,
        "risk_level": risk_level,
        "include_relatives": include_relatives,
        "include_associates": include_associates,
        "enhanced_due_diligence_required": status != "CLEAR",
        "timestamp": datetime.now().isoformat(),
    }


def generate_sar_report(
    customer_id: str,
    suspicious_activity: str,
    transaction_ids: list[str] | None = None,
    narrative: str | None = None,
) -> dict[str, Any]:
    """Generate a Suspicious Activity Report (SAR) draft.

    Creates a structured SAR document based on investigation findings
    for regulatory filing.

    Args:
        customer_id: The customer under investigation.
        suspicious_activity: Type of suspicious activity.
        transaction_ids: Related transaction identifiers.
        narrative: Detailed narrative of findings.

    Returns:
        SAR draft with all required fields.
    """
    logger.info(f"Generating SAR for customer {customer_id}")

    # In production, this would pull real customer/transaction data
    sar_reference = f"SAR-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    activity_codes = {
        "structuring": "31",
        "money_laundering": "35",
        "terrorist_financing": "39",
        "fraud": "22",
        "identity_theft": "18",
        "wire_fraud": "24",
    }

    activity_code = activity_codes.get(suspicious_activity.lower(), "99")

    sar_draft = {
        "sar_reference": sar_reference,
        "filing_institution": "Financial Services Demo Bank",
        "subject_information": {
            "customer_id": customer_id,
            "subject_type": "customer",
        },
        "suspicious_activity": {
            "type": suspicious_activity,
            "activity_code": activity_code,
            "date_range": {
                "start": "2024-01-01",
                "end": datetime.now().strftime("%Y-%m-%d"),
            },
        },
        "transaction_summary": {
            "transaction_ids": transaction_ids or [],
            "count": len(transaction_ids) if transaction_ids else 0,
        },
        "narrative": narrative
        or "Detailed narrative to be completed by compliance officer.",
        "filing_status": "DRAFT",
        "filing_deadline": "Within 30 days of detection",
        "created_by": "AI Compliance Assistant",
        "timestamp": datetime.now().isoformat(),
    }

    return {
        "status": "SAR_DRAFT_CREATED",
        "sar_reference": sar_reference,
        "sar_document": sar_draft,
        "next_steps": [
            "Review and complete narrative section",
            "Verify all subject information",
            "Obtain supervisor approval",
            "Submit via BSA E-Filing",
        ],
        "filing_deadline": "30 days from activity detection",
        "timestamp": datetime.now().isoformat(),
    }


def assess_regulatory_requirements(
    customer_id: str,
    jurisdictions: list[str] | None = None,
    transaction_types: list[str] | None = None,
) -> dict[str, Any]:
    """Assess applicable regulatory requirements for a customer.

    Determines which regulations apply based on customer type,
    jurisdictions involved, and transaction patterns.

    Args:
        customer_id: The customer identifier.
        jurisdictions: Jurisdictions involved in transactions.
        transaction_types: Types of transactions conducted.

    Returns:
        Regulatory assessment with applicable requirements.
    """
    logger.info(f"Assessing regulatory requirements for {customer_id}")

    jurisdictions = jurisdictions or ["US"]
    transaction_types = transaction_types or ["wire", "cash"]

    applicable_regulations = []
    filing_requirements = []

    # US Regulations
    if "US" in jurisdictions:
        applicable_regulations.extend(
            [
                {
                    "regulation": "Bank Secrecy Act (BSA)",
                    "jurisdiction": "US",
                    "requirements": [
                        "CDD",
                        "EDD for high-risk",
                        "SAR filing",
                        "CTR filing",
                    ],
                },
                {
                    "regulation": "USA PATRIOT Act",
                    "jurisdiction": "US",
                    "requirements": [
                        "CIP compliance",
                        "314(a) requests",
                        "314(b) sharing",
                    ],
                },
            ]
        )

        # CTR requirement for cash transactions
        if "cash" in transaction_types:
            filing_requirements.append(
                {
                    "filing_type": "CTR",
                    "trigger": "Cash transactions over $10,000",
                    "deadline": "15 days",
                }
            )

    # EU Regulations
    eu_countries = ["DE", "FR", "ES", "IT", "NL"]
    if any(j in eu_countries for j in jurisdictions):
        applicable_regulations.append(
            {
                "regulation": "6th EU AML Directive (6AMLD)",
                "jurisdiction": "EU",
                "requirements": [
                    "CDD",
                    "Beneficial ownership verification",
                    "Risk assessment",
                ],
            }
        )

    # High-risk jurisdiction requirements
    high_risk = ["KY", "BVI", "PA", "SC"]
    if any(j in high_risk for j in jurisdictions):
        applicable_regulations.append(
            {
                "regulation": "Enhanced Due Diligence",
                "jurisdiction": "Global",
                "requirements": [
                    "Source of funds verification",
                    "Enhanced monitoring",
                    "Senior management approval",
                ],
            }
        )
        filing_requirements.append(
            {
                "filing_type": "EDD Documentation",
                "trigger": "High-risk jurisdiction involvement",
                "deadline": "Before relationship establishment",
            }
        )

    # FATF requirements
    applicable_regulations.append(
        {
            "regulation": "FATF Recommendations",
            "jurisdiction": "International",
            "requirements": [
                "Risk-based approach",
                "Record keeping (5 years)",
                "Suspicious transaction reporting",
            ],
        }
    )

    return {
        "customer_id": customer_id,
        "jurisdictions_analyzed": jurisdictions,
        "transaction_types": transaction_types,
        "applicable_regulations": applicable_regulations,
        "filing_requirements": filing_requirements,
        "compliance_actions_required": [
            "Maintain complete transaction records",
            "Perform ongoing monitoring",
            "File required reports within deadlines",
            "Document all compliance decisions",
        ],
        "review_frequency": "Annual minimum, quarterly for high-risk",
        "timestamp": datetime.now().isoformat(),
    }
