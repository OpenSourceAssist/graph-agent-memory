"""Benchmark runner for extraction evaluation.

Provides tools for running extraction benchmarks against
test datasets and measuring quality metrics.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmarks.metrics import (
    BenchmarkResult,
    ExpectedEntity,
    ExtractionMetrics,
    calculate_extraction_metrics,
)


@dataclass
class BenchmarkTestCase:
    """A single test case for extraction evaluation."""

    id: str
    text: str
    expected_entities: list[ExpectedEntity]
    expected_relations: list[tuple[str, str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkTestCase":
        """Create a test case from a dictionary.

        Args:
            data: Dictionary with test case data

        Returns:
            TestCase instance
        """
        entities = [
            ExpectedEntity(
                name=e["name"],
                entity_type=e["type"],
                aliases=e.get("aliases", []),
            )
            for e in data.get("expected_entities", [])
        ]

        return cls(
            id=data["id"],
            text=data["text"],
            expected_entities=entities,
            expected_relations=data.get("expected_relations", []),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "expected_entities": [
                {"name": e.name, "type": e.entity_type, "aliases": e.aliases}
                for e in self.expected_entities
            ],
            "expected_relations": self.expected_relations,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""

    name: str = "default"
    warmup_runs: int = 1
    num_runs: int = 3
    timeout_seconds: float = 60.0
    extract_relations: bool = False
    entity_types: list[str] | None = None


@dataclass
class BenchmarkSuite:
    """Collection of test cases for benchmarking."""

    name: str
    description: str
    test_cases: list[BenchmarkTestCase]
    config: BenchmarkConfig = field(default_factory=BenchmarkConfig)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "BenchmarkSuite":
        """Load a benchmark suite from a JSON file.

        Args:
            path: Path to JSON file

        Returns:
            BenchmarkSuite instance
        """
        path = Path(path)
        with open(path) as f:
            data = json.load(f)

        test_cases = [BenchmarkTestCase.from_dict(tc) for tc in data.get("test_cases", [])]

        config_data = data.get("config", {})
        config = BenchmarkConfig(
            name=config_data.get("name", path.stem),
            warmup_runs=config_data.get("warmup_runs", 1),
            num_runs=config_data.get("num_runs", 3),
            timeout_seconds=config_data.get("timeout_seconds", 60.0),
            extract_relations=config_data.get("extract_relations", False),
            entity_types=config_data.get("entity_types"),
        )

        return cls(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            test_cases=test_cases,
            config=config,
        )

    def to_json_file(self, path: str | Path) -> None:
        """Save benchmark suite to a JSON file.

        Args:
            path: Path to save to
        """
        path = Path(path)
        data = {
            "name": self.name,
            "description": self.description,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "config": {
                "name": self.config.name,
                "warmup_runs": self.config.warmup_runs,
                "num_runs": self.config.num_runs,
                "timeout_seconds": self.config.timeout_seconds,
                "extract_relations": self.config.extract_relations,
                "entity_types": self.config.entity_types,
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


class BenchmarkRunner:
    """Runs extraction benchmarks and collects metrics.

    Usage:
        runner = BenchmarkRunner(extractor)
        result = await runner.run_suite(suite)
        print(result.metrics.micro_f1)
    """

    def __init__(self, extractor: Any) -> None:
        """Initialize the runner with an extractor.

        Args:
            extractor: An extractor instance with an `extract` method
        """
        self.extractor = extractor
        self._extractor_name = getattr(extractor, "__class__", type(extractor)).__name__

    async def run_test_case(
        self,
        test_case: BenchmarkTestCase,
        config: BenchmarkConfig,
    ) -> tuple[list[tuple[str, str]], float]:
        """Run extraction on a single test case.

        Args:
            test_case: Test case to run
            config: Benchmark configuration

        Returns:
            Tuple of (extracted entities as (name, type) tuples, latency in ms)
        """
        start = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                self.extractor.extract(
                    test_case.text,
                    extract_relations=config.extract_relations,
                ),
                timeout=config.timeout_seconds,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            # Extract (name, type) tuples from result
            extracted = []
            for entity in result.entities:
                name = entity.name
                etype = getattr(entity, "type", getattr(entity, "entity_type", "UNKNOWN"))
                extracted.append((name, etype))

            return extracted, latency_ms

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start) * 1000
            return [], latency_ms
        except Exception:
            latency_ms = (time.perf_counter() - start) * 1000
            return [], latency_ms

    async def run_suite(self, suite: BenchmarkSuite) -> BenchmarkResult:
        """Run a complete benchmark suite.

        Args:
            suite: Benchmark suite to run

        Returns:
            BenchmarkResult with aggregate metrics
        """
        config = suite.config
        all_expected: list[ExpectedEntity] = []
        all_extracted: list[tuple[str, str]] = []
        total_latency = 0.0
        errors: list[str] = []

        # Warmup runs
        if suite.test_cases and config.warmup_runs > 0:
            for _ in range(config.warmup_runs):
                await self.run_test_case(suite.test_cases[0], config)

        # Actual benchmark runs
        for test_case in suite.test_cases:
            latencies = []

            for _ in range(config.num_runs):
                extracted, latency = await self.run_test_case(test_case, config)
                latencies.append(latency)

                if not extracted and test_case.expected_entities:
                    errors.append(f"No entities extracted for test case {test_case.id}")

            # Use the last run's extractions for metrics
            # (assuming consistent results across runs)
            all_expected.extend(test_case.expected_entities)
            all_extracted.extend(extracted)
            total_latency += sum(latencies) / len(latencies)

        # Calculate metrics
        metrics = calculate_extraction_metrics(
            all_expected,
            all_extracted,
            latency_ms=total_latency,
        )

        avg_latency = total_latency / len(suite.test_cases) if suite.test_cases else 0
        throughput = (1000 / avg_latency) if avg_latency > 0 else 0

        return BenchmarkResult(
            name=suite.name,
            extractor_name=self._extractor_name,
            test_count=len(suite.test_cases),
            metrics=metrics,
            total_latency_ms=total_latency,
            avg_latency_ms=avg_latency,
            throughput_docs_per_sec=throughput,
            errors=errors,
        )

    async def compare_extractors(
        self,
        extractors: list[Any],
        suite: BenchmarkSuite,
    ) -> list[BenchmarkResult]:
        """Compare multiple extractors on the same suite.

        Args:
            extractors: List of extractor instances
            suite: Benchmark suite to run

        Returns:
            List of BenchmarkResults, one per extractor
        """
        results = []
        for extractor in extractors:
            runner = BenchmarkRunner(extractor)
            result = await runner.run_suite(suite)
            results.append(result)
        return results


def create_sample_benchmark_suite() -> BenchmarkSuite:
    """Create a sample benchmark suite for testing.

    Returns:
        A BenchmarkSuite with sample test cases
    """
    test_cases = [
        BenchmarkTestCase(
            id="tc-001",
            text="John Smith works at Acme Corporation in New York City.",
            expected_entities=[
                ExpectedEntity(name="John Smith", entity_type="PERSON"),
                ExpectedEntity(
                    name="Acme Corporation", entity_type="ORGANIZATION", aliases=["Acme Corp"]
                ),
                ExpectedEntity(
                    name="New York City", entity_type="LOCATION", aliases=["NYC", "New York"]
                ),
            ],
        ),
        BenchmarkTestCase(
            id="tc-002",
            text="Dr. Jane Doe presented her research at the MIT conference on artificial intelligence.",
            expected_entities=[
                ExpectedEntity(name="Jane Doe", entity_type="PERSON", aliases=["Dr. Jane Doe"]),
                ExpectedEntity(
                    name="MIT",
                    entity_type="ORGANIZATION",
                    aliases=["Massachusetts Institute of Technology"],
                ),
            ],
        ),
        BenchmarkTestCase(
            id="tc-003",
            text="The meeting between Apple Inc. CEO Tim Cook and Microsoft's Satya Nadella took place in San Francisco.",
            expected_entities=[
                ExpectedEntity(name="Apple Inc.", entity_type="ORGANIZATION", aliases=["Apple"]),
                ExpectedEntity(name="Tim Cook", entity_type="PERSON"),
                ExpectedEntity(name="Microsoft", entity_type="ORGANIZATION"),
                ExpectedEntity(name="Satya Nadella", entity_type="PERSON"),
                ExpectedEntity(name="San Francisco", entity_type="LOCATION"),
            ],
        ),
    ]

    return BenchmarkSuite(
        name="sample_benchmark",
        description="Sample benchmark suite for testing extraction quality",
        test_cases=test_cases,
        config=BenchmarkConfig(
            name="sample",
            warmup_runs=0,
            num_runs=1,
            timeout_seconds=30.0,
        ),
    )
