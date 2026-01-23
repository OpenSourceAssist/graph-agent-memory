"""Unit tests for streaming extraction."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from neo4j_agent_memory.extraction.base import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
)
from neo4j_agent_memory.extraction.streaming import (
    ChunkInfo,
    StreamingChunkResult,
    StreamingExtractionResult,
    StreamingExtractionStats,
    StreamingExtractor,
    chunk_text_by_chars,
    chunk_text_by_tokens,
    create_streaming_extractor,
    deduplicate_entities,
    deduplicate_relations,
)


class TestChunkTextByChars:
    """Tests for chunk_text_by_chars function."""

    def test_empty_text(self):
        """Test with empty text."""
        chunks = chunk_text_by_chars("")
        assert chunks == []

    def test_short_text_single_chunk(self):
        """Test text shorter than chunk size."""
        text = "Short text here."
        chunks = chunk_text_by_chars(text, chunk_size=1000)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].is_first is True
        assert chunks[0].is_last is True
        assert chunks[0].index == 0
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)

    def test_multiple_chunks(self):
        """Test text split into multiple chunks."""
        text = "A" * 100 + " " + "B" * 100 + " " + "C" * 100
        chunks = chunk_text_by_chars(text, chunk_size=120, overlap=20)

        assert len(chunks) > 1
        assert chunks[0].is_first is True
        assert chunks[0].is_last is False
        assert chunks[-1].is_first is False
        assert chunks[-1].is_last is True

    def test_sentence_boundary_split(self):
        """Test splitting on sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text_by_chars(text, chunk_size=40, overlap=10, split_on_sentences=True)

        # Should split on sentence boundaries
        for chunk in chunks:
            # Each chunk should not end mid-word (except possibly last)
            if not chunk.is_last:
                # Check that chunk tends to end at sentence boundaries
                assert chunk.text.rstrip().endswith((".", "!", "?", " "))

    def test_overlap(self):
        """Test that chunks have proper overlap."""
        text = "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10"
        chunks = chunk_text_by_chars(text, chunk_size=30, overlap=10, split_on_sentences=False)

        # Check that there's overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            # End of chunk i should overlap with start of chunk i+1
            # The start of next chunk should be within the current chunk
            if not chunks[i].is_last:
                assert chunks[i + 1].start_char < chunks[i].end_char

    def test_chunk_info_properties(self):
        """Test ChunkInfo properties."""
        chunk = ChunkInfo(
            index=0,
            start_char=0,
            end_char=50,
            text="Hello world this is a test chunk.",
            is_first=True,
            is_last=False,
        )

        assert chunk.char_count == 33
        assert chunk.approx_token_count == 7  # 7 words


class TestChunkTextByTokens:
    """Tests for chunk_text_by_tokens function."""

    def test_empty_text(self):
        """Test with empty text."""
        chunks = chunk_text_by_tokens("")
        assert chunks == []

    def test_short_text_single_chunk(self):
        """Test text with fewer tokens than chunk size."""
        text = "Just a few words here."
        chunks = chunk_text_by_tokens(text, chunk_size=100)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].is_first is True
        assert chunks[0].is_last is True

    def test_multiple_chunks(self):
        """Test text split into multiple token-based chunks."""
        # Create text with many tokens
        words = [f"word{i}" for i in range(50)]
        text = " ".join(words)
        chunks = chunk_text_by_tokens(text, chunk_size=10, overlap=2)

        assert len(chunks) > 1
        assert chunks[0].is_first is True
        assert chunks[-1].is_last is True

    def test_token_overlap(self):
        """Test that token-based chunks have overlap."""
        words = [f"word{i}" for i in range(30)]
        text = " ".join(words)
        chunks = chunk_text_by_tokens(text, chunk_size=10, overlap=3)

        # With overlap, consecutive chunks should share some tokens
        assert len(chunks) > 1


class TestDeduplication:
    """Tests for entity and relation deduplication."""

    def test_deduplicate_entities_empty(self):
        """Test deduplicating empty list."""
        result = deduplicate_entities([])
        assert result == []

    def test_deduplicate_entities_no_duplicates(self):
        """Test deduplicating list with no duplicates."""
        entities = [
            ExtractedEntity(name="John", type="PERSON", confidence=0.9),
            ExtractedEntity(name="Acme", type="ORGANIZATION", confidence=0.8),
        ]
        result = deduplicate_entities(entities)
        assert len(result) == 2

    def test_deduplicate_entities_with_duplicates(self):
        """Test deduplicating list with duplicates."""
        entities = [
            ExtractedEntity(name="John", type="PERSON", confidence=0.7),
            ExtractedEntity(name="Acme", type="ORGANIZATION", confidence=0.8),
            ExtractedEntity(
                name="john", type="PERSON", confidence=0.9
            ),  # Duplicate, higher confidence
        ]
        result = deduplicate_entities(entities)

        assert len(result) == 2
        # Should keep higher confidence version
        john = next(e for e in result if e.normalized_name == "john")
        assert john.confidence == 0.9

    def test_deduplicate_entities_different_types(self):
        """Test that same name with different types is not deduplicated."""
        entities = [
            ExtractedEntity(name="Apple", type="ORGANIZATION", confidence=0.9),
            ExtractedEntity(name="Apple", type="OBJECT", confidence=0.8),  # Different type
        ]
        result = deduplicate_entities(entities)
        assert len(result) == 2

    def test_deduplicate_relations_empty(self):
        """Test deduplicating empty relations list."""
        result = deduplicate_relations([])
        assert result == []

    def test_deduplicate_relations_with_duplicates(self):
        """Test deduplicating relations."""
        relations = [
            ExtractedRelation(
                source="John", target="Acme", relation_type="WORKS_AT", confidence=0.7
            ),
            ExtractedRelation(
                source="john", target="ACME", relation_type="WORKS_AT", confidence=0.9
            ),
        ]
        result = deduplicate_relations(relations)

        assert len(result) == 1
        assert result[0].confidence == 0.9


class TestStreamingChunkResult:
    """Tests for StreamingChunkResult dataclass."""

    def test_properties(self):
        """Test StreamingChunkResult properties."""
        chunk = ChunkInfo(index=0, start_char=0, end_char=100, text="Test text")
        result = ExtractionResult(
            entities=[ExtractedEntity(name="John", type="PERSON")],
            relations=[ExtractedRelation(source="John", target="Acme", relation_type="WORKS_AT")],
        )

        chunk_result = StreamingChunkResult(
            chunk=chunk,
            result=result,
            success=True,
            duration_ms=50.0,
        )

        assert chunk_result.entity_count == 1
        assert chunk_result.relation_count == 1
        assert chunk_result.success is True


class TestStreamingExtractionResult:
    """Tests for StreamingExtractionResult dataclass."""

    def test_to_extraction_result(self):
        """Test converting to standard ExtractionResult."""
        entities = [ExtractedEntity(name="John", type="PERSON")]
        relations = [ExtractedRelation(source="John", target="Acme", relation_type="WORKS_AT")]

        streaming_result = StreamingExtractionResult(
            entities=entities,
            relations=relations,
            stats=StreamingExtractionStats(total_chunks=3),
        )

        extraction_result = streaming_result.to_extraction_result(source_text="test")

        assert extraction_result.entities == entities
        assert extraction_result.relations == relations
        assert extraction_result.source_text == "test"


class TestStreamingExtractor:
    """Tests for StreamingExtractor class."""

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock extractor."""
        extractor = MagicMock()
        extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                entities=[ExtractedEntity(name="John", type="PERSON", confidence=0.9)],
                relations=[],
            )
        )
        return extractor

    def test_chunk_document_by_chars(self, mock_extractor):
        """Test document chunking by characters."""
        streamer = StreamingExtractor(
            mock_extractor,
            chunk_size=100,
            overlap=20,
            chunk_by_tokens=False,
        )

        text = "A" * 250
        chunks = streamer.chunk_document(text)

        assert len(chunks) > 1
        assert chunks[0].is_first is True
        assert chunks[-1].is_last is True

    def test_chunk_document_by_tokens(self, mock_extractor):
        """Test document chunking by tokens."""
        streamer = StreamingExtractor(
            mock_extractor,
            chunk_size=10,
            overlap=2,
            chunk_by_tokens=True,
        )

        words = [f"word{i}" for i in range(30)]
        text = " ".join(words)
        chunks = streamer.chunk_document(text)

        assert len(chunks) > 1

    @pytest.mark.asyncio
    async def test_extract_streaming(self, mock_extractor):
        """Test streaming extraction yields results."""
        streamer = StreamingExtractor(mock_extractor, chunk_size=50, overlap=10)
        text = "This is a test sentence. " * 10

        results = []
        async for chunk_result in streamer.extract_streaming(text):
            results.append(chunk_result)

        assert len(results) > 0
        assert all(isinstance(r, StreamingChunkResult) for r in results)
        assert results[0].chunk.is_first is True
        assert results[-1].chunk.is_last is True

    @pytest.mark.asyncio
    async def test_extract_streaming_with_callback(self, mock_extractor):
        """Test streaming extraction with callback."""
        streamer = StreamingExtractor(mock_extractor, chunk_size=50, overlap=10)
        text = "This is a test sentence. " * 10

        callback_results = []

        def on_complete(result):
            callback_results.append(result)

        results = []
        async for chunk_result in streamer.extract_streaming(text, on_chunk_complete=on_complete):
            results.append(chunk_result)

        assert len(callback_results) == len(results)

    @pytest.mark.asyncio
    async def test_extract_complete(self, mock_extractor):
        """Test complete extraction with deduplication."""
        streamer = StreamingExtractor(mock_extractor, chunk_size=50, overlap=10)
        text = "This is a test sentence. " * 10

        result = await streamer.extract(text, deduplicate=True)

        assert isinstance(result, StreamingExtractionResult)
        assert result.stats.total_chunks > 0
        assert result.stats.successful_chunks == result.stats.total_chunks
        assert result.stats.failed_chunks == 0

    @pytest.mark.asyncio
    async def test_extract_with_progress(self, mock_extractor):
        """Test extraction with progress callback."""
        streamer = StreamingExtractor(mock_extractor, chunk_size=50, overlap=10)
        text = "This is a test sentence. " * 10

        progress_updates = []

        def on_progress(completed, total):
            progress_updates.append((completed, total))

        await streamer.extract(text, on_progress=on_progress)

        assert len(progress_updates) > 0
        # Last update should have completed == total
        assert progress_updates[-1][0] == progress_updates[-1][1]

    @pytest.mark.asyncio
    async def test_extract_to_result(self, mock_extractor):
        """Test extract_to_result convenience method."""
        streamer = StreamingExtractor(mock_extractor, chunk_size=50, overlap=10)
        text = "This is a test sentence. " * 10

        result = await streamer.extract_to_result(text)

        assert isinstance(result, ExtractionResult)
        assert result.source_text == text

    @pytest.mark.asyncio
    async def test_extract_handles_errors(self, mock_extractor):
        """Test extraction handles errors gracefully."""
        # Make extractor fail on second call
        call_count = 0

        async def failing_extract(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Extraction failed")
            return ExtractionResult(entities=[ExtractedEntity(name="John", type="PERSON")])

        mock_extractor.extract = failing_extract

        streamer = StreamingExtractor(mock_extractor, chunk_size=50, overlap=10)
        text = "This is a test sentence. " * 10

        result = await streamer.extract(text)

        # Should still complete with some failed chunks
        assert result.stats.failed_chunks > 0
        assert result.stats.successful_chunks > 0

    @pytest.mark.asyncio
    async def test_entity_positions_adjusted(self, mock_extractor):
        """Test that entity positions are adjusted to document level."""
        # Return entity with positions
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                entities=[
                    ExtractedEntity(
                        name="John",
                        type="PERSON",
                        start_pos=5,
                        end_pos=9,
                    )
                ],
            )
        )

        streamer = StreamingExtractor(mock_extractor, chunk_size=50, overlap=10)
        text = "A" * 100  # Create multiple chunks

        results = []
        async for chunk_result in streamer.extract_streaming(text):
            results.append(chunk_result)

        # Check that positions were adjusted by chunk offset
        for chunk_result in results:
            for entity in chunk_result.result.entities:
                if entity.start_pos is not None:
                    # Position should be >= chunk start position
                    assert entity.start_pos >= chunk_result.chunk.start_char


class TestCreateStreamingExtractor:
    """Tests for create_streaming_extractor factory function."""

    def test_default_char_chunking(self):
        """Test factory with default character chunking."""
        mock_extractor = MagicMock()
        streamer = create_streaming_extractor(mock_extractor)

        assert streamer.chunk_size == 4000  # Default char chunk size
        assert streamer.overlap == 200  # Default char overlap
        assert streamer.chunk_by_tokens is False

    def test_token_chunking(self):
        """Test factory with token chunking."""
        mock_extractor = MagicMock()
        streamer = create_streaming_extractor(mock_extractor, chunk_by_tokens=True)

        assert streamer.chunk_size == 1000  # Default token chunk size
        assert streamer.overlap == 50  # Default token overlap
        assert streamer.chunk_by_tokens is True

    def test_custom_sizes(self):
        """Test factory with custom chunk sizes."""
        mock_extractor = MagicMock()
        streamer = create_streaming_extractor(
            mock_extractor,
            chunk_size=2000,
            overlap=100,
        )

        assert streamer.chunk_size == 2000
        assert streamer.overlap == 100


class TestStreamingExtractionStats:
    """Tests for StreamingExtractionStats dataclass."""

    def test_default_values(self):
        """Test default stat values."""
        stats = StreamingExtractionStats()

        assert stats.total_chunks == 0
        assert stats.successful_chunks == 0
        assert stats.failed_chunks == 0
        assert stats.total_entities == 0
        assert stats.total_relations == 0
        assert stats.deduplicated_entities == 0
        assert stats.total_duration_ms == 0.0
        assert stats.total_characters == 0
        assert stats.total_tokens_approx == 0


class TestEdgeCases:
    """Edge case tests."""

    def test_chunk_very_long_text(self):
        """Test chunking very long text."""
        # 1 million characters
        text = "word " * 200000
        chunks = chunk_text_by_chars(text, chunk_size=10000, overlap=500)

        assert len(chunks) > 1
        # All text should be covered
        total_unique_chars = sum(c.end_char - c.start_char for c in chunks) - sum(
            chunks[i + 1].start_char - chunks[i].end_char
            for i in range(len(chunks) - 1)
            if chunks[i + 1].start_char < chunks[i].end_char
        )
        # Should cover at least the original text
        assert chunks[-1].end_char == len(text)

    def test_chunk_unicode_text(self):
        """Test chunking text with unicode characters."""
        text = "Hello 你好 مرحبا Привет " * 50
        chunks = chunk_text_by_chars(text, chunk_size=100, overlap=20)

        assert len(chunks) > 0
        # Unicode characters should be preserved
        all_text = "".join(c.text for c in chunks)
        # Due to overlap, all_text will be longer, but should contain original
        assert "你好" in all_text
        assert "مرحبا" in all_text

    def test_chunk_text_with_no_spaces(self):
        """Test chunking text with no word boundaries."""
        text = "A" * 500
        chunks = chunk_text_by_chars(text, chunk_size=100, overlap=20)

        assert len(chunks) > 1
        # Should still chunk properly even without sentence boundaries

    @pytest.mark.asyncio
    async def test_extract_single_chunk_document(self):
        """Test extraction of document that fits in single chunk."""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(
            return_value=ExtractionResult(entities=[ExtractedEntity(name="John", type="PERSON")])
        )

        streamer = StreamingExtractor(mock_extractor, chunk_size=10000)
        text = "Short document."

        result = await streamer.extract(text)

        assert result.stats.total_chunks == 1
        assert result.stats.successful_chunks == 1
