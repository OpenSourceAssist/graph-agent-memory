#!/usr/bin/env python3
"""Entertainment Schema Example: Movie and TV Analysis

This example demonstrates the entertainment schema for extracting entities from
entertainment content including movie reviews, TV show discussions, and celebrity news.

The entertainment schema includes entity types like actor, director, film, tv_show,
character, award, studio, and genre.

Sample Data: Fictional movie reviews and entertainment news
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

# Sample entertainment content - fictional reviews and news
ENTERTAINMENT_CONTENT = [
    {
        "type": "Movie Review",
        "title": "Dune: Part Three - Review",
        "content": """
        Denis Villeneuve delivers another masterpiece with Dune: Part Three,
        the epic conclusion to his adaptation of Frank Herbert's beloved sci-fi
        novel. Timothee Chalamet returns as Paul Atreides, now fully embracing
        his role as the messianic leader of the Fremen.

        The film opens with a stunning 20-minute battle sequence shot entirely
        in IMAX by cinematographer Greig Fraser. Zendaya's Chani gets significantly
        more screen time, and her performance anchors the emotional core of the film.

        New additions to the cast include Oscar Isaac returning in flashback
        sequences and Florence Pugh as Princess Irulan. Javier Bardem's Stilgar
        provides unexpected comic relief while Christopher Walken brings gravitas
        to Emperor Shaddam IV.

        Hans Zimmer's score is even more ambitious than the previous installments,
        incorporating traditional Middle Eastern instruments with his signature
        electronic soundscapes.

        Warner Bros. and Legendary Pictures have crafted a fitting conclusion
        that should satisfy both fans of the book and newcomers to the franchise.
        This is bold, challenging science fiction that demands to be seen on the
        biggest screen possible.

        Rating: 9.5/10
        """,
    },
    {
        "type": "TV Show Analysis",
        "title": "The Bear Season 4 Preview",
        "content": """
        FX has renewed The Bear for a fourth season, with showrunner Christopher
        Storer promising an even more intense exploration of the Chicago restaurant
        scene. Jeremy Allen White will return as Carmen "Carmy" Berzatto, along
        with Ayo Edebiri as Sydney Adamu and Ebon Moss-Bachrach as Richard "Richie"
        Jerimovich.

        Season 3 ended with The Bear finally earning its first Michelin star,
        a moment that Executive Producer Joanna Calo described as "just the
        beginning of the pressure." The show has become known for its anthology
        episode format, with Season 2's "Fishes" episode winning multiple Emmy
        Awards including Outstanding Directing for a Comedy Series.

        Guest stars confirmed for Season 4 include Jon Bernthal reprising his
        role as Carmy's late brother Michael in flashbacks, and new additions
        John Mulaney and Olivia Colman in undisclosed roles.

        The show's depiction of kitchen culture has drawn praise from professional
        chefs, with Thomas Keller and David Chang serving as consultants. Chef
        Matty Matheson, who plays Neil Fak, continues to choreograph the cooking
        sequences.

        The Bear has revitalized the half-hour comedy format, with streaming
        rival Netflix reportedly developing several kitchen-set series in response.
        Hulu's streaming numbers for the show remain the platform's highest for
        any original series.
        """,
    },
    {
        "type": "Awards Coverage",
        "title": "Oscar Nominations 2025",
        "content": """
        The Academy of Motion Picture Arts and Sciences announced the 97th
        Academy Awards nominations this morning, with Christopher Nolan's
        Oppenheimer leading the pack with 13 nominations.

        Cillian Murphy earned his first Best Actor nomination for his portrayal
        of J. Robert Oppenheimer. He faces competition from Bradley Cooper for
        Maestro, Paul Giamatti for The Holdovers, and newcomer Colman Domingo
        for Rustin.

        Best Actress nominees include Emma Stone for Poor Things, Lily Gladstone
        for Killers of the Flower Moon (making history as the first Native American
        nominee in the category), and Margot Robbie for Barbie.

        Martin Scorsese's Killers of the Flower Moon received 10 nominations,
        while Greta Gerwig's Barbie earned 8, including Best Picture. The Warner
        Bros. phenomenon's billion-dollar box office has translated into major
        awards recognition.

        Apple Original Films scored nominations for both Killers and Napoleon,
        marking the streaming giant's strongest showing. A24 continues its
        dominant run with nominations across multiple categories for Past Lives
        and The Zone of Interest.

        The ceremony will be hosted by Jimmy Kimmel and broadcast live on ABC
        from the Dolby Theatre in Hollywood on March 10th.
        """,
    },
]


async def main():
    """Run the entertainment content analysis example."""
    print("=" * 70)
    print("Entertainment Schema Example: Movie and TV Analysis")
    print("=" * 70)
    print()

    # Create GLiNER extractor with entertainment schema
    print("Initializing GLiNER2 extractor with entertainment schema...")
    try:
        extractor = GLiNEREntityExtractor.for_schema("entertainment", threshold=0.4)
        print(f"  Model: {extractor._model_name}")
        print(f"  Entity types: {list(extractor.entity_labels.keys())}")
    except ImportError as e:
        print(f"\n  ERROR: {e}")
        print("\n  To run this example, install GLiNER:")
        print("    uv sync --all-extras")
        print("    # or: pip install gliner")
        return
    print()

    # Process each piece of content
    all_entities = []

    for i, content in enumerate(ENTERTAINMENT_CONTENT, 1):
        print(f"Content {i}: {content['title']}")
        print(f"Type: {content['type']}")
        print("-" * 50)

        result = await extractor.extract(content["content"])
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
    print("ENTERTAINMENT KNOWLEDGE GRAPH SUMMARY")
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

    # Actors
    print("\nActors & Performers:")
    actors = [e for e in unique_entities.values() if e.type == "PERSON" and e.subtype == "ACTOR"]
    for actor in sorted(actors, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {actor.name}")

    # Directors
    print("\nDirectors:")
    directors = [
        e for e in unique_entities.values() if e.type == "PERSON" and e.subtype == "DIRECTOR"
    ]
    for director in sorted(directors, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {director.name}")

    # All people (if actor/director lists are empty)
    if not actors and not directors:
        print("\nPeople (actors, directors, etc.):")
        people = [e for e in unique_entities.values() if e.type == "PERSON"]
        for person in sorted(people, key=lambda x: x.confidence or 0, reverse=True)[:12]:
            print(f"  - {person.name}")

    # Films
    print("\nFilms:")
    films = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "FILM"]
    for film in sorted(films, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {film.name}")

    # TV Shows
    print("\nTV Shows:")
    shows = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "TV_SHOW"]
    for show in sorted(shows, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {show.name}")

    # Studios
    print("\nStudios & Companies:")
    studios = [e for e in unique_entities.values() if e.type == "ORGANIZATION"]
    for studio in sorted(studios, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {studio.name}")

    # Awards
    print("\nAwards:")
    awards = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "AWARD"]
    for award in sorted(awards, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        print(f"  - {award.name}")

    # Characters
    print("\nCharacters:")
    characters = [
        e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "CHARACTER"
    ]
    for char in sorted(characters, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {char.name}")

    print()
    print("=" * 70)
    print("Entertainment Knowledge Graph Use Cases:")
    print("=" * 70)
    print("""
    1. Actor Filmography:
       - Track actor appearances across films
       - Identify frequent collaborations
       - Analyze career trajectories

    2. Director-Actor Networks:
       - Map director-actor relationships
       - Find recurring collaborations
       - Analyze creative partnerships

    3. Franchise Tracking:
       - Connect sequels and spin-offs
       - Track characters across films
       - Map franchise expansion

    4. Awards Analysis:
       - Track nominations and wins
       - Identify Oscar-worthy patterns
       - Compare studio success rates

    5. Recommendation Engine:
       - Connect similar films by genre
       - Recommend based on cast/crew
       - Suggest based on viewing history
    """)

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing entertainment entities...")

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
                        "source": "entertainment_content",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
