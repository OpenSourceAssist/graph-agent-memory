#!/usr/bin/env python3
"""News Schema Example: News Article Analysis

This example demonstrates the news schema for extracting entities from
news articles, press releases, and journalism content.

The news schema focuses on people, organizations, locations, events, and dates
commonly found in news reporting.

Sample Data: Fictional news articles
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

# Sample news articles - fictional current events
NEWS_ARTICLES = [
    {
        "headline": "Tech Giants Face New EU Regulations",
        "source": "Global Business Times",
        "date": "January 15, 2025",
        "content": """
        BRUSSELS - The European Commission announced sweeping new regulations
        targeting major technology companies on Monday, marking the most
        significant expansion of the Digital Services Act since its implementation.

        Commissioner Margrethe Vestager stated that Apple, Google, Meta, and
        Microsoft must comply with new data portability requirements by June 2025.
        "European citizens deserve control over their digital lives," Vestager
        said during a press conference at the European Parliament.

        The regulations require tech companies to allow users to export their
        data in standardized formats and prohibit certain algorithmic practices
        that the Commission deems anticompetitive.

        Tim Cook, Apple's CEO, expressed concern about the timeline in a statement
        released Tuesday. "While we support the goals of data portability, the
        implementation deadline presents significant technical challenges."

        The announcement sent tech stocks tumbling, with the NASDAQ falling 2.3%
        in afternoon trading. Analysts at Goldman Sachs estimate compliance costs
        could reach $5 billion annually across affected companies.
        """,
    },
    {
        "headline": "Climate Summit Reaches Historic Agreement",
        "source": "World News Network",
        "date": "January 18, 2025",
        "content": """
        DUBAI - World leaders reached a landmark climate agreement at the UN
        Climate Change Conference on Saturday, committing to a 60% reduction in
        global emissions by 2035.

        UN Secretary-General Antonio Guterres called the agreement "a turning
        point for humanity" during the closing ceremony. The deal was brokered
        after intense negotiations between the United States, China, and the
        European Union.

        President Biden praised the agreement, stating, "This proves that when
        nations work together, we can tackle the greatest challenges of our time."
        Chinese Premier Li Qiang committed to tripling renewable energy capacity
        by 2030.

        Environmental groups had mixed reactions. Greenpeace International
        director Jennifer Morgan welcomed the emissions targets but criticized
        the lack of specific enforcement mechanisms.

        The agreement includes a $500 billion climate fund, with contributions
        from wealthy nations to help developing countries transition to clean
        energy. India and Brazil successfully negotiated provisions for "just
        transition" financing.

        The next major review conference is scheduled for Glasgow in 2027.
        """,
    },
    {
        "headline": "Major Earthquake Strikes Japan's Noto Peninsula",
        "source": "Asia Pacific News",
        "date": "January 20, 2025",
        "content": """
        TOKYO - A powerful 7.6 magnitude earthquake struck Japan's Noto Peninsula
        early Sunday morning, causing widespread damage and triggering tsunami
        warnings across the Sea of Japan.

        Prime Minister Fumio Kishida declared a state of emergency and mobilized
        the Self-Defense Forces for rescue operations. "Our top priority is
        saving lives," Kishida told reporters at an emergency press conference.

        The Japan Meteorological Agency reported the earthquake struck at 4:10 AM
        local time, with the epicenter located 10 kilometers beneath Wajima City.
        Aftershocks continued throughout the day, with at least 20 measuring
        above magnitude 5.0.

        Ishikawa Prefecture Governor Hiroshi Hase reported significant damage to
        infrastructure, including collapsed buildings in Suzu and Nanao cities.
        The famous Kenrokuen Garden in Kanazawa sustained minor damage.

        The Red Cross dispatched emergency medical teams to the affected region.
        International aid offers came from the United States, South Korea, and
        Taiwan within hours of the disaster.

        Tokyo Electric Power Company reported no damage to nuclear facilities,
        though several thermal power plants were temporarily shut down as a
        precautionary measure.
        """,
    },
]


async def main():
    """Run the news article analysis example."""
    print("=" * 70)
    print("News Schema Example: News Article Analysis")
    print("=" * 70)
    print()

    # Check if GLiNER is available
    if not is_gliner_available():
        print("  ERROR: GLiNER is not installed.")
        print("\n  To run this example, install GLiNER:")
        print("    uv sync --all-extras")
        print("    # or: pip install gliner")
        return

    # Create GLiNER extractor with news schema using factory pattern
    print("Initializing GLiNER2 extractor with news schema (via factory)...")
    extraction_config = ExtractionConfig(
        gliner_schema="news",
        gliner_threshold=0.4,
    )
    extractor = create_gliner_extractor(extraction_config)
    print(f"  Model: {extractor._model_name}")
    print(f"  Entity types: {list(extractor.entity_labels.keys())}")
    print()

    # Process each article
    all_entities = []

    for i, article in enumerate(NEWS_ARTICLES, 1):
        print(f"Article {i}: {article['headline']}")
        print(f"Source: {article['source']} | Date: {article['date']}")
        print("-" * 50)

        result = await extractor.extract(article["content"])
        filtered = result.filter_invalid_entities()

        print(f"  Entities extracted: {filtered.entity_count}")

        # Group by type
        by_type = filtered.entities_by_type()
        for entity_type, entities in sorted(by_type.items()):
            if entities:
                print(f"\n  {entity_type}:")
                for entity in sorted(entities, key=lambda x: x.confidence or 0, reverse=True)[:8]:
                    conf = f"({entity.confidence:.0%})" if entity.confidence else ""
                    print(f"    - {entity.name} {conf}")

        all_entities.extend(filtered.entities)
        print()

    # Summary
    print("=" * 70)
    print("NEWS KNOWLEDGE GRAPH SUMMARY")
    print("=" * 70)

    # Deduplicate entities
    unique_entities = {}
    for entity in all_entities:
        key = (entity.normalized_name, entity.type)
        if key not in unique_entities or (entity.confidence or 0) > (
            unique_entities[key].confidence or 0
        ):
            unique_entities[key] = entity

    print(f"\nTotal unique entities across all articles: {len(unique_entities)}")

    # Key people
    print("\nKey People in the News:")
    persons = [e for e in unique_entities.values() if e.type == "PERSON"]
    for person in sorted(persons, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {person.name}")

    # Organizations
    print("\nOrganizations Mentioned:")
    orgs = [e for e in unique_entities.values() if e.type == "ORGANIZATION"]
    for org in sorted(orgs, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {org.name}")

    # Locations
    print("\nLocations:")
    locations = [e for e in unique_entities.values() if e.type == "LOCATION"]
    for loc in sorted(locations, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {loc.name}")

    # Events
    print("\nEvents:")
    events = [e for e in unique_entities.values() if e.type == "EVENT"]
    for event in sorted(events, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        print(f"  - {event.name}")

    print()
    print("=" * 70)
    print("News Analysis Use Cases:")
    print("=" * 70)
    print("""
    1. Event Tracking:
       - Track earthquake aftermath and rescue operations
       - Monitor climate agreement implementation
       - Follow regulatory compliance deadlines

    2. Entity Monitoring:
       - Track mentions of specific people (e.g., Margrethe Vestager)
       - Monitor company news (Apple, Google, Meta)
       - Follow government actions

    3. Geographic Analysis:
       - Map news by location (Brussels, Dubai, Tokyo)
       - Track regional impacts of global events
       - Identify hotspots of activity

    4. Relationship Discovery:
       - Person-Organization connections
       - Organization-Event participation
       - Geographic event clustering
    """)

    # Demonstrate GLiREL relation extraction (no LLM required)
    if is_glirel_available():
        print("=" * 70)
        print("RELATION EXTRACTION (GLiREL - No LLM Required)")
        print("=" * 70)
        print()

        # Use combined entity + relation extractor
        relation_extractor = GLiNERWithRelationsExtractor.for_schema("news")

        # Extract from first article as demo
        article = NEWS_ARTICLES[0]
        print(f"Extracting relations from: {article['headline']}")
        rel_result = await relation_extractor.extract(article["content"])
        filtered_rel = rel_result.filter_invalid_entities()

        if filtered_rel.relations:
            print(f"\n  Relationships found: {len(filtered_rel.relations)}")
            for rel in filtered_rel.relations:
                conf = f" ({rel.confidence:.0%})" if rel.confidence else ""
                print(f"    {rel.source} -[{rel.relation_type}]-> {rel.target}{conf}")
        else:
            print("  No relationships extracted (may need lower threshold)")
        print()
    else:
        print("\nGLiREL not installed. Install with: pip install glirel")
        print("GLiREL enables relationship extraction without LLM calls.")
        print()

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing news entities...")

        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=neo4j_uri,
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
            )
        )

        async with MemoryClient(settings) as client:
            stored_count = 0
            for entity in list(unique_entities.values())[:25]:
                await client.long_term.add_entity(
                    name=entity.name,
                    entity_type=entity.type,
                    subtype=entity.subtype,
                    attributes={
                        "source": "news_articles",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
