#!/usr/bin/env python3
"""Backfill embeddings for existing entities in the database.

This script generates embeddings for Entity nodes that don't have them,
enabling semantic vector search for entity lookup.

Usage:
    python backfill_embeddings.py [--batch-size 100] [--status]
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.graph.queries import (
    COUNT_ENTITIES_WITHOUT_EMBEDDINGS,
    GET_ENTITIES_WITHOUT_EMBEDDINGS,
    UPDATE_ENTITY_EMBEDDING,
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


async def get_status(client: MemoryClient) -> dict:
    """Get current embedding status."""
    # Count entities without embeddings
    result = await client._client.execute_read(
        COUNT_ENTITIES_WITHOUT_EMBEDDINGS, {}
    )
    pending = result[0]["count"] if result else 0

    # Count total entities
    total_result = await client._client.execute_read(
        "MATCH (e:Entity) RETURN count(e) AS count", {}
    )
    total = total_result[0]["count"] if total_result else 0

    # Count entities with embeddings
    with_embeddings = total - pending

    return {
        "total": total,
        "with_embeddings": with_embeddings,
        "pending": pending,
    }


async def backfill_embeddings(
    client: MemoryClient,
    batch_size: int = 100,
) -> None:
    """Generate embeddings for entities that don't have them."""
    # Get embedder from client
    embedder = client.long_term._embedder
    if embedder is None:
        logger.error("No embedder configured. Cannot generate embeddings.")
        return

    # Get initial status
    status = await get_status(client)
    total_pending = status["pending"]

    if total_pending == 0:
        print(color("\nAll entities already have embeddings!", Colors.GREEN))
        return

    print(f"\n{color('Entity Embedding Backfill', Colors.BOLD + Colors.CYAN)}")
    print(f"{'=' * 50}")
    print(f"Total entities: {color(str(status['total']), Colors.BOLD)}")
    print(f"With embeddings: {color(str(status['with_embeddings']), Colors.GREEN)}")
    print(f"Pending: {color(str(total_pending), Colors.YELLOW)}")
    print(f"{'=' * 50}\n")

    processed = 0
    embedded = 0
    errors = 0
    start_time = time.time()

    while True:
        # Get batch of entities without embeddings
        entities = await client._client.execute_read(
            GET_ENTITIES_WITHOUT_EMBEDDINGS,
            {"skip": 0, "limit": batch_size},  # Always skip 0 since we update as we go
        )

        if not entities:
            break

        for entity in entities:
            entity_id = entity["id"]
            name = entity["name"]
            entity_type = entity["type"]
            description = entity.get("description")

            try:
                # Create embedding text from name and description
                embed_text = name
                if description:
                    embed_text = f"{name}: {description}"

                # Generate embedding
                embedding = await embedder.embed(embed_text)

                # Update entity with embedding
                await client._client.execute_write(
                    UPDATE_ENTITY_EMBEDDING,
                    {"id": entity_id, "embedding": embedding},
                )

                embedded += 1

            except Exception as e:
                logger.warning(f"Error embedding entity {name}: {e}")
                errors += 1

            processed += 1

            # Progress update
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = total_pending - processed
            eta_seconds = remaining / rate if rate > 0 else 0
            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"

            progress_pct = (processed / total_pending) * 100
            progress_bar = f"[{'=' * int(progress_pct // 5)}{' ' * (20 - int(progress_pct // 5))}]"

            print(
                f"\r{progress_bar} {processed}/{total_pending} ({progress_pct:.1f}%) | "
                f"Embedded: {embedded} | Errors: {errors} | "
                f"{rate:.1f} ent/s | ETA: {eta_str}    ",
                end="",
                flush=True,
            )

    print()  # New line after progress

    elapsed = time.time() - start_time
    print(f"\n{color('Backfill Complete', Colors.BOLD + Colors.GREEN)}")
    print(f"{'=' * 50}")
    print(f"Processed: {processed} entities")
    print(f"Embedded: {color(str(embedded), Colors.GREEN)}")
    print(f"Errors: {color(str(errors), Colors.RED if errors > 0 else Colors.DIM)}")
    print(f"Time: {elapsed:.1f}s")
    print(f"{'=' * 50}")


async def main():
    parser = argparse.ArgumentParser(
        description="Backfill embeddings for entities without them"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of entities to process per batch (default: 100)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show status only, don't process",
    )
    args = parser.parse_args()

    # Get Neo4j config from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    # Get OpenAI API key for embeddings
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable is required")
        sys.exit(1)

    neo4j_config = Neo4jConfig(
        uri=neo4j_uri,
        user=neo4j_user,
        password=SecretStr(neo4j_password),
        database=neo4j_database,
    )

    settings = MemorySettings(
        neo4j=neo4j_config,
        openai_api_key=SecretStr(openai_api_key),
    )

    async with MemoryClient(settings) as client:
        if args.status:
            status = await get_status(client)
            print(f"\n{color('Entity Embedding Status', Colors.BOLD + Colors.CYAN)}")
            print(f"{'=' * 50}")
            print(f"Total entities: {color(str(status['total']), Colors.BOLD)}")
            print(f"With embeddings: {color(str(status['with_embeddings']), Colors.GREEN)}")
            print(f"Pending: {color(str(status['pending']), Colors.YELLOW)}")
            print(f"{'=' * 50}")
        else:
            await backfill_embeddings(client, batch_size=args.batch_size)


if __name__ == "__main__":
    asyncio.run(main())
