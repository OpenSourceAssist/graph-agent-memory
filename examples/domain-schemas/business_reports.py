#!/usr/bin/env python3
"""Business Schema Example: Business Document Analysis

This example demonstrates the business schema for extracting entities from
business documents, earnings reports, market analysis, and corporate content.

The business schema focuses on companies, executives, products, industries,
financial metrics, and business locations.

Sample Data: Fictional business and earnings content
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

# Sample business documents - fictional earnings and market analysis
BUSINESS_DOCUMENTS = [
    {
        "type": "Earnings Call Transcript",
        "company": "TechVision Inc.",
        "date": "Q4 2024",
        "content": """
        Good afternoon, everyone. I'm Sarah Mitchell, CEO of TechVision Inc.,
        and joining me today is our CFO, Robert Chen.

        Q4 was a transformative quarter for TechVision. We achieved revenue of
        $2.4 billion, representing 34% year-over-year growth. Our cloud platform,
        TechVision Cloud, now serves over 50,000 enterprise customers, up from
        38,000 last year.

        Gross margin improved to 72%, driven by efficiencies in our AWS and
        Azure-hosted infrastructure. Operating margin reached 18%, exceeding
        our guidance of 15-17%.

        Our acquisition of DataStream Analytics, completed in October for
        $890 million, is already contributing to growth. DataStream's real-time
        analytics capabilities have enhanced our flagship product, Insight Pro.

        Looking ahead to 2025, we're raising guidance. We expect revenue of
        $11-11.5 billion, representing 25-30% growth. We're also announcing a
        new $500 million stock buyback program.

        I'll now turn it over to Robert for detailed financials.

        Robert Chen: Thank you, Sarah. Let me walk through the numbers. GAAP
        EPS was $1.87, above consensus of $1.72. Non-GAAP EPS was $2.14. Free
        cash flow reached $780 million, a record quarter.
        """,
    },
    {
        "type": "Market Analysis Report",
        "company": "Morgan Stanley Research",
        "date": "January 2025",
        "content": """
        SEMICONDUCTOR INDUSTRY OUTLOOK 2025

        Analyst: Jennifer Wong, Senior Technology Analyst

        Executive Summary: We maintain an Overweight rating on the semiconductor
        sector, with NVIDIA as our top pick. The AI chip market is projected to
        reach $150 billion by 2027, growing at 45% CAGR.

        Key Findings:

        NVIDIA continues to dominate the AI accelerator market with 82% share.
        Their new Blackwell architecture, launching in Q2, offers 2x performance
        over the current Hopper generation. We raise our price target to $750
        from $650.

        AMD is gaining traction with its MI300X chips. CEO Lisa Su has secured
        design wins at Microsoft Azure and Meta. We upgrade AMD to Overweight
        with a $200 price target.

        Intel's turnaround under Pat Gelsinger faces headwinds. The foundry
        business lost $7 billion in 2024, and the 18A node is delayed to late
        2025. We maintain Underweight with a $25 target.

        Emerging Competitors:

        Cerebras Systems and Groq are gaining attention in the startup space.
        Cerebras's wafer-scale chip is being adopted by pharmaceutical companies
        including Pfizer and AstraZeneca for drug discovery.

        Geographic Risks:

        Taiwan Semiconductor Manufacturing Company (TSMC) produces 90% of
        advanced chips. Geopolitical tensions around Taiwan remain the sector's
        biggest risk. TSMC's Arizona fab is on track for 2025 production.
        """,
    },
    {
        "type": "Private Equity Deal Announcement",
        "company": "Vista Equity Partners",
        "date": "January 2025",
        "content": """
        Vista Equity Partners to Acquire CloudSecure for $8.5 Billion

        SAN FRANCISCO - Vista Equity Partners announced today a definitive
        agreement to acquire CloudSecure Inc., a leading cybersecurity platform
        provider, for $8.5 billion in cash.

        Vista founder and CEO Robert Smith called the deal "a landmark investment
        in enterprise security." CloudSecure's CEO, Michelle Park, will continue
        leading the company post-acquisition.

        CloudSecure's platform protects over 2,000 Fortune 500 companies from
        cyber threats. The company achieved $1.2 billion in annual recurring
        revenue in 2024, growing 55% year-over-year.

        The transaction values CloudSecure at 7x revenue, a premium to peer
        companies CrowdStrike and Palo Alto Networks which trade at 5-6x.

        Vista will combine CloudSecure with its existing portfolio company,
        IdentityGuard, creating a comprehensive identity and security platform.
        The combined entity will be headquartered in Austin, Texas.

        J.P. Morgan and Goldman Sachs served as financial advisors to CloudSecure.
        Skadden, Arps provided legal counsel. The deal is expected to close in
        Q2 2025, subject to regulatory approval.
        """,
    },
]


async def main():
    """Run the business document analysis example."""
    print("=" * 70)
    print("Business Schema Example: Business Document Analysis")
    print("=" * 70)
    print()

    # Create GLiNER extractor with business schema
    print("Initializing GLiNER2 extractor with business schema...")
    try:
        extractor = GLiNEREntityExtractor.for_schema("business", threshold=0.4)
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

    for i, doc in enumerate(BUSINESS_DOCUMENTS, 1):
        print(f"Document {i}: {doc['type']}")
        print(f"Source: {doc['company']} | Date: {doc['date']}")
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
    print("BUSINESS INTELLIGENCE SUMMARY")
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

    # Companies
    print("\nCompanies:")
    companies = [e for e in unique_entities.values() if e.type == "ORGANIZATION"]
    for company in sorted(companies, key=lambda x: x.confidence or 0, reverse=True)[:12]:
        print(f"  - {company.name}")

    # Executives
    print("\nExecutives & Key People:")
    people = [e for e in unique_entities.values() if e.type == "PERSON"]
    for person in sorted(people, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {person.name}")

    # Products
    print("\nProducts & Platforms:")
    products = [
        e
        for e in unique_entities.values()
        if e.type == "OBJECT" and e.subtype in ("PRODUCT", "TECHNOLOGY")
    ]
    for product in sorted(products, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {product.name}")

    # Locations
    print("\nBusiness Locations:")
    locations = [e for e in unique_entities.values() if e.type == "LOCATION"]
    for loc in sorted(locations, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {loc.name}")

    print()
    print("=" * 70)
    print("Business Intelligence Use Cases:")
    print("=" * 70)
    print("""
    1. Competitive Intelligence:
       - Track competitor mentions and market positioning
       - Monitor executive changes and leadership commentary
       - Identify emerging threats and opportunities

    2. Investment Research:
       - Extract financial metrics (revenue, margins, growth)
       - Track analyst ratings and price targets
       - Monitor M&A activity and deal terms

    3. Market Mapping:
       - Identify industry participants and relationships
       - Track product launches and feature announcements
       - Map vendor-customer relationships

    4. Executive Tracking:
       - Monitor leadership changes
       - Track executive commentary and sentiment
       - Identify key decision-makers by company

    5. Supply Chain Analysis:
       - Map supplier relationships
       - Track geographic concentration risks
       - Monitor manufacturing locations
    """)

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing business entities...")

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
                        "source": "business_documents",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
