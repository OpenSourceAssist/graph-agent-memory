"""Compliance Agent for regulatory compliance and report generation."""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from ..config import get_settings
from .prompts import COMPLIANCE_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Global agent instance
_compliance_agent: Agent | None = None

# Sample sanctions list entries (simulated)
SAMPLE_SANCTIONS_ENTRIES = [
    {"name": "Bad Actor LLC", "list": "OFAC SDN", "type": "entity"},
    {"name": "Suspicious Trading Co", "list": "UN Consolidated", "type": "entity"},
    {"name": "John Sanctioned", "list": "OFAC SDN", "type": "individual"},
]

# Sample PEP database entries (simulated)
SAMPLE_PEP_ENTRIES = [
    {
        "name": "Minister Example",
        "country": "Countryland",
        "position": "Finance Minister",
    },
    {"name": "Senator Sample", "country": "US", "position": "Senator"},
]


@tool
def check_sanctions(
    entity_name: str,
    entity_type: str = "individual",
    additional_identifiers: dict[str, str] | None = None,
    lists_to_check: list[str] | None = None,
) -> dict[str, Any]:
    """Screen an entity against sanctions lists.

    Use this tool to check customers, counterparties, or related entities
    against OFAC, UN, EU, and other sanctions lists.

    Args:
        entity_name: Name of the entity to screen
        entity_type: Type (individual, entity, vessel)
        additional_identifiers: Additional IDs (passport, tax_id, etc.)
        lists_to_check: Specific lists to check (defaults to all)

    Returns:
        Screening results with any matches and confidence scores
    """
    logger.info(f"Checking sanctions for {entity_name}")

    if lists_to_check is None:
        lists_to_check = [
            "OFAC SDN",
            "UN Consolidated",
            "EU Consolidated",
            "UK Sanctions",
        ]

    # Simulated sanctions screening
    # In production, integrate with sanctions screening API
    matches = []

    # Small chance of a match for simulation
    if random.random() > 0.95:
        sample_match = random.choice(SAMPLE_SANCTIONS_ENTRIES)
        matches.append(
            {
                "matched_name": sample_match["name"],
                "matched_list": sample_match["list"],
                "match_score": random.uniform(0.85, 0.99),
                "match_type": "exact" if random.random() > 0.5 else "fuzzy",
                "matched_identifiers": [],
                "list_entry_id": f"ENTRY-{random.randint(10000, 99999)}",
            }
        )

    screening_results = {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "additional_identifiers": additional_identifiers or {},
        "lists_checked": lists_to_check,
        "screening_date": datetime.utcnow().isoformat(),
        "matches_found": len(matches) > 0,
        "match_count": len(matches),
        "matches": matches,
        "status": "HIT" if matches else "CLEAR",
        "risk_level": "critical" if matches else "low",
        "required_actions": (
            [
                "IMMEDIATE: Escalate to compliance officer",
                "Freeze any pending transactions",
                "Document all interactions",
                "File SAR if appropriate",
            ]
            if matches
            else ["No action required - screening clear"]
        ),
    }

    return screening_results


@tool
def verify_pep(
    individual_name: str,
    country: str | None = None,
    date_of_birth: str | None = None,
    check_relatives: bool = True,
    check_associates: bool = True,
) -> dict[str, Any]:
    """Check if an individual is a Politically Exposed Person (PEP).

    Use this tool to identify PEPs and their close associates or family
    members who require enhanced due diligence.

    Args:
        individual_name: Name of the individual to check
        country: Country of nationality/residence
        date_of_birth: Date of birth for matching
        check_relatives: Include relatives/family members
        check_associates: Include close associates

    Returns:
        PEP screening results with position and relationship details
    """
    logger.info(f"Verifying PEP status for {individual_name}")

    # Simulated PEP screening
    matches = []

    if random.random() > 0.9:
        sample_pep = random.choice(SAMPLE_PEP_ENTRIES)
        relationship = random.choice(["direct", "relative", "associate"])

        matches.append(
            {
                "matched_name": sample_pep["name"],
                "match_score": random.uniform(0.8, 0.98),
                "pep_type": "direct" if relationship == "direct" else "rca",
                "position": sample_pep["position"],
                "country": sample_pep["country"],
                "relationship": relationship,
                "status": random.choice(["current", "former"]),
                "last_updated": "2024-01-15",
            }
        )

    is_pep = len(matches) > 0

    return {
        "individual_name": individual_name,
        "search_parameters": {
            "country": country,
            "date_of_birth": date_of_birth,
            "check_relatives": check_relatives,
            "check_associates": check_associates,
        },
        "screening_date": datetime.utcnow().isoformat(),
        "is_pep": is_pep,
        "pep_type": matches[0]["pep_type"] if matches else None,
        "matches": matches,
        "match_count": len(matches),
        "risk_level": "high" if is_pep else "low",
        "required_actions": (
            [
                "Apply Enhanced Due Diligence (EDD)",
                "Obtain senior management approval",
                "Document source of wealth",
                "Implement enhanced monitoring",
            ]
            if is_pep
            else ["Standard due diligence sufficient"]
        ),
    }


@tool
def generate_report(
    report_type: str,
    customer_id: str,
    investigation_id: str | None = None,
    include_sections: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a compliance report (SAR, Risk Assessment, etc.).

    Use this tool to create formatted compliance reports based on
    investigation findings and customer data.

    Args:
        report_type: Type of report (sar, risk_assessment, edd, periodic_review)
        customer_id: Customer the report is about
        investigation_id: Related investigation ID if applicable
        include_sections: Specific sections to include

    Returns:
        Generated report metadata and content structure
    """
    logger.info(f"Generating {report_type} report for customer {customer_id}")

    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

    if include_sections is None:
        if report_type == "sar":
            include_sections = [
                "subject_information",
                "suspicious_activity",
                "transaction_summary",
                "narrative",
            ]
        elif report_type == "risk_assessment":
            include_sections = [
                "customer_profile",
                "risk_scoring",
                "transaction_analysis",
                "recommendations",
            ]
        else:
            include_sections = ["summary", "findings", "recommendations"]

    # Generate report sections
    sections = {}
    for section in include_sections:
        sections[section] = {
            "status": "generated",
            "word_count": random.randint(100, 500),
            "last_updated": datetime.utcnow().isoformat(),
        }

    report_metadata = {
        "report_id": report_id,
        "report_type": report_type,
        "customer_id": customer_id,
        "investigation_id": investigation_id,
        "status": "draft",
        "created_at": datetime.utcnow().isoformat(),
        "created_by": "compliance_agent",
        "sections": sections,
        "total_pages": random.randint(3, 15),
        "review_status": "pending_review",
        "filing_deadline": (datetime.utcnow() + timedelta(days=30)).isoformat()
        if report_type == "sar"
        else None,
        "next_steps": [
            "Review generated content for accuracy",
            "Attach supporting documentation",
            "Submit for supervisor review",
            "File with regulator"
            if report_type == "sar"
            else "Store in compliance records",
        ],
    }

    return report_metadata


@tool
def assess_regulatory_requirements(
    customer_type: str,
    jurisdiction: str,
    products: list[str],
    transaction_types: list[str] | None = None,
) -> dict[str, Any]:
    """Determine applicable regulatory requirements for a customer.

    Use this tool to identify which regulations apply based on customer
    characteristics, jurisdiction, and products/services used.

    Args:
        customer_type: Type of customer (individual, corporate, etc.)
        jurisdiction: Customer's jurisdiction
        products: Products/services the customer uses
        transaction_types: Types of transactions involved

    Returns:
        Applicable regulations and compliance requirements
    """
    logger.info(
        f"Assessing regulatory requirements for {customer_type} in {jurisdiction}"
    )

    # Determine applicable regulations based on jurisdiction
    regulations = []

    # US regulations
    if jurisdiction == "US":
        regulations.extend(
            [
                {
                    "name": "Bank Secrecy Act (BSA)",
                    "authority": "FinCEN",
                    "requirements": ["CTR filing", "SAR filing", "AML program"],
                },
                {
                    "name": "USA PATRIOT Act",
                    "authority": "FinCEN",
                    "requirements": ["CIP", "CDD", "Enhanced due diligence"],
                },
            ]
        )

    # EU regulations
    if jurisdiction in ["DE", "FR", "IT", "ES", "NL"] or jurisdiction == "EU":
        regulations.extend(
            [
                {
                    "name": "6th AML Directive (6AMLD)",
                    "authority": "EU",
                    "requirements": [
                        "AML program",
                        "Beneficial ownership",
                        "PEP screening",
                    ],
                },
                {
                    "name": "EU AI Act",
                    "authority": "EU",
                    "requirements": [
                        "AI transparency",
                        "Explainability",
                        "Human oversight",
                    ],
                },
            ]
        )

    # UK regulations
    if jurisdiction == "UK":
        regulations.append(
            {
                "name": "Money Laundering Regulations 2017",
                "authority": "FCA",
                "requirements": ["Risk assessment", "CDD", "Record keeping"],
            }
        )

    # FATF recommendations (global)
    regulations.append(
        {
            "name": "FATF Recommendations",
            "authority": "FATF",
            "requirements": [
                "Risk-based approach",
                "CDD",
                "Suspicious transaction reporting",
            ],
        }
    )

    # Product-specific requirements
    product_requirements = []
    if "wire_transfer" in products:
        product_requirements.append("Travel Rule compliance")
    if "cryptocurrency" in products:
        product_requirements.append("VASP registration")
    if "correspondent_banking" in products:
        product_requirements.append("Enhanced correspondent due diligence")

    # Risk-based requirements
    due_diligence_level = "enhanced" if customer_type == "corporate" else "standard"

    return {
        "customer_type": customer_type,
        "jurisdiction": jurisdiction,
        "products": products,
        "applicable_regulations": regulations,
        "regulation_count": len(regulations),
        "product_specific_requirements": product_requirements,
        "due_diligence_level": due_diligence_level,
        "key_requirements": [
            "Customer identification program (CIP)",
            "Customer due diligence (CDD)",
            "Ongoing monitoring",
            "Suspicious activity reporting",
            "Record retention (5+ years)",
        ],
        "reporting_obligations": [
            "Suspicious Activity Reports (SAR)",
            "Currency Transaction Reports (CTR)" if jurisdiction == "US" else None,
            "Cross-border reporting"
            if transaction_types and "international" in transaction_types
            else None,
        ],
        "assessment_date": datetime.utcnow().isoformat(),
    }


def create_compliance_agent() -> Agent:
    """Create the Compliance Agent for regulatory compliance.

    Returns:
        Configured Strands Agent for compliance operations
    """
    settings = get_settings()

    compliance_tools = [
        check_sanctions,
        verify_pep,
        generate_report,
        assess_regulatory_requirements,
    ]

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock.model_id,
            region_name=settings.aws.region,
        ),
        tools=compliance_tools,
        system_prompt=COMPLIANCE_AGENT_SYSTEM_PROMPT,
    )


def get_compliance_agent() -> Agent:
    """Get or create the global Compliance Agent instance.

    Returns:
        Compliance Agent instance
    """
    global _compliance_agent
    if _compliance_agent is None:
        _compliance_agent = create_compliance_agent()
    return _compliance_agent
