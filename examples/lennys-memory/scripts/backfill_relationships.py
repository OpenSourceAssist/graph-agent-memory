#!/usr/bin/env python3
"""Backfill RELATED_TO relationships for existing entities in the database.

This script runs GLiREL relationship extraction on messages that already have
extracted entities, and creates RELATED_TO relationships between Entity nodes.

This is useful for databases that were populated before relationship extraction
was implemented, or when relationship extraction was disabled during initial load.

Features:
- Processes messages that have entities but no relationships extracted yet
- Uses GLiREL for relationship extraction (no LLM required)
- Batch processing with progress tracking
- Resume capability (tracks which messages have been processed)
- Rate limiting to avoid overwhelming the database
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import warnings
from pathlib import Path

# Suppress warnings before imports
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

from dotenv import load_dotenv
from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.extraction.gliner_extractor import (
    GLiRELExtractor,
    is_glirel_available,
)
from neo4j_agent_memory.extraction.base import ExtractedEntity
from neo4j_agent_memory.graph.queries import (
    CREATE_ENTITY_RELATION_BY_ID,
    CREATE_ENTITY_RELATION_BY_NAME,
)

# Load .env file from backend directory
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"


def supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLORS = supports_color()


def color(text: str, color_code: str) -> str:
    if USE_COLORS:
        return f"{color_code}{text}{Colors.RESET}"
    return text


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


# Cypher queries for backfill
GET_MESSAGES_WITH_ENTITIES = """
MATCH (m:Message)-[:MENTIONS]->(e:Entity)
WITH m, collect(DISTINCT {
    id: e.id,
    name: e.name,
    type: e.type,
    subtype: e.subtype
}) AS entities
WHERE size(entities) >= 2
RETURN m.id AS message_id,
       m.content AS content,
       entities
ORDER BY m.created_at
SKIP $skip
LIMIT $limit
"""

GET_MESSAGES_WITHOUT_RELATIONSHIPS = """
// Find messages that have entities but where those entities don't have RELATED_TO between them
MATCH (m:Message)-[:MENTIONS]->(e:Entity)
WITH m, collect(DISTINCT e) AS entities
WHERE size(entities) >= 2
// Check if any pair of entities from this message has a RELATED_TO relationship
WITH m, entities,
     [e IN entities | e.id] AS entity_ids
OPTIONAL MATCH (e1:Entity)-[r:RELATED_TO]-(e2:Entity)
WHERE e1.id IN entity_ids AND e2.id IN entity_ids
WITH m, entities, count(r) AS rel_count
WHERE rel_count = 0
RETURN m.id AS message_id,
       m.content AS content,
       [e IN entities | {
           id: e.id,
           name: e.name,
           type: e.type,
           subtype: e.subtype
       }] AS entities
ORDER BY m.created_at
SKIP $skip
LIMIT $limit
"""

COUNT_MESSAGES_WITH_ENTITIES = """
MATCH (m:Message)-[:MENTIONS]->(e:Entity)
WITH m, count(DISTINCT e) AS entity_count
WHERE entity_count >= 2
RETURN count(m) AS total
"""

COUNT_MESSAGES_WITHOUT_RELATIONSHIPS = """
MATCH (m:Message)-[:MENTIONS]->(e:Entity)
WITH m, collect(DISTINCT e) AS entities
WHERE size(entities) >= 2
WITH m, entities,
     [e IN entities | e.id] AS entity_ids
OPTIONAL MATCH (e1:Entity)-[r:RELATED_TO]-(e2:Entity)
WHERE e1.id IN entity_ids AND e2.id IN entity_ids
WITH m, count(r) AS rel_count
WHERE rel_count = 0
RETURN count(m) AS total
"""

GET_RELATIONSHIP_STATS = """
MATCH ()-[r:RELATED_TO]->()
RETURN count(r) AS total_relationships,
       count(DISTINCT r.relation_type) AS unique_types
"""


async def get_message_count(
    memory: MemoryClient,
    skip_processed: bool = True,
) -> int:
    """Get count of messages that need relationship extraction."""
    query = (
        COUNT_MESSAGES_WITHOUT_RELATIONSHIPS
        if skip_processed
        else COUNT_MESSAGES_WITH_ENTITIES
    )
    results = await memory._client.execute_read(query)
    return results[0]["total"] if results else 0


async def get_messages_batch(
    memory: MemoryClient,
    skip: int,
    limit: int,
    skip_processed: bool = True,
) -> list[dict]:
    """Get a batch of messages with their entities."""
    query = (
        GET_MESSAGES_WITHOUT_RELATIONSHIPS
        if skip_processed
        else GET_MESSAGES_WITH_ENTITIES
    )
    results = await memory._client.execute_read(query, {"skip": skip, "limit": limit})
    return results


async def get_relationship_stats(memory: MemoryClient) -> dict:
    """Get current relationship statistics."""
    results = await memory._client.execute_read(GET_RELATIONSHIP_STATS)
    if results:
        return {
            "total_relationships": results[0]["total_relationships"],
            "unique_types": results[0]["unique_types"],
        }
    return {"total_relationships": 0, "unique_types": 0}


async def store_relations(
    memory: MemoryClient,
    relations: list[dict],
    entity_id_map: dict[str, str],
) -> int:
    """Store extracted relations as RELATED_TO relationships.

    Args:
        memory: MemoryClient instance
        relations: List of relation dicts with source, target, relation_type, confidence
        entity_id_map: Mapping from entity name (lowercase) to entity ID

    Returns:
        Number of relationships created
    """
    created = 0

    for rel in relations:
        source_name = rel["source"].lower()
        target_name = rel["target"].lower()

        # Try to find entity IDs
        source_id = entity_id_map.get(source_name)
        target_id = entity_id_map.get(target_name)

        if source_id and target_id:
            # Use ID-based query (faster)
            try:
                await memory._client.execute_write(
                    CREATE_ENTITY_RELATION_BY_ID,
                    {
                        "source_id": source_id,
                        "target_id": target_id,
                        "relation_type": rel["relation_type"],
                        "confidence": rel["confidence"],
                    },
                )
                created += 1
            except Exception as e:
                logger.debug(f"Failed to create relation by ID: {e}")
        else:
            # Fallback to name-based query
            try:
                await memory._client.execute_write(
                    CREATE_ENTITY_RELATION_BY_NAME,
                    {
                        "source_name": rel["source"],
                        "target_name": rel["target"],
                        "relation_type": rel["relation_type"],
                        "confidence": rel["confidence"],
                    },
                )
                created += 1
            except Exception as e:
                logger.debug(f"Failed to create relation by name: {e}")

    return created


async def process_message(
    memory: MemoryClient,
    extractor: GLiRELExtractor,
    message: dict,
) -> dict:
    """Process a single message to extract and store relationships.

    Args:
        memory: MemoryClient instance
        extractor: GLiREL extractor
        message: Message dict with content and entities

    Returns:
        Dict with processing stats
    """
    content = message["content"]
    entities_data = message["entities"]

    # Convert to ExtractedEntity objects for GLiREL
    entities = []
    entity_id_map = {}

    for e in entities_data:
        entity = ExtractedEntity(
            name=e["name"],
            type=e["type"],
            subtype=e.get("subtype"),
            confidence=1.0,  # Existing entities have implicit high confidence
        )
        entities.append(entity)
        # Build name-to-ID mapping for relationship storage
        entity_id_map[e["name"].lower()] = e["id"]

    if len(entities) < 2:
        return {"relations_extracted": 0, "relations_stored": 0}

    # Extract relations using GLiREL
    try:
        relations = await extractor.extract_relations(content, entities)
    except Exception as e:
        logger.warning(f"Failed to extract relations: {e}")
        return {"relations_extracted": 0, "relations_stored": 0, "error": str(e)}

    if not relations:
        return {"relations_extracted": 0, "relations_stored": 0}

    # Convert to dict format for storage
    relations_data = [
        {
            "source": r.source,
            "target": r.target,
            "relation_type": r.relation_type,
            "confidence": r.confidence,
        }
        for r in relations
    ]

    # Store relations
    stored = await store_relations(memory, relations_data, entity_id_map)

    return {
        "relations_extracted": len(relations),
        "relations_stored": stored,
    }


async def backfill_relationships(
    memory: MemoryClient,
    extractor: GLiRELExtractor,
    batch_size: int = 50,
    skip_processed: bool = True,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """Backfill RELATED_TO relationships for existing entities.

    Args:
        memory: MemoryClient instance
        extractor: GLiREL extractor
        batch_size: Number of messages to process per batch
        skip_processed: Skip messages that already have relationships
        dry_run: If True, only show what would be done
        limit: Optional limit on total messages to process

    Returns:
        Stats dict with total processed, relations extracted, etc.
    """
    # Get initial stats
    initial_stats = await get_relationship_stats(memory)
    total_messages = await get_message_count(memory, skip_processed)

    if limit:
        total_messages = min(total_messages, limit)

    print(f"\n{color('Relationship Backfill', Colors.BOLD + Colors.CYAN)}")
    print(f"{'=' * 50}")
    print(f"  Messages to process: {total_messages:,}")
    print(f"  Existing relationships: {initial_stats['total_relationships']:,}")
    print(f"  Batch size: {batch_size}")
    print(f"  Skip processed: {skip_processed}")
    if dry_run:
        print(f"  {color('DRY RUN MODE', Colors.YELLOW)}")
    print()

    if total_messages == 0:
        print(color("No messages need relationship extraction!", Colors.GREEN))
        return {
            "messages_processed": 0,
            "relations_extracted": 0,
            "relations_stored": 0,
        }

    if dry_run:
        # Show sample of messages that would be processed
        print(f"Sample of messages that would be processed:")
        sample = await get_messages_batch(memory, 0, 5, skip_processed)
        for msg in sample:
            entity_names = [e["name"] for e in msg["entities"]]
            print(f"  • {len(msg['entities'])} entities: {', '.join(entity_names[:5])}")
            if len(entity_names) > 5:
                print(f"    ... and {len(entity_names) - 5} more")
        print()
        return {
            "messages_processed": 0,
            "relations_extracted": 0,
            "relations_stored": 0,
            "dry_run": True,
        }

    # Process messages in batches
    start_time = time.time()
    processed = 0
    total_extracted = 0
    total_stored = 0
    errors = 0
    skip = 0

    while processed < total_messages:
        batch = await get_messages_batch(memory, skip, batch_size, skip_processed)

        if not batch:
            break

        for msg in batch:
            result = await process_message(memory, extractor, msg)

            total_extracted += result.get("relations_extracted", 0)
            total_stored += result.get("relations_stored", 0)
            if result.get("error"):
                errors += 1

            processed += 1

            # Progress update
            if processed % 10 == 0 or processed == total_messages:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (total_messages - processed) / rate if rate > 0 else 0

                sys.stdout.write(
                    f"\r  Progress: {processed}/{total_messages} "
                    f"({processed/total_messages*100:.0f}%) "
                    f"| Relations: {total_stored:,} stored "
                    f"| {rate:.1f} msg/s "
                    f"| ETA: {format_duration(eta)}"
                )
                sys.stdout.flush()

            if limit and processed >= limit:
                break

        # When not skipping processed, we need to move skip forward
        if not skip_processed:
            skip += batch_size
        # When skipping processed, keep skip at 0 since we're filtering out done ones

    print()  # Newline after progress

    # Final stats
    elapsed = time.time() - start_time
    final_stats = await get_relationship_stats(memory)

    print()
    print(color("═" * 50, Colors.CYAN))
    print(color("  Backfill Complete!", Colors.BOLD + Colors.GREEN))
    print(color("═" * 50, Colors.CYAN))
    print()
    print(f"  {color('Messages processed:', Colors.DIM)} {processed:,}")
    print(f"  {color('Relations extracted:', Colors.DIM)} {total_extracted:,}")
    print(f"  {color('Relations stored:', Colors.DIM)} {total_stored:,}")
    print(f"  {color('Errors:', Colors.DIM)} {errors}")
    print(f"  {color('Elapsed time:', Colors.DIM)} {format_duration(elapsed)}")
    print(f"  {color('Throughput:', Colors.DIM)} {processed / elapsed:.1f} msg/s")
    print()
    print(f"  {color('Total relationships now:', Colors.DIM)} {final_stats['total_relationships']:,}")
    print(f"  {color('New relationships:', Colors.DIM)} {final_stats['total_relationships'] - initial_stats['total_relationships']:,}")
    print()

    return {
        "messages_processed": processed,
        "relations_extracted": total_extracted,
        "relations_stored": total_stored,
        "errors": errors,
        "elapsed_seconds": elapsed,
        "new_relationships": final_stats["total_relationships"] - initial_stats["total_relationships"],
    }


async def show_status(memory: MemoryClient) -> None:
    """Show current relationship extraction status."""
    # Get counts
    total_with_entities = await get_message_count(memory, skip_processed=False)
    pending = await get_message_count(memory, skip_processed=True)
    processed = total_with_entities - pending

    stats = await get_relationship_stats(memory)

    print()
    print(color("Relationship Extraction Status", Colors.BOLD + Colors.CYAN))
    print("=" * 50)
    print()
    print(f"  {color('Messages with 2+ entities:', Colors.DIM)} {total_with_entities:,}")
    print(f"  {color('Messages processed:', Colors.DIM)} {processed:,}")
    print(f"  {color('Messages pending:', Colors.DIM)} {pending:,}")
    print()
    print(f"  {color('Total RELATED_TO relationships:', Colors.DIM)} {stats['total_relationships']:,}")
    print(f"  {color('Unique relationship types:', Colors.DIM)} {stats['unique_types']}")
    print()

    if pending > 0:
        print(f"  Run {color('make backfill-relationships', Colors.YELLOW)} to process pending messages.")
    else:
        print(f"  {color('All messages have been processed!', Colors.GREEN)}")
    print()


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill RELATED_TO relationships for existing entities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current status
  %(prog)s --status

  # Run backfill (skip already processed)
  %(prog)s

  # Reprocess all messages (including already processed)
  %(prog)s --reprocess

  # Process only 100 messages
  %(prog)s --limit 100

  # Preview without making changes
  %(prog)s --dry-run
""",
    )
    parser.add_argument(
        "--neo4j-uri",
        default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j connection URI",
    )
    parser.add_argument(
        "--neo4j-user",
        default=os.getenv("NEO4J_USERNAME", "neo4j"),
        help="Neo4j username",
    )
    parser.add_argument(
        "--neo4j-password",
        default=os.getenv("NEO4J_PASSWORD", "password"),
        help="Neo4j password",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of messages per batch (default: 50)",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Reprocess all messages, not just pending ones",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit total messages to process",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status and exit",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Confidence threshold for relations (default: 0.5)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda", "mps"],
        help="Device to run GLiREL on (default: cpu)",
    )

    args = parser.parse_args()

    # Check GLiREL availability
    if not args.status and not is_glirel_available():
        print(color("Error: GLiREL is not installed.", Colors.RED))
        print("Install it with: pip install glirel")
        sys.exit(1)

    # Connect to Neo4j
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=args.neo4j_uri,
            username=args.neo4j_user,
            password=SecretStr(args.neo4j_password),
        ),
    )

    print()
    print(color("Connecting to Neo4j...", Colors.DIM), end=" ", flush=True)

    try:
        memory_client = MemoryClient(settings)
        async with memory_client as memory:
            print(color("Connected!", Colors.GREEN))

            if args.status:
                await show_status(memory)
                return

            # Initialize GLiREL extractor
            print(color("Loading GLiREL model...", Colors.DIM), end=" ", flush=True)
            extractor = GLiRELExtractor.for_poleo(
                threshold=args.threshold,
                device=args.device,
            )
            # Force model load
            _ = extractor.model
            print(color("Loaded!", Colors.GREEN))

            # Run backfill
            await backfill_relationships(
                memory,
                extractor,
                batch_size=args.batch_size,
                skip_processed=not args.reprocess,
                dry_run=args.dry_run,
                limit=args.limit,
            )

    except KeyboardInterrupt:
        print()
        print(color("\nInterrupted by user.", Colors.YELLOW))
        sys.exit(130)
    except Exception as e:
        print(color(f"Error: {e}", Colors.RED))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
