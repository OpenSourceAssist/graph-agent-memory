"""Metrics calculation for extraction benchmarks.

Provides precision, recall, and F1 score calculations for
entity extraction evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EntityMetrics:
    """Metrics for a single entity type."""

    entity_type: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        """Calculate precision (TP / (TP + FP))."""
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        """Calculate recall (TP / (TP + FN))."""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1_score(self) -> float:
        """Calculate F1 score (2 * precision * recall / (precision + recall))."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_type": self.entity_type,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
        }


@dataclass
class ExtractionMetrics:
    """Aggregate metrics for extraction evaluation."""

    entity_metrics: dict[str, EntityMetrics] = field(default_factory=dict)
    total_true_positives: int = 0
    total_false_positives: int = 0
    total_false_negatives: int = 0
    latency_ms: float = 0.0
    token_count: int = 0

    @property
    def micro_precision(self) -> float:
        """Calculate micro-averaged precision."""
        if self.total_true_positives + self.total_false_positives == 0:
            return 0.0
        return self.total_true_positives / (self.total_true_positives + self.total_false_positives)

    @property
    def micro_recall(self) -> float:
        """Calculate micro-averaged recall."""
        if self.total_true_positives + self.total_false_negatives == 0:
            return 0.0
        return self.total_true_positives / (self.total_true_positives + self.total_false_negatives)

    @property
    def micro_f1(self) -> float:
        """Calculate micro-averaged F1 score."""
        if self.micro_precision + self.micro_recall == 0:
            return 0.0
        return (
            2
            * self.micro_precision
            * self.micro_recall
            / (self.micro_precision + self.micro_recall)
        )

    @property
    def macro_precision(self) -> float:
        """Calculate macro-averaged precision."""
        if not self.entity_metrics:
            return 0.0
        return sum(m.precision for m in self.entity_metrics.values()) / len(self.entity_metrics)

    @property
    def macro_recall(self) -> float:
        """Calculate macro-averaged recall."""
        if not self.entity_metrics:
            return 0.0
        return sum(m.recall for m in self.entity_metrics.values()) / len(self.entity_metrics)

    @property
    def macro_f1(self) -> float:
        """Calculate macro-averaged F1 score."""
        if not self.entity_metrics:
            return 0.0
        return sum(m.f1_score for m in self.entity_metrics.values()) / len(self.entity_metrics)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_metrics": {k: v.to_dict() for k, v in self.entity_metrics.items()},
            "micro_precision": self.micro_precision,
            "micro_recall": self.micro_recall,
            "micro_f1": self.micro_f1,
            "macro_precision": self.macro_precision,
            "macro_recall": self.macro_recall,
            "macro_f1": self.macro_f1,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
        }


@dataclass
class ExpectedEntity:
    """Expected entity in a test case."""

    name: str
    entity_type: str
    aliases: list[str] = field(default_factory=list)

    def matches(self, extracted_name: str, extracted_type: str) -> bool:
        """Check if an extracted entity matches this expected entity.

        Args:
            extracted_name: Name of extracted entity
            extracted_type: Type of extracted entity

        Returns:
            True if the extracted entity matches
        """
        # Type must match (case-insensitive)
        if extracted_type.upper() != self.entity_type.upper():
            return False

        # Name must match (case-insensitive) or be an alias
        extracted_lower = extracted_name.lower().strip()
        if extracted_lower == self.name.lower().strip():
            return True

        # Check aliases
        for alias in self.aliases:
            if extracted_lower == alias.lower().strip():
                return True

        return False


def calculate_entity_metrics(
    expected: list[ExpectedEntity],
    extracted: list[tuple[str, str]],  # (name, type) tuples
) -> EntityMetrics:
    """Calculate metrics for a single entity type.

    Args:
        expected: List of expected entities
        extracted: List of (name, type) tuples for extracted entities

    Returns:
        EntityMetrics with TP, FP, FN counts
    """
    if not expected:
        entity_type = extracted[0][1] if extracted else "UNKNOWN"
    else:
        entity_type = expected[0].entity_type

    metrics = EntityMetrics(entity_type=entity_type)

    # Track which expected entities were found
    found_expected = set()

    for ext_name, ext_type in extracted:
        matched = False
        for i, exp in enumerate(expected):
            if i not in found_expected and exp.matches(ext_name, ext_type):
                metrics.true_positives += 1
                found_expected.add(i)
                matched = True
                break

        if not matched:
            metrics.false_positives += 1

    # Count expected entities that weren't found
    metrics.false_negatives = len(expected) - len(found_expected)

    return metrics


def calculate_extraction_metrics(
    expected_entities: list[ExpectedEntity],
    extracted_entities: list[tuple[str, str]],
    latency_ms: float = 0.0,
    token_count: int = 0,
) -> ExtractionMetrics:
    """Calculate comprehensive extraction metrics.

    Groups entities by type and calculates per-type and aggregate metrics.

    Args:
        expected_entities: List of expected entities
        extracted_entities: List of (name, type) tuples
        latency_ms: Extraction latency in milliseconds
        token_count: Number of tokens processed

    Returns:
        ExtractionMetrics with per-type and aggregate metrics
    """
    metrics = ExtractionMetrics(latency_ms=latency_ms, token_count=token_count)

    # Group by entity type
    expected_by_type: dict[str, list[ExpectedEntity]] = {}
    extracted_by_type: dict[str, list[tuple[str, str]]] = {}

    for exp in expected_entities:
        etype = exp.entity_type.upper()
        if etype not in expected_by_type:
            expected_by_type[etype] = []
        expected_by_type[etype].append(exp)

    for ext_name, ext_type in extracted_entities:
        etype = ext_type.upper()
        if etype not in extracted_by_type:
            extracted_by_type[etype] = []
        extracted_by_type[etype].append((ext_name, ext_type))

    # Calculate per-type metrics
    all_types = set(expected_by_type.keys()) | set(extracted_by_type.keys())

    for etype in all_types:
        exp_list = expected_by_type.get(etype, [])
        ext_list = extracted_by_type.get(etype, [])

        type_metrics = calculate_entity_metrics(exp_list, ext_list)
        metrics.entity_metrics[etype] = type_metrics

        metrics.total_true_positives += type_metrics.true_positives
        metrics.total_false_positives += type_metrics.false_positives
        metrics.total_false_negatives += type_metrics.false_negatives

    return metrics


@dataclass
class BenchmarkResult:
    """Result of running a benchmark suite."""

    name: str
    extractor_name: str
    test_count: int
    metrics: ExtractionMetrics
    total_latency_ms: float
    avg_latency_ms: float
    throughput_docs_per_sec: float
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "extractor_name": self.extractor_name,
            "test_count": self.test_count,
            "metrics": self.metrics.to_dict(),
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "throughput_docs_per_sec": self.throughput_docs_per_sec,
            "errors": self.errors,
        }
