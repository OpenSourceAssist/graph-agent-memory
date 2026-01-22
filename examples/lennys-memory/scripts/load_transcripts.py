#!/usr/bin/env python3
"""Load Lenny's Podcast transcripts into neo4j-agent-memory.

Features:
- Real-time progress bars and ETA
- Concurrent transcript processing
- Resume capability (skip already loaded transcripts)
- Detailed statistics and timing
- Retry logic for transient failures
- Buffered warnings/logs to prevent progress bar disruption
"""

# ============================================================================
# IMPORTANT: Warning suppression must happen BEFORE any other imports
# to catch warnings triggered during module initialization
# ============================================================================
import os
import warnings

# Suppress all warnings from noisy libraries
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*resume_download.*")
warnings.filterwarnings("ignore", message=".*byte fallback.*")
warnings.filterwarnings("ignore", message=".*truncate to max_length.*")
warnings.filterwarnings("ignore", message=".*no predefined maximum length.*")
warnings.filterwarnings("ignore", message=".*schema.*shadows.*")

# Disable huggingface progress bars and logging noise
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import argparse
import asyncio
import io
import logging
import re
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig

# Load .env file from backend directory
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    # ANSI escape sequences for cursor control
    CLEAR_LINE = "\033[2K"
    CURSOR_UP = "\033[1A"
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"


def supports_color() -> bool:
    """Check if terminal supports colors."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLORS = supports_color()


class BufferedLogHandler(logging.Handler):
    """A logging handler that buffers messages to avoid disrupting progress bars."""

    def __init__(self):
        super().__init__()
        self.buffer: list[logging.LogRecord] = []
        self._buffering = False

    def emit(self, record: logging.LogRecord) -> None:
        if self._buffering:
            self.buffer.append(record)
        else:
            # Print immediately if not buffering
            msg = self.format(record)
            print(msg, file=sys.stderr)

    def start_buffering(self) -> None:
        self._buffering = True

    def stop_buffering(self) -> None:
        self._buffering = False

    def flush_buffer(self, clear_line: bool = True) -> list[str]:
        """Flush buffered messages and return them."""
        messages = []
        for record in self.buffer:
            messages.append(self.format(record))
        self.buffer.clear()
        return messages


# Global buffered handler for capturing logs during progress
_buffered_handler = BufferedLogHandler()
_buffered_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))


def setup_logging(verbose: bool = False) -> None:
    """Configure logging to use buffered handler."""
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING if not verbose else logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our buffered handler
    root_logger.addHandler(_buffered_handler)

    # Also suppress specific noisy loggers
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


@contextmanager
def suppress_output_during_progress():
    """Context manager to buffer logs and warnings during progress bar updates."""
    # Start buffering logs
    _buffered_handler.start_buffering()

    # Capture warnings
    old_showwarning = warnings.showwarning
    captured_warnings: list[str] = []

    def capture_warning(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(f"Warning: {message}")

    warnings.showwarning = capture_warning

    # Also redirect stderr temporarily to catch any direct prints
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()

    try:
        yield
    finally:
        # Restore stderr
        stderr_content = sys.stderr.getvalue()
        sys.stderr = old_stderr

        # Stop buffering
        _buffered_handler.stop_buffering()

        # Restore warnings
        warnings.showwarning = old_showwarning


def flush_buffered_output(progress_bar_active: bool = False) -> list[str]:
    """Flush any buffered output and return messages for later display.

    Args:
        progress_bar_active: If True, messages are returned for display after
                           progress bar completes. If False, messages are
                           printed immediately.

    Returns:
        List of buffered messages if progress_bar_active, empty list otherwise.
    """
    messages = _buffered_handler.flush_buffer()
    if not progress_bar_active and messages:
        for msg in messages:
            print(msg, file=sys.stderr)
        return []
    return messages


def color(text: str, color_code: str) -> str:
    """Apply color to text if supported."""
    if USE_COLORS:
        return f"{color_code}{text}{Colors.RESET}"
    return text


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
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


def format_rate(count: int, seconds: float) -> str:
    """Format rate as items per second or per minute."""
    if seconds == 0:
        return "N/A"
    rate = count / seconds
    if rate >= 1:
        return f"{rate:.1f}/s"
    else:
        return f"{rate * 60:.1f}/min"


class ProgressBar:
    """A simple progress bar for terminal output.

    Handles buffered warnings and logs to prevent disruption.
    """

    def __init__(
        self,
        total: int,
        prefix: str = "",
        width: int = 30,
        show_eta: bool = True,
    ):
        self.total = total
        self.prefix = prefix
        self.width = width
        self.show_eta = show_eta
        self.current = 0
        self.start_time = time.time()
        self._last_update = 0
        self._buffered_messages: list[str] = []
        self._active = False
        self._status: str = ""  # Current operation status

    def __enter__(self):
        """Start progress bar and begin buffering output."""
        self._active = True
        _buffered_handler.start_buffering()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop progress bar and flush buffered output."""
        self._active = False
        _buffered_handler.stop_buffering()
        # Collect any buffered messages
        self._buffered_messages.extend(_buffered_handler.flush_buffer())
        return False

    def set_status(self, status: str) -> None:
        """Set the current operation status."""
        self._status = status

    def update(self, current: int | None = None, suffix: str = "") -> None:
        """Update the progress bar."""
        if current is not None:
            self.current = current
        else:
            self.current += 1

        # Throttle updates to avoid flickering (max 10 updates/sec)
        now = time.time()
        if now - self._last_update < 0.1 and self.current < self.total:
            return
        self._last_update = now

        elapsed = now - self.start_time
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        # Calculate ETA
        eta_str = ""
        if self.show_eta and self.current > 0 and self.current < self.total:
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            eta_str = f" ETA: {format_duration(remaining)}"

        # Build the line
        line = f"\r{self.prefix} [{bar}] {self.current}/{self.total} ({percent:.0%}){eta_str}"
        if suffix:
            line += f" {suffix}"
        if self._status:
            line += f" {color(f'| {self._status}', Colors.DIM)}"

        # Clear to end of line and print
        sys.stdout.write(f"{line}\033[K")
        sys.stdout.flush()

    def finish(self, message: str = "") -> None:
        """Complete the progress bar."""
        self._status = ""  # Clear status
        elapsed = time.time() - self.start_time
        self.update(self.total)
        rate = format_rate(self.total, elapsed)
        final_msg = f" [{format_duration(elapsed)}, {rate}]"
        if message:
            final_msg += f" {message}"
        print(final_msg)

        # Print any buffered messages after the progress bar is done
        if self._buffered_messages:
            print()  # Add spacing
            for msg in self._buffered_messages:
                print(f"  {color('⚠', Colors.YELLOW)} {msg}")
            self._buffered_messages.clear()

    def add_warning(self, message: str) -> None:
        """Add a warning message to be displayed after progress completes."""
        self._buffered_messages.append(message)


@dataclass
class SpeakerTurn:
    """A single speaker turn in a transcript."""

    speaker: str
    timestamp: str
    content: str
    episode_guest: str


@dataclass
class LoadStats:
    """Statistics for a loading operation."""

    files_loaded: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    turns_loaded: int = 0
    entities_extracted: int = 0
    speakers: set = field(default_factory=set)
    errors: list = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def turns_per_second(self) -> float:
        return self.turns_loaded / self.elapsed if self.elapsed > 0 else 0


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


async def check_session_exists(memory: MemoryClient, session_id: str) -> bool:
    """Check if a session already exists in the database."""
    try:
        messages = await memory.short_term.get_messages(session_id, limit=1)
        return len(messages) > 0
    except Exception:
        return False


async def load_transcript(
    memory: MemoryClient,
    file_path: Path,
    extract_entities: bool = True,
    generate_embeddings: bool = True,
    batch_size: int = 50,
    max_retries: int = 3,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    """Load a single transcript into memory.

    Args:
        memory: MemoryClient instance
        file_path: Path to transcript file
        extract_entities: Whether to extract entities from messages
        generate_embeddings: Whether to generate embeddings for semantic search
        batch_size: Number of messages to process in each batch
        max_retries: Maximum retry attempts for transient failures
        on_progress: Optional callback for progress updates (current, total)

    Returns:
        Stats dict with turns loaded, speakers found, and any errors
    """
    turns = parse_transcript(file_path)
    guest_name = file_path.stem

    # Create a session_id for this episode
    session_id = f"lenny-podcast-{slugify(guest_name)}"

    stats = {"turns": 0, "speakers": set(), "errors": []}

    # Prepare messages
    messages = []
    for i, turn in enumerate(turns):
        role = "user" if turn.speaker.lower() == "lenny" else "assistant"
        metadata = {
            "episode_guest": turn.episode_guest,
            "speaker": turn.speaker,
            "timestamp": turn.timestamp,
            "source": "lenny_podcast",
            "turn_index": i,
        }
        messages.append(
            {
                "role": role,
                "content": turn.content,
                "metadata": metadata,
            }
        )
        stats["speakers"].add(turn.speaker)

    # Try batch loading with retries
    for attempt in range(max_retries):
        try:
            await memory.short_term.add_messages_batch(
                session_id=session_id,
                messages=messages,
                batch_size=batch_size,
                generate_embeddings=generate_embeddings,
                extract_entities=extract_entities,
                on_progress=on_progress,
            )
            stats["turns"] = len(messages)
            return stats
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                stats["errors"].append(
                    f"Attempt {attempt + 1} failed: {e}, retrying in {wait_time}s"
                )
                await asyncio.sleep(wait_time)
            else:
                stats["errors"].append(f"All {max_retries} attempts failed: {e}")
                raise

    return stats


async def load_all_transcripts(
    memory: MemoryClient,
    data_dir: Path,
    sample_size: int | None = None,
    extract_entities: bool = True,
    generate_embeddings: bool = True,
    skip_existing: bool = False,
    batch_size: int = 50,
    concurrency: int = 1,
    dry_run: bool = False,
) -> LoadStats:
    """Load all transcripts from the data directory.

    Args:
        memory: MemoryClient instance
        data_dir: Directory containing transcript files
        sample_size: Optional limit on number of files to load
        extract_entities: Whether to extract entities
        generate_embeddings: Whether to generate embeddings
        skip_existing: Skip transcripts that are already loaded
        batch_size: Batch size for message loading
        concurrency: Number of transcripts to process concurrently
        dry_run: If True, only show what would be loaded without loading

    Returns:
        LoadStats with detailed statistics
    """
    files = sorted(data_dir.glob("*.txt"))

    if not files:
        print(f"No .txt files found in {data_dir}")
        return LoadStats()

    if sample_size:
        files = files[:sample_size]

    stats = LoadStats()

    # Check which files to skip if resume mode
    files_to_load = []
    if skip_existing:
        print("Checking for existing transcripts...")
        check_bar = ProgressBar(len(files), prefix="Scanning")
        with check_bar:
            for i, file_path in enumerate(files):
                session_id = f"lenny-podcast-{slugify(file_path.stem)}"
                exists = await check_session_exists(memory, session_id)
                if exists:
                    stats.files_skipped += 1
                else:
                    files_to_load.append(file_path)
                check_bar.update(i + 1)
        check_bar.finish()

        if stats.files_skipped > 0:
            print(
                f"  {color(f'Skipping {stats.files_skipped} already loaded', Colors.YELLOW)}, "
                f"{len(files_to_load)} remaining"
            )
    else:
        files_to_load = files

    if not files_to_load:
        print(color("All transcripts already loaded!", Colors.GREEN))
        return stats

    # Dry run - just show what would be loaded
    if dry_run:
        print(
            f"\n{color('DRY RUN', Colors.YELLOW)} - Would load {len(files_to_load)} transcript(s):"
        )
        total_turns = 0
        for file_path in files_to_load:
            turns = parse_transcript(file_path)
            total_turns += len(turns)
            print(f"  • {file_path.name}: {len(turns)} turns")
        print(f"\nTotal: {len(files_to_load)} files, {total_turns} turns")
        return stats

    print(f"\nLoading {len(files_to_load)} transcript(s)...")
    print()

    # Calculate total turns for overall progress
    total_turns = 0
    file_turns: dict[Path, int] = {}
    for file_path in files_to_load:
        turns = parse_transcript(file_path)
        file_turns[file_path] = len(turns)
        total_turns += len(turns)

    # Build processing pipeline description
    pipeline_steps = []
    if generate_embeddings:
        pipeline_steps.append("embeddings")
    if extract_entities:
        pipeline_steps.append("entities")
    pipeline_desc = " + ".join(pipeline_steps) if pipeline_steps else "storage only"

    # Overall progress bar
    overall_bar = ProgressBar(total_turns, prefix="Loading ")
    turns_loaded = 0

    async def load_one(file_path: Path, file_index: int) -> dict | None:
        """Load a single transcript with progress reporting."""
        nonlocal turns_loaded

        file_name = file_path.name

        def progress_callback(current: int, total: int) -> None:
            nonlocal turns_loaded
            # Determine current phase based on progress
            phase = "storing"
            if generate_embeddings and current < total:
                phase = "generating embeddings"
            if extract_entities and current >= total * 0.5:
                phase = "extracting entities"
            if current >= total:
                phase = "finalizing"

            overall_bar.set_status(phase)
            # Update overall progress
            overall_bar.update(
                turns_loaded + current,
                suffix=color(f"[{file_index}/{len(files_to_load)}] {file_name}", Colors.DIM),
            )

        try:
            # Show initial status
            overall_bar.set_status("parsing transcript")
            overall_bar.update(
                turns_loaded,
                suffix=color(f"[{file_index}/{len(files_to_load)}] {file_name}", Colors.DIM),
            )

            result = await load_transcript(
                memory,
                file_path,
                extract_entities=extract_entities,
                generate_embeddings=generate_embeddings,
                batch_size=batch_size,
                on_progress=progress_callback,
            )
            turns_loaded += result["turns"]
            # Capture any errors from retries as warnings
            if result.get("errors"):
                for err in result["errors"]:
                    overall_bar.add_warning(f"{file_name}: {err}")
            return result
        except Exception as e:
            stats.errors.append(f"{file_name}: {e}")
            overall_bar.add_warning(f"{file_name}: {e}")
            return None

    # Show pipeline info
    print(f"  {color('Pipeline:', Colors.DIM)} {pipeline_desc}")
    print()

    # Process files with buffered output to prevent log disruption
    # Use context manager to buffer logs during progress bar updates
    with overall_bar:
        for i, file_path in enumerate(files_to_load, 1):
            result = await load_one(file_path, i)
            if result:
                stats.files_loaded += 1
                stats.turns_loaded += result["turns"]
                stats.speakers.update(result["speakers"])
            else:
                stats.files_failed += 1

    overall_bar.finish(color("Done!", Colors.GREEN))

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Load Lenny's Podcast transcripts into neo4j-agent-memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load 5 sample transcripts for testing
  %(prog)s --sample 5

  # Load all transcripts without entity extraction (faster)
  %(prog)s --no-entities

  # Resume loading (skip already loaded transcripts)
  %(prog)s --resume

  # Preview what would be loaded
  %(prog)s --dry-run

  # Verbose output with larger batches
  %(prog)s -v --batch-size 100
""",
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
        metavar="N",
        help="Load only N transcripts (for testing)",
    )
    parser.add_argument(
        "--neo4j-uri",
        default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j connection URI (default: from NEO4J_URI env var)",
    )
    parser.add_argument(
        "--neo4j-user",
        default=os.getenv("NEO4J_USERNAME", "neo4j"),
        help="Neo4j username (default: from NEO4J_USERNAME env var)",
    )
    parser.add_argument(
        "--neo4j-password",
        default=os.getenv("NEO4J_PASSWORD", "password"),
        help="Neo4j password (default: from NEO4J_PASSWORD env var)",
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
        "--resume",
        action="store_true",
        help="Skip transcripts that are already loaded",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        metavar="N",
        help="Number of messages per batch (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be loaded without loading",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress",
    )

    args = parser.parse_args()

    # Set up logging to prevent disruption of progress bars
    setup_logging(verbose=args.verbose)

    # Validate data directory
    if not args.data_dir.exists():
        print(color(f"Error: Data directory not found: {args.data_dir}", Colors.RED))
        sys.exit(1)

    # Count available files
    files = list(args.data_dir.glob("*.txt"))
    if not files:
        print(color(f"Error: No .txt files found in {args.data_dir}", Colors.RED))
        sys.exit(1)

    print()
    print(color("═" * 60, Colors.CYAN))
    print(color("  Lenny's Podcast Transcript Loader", Colors.BOLD))
    print(color("═" * 60, Colors.CYAN))
    print()
    print(f"  {color('Data directory:', Colors.DIM)} {args.data_dir}")
    print(f"  {color('Available files:', Colors.DIM)} {len(files)}")
    print(f"  {color('Neo4j URI:', Colors.DIM)} {args.neo4j_uri}")
    print(f"  {color('Sample size:', Colors.DIM)} {args.sample or 'all'}")
    print(
        f"  {color('Entity extraction:', Colors.DIM)} {color('enabled', Colors.GREEN) if not args.no_entities else color('disabled', Colors.YELLOW)}"
    )
    print(
        f"  {color('Embeddings:', Colors.DIM)} {color('enabled', Colors.GREEN) if not args.no_embeddings else color('disabled', Colors.YELLOW)}"
    )
    print(
        f"  {color('Resume mode:', Colors.DIM)} {color('enabled', Colors.GREEN) if args.resume else color('disabled', Colors.DIM)}"
    )
    print(f"  {color('Batch size:', Colors.DIM)} {args.batch_size}")
    if args.dry_run:
        print(f"  {color('Mode:', Colors.DIM)} {color('DRY RUN', Colors.YELLOW)}")
    print()

    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=args.neo4j_uri,
            username=args.neo4j_user,
            password=SecretStr(args.neo4j_password),
        )
    )

    if not args.dry_run:
        print("Connecting to Neo4j...", end=" ", flush=True)

    try:
        # Suppress any warnings during connection
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            memory_client = MemoryClient(settings)

        async with memory_client as memory:
            if not args.dry_run:
                print(color("Connected!", Colors.GREEN))

            stats = await load_all_transcripts(
                memory,
                args.data_dir,
                sample_size=args.sample,
                extract_entities=not args.no_entities,
                generate_embeddings=not args.no_embeddings,
                skip_existing=args.resume,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )

            if args.dry_run:
                sys.exit(0)

            # Print summary
            print()
            print(color("═" * 60, Colors.CYAN))
            print(color("  Loading Complete!", Colors.BOLD + Colors.GREEN))
            print(color("═" * 60, Colors.CYAN))
            print()
            print(f"  {color('Files loaded:', Colors.DIM)} {stats.files_loaded}")
            if stats.files_skipped > 0:
                print(f"  {color('Files skipped:', Colors.DIM)} {stats.files_skipped}")
            if stats.files_failed > 0:
                print(
                    f"  {color('Files failed:', Colors.DIM)} {color(str(stats.files_failed), Colors.RED)}"
                )
            print(f"  {color('Total turns:', Colors.DIM)} {stats.turns_loaded:,}")
            print(f"  {color('Unique speakers:', Colors.DIM)} {len(stats.speakers)}")
            print(f"  {color('Elapsed time:', Colors.DIM)} {format_duration(stats.elapsed)}")
            print(
                f"  {color('Throughput:', Colors.DIM)} {format_rate(stats.turns_loaded, stats.elapsed)}"
            )
            if stats.speakers:
                print()
                print(f"  {color('Speakers:', Colors.DIM)}")
                for speaker in sorted(stats.speakers):
                    print(f"    • {speaker}")

            if stats.errors:
                print()
                print(color("  Errors:", Colors.RED))
                for error in stats.errors[:10]:  # Show first 10 errors
                    print(f"    • {error}")
                if len(stats.errors) > 10:
                    print(f"    ... and {len(stats.errors) - 10} more")

            print()

    except KeyboardInterrupt:
        print()
        print(color("\nInterrupted by user.", Colors.YELLOW))
        sys.exit(130)
    except Exception as e:
        print(color(f"Error: {e}", Colors.RED))
        sys.exit(1)

    # Explicit successful exit
    sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print(color("\nInterrupted by user.", Colors.YELLOW))
        sys.exit(130)
