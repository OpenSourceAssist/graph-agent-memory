#!/usr/bin/env python3
"""Enrich entities with Wikipedia data.

This script enriches Entity nodes in Neo4j with data from Wikipedia/Wikimedia:
- Description/summary from Wikipedia
- Wikipedia URL
- Wikidata ID
- Thumbnail image URL

Features:
- Real-time progress bars with ETA
- Configurable rate limiting (respects Wikimedia ToS)
- Skip already-enriched entities
- Filter by entity type
- Detailed statistics on completion
"""

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from backend directory
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.config.settings import EmbeddingConfig
from neo4j_agent_memory.enrichment.wikimedia import WikimediaProvider
from neo4j_agent_memory.enrichment.base import EnrichmentStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)


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
    PURPLE = "\033[95m"


def supports_color() -> bool:
    """Check if terminal supports colors."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLORS = supports_color()


def color(text: str, color_code: str) -> str:
    """Apply color to text if supported."""
    if USE_COLORS:
        return f"{color_code}{text}{Colors.RESET}"
    return text


@dataclass
class EnrichmentStats:
    """Statistics for enrichment run."""
    total: int = 0
    enriched: int = 0
    not_found: int = 0
    skipped: int = 0
    errors: int = 0
    rate_limited: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        processed = self.enriched + self.not_found + self.errors
        if processed == 0:
            return 0.0
        return self.enriched / processed * 100


def format_time(seconds: float) -> str:
    """Format seconds as human-readable time."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def print_progress(
    current: int,
    total: int,
    stats: EnrichmentStats,
    start_time: float,
    current_entity: str = "",
) -> None:
    """Print progress bar with stats."""
    if total == 0:
        return

    # Calculate progress
    progress = current / total
    bar_width = 30
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)

    # Calculate ETA
    elapsed = time.time() - start_time
    if current > 0:
        eta = (elapsed / current) * (total - current)
        eta_str = format_time(eta)
    else:
        eta_str = "calculating..."

    # Truncate entity name
    entity_display = current_entity[:30] + "..." if len(current_entity) > 30 else current_entity

    # Build status line
    status = (
        f"\r{color('Progress', Colors.CYAN)} [{bar}] "
        f"{current}/{total} ({progress*100:.1f}%) "
        f"ETA: {eta_str} "
        f"| {color('✓', Colors.GREEN)}{stats.enriched} "
        f"{color('✗', Colors.RED)}{stats.not_found} "
        f"{color('!', Colors.YELLOW)}{stats.errors} "
        f"| {entity_display:<35}"
    )

    print(status, end="", flush=True)


async def get_unenriched_entities(
    client: MemoryClient,
    entity_types: list[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Get entities that haven't been enriched yet.

    Args:
        client: Memory client
        entity_types: Filter by entity types (e.g., ["PERSON", "ORGANIZATION"])
        limit: Maximum number of entities to return

    Returns:
        List of entity dicts with id, name, type
    """
    # Build query
    type_filter = ""
    if entity_types:
        types_str = ", ".join(f"'{t.upper()}'" for t in entity_types)
        type_filter = f"AND e.type IN [{types_str}]"

    limit_clause = f"LIMIT {limit}" if limit else ""

    query = f"""
    MATCH (e:Entity)
    WHERE e.enriched_description IS NULL
      AND e.enrichment_error IS NULL
      {type_filter}
    RETURN e.id AS id, e.name AS name, e.type AS type, e.description AS description
    ORDER BY e.name
    {limit_clause}
    """

    result = await client._client.execute_read(query)
    return [dict(record) for record in result]


async def get_enrichment_status(client: MemoryClient) -> dict:
    """Get current enrichment status of all entities.

    Returns:
        Dict with counts: total, enriched, pending, errors
    """
    query = """
    MATCH (e:Entity)
    RETURN
        count(e) AS total,
        count(CASE WHEN e.enriched_description IS NOT NULL THEN 1 END) AS enriched,
        count(CASE WHEN e.enriched_description IS NULL AND e.enrichment_error IS NULL THEN 1 END) AS pending,
        count(CASE WHEN e.enrichment_error IS NOT NULL THEN 1 END) AS errors
    """

    result = await client._client.execute_read(query)
    record = result[0] if result else {}
    return {
        "total": record.get("total", 0),
        "enriched": record.get("enriched", 0),
        "pending": record.get("pending", 0),
        "errors": record.get("errors", 0),
    }


async def update_entity_enrichment(
    client: MemoryClient,
    entity_id: str,
    enrichment_data: dict,
) -> None:
    """Update entity with enrichment data.

    Args:
        client: Memory client
        entity_id: Entity UUID
        enrichment_data: Dict with enrichment fields
    """
    query = """
    MATCH (e:Entity {id: $id})
    SET e.enriched_description = $enriched_description,
        e.wikipedia_url = $wikipedia_url,
        e.wikidata_id = $wikidata_id,
        e.image_url = $image_url,
        e.enriched_at = datetime(),
        e.enrichment_provider = $provider
    """

    await client._client.execute_write(query, {
        "id": entity_id,
        "enriched_description": enrichment_data.get("description"),
        "wikipedia_url": enrichment_data.get("wikipedia_url"),
        "wikidata_id": enrichment_data.get("wikidata_id"),
        "image_url": enrichment_data.get("image_url"),
        "provider": "wikimedia",
    })


async def mark_entity_not_found(
    client: MemoryClient,
    entity_id: str,
    reason: str,
) -> None:
    """Mark entity as not found in enrichment source.

    Args:
        client: Memory client
        entity_id: Entity UUID
        reason: Reason for not finding
    """
    query = """
    MATCH (e:Entity {id: $id})
    SET e.enrichment_error = $reason,
        e.enrichment_attempted_at = datetime()
    """

    await client._client.execute_write(query, {
        "id": entity_id,
        "reason": reason,
    })


async def enrich_entities(
    client: MemoryClient,
    entity_types: list[str] | None = None,
    limit: int | None = None,
    rate_limit: float = 0.5,
    dry_run: bool = False,
) -> EnrichmentStats:
    """Enrich entities with Wikipedia data.

    Args:
        client: Memory client
        entity_types: Filter by entity types
        limit: Maximum entities to process
        rate_limit: Seconds between API calls (default 0.5 = 2 req/sec)
        dry_run: If True, don't actually update entities

    Returns:
        EnrichmentStats with counts
    """
    stats = EnrichmentStats()

    # Get entities to enrich
    print(f"\n{color('Fetching entities to enrich...', Colors.CYAN)}")
    entities = await get_unenriched_entities(client, entity_types, limit)
    stats.total = len(entities)

    if stats.total == 0:
        print(f"{color('✓ All entities are already enriched!', Colors.GREEN)}")
        return stats

    print(f"Found {color(str(stats.total), Colors.BOLD)} entities to enrich")

    if dry_run:
        print(f"{color('DRY RUN - no changes will be made', Colors.YELLOW)}")
        for entity in entities[:10]:
            print(f"  Would enrich: {entity['name']} ({entity['type']})")
        if stats.total > 10:
            print(f"  ... and {stats.total - 10} more")
        return stats

    # Create Wikimedia provider
    provider = WikimediaProvider(
        rate_limit=rate_limit,
        language="en",
    )

    print(f"\n{color('Starting enrichment...', Colors.CYAN)}")
    print(f"Rate limit: {1/rate_limit:.1f} requests/second")
    print()

    start_time = time.time()

    for i, entity in enumerate(entities):
        entity_name = entity["name"]
        entity_type = entity["type"]
        entity_id = entity["id"]

        # Print progress
        print_progress(i, stats.total, stats, start_time, entity_name)

        try:
            # Call Wikimedia API
            result = await provider.enrich(
                entity_name,
                entity_type,
                context=entity.get("description"),
            )

            if result.status == EnrichmentStatus.SUCCESS and result.has_data():
                # Update entity with enrichment data
                await update_entity_enrichment(client, entity_id, {
                    "description": result.description,
                    "wikipedia_url": result.wikipedia_url,
                    "wikidata_id": result.wikidata_id,
                    "image_url": result.image_url,
                })
                stats.enriched += 1

            elif result.status == EnrichmentStatus.NOT_FOUND:
                await mark_entity_not_found(client, entity_id, "Not found in Wikipedia")
                stats.not_found += 1

            elif result.status == EnrichmentStatus.RATE_LIMITED:
                stats.rate_limited += 1
                # Wait longer and retry
                await asyncio.sleep(rate_limit * 5)
                continue

            else:
                await mark_entity_not_found(client, entity_id, result.error_message or "Unknown error")
                stats.errors += 1

        except Exception as e:
            logger.error(f"Error enriching {entity_name}: {e}")
            await mark_entity_not_found(client, entity_id, str(e))
            stats.errors += 1

        # Rate limiting
        await asyncio.sleep(rate_limit)

    # Final progress
    print_progress(stats.total, stats.total, stats, start_time, "Complete!")
    print()  # New line after progress bar

    return stats


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich entities with Wikipedia data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enrich all entities
  python enrich_entities.py

  # Enrich only PERSON and ORGANIZATION entities
  python enrich_entities.py --types PERSON ORGANIZATION

  # Enrich with slower rate limit (1 req/sec)
  python enrich_entities.py --rate-limit 1.0

  # Preview what would be enriched
  python enrich_entities.py --dry-run

  # Check enrichment status
  python enrich_entities.py --status
        """,
    )

    parser.add_argument(
        "--types", "-t",
        nargs="+",
        help="Entity types to enrich (e.g., PERSON ORGANIZATION LOCATION)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Maximum number of entities to enrich",
    )
    parser.add_argument(
        "--rate-limit", "-r",
        type=float,
        default=0.5,
        help="Seconds between API calls (default: 0.5 = 2 req/sec)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be enriched without making changes",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current enrichment status and exit",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Print header
    print()
    print(color("═" * 60, Colors.PURPLE))
    print(color("  Wikipedia Entity Enrichment", Colors.BOLD))
    print(color("═" * 60, Colors.PURPLE))

    # Get settings from environment
    import os
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        ),
        embedding=EmbeddingConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
        ),
    )

    print(f"\n{color('Connecting to Neo4j...', Colors.CYAN)}")

    async with MemoryClient(settings) as client:
        print(f"{color('✓ Connected', Colors.GREEN)}")

        # Show status
        status = await get_enrichment_status(client)
        print(f"\n{color('Current Status:', Colors.BOLD)}")
        print(f"  Total entities:    {status['total']:,}")
        print(f"  {color('Enriched:', Colors.GREEN)}        {status['enriched']:,}")
        print(f"  {color('Pending:', Colors.YELLOW)}         {status['pending']:,}")
        print(f"  {color('Errors:', Colors.RED)}          {status['errors']:,}")

        if status['total'] > 0:
            pct = status['enriched'] / status['total'] * 100
            print(f"  Coverage:          {pct:.1f}%")

        if args.status:
            return

        if status['pending'] == 0:
            print(f"\n{color('✓ All entities are already enriched!', Colors.GREEN)}")
            return

        # Estimate time
        pending = status['pending']
        if args.limit:
            pending = min(pending, args.limit)
        estimated_time = pending * args.rate_limit
        print(f"\n{color('Estimated time:', Colors.DIM)} {format_time(estimated_time)}")

        # Run enrichment
        stats = await enrich_entities(
            client,
            entity_types=args.types,
            limit=args.limit,
            rate_limit=args.rate_limit,
            dry_run=args.dry_run,
        )

        # Print summary
        print()
        print(color("═" * 60, Colors.PURPLE))
        print(color("  Enrichment Complete", Colors.BOLD))
        print(color("═" * 60, Colors.PURPLE))
        print(f"  Processed:     {stats.total:,}")
        print(f"  {color('Enriched:', Colors.GREEN)}     {stats.enriched:,}")
        print(f"  {color('Not found:', Colors.YELLOW)}    {stats.not_found:,}")
        print(f"  {color('Errors:', Colors.RED)}       {stats.errors:,}")
        if stats.rate_limited > 0:
            print(f"  {color('Rate limited:', Colors.YELLOW)} {stats.rate_limited:,}")
        print(f"  Success rate:  {stats.success_rate:.1f}%")
        print()


if __name__ == "__main__":
    asyncio.run(main())
