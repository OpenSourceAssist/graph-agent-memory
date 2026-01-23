"""Unit tests for benchmarks module."""

from __future__ import annotations

import json

# Use direct imports since benchmarks is not in the package
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add benchmarks to path for testing
benchmarks_path = Path(__file__).parent.parent.parent / "benchmarks"
sys.path.insert(0, str(benchmarks_path.parent))

from benchmarks.metrics import (
    BenchmarkResult,
    EntityMetrics,
    ExpectedEntity,
    ExtractionMetrics,
    calculate_entity_metrics,
    calculate_extraction_metrics,
)
from benchmarks.runner import (
    BenchmarkConfig,
    BenchmarkRunner,
    BenchmarkSuite,
    BenchmarkTestCase,
    create_sample_benchmark_suite,
)


class TestEntityMetrics:
    """Tests for EntityMetrics."""

    def test_precision_calculation(self):
        """Test precision calculation."""
        metrics = EntityMetrics(entity_type="PERSON", true_positives=8, false_positives=2)
        assert metrics.precision == 0.8

    def test_recall_calculation(self):
        """Test recall calculation."""
        metrics = EntityMetrics(entity_type="PERSON", true_positives=8, false_negatives=2)
        assert metrics.recall == 0.8

    def test_f1_calculation(self):
        """Test F1 score calculation."""
        metrics = EntityMetrics(
            entity_type="PERSON", true_positives=8, false_positives=2, false_negatives=2
        )
        # precision = 8/10 = 0.8, recall = 8/10 = 0.8
        # f1 = 2 * 0.8 * 0.8 / (0.8 + 0.8) = 0.8
        assert abs(metrics.f1_score - 0.8) < 0.001

    def test_precision_zero_when_no_predictions(self):
        """Test precision is 0 when no predictions."""
        metrics = EntityMetrics(entity_type="PERSON")
        assert metrics.precision == 0.0

    def test_recall_zero_when_no_expected(self):
        """Test recall is 0 when no expected entities."""
        metrics = EntityMetrics(entity_type="PERSON")
        assert metrics.recall == 0.0

    def test_f1_zero_when_precision_and_recall_zero(self):
        """Test F1 is 0 when precision and recall are both 0."""
        metrics = EntityMetrics(entity_type="PERSON")
        assert metrics.f1_score == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = EntityMetrics(
            entity_type="PERSON", true_positives=5, false_positives=1, false_negatives=2
        )
        d = metrics.to_dict()
        assert d["entity_type"] == "PERSON"
        assert d["true_positives"] == 5
        assert d["false_positives"] == 1
        assert d["false_negatives"] == 2
        assert "precision" in d
        assert "recall" in d
        assert "f1_score" in d


class TestExtractionMetrics:
    """Tests for ExtractionMetrics."""

    def test_micro_averages(self):
        """Test micro-averaged metrics."""
        metrics = ExtractionMetrics(
            total_true_positives=10,
            total_false_positives=2,
            total_false_negatives=3,
        )
        assert metrics.micro_precision == 10 / 12
        assert metrics.micro_recall == 10 / 13

    def test_macro_averages(self):
        """Test macro-averaged metrics."""
        metrics = ExtractionMetrics()
        metrics.entity_metrics["PERSON"] = EntityMetrics(
            entity_type="PERSON", true_positives=5, false_positives=1, false_negatives=1
        )
        metrics.entity_metrics["LOCATION"] = EntityMetrics(
            entity_type="LOCATION", true_positives=3, false_positives=1, false_negatives=1
        )

        # Person precision = 5/6, Location precision = 3/4
        # Macro precision = (5/6 + 3/4) / 2
        expected_macro_precision = (5 / 6 + 3 / 4) / 2
        assert abs(metrics.macro_precision - expected_macro_precision) < 0.001

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ExtractionMetrics(
            total_true_positives=10,
            latency_ms=100.5,
            token_count=500,
        )
        d = metrics.to_dict()
        assert "micro_precision" in d
        assert "micro_recall" in d
        assert "micro_f1" in d
        assert "macro_precision" in d
        assert d["latency_ms"] == 100.5
        assert d["token_count"] == 500


class TestExpectedEntity:
    """Tests for ExpectedEntity."""

    def test_exact_match(self):
        """Test exact name matching."""
        expected = ExpectedEntity(name="John Smith", entity_type="PERSON")
        assert expected.matches("John Smith", "PERSON") is True
        assert expected.matches("john smith", "PERSON") is True  # Case insensitive

    def test_alias_match(self):
        """Test alias matching."""
        expected = ExpectedEntity(
            name="New York City",
            entity_type="LOCATION",
            aliases=["NYC", "New York"],
        )
        assert expected.matches("NYC", "LOCATION") is True
        assert expected.matches("New York", "LOCATION") is True

    def test_type_mismatch(self):
        """Test type mismatch returns False."""
        expected = ExpectedEntity(name="John Smith", entity_type="PERSON")
        assert expected.matches("John Smith", "ORGANIZATION") is False

    def test_name_mismatch(self):
        """Test name mismatch returns False."""
        expected = ExpectedEntity(name="John Smith", entity_type="PERSON")
        assert expected.matches("Jane Doe", "PERSON") is False


class TestCalculateEntityMetrics:
    """Tests for calculate_entity_metrics function."""

    def test_all_correct(self):
        """Test when all extractions are correct."""
        expected = [
            ExpectedEntity(name="John", entity_type="PERSON"),
            ExpectedEntity(name="Jane", entity_type="PERSON"),
        ]
        extracted = [("John", "PERSON"), ("Jane", "PERSON")]

        metrics = calculate_entity_metrics(expected, extracted)
        assert metrics.true_positives == 2
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0
        assert metrics.f1_score == 1.0

    def test_some_missing(self):
        """Test when some expected entities are missing."""
        expected = [
            ExpectedEntity(name="John", entity_type="PERSON"),
            ExpectedEntity(name="Jane", entity_type="PERSON"),
        ]
        extracted = [("John", "PERSON")]

        metrics = calculate_entity_metrics(expected, extracted)
        assert metrics.true_positives == 1
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 1

    def test_extra_extractions(self):
        """Test when there are extra extractions."""
        expected = [ExpectedEntity(name="John", entity_type="PERSON")]
        extracted = [("John", "PERSON"), ("Bob", "PERSON")]

        metrics = calculate_entity_metrics(expected, extracted)
        assert metrics.true_positives == 1
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 0

    def test_empty_expected(self):
        """Test with no expected entities."""
        metrics = calculate_entity_metrics([], [("John", "PERSON")])
        assert metrics.true_positives == 0
        assert metrics.false_positives == 1

    def test_empty_extracted(self):
        """Test with no extracted entities."""
        expected = [ExpectedEntity(name="John", entity_type="PERSON")]
        metrics = calculate_entity_metrics(expected, [])
        assert metrics.true_positives == 0
        assert metrics.false_negatives == 1


class TestCalculateExtractionMetrics:
    """Tests for calculate_extraction_metrics function."""

    def test_aggregation_across_types(self):
        """Test that metrics are aggregated across entity types."""
        expected = [
            ExpectedEntity(name="John", entity_type="PERSON"),
            ExpectedEntity(name="NYC", entity_type="LOCATION"),
        ]
        extracted = [("John", "PERSON"), ("NYC", "LOCATION")]

        metrics = calculate_extraction_metrics(expected, extracted)
        assert "PERSON" in metrics.entity_metrics
        assert "LOCATION" in metrics.entity_metrics
        assert metrics.total_true_positives == 2

    def test_latency_and_tokens(self):
        """Test that latency and token count are preserved."""
        metrics = calculate_extraction_metrics([], [], latency_ms=150.0, token_count=1000)
        assert metrics.latency_ms == 150.0
        assert metrics.token_count == 1000


class TestBenchmarkTestCase:
    """Tests for BenchmarkTestCase."""

    def test_from_dict(self):
        """Test creating BenchmarkTestCase from dictionary."""
        data = {
            "id": "tc-001",
            "text": "John works at Acme.",
            "expected_entities": [
                {"name": "John", "type": "PERSON", "aliases": []},
                {"name": "Acme", "type": "ORGANIZATION"},
            ],
        }
        tc = BenchmarkTestCase.from_dict(data)
        assert tc.id == "tc-001"
        assert len(tc.expected_entities) == 2
        assert tc.expected_entities[0].name == "John"

    def test_to_dict(self):
        """Test converting BenchmarkTestCase to dictionary."""
        tc = BenchmarkTestCase(
            id="tc-001",
            text="Test text",
            expected_entities=[
                ExpectedEntity(name="John", entity_type="PERSON"),
            ],
        )
        d = tc.to_dict()
        assert d["id"] == "tc-001"
        assert d["text"] == "Test text"
        assert len(d["expected_entities"]) == 1


class TestBenchmarkConfig:
    """Tests for BenchmarkConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BenchmarkConfig()
        assert config.name == "default"
        assert config.warmup_runs == 1
        assert config.num_runs == 3
        assert config.timeout_seconds == 60.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = BenchmarkConfig(
            name="custom",
            warmup_runs=2,
            num_runs=5,
        )
        assert config.name == "custom"
        assert config.warmup_runs == 2
        assert config.num_runs == 5


class TestBenchmarkSuite:
    """Tests for BenchmarkSuite."""

    def test_create_suite(self):
        """Test creating a benchmark suite."""
        suite = BenchmarkSuite(
            name="test_suite",
            description="Test description",
            test_cases=[],
        )
        assert suite.name == "test_suite"
        assert suite.description == "Test description"

    def test_from_json_file(self, tmp_path):
        """Test loading suite from JSON file."""
        data = {
            "name": "json_suite",
            "description": "From JSON",
            "test_cases": [
                {
                    "id": "tc-001",
                    "text": "Test text",
                    "expected_entities": [],
                }
            ],
            "config": {
                "name": "json_config",
                "num_runs": 5,
            },
        }
        json_file = tmp_path / "suite.json"
        with open(json_file, "w") as f:
            json.dump(data, f)

        suite = BenchmarkSuite.from_json_file(json_file)
        assert suite.name == "json_suite"
        assert len(suite.test_cases) == 1
        assert suite.config.num_runs == 5

    def test_to_json_file(self, tmp_path):
        """Test saving suite to JSON file."""
        suite = BenchmarkSuite(
            name="save_test",
            description="Test saving",
            test_cases=[
                BenchmarkTestCase(
                    id="tc-001",
                    text="Test",
                    expected_entities=[],
                )
            ],
        )
        json_file = tmp_path / "output.json"
        suite.to_json_file(json_file)

        with open(json_file) as f:
            data = json.load(f)
        assert data["name"] == "save_test"


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner."""

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock extractor."""
        extractor = MagicMock()
        extractor.extract = AsyncMock()
        return extractor

    @pytest.mark.asyncio
    async def test_run_test_case(self, mock_extractor):
        """Test running a single test case."""
        # Setup mock result
        mock_result = MagicMock()
        mock_entity = MagicMock()
        mock_entity.name = "John"
        mock_entity.type = "PERSON"
        mock_result.entities = [mock_entity]
        mock_extractor.extract.return_value = mock_result

        runner = BenchmarkRunner(mock_extractor)
        test_case = BenchmarkTestCase(
            id="tc-001",
            text="John works at Acme.",
            expected_entities=[],
        )
        config = BenchmarkConfig(timeout_seconds=30.0)

        extracted, latency = await runner.run_test_case(test_case, config)
        assert len(extracted) == 1
        assert extracted[0] == ("John", "PERSON")
        assert latency > 0

    @pytest.mark.asyncio
    async def test_run_suite(self, mock_extractor):
        """Test running a complete benchmark suite."""
        # Setup mock result
        mock_result = MagicMock()
        mock_entity = MagicMock()
        mock_entity.name = "John"
        mock_entity.type = "PERSON"
        mock_result.entities = [mock_entity]
        mock_extractor.extract.return_value = mock_result

        runner = BenchmarkRunner(mock_extractor)
        suite = BenchmarkSuite(
            name="test_suite",
            description="Test",
            test_cases=[
                BenchmarkTestCase(
                    id="tc-001",
                    text="John works at Acme.",
                    expected_entities=[
                        ExpectedEntity(name="John", entity_type="PERSON"),
                    ],
                ),
            ],
            config=BenchmarkConfig(warmup_runs=0, num_runs=1),
        )

        result = await runner.run_suite(suite)
        assert result.name == "test_suite"
        assert result.test_count == 1
        assert result.metrics.total_true_positives == 1

    @pytest.mark.asyncio
    async def test_run_suite_with_errors(self, mock_extractor):
        """Test handling extraction errors."""
        mock_extractor.extract.side_effect = Exception("Test error")

        runner = BenchmarkRunner(mock_extractor)
        suite = BenchmarkSuite(
            name="error_suite",
            description="Test errors",
            test_cases=[
                BenchmarkTestCase(
                    id="tc-001",
                    text="Test text",
                    expected_entities=[
                        ExpectedEntity(name="John", entity_type="PERSON"),
                    ],
                ),
            ],
            config=BenchmarkConfig(warmup_runs=0, num_runs=1),
        )

        result = await runner.run_suite(suite)
        assert len(result.errors) > 0


class TestCreateSampleBenchmarkSuite:
    """Tests for create_sample_benchmark_suite function."""

    def test_creates_valid_suite(self):
        """Test that sample suite is valid."""
        suite = create_sample_benchmark_suite()
        assert suite.name == "sample_benchmark"
        assert len(suite.test_cases) > 0

    def test_test_cases_have_entities(self):
        """Test that test cases have expected entities."""
        suite = create_sample_benchmark_suite()
        for tc in suite.test_cases:
            assert len(tc.expected_entities) > 0


class TestBenchmarkResult:
    """Tests for BenchmarkResult."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = BenchmarkResult(
            name="test",
            extractor_name="TestExtractor",
            test_count=10,
            metrics=ExtractionMetrics(),
            total_latency_ms=1000.0,
            avg_latency_ms=100.0,
            throughput_docs_per_sec=10.0,
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["extractor_name"] == "TestExtractor"
        assert d["test_count"] == 10
        assert "metrics" in d
