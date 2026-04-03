#!/usr/bin/env python3
"""POLE+O Schema Example: Investigation/Intelligence Analysis

This example demonstrates the POLE+O (Person, Object, Location, Event, Organization)
schema for investigation and intelligence analysis use cases.

The POLE+O model is widely used in law enforcement, intelligence, and fraud
investigation to track entities and their relationships.

Sample Data: Fictional fraud investigation involving shell companies
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

# Load environment from examples/.env
load_dotenv(Path(__file__).parent.parent / ".env")

from neo4j_agent_memory import ExtractionConfig, MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.extraction import (
    create_gliner_extractor,
    is_gliner_available,
    is_glirel_available,
    GLiNERWithRelationsExtractor,
)

# Sample investigation data - fictional fraud case
INVESTIGATION_DATA = [
    {
        "source": "Financial Intelligence Report",
        "content": """
        Subject: Suspicious Transaction Report - Operation Phantom

        Investigation into suspected money laundering operation centered on
        John Marcus Reynolds, CEO of Meridian Holdings LLC. Reynolds was observed
        meeting with Viktor Petrov at the Grand Continental Hotel in Zurich on
        March 15, 2024.

        Wire transfers totaling $2.3 million were traced from Meridian Holdings
        to offshore accounts at First Caribbean Trust in the Cayman Islands.
        The funds originated from Apex Trading Partners, a shell company registered
        in Delaware with no apparent business operations.

        A black Mercedes S-Class (license plate ZH-482991) registered to Meridian
        Holdings was observed at multiple meeting locations. Cell phone records
        indicate calls between Reynolds and known associate Maria Santos, who
        manages Cyprus-based Helios Investments.
        """,
    },
    {
        "source": "Field Surveillance Report",
        "content": """
        Date: March 20, 2024
        Location: 1847 Harbor Drive, Miami, FL

        Subject John Reynolds arrived at the Oceanview Marina at 14:32 aboard
        a 45-foot yacht named "Sea Shadow" (registration FL-8827-MK). He was
        accompanied by two unidentified males in business attire.

        Reynolds met with Carlos Mendez, previously flagged in Operation Nightfall
        for suspected drug trafficking connections. The meeting lasted approximately
        45 minutes at the marina's private club.

        A laptop computer and multiple document folders were exchanged during the
        meeting. Reynolds departed at 16:15, traveling to Miami International Airport
        where he boarded a private jet (tail number N482JR) with flight plan filed
        to Nassau, Bahamas.
        """,
    },
    {
        "source": "Corporate Registry Analysis",
        "content": """
        Entity Analysis: Meridian Holdings LLC Network

        Meridian Holdings LLC (Delaware, incorporated 2019) lists John Reynolds
        as sole director. The registered agent is Smith & Associates Legal Services
        at 100 Corporate Plaza, Wilmington, DE.

        Subsidiary relationships identified:
        - Apex Trading Partners (Delaware) - 100% owned
        - Pacific Rim Ventures (Nevada) - 60% owned
        - Northern Star Logistics (Wyoming) - 100% owned

        Cross-reference with Panama Papers database shows Viktor Petrov as
        beneficial owner of Helios Investments (Cyprus), which holds minority
        stakes in Pacific Rim Ventures.

        Bank Secrecy Act filing from First National Bank of Miami flagged
        structured deposits totaling $890,000 across 12 transactions in February 2024.
        """,
    },
]


async def main():
    """Run the POLE+O investigation analysis example."""
    print("=" * 70)
    print("POLE+O Schema Example: Investigation/Intelligence Analysis")
    print("=" * 70)
    print()

    # Check if GLiNER is available
    if not is_gliner_available():
        print("  ERROR: GLiNER is not installed.")
        print("\n  To run this example, install GLiNER:")
        print("    uv sync --all-extras")
        print("    # or: pip install gliner")
        return

    # Create GLiNER extractor with POLE+O schema using factory pattern
    print("Initializing GLiNER2 extractor with POLE+O schema (via factory)...")
    extraction_config = ExtractionConfig(
        gliner_schema="poleo",
        gliner_threshold=0.4,
    )
    extractor = create_gliner_extractor(extraction_config)
    print(f"  Model: {extractor._model_name}")
    print(f"  Entity types: {list(extractor.entity_labels.keys())}")
    print()

    # Process each document
    all_entities = []

    for i, doc in enumerate(INVESTIGATION_DATA, 1):
        print(f"Processing Document {i}: {doc['source']}")
        print("-" * 50)

        result = await extractor.extract(doc["content"])
        filtered = result.filter_invalid_entities()

        print(f"  Entities extracted: {filtered.entity_count}")

        # Group by type
        by_type = filtered.entities_by_type()
        for entity_type, entities in sorted(by_type.items()):
            print(f"\n  {entity_type}:")
            for entity in entities:
                conf = f"({entity.confidence:.0%})" if entity.confidence else ""
                subtype = f" [{entity.subtype}]" if entity.subtype else ""
                print(f"    - {entity.name}{subtype} {conf}")

        all_entities.extend(filtered.entities)
        print()

    # Summary statistics
    print("=" * 70)
    print("INVESTIGATION SUMMARY")
    print("=" * 70)

    # Deduplicate entities by normalized name
    unique_entities = {}
    for entity in all_entities:
        key = (entity.normalized_name, entity.type)
        if key not in unique_entities or entity.confidence > unique_entities[key].confidence:
            unique_entities[key] = entity

    print(f"\nTotal unique entities identified: {len(unique_entities)}")

    # Count by type
    type_counts = {}
    for entity in unique_entities.values():
        type_counts[entity.type] = type_counts.get(entity.type, 0) + 1

    print("\nEntity breakdown:")
    for entity_type, count in sorted(type_counts.items()):
        print(f"  {entity_type}: {count}")

    # Key subjects
    print("\nKey PERSON entities:")
    persons = [e for e in unique_entities.values() if e.type == "PERSON"]
    for person in sorted(persons, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        print(f"  - {person.name}")

    # Organizations
    print("\nKey ORGANIZATION entities:")
    orgs = [e for e in unique_entities.values() if e.type == "ORGANIZATION"]
    for org in sorted(orgs, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        print(f"  - {org.name}")

    # Locations
    print("\nKey LOCATION entities:")
    locations = [e for e in unique_entities.values() if e.type == "LOCATION"]
    for loc in sorted(locations, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        print(f"  - {loc.name}")

    # Objects (vehicles, documents, etc.)
    print("\nKey OBJECT entities:")
    objects = [e for e in unique_entities.values() if e.type == "OBJECT"]
    for obj in sorted(objects, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        subtype = f" [{obj.subtype}]" if obj.subtype else ""
        print(f"  - {obj.name}{subtype}")

    # Demonstrate GLiREL relation extraction for investigations
    if is_glirel_available():
        print()
        print("=" * 70)
        print("RELATION EXTRACTION (GLiREL - No LLM Required)")
        print("=" * 70)
        print()

        # Use combined entity + relation extractor for POLE+O
        relation_extractor = GLiNERWithRelationsExtractor.for_poleo()

        # Extract from first document (financial intelligence report)
        doc = INVESTIGATION_DATA[0]
        print(f"Extracting relations from: {doc['source']}")
        rel_result = await relation_extractor.extract(doc["content"])
        filtered_rel = rel_result.filter_invalid_entities()

        if filtered_rel.relations:
            print(f"\n  Relationships found: {len(filtered_rel.relations)}")
            for rel in filtered_rel.relations:
                conf = f" ({rel.confidence:.0%})" if rel.confidence else ""
                print(f"    {rel.source} -[{rel.relation_type}]-> {rel.target}{conf}")
        else:
            print("  No relationships extracted (may need lower threshold)")
    else:
        print("\n  GLiREL not installed. Install with: pip install glirel")
        print("  GLiREL enables relationship extraction without LLM calls.")

    print()
    print("=" * 70)
    print("Example complete. In a real application, these entities would be")
    print("stored in Neo4j for graph analysis and relationship discovery.")
    print("=" * 70)

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing entities...")

        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=neo4j_uri,
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
            )
        )

        async with MemoryClient(settings) as client:
            # Store entities
            stored_count = 0
            for entity in list(unique_entities.values())[:20]:  # Limit for demo
                await client.long_term.add_entity(
                    name=entity.name,
                    entity_type=entity.type,
                    subtype=entity.subtype,
                    attributes={
                        "source": "Operation Phantom Investigation",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
            print("\nQuery example entities with:")
            print("  MATCH (e:Entity:Person) RETURN e.name, e.type LIMIT 10")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
