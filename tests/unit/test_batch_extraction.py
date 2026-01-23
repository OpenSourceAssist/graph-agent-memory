"""Tests for batch extraction API."""

import asyncio

import pytest

from neo4j_agent_memory.extraction.base import (
    ExtractedEntity,
    ExtractionResult,
)
from neo4j_agent_memory.extraction.pipeline import (
    BatchExtractionResult,
    BatchItemResult,
    ExtractionPipeline,
    MergeStrategy,
)


class MockExtractor:
    """Mock extractor for testing batch extraction."""

    def __init__(
        self,
        entities_per_text: int = 1,
        raise_on_indices: set[int] | None = None,
        delay_ms: float = 0,
    ):
        """
        Args:
            entities_per_text: Number of entities to return per text
            raise_on_indices: Set of text indices that should raise errors
            delay_ms: Artificial delay in milliseconds to simulate processing time
        """
        self.entities_per_text = entities_per_text
        self.raise_on_indices = raise_on_indices or set()
        self.delay_ms = delay_ms
        self.call_count = 0
        self.texts_processed: list[str] = []

    async def extract(
        self,
        text: str,
        *,
        entity_types: list[str] | None = None,
        extract_relations: bool = True,
        extract_preferences: bool = True,
    ) -> ExtractionResult:
        self.call_count += 1
        self.texts_processed.append(text)

        # Simulate processing time
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000)

        # Check if this text should raise an error
        index = self.call_count - 1
        if index in self.raise_on_indices:
            raise RuntimeError(f"Mock extraction error for index {index}")

        # Generate entities based on text content
        entities = []
        for i in range(self.entities_per_text):
            entities.append(
                ExtractedEntity(
                    name=f"Entity_{index}_{i}",
                    type="PERSON",
                    confidence=0.9,
                    extractor="mock",
                )
            )

        return ExtractionResult(
            entities=entities,
            relations=[],
            preferences=[],
            source_text=text,
        )


class TestBatchExtractionResult:
    """Tests for BatchExtractionResult dataclass."""

    def test_empty_result(self):
        """Test empty batch result properties."""
        result = BatchExtractionResult()

        assert result.total_items == 0
        assert result.successful_items == 0
        assert result.failed_items == 0
        assert result.success_rate == 0.0
        assert result.total_entities == 0
        assert result.total_relations == 0
        assert result.get_extraction_results() == []
        assert result.get_all_entities() == []
        assert result.get_errors() == []

    def test_successful_results(self):
        """Test batch result with successful extractions."""
        items = [
            BatchItemResult(
                index=0,
                result=ExtractionResult(
                    entities=[
                        ExtractedEntity(name="John", type="PERSON"),
                        ExtractedEntity(name="Jane", type="PERSON"),
                    ]
                ),
                success=True,
                duration_ms=100,
            ),
            BatchItemResult(
                index=1,
                result=ExtractionResult(entities=[ExtractedEntity(name="NYC", type="LOCATION")]),
                success=True,
                duration_ms=150,
            ),
        ]
        result = BatchExtractionResult(results=items, total_duration_ms=300)

        assert result.total_items == 2
        assert result.successful_items == 2
        assert result.failed_items == 0
        assert result.success_rate == 1.0
        assert result.total_entities == 3
        assert len(result.get_extraction_results()) == 2
        assert len(result.get_all_entities()) == 3
        assert result.get_errors() == []

    def test_mixed_results(self):
        """Test batch result with mixed success/failure."""
        items = [
            BatchItemResult(
                index=0,
                result=ExtractionResult(entities=[ExtractedEntity(name="John", type="PERSON")]),
                success=True,
            ),
            BatchItemResult(
                index=1,
                result=ExtractionResult(),
                success=False,
                error="Extraction failed",
            ),
            BatchItemResult(
                index=2,
                result=ExtractionResult(entities=[ExtractedEntity(name="NYC", type="LOCATION")]),
                success=True,
            ),
        ]
        result = BatchExtractionResult(results=items)

        assert result.total_items == 3
        assert result.successful_items == 2
        assert result.failed_items == 1
        assert result.success_rate == pytest.approx(2 / 3)
        assert result.total_entities == 2
        assert len(result.get_errors()) == 1
        assert result.get_errors()[0] == (1, "Extraction failed")


class TestPipelineBatchExtraction:
    """Tests for ExtractionPipeline.extract_batch()."""

    @pytest.mark.asyncio
    async def test_batch_extraction_basic(self):
        """Test basic batch extraction."""
        extractor = MockExtractor(entities_per_text=2)
        pipeline = ExtractionPipeline(stages=[extractor])

        texts = ["Text 1", "Text 2", "Text 3"]
        result = await pipeline.extract_batch(texts)

        assert result.total_items == 3
        assert result.successful_items == 3
        assert result.total_entities == 6  # 2 entities per text
        assert extractor.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_extraction_empty_list(self):
        """Test batch extraction with empty list."""
        extractor = MockExtractor()
        pipeline = ExtractionPipeline(stages=[extractor])

        result = await pipeline.extract_batch([])

        assert result.total_items == 0
        assert extractor.call_count == 0

    @pytest.mark.asyncio
    async def test_batch_extraction_single_item(self):
        """Test batch extraction with single item."""
        extractor = MockExtractor(entities_per_text=3)
        pipeline = ExtractionPipeline(stages=[extractor])

        result = await pipeline.extract_batch(["Single text"])

        assert result.total_items == 1
        assert result.total_entities == 3

    @pytest.mark.asyncio
    async def test_batch_extraction_preserves_order(self):
        """Test that batch extraction preserves input order."""
        extractor = MockExtractor(entities_per_text=1)
        pipeline = ExtractionPipeline(stages=[extractor])

        texts = [f"Text {i}" for i in range(10)]
        result = await pipeline.extract_batch(texts, max_concurrency=5)

        # Results should be in order
        for i, item in enumerate(result.results):
            assert item.index == i
            assert item.result.source_text == f"Text {i}"

    @pytest.mark.asyncio
    async def test_batch_extraction_with_errors(self):
        """Test batch extraction handles errors gracefully.

        Note: The pipeline has its own fallback_on_error mechanism. To test
        batch-level error handling, we need to set fallback_on_error=False
        on the pipeline so errors propagate to the batch level.
        """
        extractor = MockExtractor(raise_on_indices={1, 3})
        pipeline = ExtractionPipeline(stages=[extractor], fallback_on_error=False)

        texts = ["Text 0", "Text 1", "Text 2", "Text 3", "Text 4"]
        result = await pipeline.extract_batch(texts)

        assert result.total_items == 5
        assert result.successful_items == 3
        assert result.failed_items == 2

        errors = result.get_errors()
        assert len(errors) == 2
        assert errors[0][0] == 1  # Index 1 failed
        assert errors[1][0] == 3  # Index 3 failed

    @pytest.mark.asyncio
    async def test_batch_extraction_with_pipeline_fallback(self):
        """Test batch extraction when pipeline handles errors internally.

        When fallback_on_error=True (default), the pipeline catches stage errors
        and returns empty results, so all batch items succeed (but may have no entities).
        """
        extractor = MockExtractor(raise_on_indices={1, 3})
        pipeline = ExtractionPipeline(stages=[extractor], fallback_on_error=True)

        texts = ["Text 0", "Text 1", "Text 2", "Text 3", "Text 4"]
        result = await pipeline.extract_batch(texts)

        # All items succeed at the batch level (pipeline handled errors internally)
        assert result.total_items == 5
        assert result.successful_items == 5
        assert result.failed_items == 0

        # But items 1 and 3 have no entities because extraction failed
        assert result.results[0].result.entity_count == 1  # Success
        assert result.results[1].result.entity_count == 0  # Pipeline fallback
        assert result.results[2].result.entity_count == 1  # Success
        assert result.results[3].result.entity_count == 0  # Pipeline fallback
        assert result.results[4].result.entity_count == 1  # Success

    @pytest.mark.asyncio
    async def test_batch_extraction_fail_fast(self):
        """Test batch extraction with fail_fast=True.

        When fail_fast=True and an error occurs, the batch should raise immediately.
        We need fallback_on_error=False on the pipeline for errors to propagate.
        """
        extractor = MockExtractor(raise_on_indices={2})
        pipeline = ExtractionPipeline(stages=[extractor], fallback_on_error=False)

        texts = ["Text 0", "Text 1", "Text 2", "Text 3", "Text 4"]

        with pytest.raises(RuntimeError, match="index 2"):
            await pipeline.extract_batch(texts, fail_fast=True, max_concurrency=1)

    @pytest.mark.asyncio
    async def test_batch_extraction_progress_callback(self):
        """Test batch extraction progress callback."""
        extractor = MockExtractor()
        pipeline = ExtractionPipeline(stages=[extractor])

        progress_calls: list[tuple[int, int]] = []

        def on_progress(completed: int, total: int) -> None:
            progress_calls.append((completed, total))

        texts = ["Text 1", "Text 2", "Text 3"]
        await pipeline.extract_batch(texts, on_progress=on_progress, max_concurrency=1)

        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)

    @pytest.mark.asyncio
    async def test_batch_extraction_batch_size(self):
        """Test that batch_size controls memory batching."""
        extractor = MockExtractor()
        pipeline = ExtractionPipeline(stages=[extractor])

        texts = [f"Text {i}" for i in range(25)]
        result = await pipeline.extract_batch(texts, batch_size=10)

        assert result.total_items == 25
        assert result.successful_items == 25

    @pytest.mark.asyncio
    async def test_batch_extraction_concurrency(self):
        """Test that max_concurrency limits parallel execution."""
        # Use delay to make concurrency visible
        extractor = MockExtractor(delay_ms=10)
        pipeline = ExtractionPipeline(stages=[extractor])

        texts = [f"Text {i}" for i in range(10)]

        # With concurrency=1, should take ~100ms
        # With concurrency=10, should take ~10ms
        result_serial = await pipeline.extract_batch(texts, max_concurrency=1, batch_size=100)
        result_parallel = await pipeline.extract_batch(texts, max_concurrency=10, batch_size=100)

        # Both should complete successfully
        assert result_serial.successful_items == 10
        assert result_parallel.successful_items == 10

        # Parallel should be faster (with some tolerance)
        # Note: This is a rough check due to test environment variability
        assert result_parallel.total_duration_ms < result_serial.total_duration_ms * 0.8

    @pytest.mark.asyncio
    async def test_batch_extraction_with_entity_types(self):
        """Test batch extraction with entity_types filter."""
        extractor = MockExtractor(entities_per_text=1)
        pipeline = ExtractionPipeline(stages=[extractor])

        texts = ["Text 1", "Text 2"]
        result = await pipeline.extract_batch(texts, entity_types=["PERSON", "LOCATION"])

        assert result.successful_items == 2
        # The mock extractor doesn't actually filter, but the param should be passed

    @pytest.mark.asyncio
    async def test_batch_extraction_aggregate_methods(self):
        """Test BatchExtractionResult aggregate methods."""
        extractor = MockExtractor(entities_per_text=2)
        pipeline = ExtractionPipeline(stages=[extractor])

        texts = ["Text 1", "Text 2", "Text 3"]
        result = await pipeline.extract_batch(texts)

        # Test get_extraction_results
        extraction_results = result.get_extraction_results()
        assert len(extraction_results) == 3
        assert all(isinstance(r, ExtractionResult) for r in extraction_results)

        # Test get_all_entities
        all_entities = result.get_all_entities()
        assert len(all_entities) == 6
        assert all(isinstance(e, ExtractedEntity) for e in all_entities)

    @pytest.mark.asyncio
    async def test_batch_extraction_with_pipeline_stages(self):
        """Test batch extraction with multiple pipeline stages."""
        extractor1 = MockExtractor(entities_per_text=1)
        extractor2 = MockExtractor(entities_per_text=1)

        pipeline = ExtractionPipeline(
            stages=[extractor1, extractor2],
            merge_strategy=MergeStrategy.UNION,
        )

        texts = ["Text 1", "Text 2"]
        result = await pipeline.extract_batch(texts)

        assert result.successful_items == 2
        # Each text goes through both extractors
        assert extractor1.call_count == 2
        assert extractor2.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_extraction_duration_tracking(self):
        """Test that duration is tracked correctly."""
        extractor = MockExtractor(delay_ms=5)
        pipeline = ExtractionPipeline(stages=[extractor])

        texts = ["Text 1", "Text 2"]
        result = await pipeline.extract_batch(texts, max_concurrency=1)

        # Total duration should be at least 10ms (2 texts * 5ms delay)
        assert result.total_duration_ms >= 10

        # Individual item durations should be tracked
        for item in result.results:
            assert item.duration_ms >= 5


class TestBatchItemResult:
    """Tests for BatchItemResult dataclass."""

    def test_successful_item(self):
        """Test successful item result."""
        item = BatchItemResult(
            index=0,
            result=ExtractionResult(entities=[ExtractedEntity(name="Test", type="OBJECT")]),
            success=True,
            duration_ms=50.5,
        )

        assert item.index == 0
        assert item.success is True
        assert item.error is None
        assert item.result.entity_count == 1
        assert item.duration_ms == 50.5

    def test_failed_item(self):
        """Test failed item result."""
        item = BatchItemResult(
            index=5,
            result=ExtractionResult(),
            success=False,
            error="Connection timeout",
            duration_ms=1000,
        )

        assert item.index == 5
        assert item.success is False
        assert item.error == "Connection timeout"
        assert item.result.entity_count == 0
