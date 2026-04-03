#!/usr/bin/env python3
"""Podcast Schema Example: Podcast Transcript Analysis

This example demonstrates the podcast schema for extracting entities from
podcast transcripts, interviews, and conversational content.

The podcast schema is optimized for business/tech podcasts and includes
entity types like person, company, product, concept, book, technology, etc.

Sample Data: Fictional tech podcast transcript excerpts
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
    BatchExtractionResult,
    create_gliner_extractor,
    is_gliner_available,
)

# Sample podcast transcript excerpts - fictional tech interviews
PODCAST_TRANSCRIPTS = [
    {
        "episode": "Growth Strategies with Elena Rodriguez",
        "guest": "Elena Rodriguez, VP of Growth at Stripe",
        "content": """
        Host: Elena, you've been at Stripe for five years now and led their
        expansion into Latin America. What was the key insight that drove that growth?

        Elena: Great question. When I joined Stripe, we were primarily focused on
        the US market. But I had experience at Mercado Libre before, and I knew
        the opportunity in Brazil and Mexico was massive. The key was understanding
        that product-market fit looks different in emerging markets.

        We launched Stripe Atlas specifically for entrepreneurs in these regions,
        and it was a game-changer. Patrick Collison was incredibly supportive of
        the initiative. We grew from zero to processing over $10 billion in
        payments within three years.

        Host: That's incredible. You mentioned product-market fit - how do you
        measure that? Do you use frameworks like Sean Ellis's PMF survey?

        Elena: Absolutely. We use the "very disappointed" question religiously.
        But we also track activation metrics closely. At Stripe, we define
        activation as the first successful API call. For Stripe Atlas, it's when
        a founder receives their EIN from the IRS.
        """,
    },
    {
        "episode": "Building AI Products with Marcus Chen",
        "guest": "Marcus Chen, Co-founder & CTO at Anthropic",
        "content": """
        Host: Marcus, Anthropic has become one of the leading AI safety companies.
        Can you tell us about the journey from leaving Google to starting Anthropic?

        Marcus: When Dario Amodei, my co-founder, and I were at Google Brain, we
        were working on large language models. We saw the potential but also the
        risks. That's when we decided to start Anthropic with a focus on AI safety.

        We developed Constitutional AI as our core approach. The idea is to train
        AI systems using principles rather than just examples. Claude, our
        assistant, is built on this foundation.

        Host: How does Constitutional AI differ from RLHF that OpenAI uses?

        Marcus: RLHF - Reinforcement Learning from Human Feedback - requires
        massive amounts of human annotation. Constitutional AI is more scalable.
        We define a constitution of principles, and the model learns to follow
        them through self-supervision.

        We recently published a paper in Nature about this approach. The key
        finding was that models trained with CAIL showed 40% fewer harmful outputs
        than baseline GPT-4.
        """,
    },
    {
        "episode": "Scaling Engineering Teams with Priya Sharma",
        "guest": "Priya Sharma, VP of Engineering at Figma",
        "content": """
        Host: Priya, Figma went from a small team to over 800 people after the
        Adobe acquisition fell through. How do you maintain engineering velocity
        at that scale?

        Priya: It's all about organizational design. Dylan Field, our CEO, gave
        me a lot of autonomy to restructure the engineering org. We adopted a
        model inspired by Spotify's squad framework but adapted it to our needs.

        Each squad owns a specific area - like the multiplayer editing engine or
        the component library. We use Linear for project management and have
        weekly engineering all-hands on Zoom.

        Host: I've heard great things about Figma's developer experience. What
        tools do you use internally?

        Priya: We're big believers in developer productivity. We built our own
        internal platform called DevX that handles CI/CD, feature flags, and
        observability. It's built on Kubernetes and uses Datadog for monitoring.

        We also heavily use TypeScript and React. Our design-to-code workflow
        integrates directly with our Storybook components. Engineers can literally
        copy production-ready code from the design specs.

        Host: Have you read "Team Topologies" by Matthew Skelton? It sounds like
        you're implementing many of those patterns.

        Priya: Yes! It's required reading for our engineering managers. The
        concept of stream-aligned teams versus platform teams really shaped how
        we think about organization.
        """,
    },
]


async def main():
    """Run the podcast transcript analysis example."""
    print("=" * 70)
    print("Podcast Schema Example: Podcast Transcript Analysis")
    print("=" * 70)
    print()

    # Check if GLiNER is available
    if not is_gliner_available():
        print("  ERROR: GLiNER is not installed.")
        print("\n  To run this example, install GLiNER:")
        print("    uv sync --all-extras")
        print("    # or: pip install gliner")
        print("\n  The GLiNER model (~500MB) will be downloaded on first use.")
        return

    # Create GLiNER extractor with podcast schema using factory pattern
    print("Initializing GLiNER2 extractor with podcast schema (via factory)...")
    extraction_config = ExtractionConfig(
        gliner_schema="podcast",
        gliner_threshold=0.45,
    )
    extractor = create_gliner_extractor(extraction_config)
    print(f"  Model: {extractor._model_name}")
    print(f"  Entity types: {list(extractor.entity_labels.keys())}")
    print()

    # Process each episode
    all_entities = []
    episode_entities = {}

    for i, episode in enumerate(PODCAST_TRANSCRIPTS, 1):
        print(f"Episode {i}: {episode['episode']}")
        print(f"Guest: {episode['guest']}")
        print("-" * 50)

        result = await extractor.extract(episode["content"])
        filtered = result.filter_invalid_entities()

        episode_entities[episode["episode"]] = filtered.entities
        print(f"  Entities extracted: {filtered.entity_count}")

        # Group by type
        by_type = filtered.entities_by_type()
        for entity_type, entities in sorted(by_type.items()):
            if entities:
                print(f"\n  {entity_type}:")
                for entity in sorted(entities, key=lambda x: x.confidence or 0, reverse=True)[:5]:
                    conf = f"({entity.confidence:.0%})" if entity.confidence else ""
                    print(f"    - {entity.name} {conf}")

        all_entities.extend(filtered.entities)
        print()

    # Demonstrate batch extraction - process all transcripts at once
    print("=" * 70)
    print("BATCH EXTRACTION DEMO")
    print("=" * 70)
    print()

    texts = [ep["content"] for ep in PODCAST_TRANSCRIPTS]
    batch_result: BatchExtractionResult = await extractor.extract_batch(
        texts,
        batch_size=10,
        on_progress=lambda done, total: print(f"  Batch progress: {done}/{total}"),
    )
    print(f"  Processed: {batch_result.total_items}, Success: {batch_result.successful_items}")
    print(f"  Total entities (batch): {batch_result.total_entities}")
    print(f"  Success rate: {batch_result.success_rate:.0%}")
    print()

    # Summary and insights
    print("=" * 70)
    print("PODCAST KNOWLEDGE GRAPH SUMMARY")
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

    # Key people mentioned
    print("\nKey People Mentioned:")
    persons = [e for e in unique_entities.values() if e.type == "PERSON"]
    for person in sorted(persons, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {person.name}")

    # Companies and organizations
    print("\nCompanies & Organizations:")
    orgs = [e for e in unique_entities.values() if e.type == "ORGANIZATION"]
    for org in sorted(orgs, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {org.name}")

    # Products and technologies
    print("\nProducts & Technologies:")
    products = [
        e
        for e in unique_entities.values()
        if e.type == "OBJECT" and e.subtype in ("PRODUCT", "TECHNOLOGY", "TOOL")
    ]
    for product in sorted(products, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        subtype = f" [{e.subtype}]" if product.subtype else ""
        print(f"  - {product.name}{subtype}")

    # Concepts and methodologies
    print("\nConcepts & Methodologies:")
    concepts = [
        e
        for e in unique_entities.values()
        if e.type == "OBJECT" and e.subtype in ("CONCEPT", "METHOD", "METRIC")
    ]
    for concept in sorted(concepts, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {concept.name}")

    # Books mentioned
    print("\nBooks Mentioned:")
    books = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "BOOK"]
    for book in sorted(books, key=lambda x: x.confidence or 0, reverse=True):
        print(f"  - {book.name}")

    print()
    print("=" * 70)
    print("Insights for Knowledge Graph:")
    print("=" * 70)
    print("""
    Potential relationships that could be extracted:

    - Elena Rodriguez -[WORKS_AT]-> Stripe
    - Elena Rodriguez -[PREVIOUSLY_AT]-> Mercado Libre
    - Patrick Collison -[FOUNDED]-> Stripe
    - Stripe -[CREATED]-> Stripe Atlas

    - Marcus Chen -[CO_FOUNDED]-> Anthropic
    - Dario Amodei -[CO_FOUNDED]-> Anthropic
    - Anthropic -[CREATED]-> Claude
    - Anthropic -[DEVELOPED]-> Constitutional AI

    - Priya Sharma -[WORKS_AT]-> Figma
    - Dylan Field -[CEO_OF]-> Figma
    - Figma -[USES]-> Kubernetes
    - Figma -[USES]-> TypeScript

    Note: Relationship extraction requires the LLM extractor stage.
    """)

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing podcast entities...")

        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=neo4j_uri,
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
            )
        )

        async with MemoryClient(settings) as client:
            # Store unique entities
            stored_count = 0
            for entity in list(unique_entities.values())[:30]:
                await client.long_term.add_entity(
                    name=entity.name,
                    entity_type=entity.type,
                    subtype=entity.subtype,
                    attributes={
                        "source": "tech_podcast",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
