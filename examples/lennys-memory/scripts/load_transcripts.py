#!/usr/bin/env python3
"""Load Lenny's Podcast transcripts into neo4j-agent-memory."""

import argparse
import asyncio
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig

# Load .env file from backend directory
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")


@dataclass
class SpeakerTurn:
    """A single speaker turn in a transcript."""

    speaker: str
    timestamp: str
    content: str
    episode_guest: str


def parse_transcript(file_path: Path) -> list[SpeakerTurn]:
    """Parse a transcript file into speaker turns.

    Format:
        Speaker Name (HH:MM:SS):
        [Content...]

        (HH:MM:SS):
        [Content continuation from same speaker...]
    """
    content = file_path.read_text(encoding="utf-8")
    guest_name = file_path.stem  # Filename without .txt

    # Pattern matches "Speaker Name (HH:MM:SS):" or just "(HH:MM:SS):"
    # The speaker name is optional (continuation of previous speaker)
    pattern = r"^(?:([A-Za-z][A-Za-z0-9\s\.\-\']+?)\s+)?\((\d{2}:\d{2}:\d{2})\):$"

    turns: list[SpeakerTurn] = []
    current_speaker: str | None = None
    current_timestamp: str | None = None
    current_content: list[str] = []

    for line in content.split("\n"):
        line = line.strip()
        match = re.match(pattern, line)

        if match:
            # Save previous turn if exists
            if current_speaker and current_content:
                turns.append(
                    SpeakerTurn(
                        speaker=current_speaker,
                        timestamp=current_timestamp or "00:00:00",
                        content="\n".join(current_content).strip(),
                        episode_guest=guest_name,
                    )
                )

            # Start new turn
            speaker_name = match.group(1)
            if speaker_name:
                current_speaker = speaker_name.strip()
            # If no speaker name, it's a continuation of previous speaker
            current_timestamp = match.group(2)
            current_content = []
        elif line:
            # Content line
            current_content.append(line)

    # Don't forget last turn
    if current_speaker and current_content:
        turns.append(
            SpeakerTurn(
                speaker=current_speaker,
                timestamp=current_timestamp or "00:00:00",
                content="\n".join(current_content).strip(),
                episode_guest=guest_name,
            )
        )

    return turns


def slugify(name: str) -> str:
    """Convert name to URL-friendly slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


async def load_transcript(
    memory: MemoryClient,
    file_path: Path,
    extract_entities: bool = True,
    generate_embeddings: bool = True,
    verbose: bool = False,
) -> dict:
    """Load a single transcript into memory."""
    turns = parse_transcript(file_path)
    guest_name = file_path.stem

    # Create a session_id for this episode
    session_id = f"lenny-podcast-{slugify(guest_name)}"

    stats = {"turns": 0, "speakers": set()}

    for i, turn in enumerate(turns):
        # Use "user" role for Lenny, "assistant" role for guests
        role = "user" if turn.speaker.lower() == "lenny" else "assistant"

        # Include metadata about the episode
        metadata = {
            "episode_guest": turn.episode_guest,
            "speaker": turn.speaker,
            "timestamp": turn.timestamp,
            "source": "lenny_podcast",
            "turn_index": i,
        }

        try:
            await memory.episodic.add_message(
                session_id=session_id,
                role=role,
                content=turn.content,
                metadata=metadata,
                extract_entities=extract_entities,
                generate_embedding=generate_embeddings,
            )
            stats["turns"] += 1
            stats["speakers"].add(turn.speaker)

            if verbose and stats["turns"] % 10 == 0:
                print(f"  Loaded {stats['turns']} turns...")

        except Exception as e:
            print(f"  Warning: Failed to load turn {i}: {e}")

    return stats


async def load_all_transcripts(
    memory: MemoryClient,
    data_dir: Path,
    sample_size: int | None = None,
    extract_entities: bool = True,
    generate_embeddings: bool = True,
    verbose: bool = False,
) -> dict:
    """Load all transcripts from the data directory."""
    files = sorted(data_dir.glob("*.txt"))

    if not files:
        print(f"No .txt files found in {data_dir}")
        return {"files": 0, "turns": 0, "speakers": set()}

    if sample_size:
        files = files[:sample_size]

    total_stats = {"files": 0, "turns": 0, "speakers": set()}

    print(f"Loading {len(files)} transcript(s)...")
    print()

    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Loading: {file_path.name}")

        try:
            stats = await load_transcript(
                memory,
                file_path,
                extract_entities=extract_entities,
                generate_embeddings=generate_embeddings,
                verbose=verbose,
            )
            total_stats["files"] += 1
            total_stats["turns"] += stats["turns"]
            total_stats["speakers"].update(stats["speakers"])
            print(f"  -> {stats['turns']} turns, {len(stats['speakers'])} speakers")
        except Exception as e:
            print(f"  ERROR: {e}")

    return total_stats


async def main():
    parser = argparse.ArgumentParser(
        description="Load Lenny's Podcast transcripts into neo4j-agent-memory"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Directory containing transcript .txt files",
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Load only N transcripts (for testing)",
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
        "--no-entities",
        action="store_true",
        help="Skip entity extraction (faster loading)",
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Skip embedding generation (faster loading)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )

    args = parser.parse_args()

    # Validate data directory
    if not args.data_dir.exists():
        print(f"Error: Data directory not found: {args.data_dir}")
        sys.exit(1)

    print("=" * 60)
    print("Lenny's Podcast Transcript Loader")
    print("=" * 60)
    print()
    print(f"Data directory: {args.data_dir}")
    print(f"Neo4j URI: {args.neo4j_uri}")
    print(f"Sample size: {args.sample or 'all'}")
    print(f"Entity extraction: {not args.no_entities}")
    print(f"Embeddings: {not args.no_embeddings}")
    print()

    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=args.neo4j_uri,
            username=args.neo4j_user,
            password=SecretStr(args.neo4j_password),
        )
    )

    print("Connecting to Neo4j...")
    async with MemoryClient(settings) as memory:
        print("Connected!")
        print()

        stats = await load_all_transcripts(
            memory,
            args.data_dir,
            sample_size=args.sample,
            extract_entities=not args.no_entities,
            generate_embeddings=not args.no_embeddings,
            verbose=args.verbose,
        )

        print()
        print("=" * 60)
        print("Loading Complete!")
        print("=" * 60)
        print(f"Files loaded: {stats['files']}")
        print(f"Total turns: {stats['turns']}")
        print(f"Unique speakers: {len(stats['speakers'])}")
        if stats["speakers"]:
            print(f"Speakers: {', '.join(sorted(stats['speakers']))}")


if __name__ == "__main__":
    asyncio.run(main())
