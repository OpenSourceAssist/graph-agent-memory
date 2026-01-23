"""Smoke tests for entity_resolution.py example.

This example doesn't require Neo4j - it tests resolution algorithms only.
"""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"


class TestEntityResolutionExample:
    """Smoke tests for the entity resolution example."""

    def test_example_file_exists(self, examples_dir):
        """Verify the example file exists."""
        example_path = examples_dir / "entity_resolution.py"
        assert example_path.exists(), f"Example file not found: {example_path}"

    def test_example_imports_work(self):
        """Verify the example can import required modules."""
        # Test that core resolution modules are importable
        from neo4j_agent_memory.resolution import (
            CompositeResolver,
            ExactMatchResolver,
            FuzzyMatchResolver,
        )

        assert ExactMatchResolver is not None
        assert FuzzyMatchResolver is not None
        assert CompositeResolver is not None

    @pytest.mark.asyncio
    async def test_exact_match_resolver(self):
        """Test the ExactMatchResolver functionality shown in the example."""
        from neo4j_agent_memory.resolution import ExactMatchResolver

        resolver = ExactMatchResolver()
        existing = ["John Smith", "Acme Corporation"]

        # Exact match
        result = await resolver.resolve("John Smith", "PERSON", existing_entities=existing)
        assert result.canonical_name == "John Smith"

        # Case-insensitive match
        result = await resolver.resolve("john smith", "PERSON", existing_entities=existing)
        assert result.canonical_name.lower() == "john smith"

    @pytest.mark.asyncio
    async def test_fuzzy_match_resolver(self):
        """Test the FuzzyMatchResolver functionality shown in the example."""
        try:
            from rapidfuzz import fuzz  # noqa: F401
        except ImportError:
            pytest.skip("rapidfuzz not installed - fuzzy matching unavailable")

        from neo4j_agent_memory.resolution import FuzzyMatchResolver

        resolver = FuzzyMatchResolver(threshold=0.8)
        existing = ["John Smith", "Acme Corporation"]

        # Typo should match
        result = await resolver.resolve("Jon Smith", "PERSON", existing_entities=existing)
        assert result.canonical_name == "John Smith"
        assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_composite_resolver(self):
        """Test the CompositeResolver functionality shown in the example."""
        try:
            from rapidfuzz import fuzz  # noqa: F401
        except ImportError:
            pytest.skip("rapidfuzz not installed - composite resolution unavailable")

        from neo4j_agent_memory.resolution import CompositeResolver

        resolver = CompositeResolver(fuzzy_threshold=0.8)
        existing = ["John Smith"]

        # Exact match takes priority - with existing entities it should match
        result = await resolver.resolve("John Smith", "PERSON", existing_entities=existing)
        assert result.canonical_name == "John Smith"
        # Confidence should be high for exact match
        assert result.confidence >= 0.9

        # Fuzzy match for typos
        result = await resolver.resolve("Jon Smith", "PERSON", existing_entities=existing)
        assert result.canonical_name == "John Smith"

        # No match returns original
        result = await resolver.resolve("Totally Different", "PERSON", existing_entities=existing)
        assert result.canonical_name == "Totally Different"
        assert result.match_type == "none"

    @pytest.mark.asyncio
    async def test_batch_resolution(self):
        """Test batch resolution functionality shown in the example."""
        try:
            from neo4j_agent_memory.resolution import CompositeResolver

            resolver = CompositeResolver()

            batch = [
                ("John Smith", "PERSON"),
                ("Jane Doe", "PERSON"),
                ("john smith", "PERSON"),  # Duplicate
            ]

            results = await resolver.resolve_batch(batch)
            assert len(results) == 3

            # Check deduplication potential
            canonical_names = [r.canonical_name for r in results]
            assert "John Smith" in canonical_names or "john smith" in canonical_names

        except ImportError:
            pytest.skip("rapidfuzz not installed - batch resolution unavailable")

    @pytest.mark.slow
    def test_example_runs_successfully(self):
        """Run the complete example script and verify it completes."""
        example_path = EXAMPLES_DIR / "entity_resolution.py"

        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(EXAMPLES_DIR),
        )

        # Check it completed (may have warnings about missing packages)
        assert "Demo complete" in result.stdout, (
            f"Example failed:\n{result.stdout}\n{result.stderr}"
        )

    def test_example_sections_present(self, examples_dir):
        """Verify the example covers all documented sections."""
        example_path = examples_dir / "entity_resolution.py"
        content = example_path.read_text()

        # Check for key sections from the example
        assert "Exact Match Resolution" in content
        assert "Fuzzy Match Resolution" in content
        assert "Composite Resolution" in content
        assert "Batch Resolution" in content
        assert "ExactMatchResolver" in content
        assert "FuzzyMatchResolver" in content
        assert "CompositeResolver" in content
