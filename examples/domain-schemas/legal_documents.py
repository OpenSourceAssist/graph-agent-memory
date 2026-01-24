#!/usr/bin/env python3
"""Legal Schema Example: Legal Document Analysis

This example demonstrates the legal schema for extracting entities from
legal documents, court cases, contracts, and regulatory filings.

The legal schema includes entity types like case, person, organization, law,
court, date, and monetary_amount commonly found in legal contexts.

Sample Data: Fictional legal documents and case summaries
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

# Load environment from examples/.env
load_dotenv(Path(__file__).parent.parent / ".env")

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.extraction import GLiNEREntityExtractor, is_gliner_available

# Sample legal documents - fictional cases and filings
LEGAL_DOCUMENTS = [
    {
        "type": "Court Opinion Summary",
        "case": "Tech Antitrust Case",
        "content": """
        UNITED STATES DISTRICT COURT
        NORTHERN DISTRICT OF CALIFORNIA

        FEDERAL TRADE COMMISSION, Plaintiff,
        v.
        MEGACORP TECHNOLOGIES, INC., Defendant.

        Case No. 3:23-cv-01234-ABC

        ORDER GRANTING PRELIMINARY INJUNCTION

        Before the Court is the FTC's Motion for Preliminary Injunction seeking
        to block MegaCorp Technologies' proposed acquisition of CloudStart, Inc.
        for $12.4 billion.

        Judge Sarah Martinez finds that the FTC has demonstrated a likelihood
        of success on the merits under Section 7 of the Clayton Act. The
        acquisition would combine the two largest cloud infrastructure providers,
        controlling approximately 65% of the relevant market.

        The Court notes testimony from CEO Richard Chen acknowledging internal
        documents stating the acquisition would "eliminate our primary competitor."
        Expert witness Dr. Michael Torres from Stanford University provided
        economic analysis showing likely price increases of 15-20%.

        MegaCorp's counsel, represented by Gibson Dunn & Crutcher LLP, argued
        that the merger would create efficiencies benefiting consumers. However,
        the Court finds these efficiency claims speculative and unsubstantiated.

        ORDERED: The preliminary injunction is GRANTED. MegaCorp is enjoined from
        completing the acquisition pending trial on the merits, scheduled to
        commence April 15, 2025.

        IT IS SO ORDERED.
        Dated: January 18, 2025
        Hon. Sarah Martinez, United States District Judge
        """,
    },
    {
        "type": "SEC Enforcement Action",
        "case": "Securities Fraud Settlement",
        "content": """
        SECURITIES AND EXCHANGE COMMISSION
        LITIGATION RELEASE NO. 25789

        SEC Charges Former Executives of BioVenture Therapeutics with
        Securities Fraud

        Washington, D.C., January 10, 2025 - The Securities and Exchange
        Commission today announced that former BioVenture Therapeutics CEO
        James Morrison and CFO Linda Park have agreed to pay $4.2 million and
        $1.8 million, respectively, to settle charges that they misled investors
        about the company's clinical trial results.

        According to the SEC's complaint filed in the U.S. District Court for
        the Southern District of New York, Morrison and Park made materially
        false statements regarding the efficacy of BioVenture's lead drug
        candidate, BVT-401, in Phase II trials for pancreatic cancer treatment.

        The SEC alleges that between March 2023 and August 2023, the defendants
        concealed negative safety data from investors while selling $28 million
        in personal stock holdings. When the true trial results were disclosed
        in September 2023, BioVenture's stock price fell 72%.

        "Executives who deceive investors about clinical trial data undermine
        the integrity of our capital markets," said SEC Enforcement Division
        Director Gurbir Grewal.

        Without admitting or denying the allegations, Morrison and Park agreed
        to officer-and-director bars of ten and five years, respectively.
        Morrison also agreed to disgorgement of $8.5 million plus prejudgment
        interest.

        The SEC's investigation was led by attorneys from the SEC's New York
        Regional Office.
        """,
    },
    {
        "type": "Contract Dispute Summary",
        "case": "Commercial Licensing Arbitration",
        "content": """
        AMERICAN ARBITRATION ASSOCIATION
        Commercial Arbitration Tribunal

        AWARD

        In the Matter of Arbitration Between:

        INNOVATECH SOLUTIONS, INC., Claimant
        and
        GLOBAL ENTERPRISES LLC, Respondent

        AAA Case No. 01-24-0003-8765

        Arbitrator: Hon. Robert Williams (Ret.)

        SUMMARY OF DISPUTE:

        Claimant InnovaTech Solutions seeks damages of $47.5 million arising
        from Respondent Global Enterprises' alleged breach of a Software
        Licensing Agreement dated February 1, 2022. InnovaTech alleges that
        Global Enterprises exceeded the licensed user count by deploying
        the software to 15,000 users rather than the contracted 2,500 users.

        InnovaTech was represented by Latham & Watkins LLP (Partner: Jennifer
        Adams). Global Enterprises was represented by Kirkland & Ellis LLP
        (Partner: David Thompson).

        FINDINGS:

        After reviewing the License Agreement, audit reports from Deloitte,
        and testimony from both parties' IT directors, the Arbitrator finds
        that Global Enterprises materially breached Section 4.2 of the Agreement.

        However, InnovaTech's damages calculation is rejected as speculative.
        The Arbitrator applies the standard licensing fee methodology.

        AWARD:

        Global Enterprises shall pay InnovaTech Solutions:
        - Compensatory damages: $18,750,000
        - Audit costs: $425,000
        - Attorneys' fees: $2,100,000
        - Interest at 5% per annum from date of breach

        Total Award: $21,275,000 plus accrued interest

        This Award is final and binding. Dated: January 5, 2025.
        """,
    },
]


async def main():
    """Run the legal document analysis example."""
    print("=" * 70)
    print("Legal Schema Example: Legal Document Analysis")
    print("=" * 70)
    print()

    # Create GLiNER extractor with legal schema
    print("Initializing GLiNER2 extractor with legal schema...")
    try:
        extractor = GLiNEREntityExtractor.for_schema("legal", threshold=0.4)
        print(f"  Model: {extractor._model_name}")
        print(f"  Entity types: {list(extractor.entity_labels.keys())}")
    except ImportError as e:
        print(f"\n  ERROR: {e}")
        print("\n  To run this example, install GLiNER:")
        print("    uv sync --all-extras")
        print("    # or: pip install gliner")
        return
    print()

    # Process each document
    all_entities = []

    for i, doc in enumerate(LEGAL_DOCUMENTS, 1):
        print(f"Document {i}: {doc['type']}")
        print(f"Case: {doc['case']}")
        print("-" * 50)

        result = await extractor.extract(doc["content"])
        filtered = result.filter_invalid_entities()

        print(f"  Entities extracted: {filtered.entity_count}")

        # Group by type
        by_type = filtered.entities_by_type()
        for entity_type, entities in sorted(by_type.items()):
            if entities:
                print(f"\n  {entity_type}:")
                for entity in sorted(entities, key=lambda x: x.confidence or 0, reverse=True)[:8]:
                    conf = f"({entity.confidence:.0%})" if entity.confidence else ""
                    subtype = f" [{entity.subtype}]" if entity.subtype else ""
                    print(f"    - {entity.name}{subtype} {conf}")

        all_entities.extend(filtered.entities)
        print()

    # Summary
    print("=" * 70)
    print("LEGAL KNOWLEDGE GRAPH SUMMARY")
    print("=" * 70)

    # Deduplicate entities
    unique_entities = {}
    for entity in all_entities:
        key = (entity.normalized_name, entity.type)
        if key not in unique_entities or (entity.confidence or 0) > (
            unique_entities[key].confidence or 0
        ):
            unique_entities[key] = entity

    print(f"\nTotal unique entities: {len(unique_entities)}")

    # Cases
    print("\nCases & Legal Proceedings:")
    cases = [e for e in unique_entities.values() if e.type == "EVENT" and e.subtype == "CASE"]
    for case in sorted(cases, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {case.name}")

    # Persons
    print("\nParties, Attorneys & Judges:")
    persons = [e for e in unique_entities.values() if e.type == "PERSON"]
    for person in sorted(persons, key=lambda x: x.confidence or 0, reverse=True)[:12]:
        print(f"  - {person.name}")

    # Organizations
    print("\nOrganizations (Parties, Courts, Firms):")
    orgs = [e for e in unique_entities.values() if e.type == "ORGANIZATION"]
    for org in sorted(orgs, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {org.name}")

    # Courts
    print("\nCourts & Tribunals:")
    courts = [
        e for e in unique_entities.values() if e.type == "ORGANIZATION" and e.subtype == "COURT"
    ]
    for court in sorted(courts, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        print(f"  - {court.name}")

    # Laws
    print("\nLaws & Regulations:")
    laws = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "LAW"]
    for law in sorted(laws, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {law.name}")

    # Monetary amounts
    print("\nMonetary Amounts:")
    amounts = [
        e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "MONETARY_AMOUNT"
    ]
    for amount in sorted(amounts, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {amount.name}")

    print()
    print("=" * 70)
    print("Legal Knowledge Graph Use Cases:")
    print("=" * 70)
    print("""
    1. Case Law Research:
       - Find similar cases by subject matter
       - Track judicial reasoning patterns
       - Identify influential precedents

    2. Party & Attorney Analytics:
       - Track law firm success rates
       - Identify expert witnesses by specialty
       - Map attorney-judge relationships

    3. Regulatory Tracking:
       - Monitor enforcement actions
       - Track penalty trends
       - Identify compliance risks

    4. Contract Analysis:
       - Extract key terms and obligations
       - Identify risky clauses
       - Track dispute patterns

    5. Due Diligence:
       - Map litigation history
       - Identify regulatory exposure
       - Track settlement patterns

    IMPORTANT: This example uses fictional data for demonstration purposes.
    In real legal applications, ensure compliance with attorney-client
    privilege and other applicable confidentiality requirements.
    """)

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing legal entities...")

        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=neo4j_uri,
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
            )
        )

        async with MemoryClient(settings) as client:
            stored_count = 0
            for entity in list(unique_entities.values())[:30]:
                await client.long_term.add_entity(
                    name=entity.name,
                    entity_type=entity.type,
                    subtype=entity.subtype,
                    attributes={
                        "source": "legal_documents",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
