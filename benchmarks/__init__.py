"""Extraction quality benchmarks for neo4j-agent-memory.

This module provides tools for measuring extraction quality:
- Precision, recall, and F1 scores by entity type
- Latency and throughput measurements
- Cost tracking for LLM-based extraction
- Comparison across different extractors
"""

from benchmarks.metrics import (
    BenchmarkResult,
    EntityMetrics,
    ExtractionMetrics,
    calculate_entity_metrics,
    calculate_extraction_metrics,
)
from benchmarks.runner import (
    BenchmarkConfig,
    BenchmarkRunner,
    BenchmarkSuite,
    BenchmarkTestCase,
)

__all__ = [
    "BenchmarkResult",
    "BenchmarkConfig",
    "BenchmarkRunner",
    "BenchmarkSuite",
    "BenchmarkTestCase",
    "EntityMetrics",
    "ExtractionMetrics",
    "calculate_entity_metrics",
    "calculate_extraction_metrics",
]
