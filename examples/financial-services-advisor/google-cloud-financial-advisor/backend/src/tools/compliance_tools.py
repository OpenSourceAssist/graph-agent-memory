"""Compliance tools for sanctions screening, PEP verification, and reporting.

These tools are used by the Compliance Agent to perform regulatory checks
and prepare required reports. Sanctions and PEP data is queried from Neo4j.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..services.neo4j_service import Neo4jDomainService

logger = logging.getLogger(__name__)


async def check_sanctions(
    entity_name: str,
    lists: list[str] | None = None,
    include_aliases: bool = True,
    *,
    neo4j_service: Neo4jDomainService,
) -> dict[str, Any]:
    """Screen an entity against sanctions lists."""
    logger.info(f"Checking sanctions for: {entity_name}")

    results = await neo4j_service.check_sanctions(entity_name, include_aliases=include_aliases)

    matches = []
    for r in results:
        entity = r.get("entity", {})
        match = {
            "match_type": r.get("match_type", "PARTIAL"),
            "sanctioned_name": entity.get("name"),
            "list": entity.get("list"),
            "reason": entity.get("reason"),
            "date_added": entity.get("added"),
            "confidence": r.get("confidence", 0.7),
        }
        if r.get("match_type") == "ALIAS":
            match["matched_alias"] = entity_name
        matches.append(match)

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


async def verify_pep_status(
    person_name: str,
    include_relatives: bool = True,
    include_associates: bool = False,
    *,
    neo4j_service: Neo4jDomainService,
) -> dict[str, Any]:
    """Verify if a person is a Politically Exposed Person."""
    logger.info(f"Verifying PEP status for: {person_name}")

    results = await neo4j_service.check_pep(person_name, include_relatives=include_relatives)

    matches = []
    for r in results:
        pep = r.get("pep", {})
        match_type = r.get("match_type", "POTENTIAL_PEP")
        match = {
            "match_type": match_type,
            "name": pep.get("name"),
            "confidence": r.get("confidence", 0.7),
        }
        if match_type == "PEP_RELATIVE":
            match["relation"] = pep.get("relation")
            match["related_pep"] = pep.get("pep_name")
        else:
            match["position"] = pep.get("position")
            match["country"] = pep.get("country")
            match["tier"] = pep.get("tier")
        matches.append(match)

    if matches:
        has_direct = any(m["match_type"] == "DIRECT_PEP" for m in matches)
        is_pep = has_direct or any(m["match_type"] == "POTENTIAL_PEP" for m in matches)
        status = "PEP_CONFIRMED" if has_direct else "PEP_ASSOCIATED" if matches else "CLEAR"
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


async def generate_sar_report(
    customer_id: str,
    suspicious_activity: str,
    transaction_ids: list[str] | None = None,
    narrative: str | None = None,
    *,
    neo4j_service: Neo4jDomainService,
) -> dict[str, Any]:
    """Generate a Suspicious Activity Report (SAR) draft."""
    logger.info(f"Generating SAR for customer {customer_id}")

    # Fetch customer data from Neo4j
    customer = await neo4j_service.get_customer(customer_id)
    customer_name = customer.get("name", "Unknown") if customer else "Unknown"

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

    # Get transaction details if IDs provided
    txn_count = 0
    if transaction_ids:
        txn_count = len(transaction_ids)

    sar_draft = {
        "sar_reference": sar_reference,
        "filing_institution": "Financial Services Demo Bank",
        "subject_information": {
            "customer_id": customer_id,
            "customer_name": customer_name,
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
            "count": txn_count,
        },
        "narrative": narrative or "Detailed narrative to be completed by compliance officer.",
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


async def assess_regulatory_requirements(
    customer_id: str,
    jurisdictions: list[str] | None = None,
    transaction_types: list[str] | None = None,
    *,
    neo4j_service: Neo4jDomainService,
) -> dict[str, Any]:
    """Assess applicable regulatory requirements for a customer."""
    logger.info(f"Assessing regulatory requirements for {customer_id}")

    # Fetch customer to determine jurisdictions from their profile and network
    customer = await neo4j_service.get_customer(customer_id)

    if not jurisdictions:
        jurisdictions = ["US"]
        if customer:
            nationality = customer.get("nationality")
            if nationality and nationality != "US":
                jurisdictions.append(nationality)
            cust_jurisdiction = customer.get("jurisdiction")
            if cust_jurisdiction and cust_jurisdiction not in jurisdictions:
                jurisdictions.append(cust_jurisdiction)

    if not transaction_types:
        # Infer from actual transactions
        transactions = await neo4j_service.get_transactions(customer_id)
        transaction_types = (
            list({t["type"] for t in transactions}) if transactions else ["wire", "cash"]
        )

    applicable_regulations = []
    filing_requirements = []

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

        if any("cash" in t for t in transaction_types):
            filing_requirements.append(
                {
                    "filing_type": "CTR",
                    "trigger": "Cash transactions over $10,000",
                    "deadline": "15 days",
                }
            )

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
