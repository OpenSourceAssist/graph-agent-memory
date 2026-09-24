"""Tests for GLiREL relation extraction."""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from neo4j_agent_memory.extraction.base import ExtractedEntity, ExtractedRelation
from neo4j_agent_memory.extraction.gliner_extractor import (
    DEFAULT_GLIREL_MODEL,
    DEFAULT_RELATION_TYPES,
    GLiNERWithRelationsExtractor,
    GLiRELConfig,
    GLiRELExtractor,
    is_glirel_available,
)


class _FakeSpan:
    def __init__(self, doc: "_FakeDoc", start: int, end: int) -> None:
        self.start = start
        self.end = end
        self.text = doc.text[doc.offsets[start][0] : doc.offsets[end - 1][1]] if end > start else ""

    def __len__(self) -> int:
        return self.end - self.start


class _FakeToken:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeDoc:
    """Just enough of a spaCy Doc: word/punctuation tokens with character offsets."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.offsets = [(m.start(), m.end()) for m in re.finditer(r"\w+|\S", text)]

    def __len__(self) -> int:
        return len(self.offsets)

    def __iter__(self):
        return iter(_FakeToken(self.text[s:e]) for s, e in self.offsets)

    def __getitem__(self, item: slice) -> _FakeSpan:
        return _FakeSpan(self, item.start, item.stop)

    def char_span(self, start: int, end: int, alignment_mode: str = "strict") -> _FakeSpan | None:
        assert alignment_mode == "expand"
        covered = [i for i, (s, e) in enumerate(self.offsets) if s < end and e > start]
        if not covered:
            return None
        return _FakeSpan(self, covered[0], covered[-1] + 1)


class _FakeGLiREL:
    """Stands in for glirel.GLiREL and records what predict_relations received."""

    def __init__(self, predictions: list[dict]) -> None:
        self.predictions = predictions
        self.calls: list[dict] = []

    def predict_relations(self, tokens, labels, threshold=0.5, ner=None):
        self.calls.append({"tokens": tokens, "labels": labels, "ner": ner})
        return self.predictions


class TestIsGlirelAvailable:
    """Tests for is_glirel_available function."""

    def test_returns_bool(self):
        """Test that function returns a boolean."""
        result = is_glirel_available()
        assert isinstance(result, bool)


class TestDefaultRelationTypes:
    """Tests for default relation types."""

    def test_contains_person_relations(self):
        """Test that person relations are defined."""
        assert "works_at" in DEFAULT_RELATION_TYPES
        assert "lives_in" in DEFAULT_RELATION_TYPES
        assert "knows" in DEFAULT_RELATION_TYPES

    def test_contains_organization_relations(self):
        """Test that organization relations are defined."""
        assert "located_in" in DEFAULT_RELATION_TYPES
        assert "subsidiary_of" in DEFAULT_RELATION_TYPES
        assert "founded_by" in DEFAULT_RELATION_TYPES

    def test_contains_event_relations(self):
        """Test that event relations are defined."""
        assert "occurred_at" in DEFAULT_RELATION_TYPES
        assert "participated_in" in DEFAULT_RELATION_TYPES

    def test_all_have_descriptions(self):
        """Test that all relation types have descriptions."""
        for rel_type, description in DEFAULT_RELATION_TYPES.items():
            assert isinstance(description, str)
            assert len(description) > 0


class TestGLiRELConfig:
    """Tests for GLiRELConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GLiRELConfig()

        assert config.model == DEFAULT_GLIREL_MODEL
        assert config.threshold == 0.5
        assert config.device == "cpu"
        assert len(config.relation_types) > 0

    def test_custom_config(self):
        """Test custom configuration."""
        config = GLiRELConfig(
            model="custom/model",
            threshold=0.7,
            device="cuda",
            relation_types={"custom_rel": "A custom relation"},
        )

        assert config.model == "custom/model"
        assert config.threshold == 0.7
        assert config.device == "cuda"
        assert config.relation_types == {"custom_rel": "A custom relation"}


class TestGLiRELExtractor:
    """Tests for GLiRELExtractor."""

    def test_init_default(self):
        """Test default initialization."""
        extractor = GLiRELExtractor()

        assert extractor._model_name == DEFAULT_GLIREL_MODEL
        assert extractor.threshold == 0.5
        assert extractor.device == "cpu"
        assert extractor.relation_types == DEFAULT_RELATION_TYPES

    def test_init_with_list_relation_types(self):
        """Test initialization with list of relation types."""
        relation_types = ["works_at", "lives_in", "knows"]
        extractor = GLiRELExtractor(relation_types=relation_types)

        # List should be converted to dict with type as both key and value
        assert "works_at" in extractor.relation_types
        assert extractor.relation_types["works_at"] == "works_at"

    def test_init_with_dict_relation_types(self):
        """Test initialization with dict relation types."""
        relation_types = {
            "works_at": "Person works at organization",
            "lives_in": "Person lives in location",
        }
        extractor = GLiRELExtractor(relation_types=relation_types)

        assert extractor.relation_types == relation_types

    def test_from_config(self):
        """Test creation from config."""
        config = GLiRELConfig(
            model="test/model",
            threshold=0.8,
            device="mps",
        )
        extractor = GLiRELExtractor.from_config(config)

        assert extractor._model_name == "test/model"
        assert extractor.threshold == 0.8
        assert extractor.device == "mps"

    def test_for_poleo(self):
        """Test for_poleo factory method."""
        extractor = GLiRELExtractor.for_poleo(threshold=0.6)

        assert extractor.threshold == 0.6
        assert extractor.relation_types == DEFAULT_RELATION_TYPES

    def test_entities_to_glirel_format_uses_token_indices(self):
        """Character offsets become GLiREL token spans with an inclusive end."""
        extractor = GLiRELExtractor()
        text = "John Smith joined Acme Corp in 2020."
        entities = [
            ExtractedEntity(
                name="John Smith",
                type="PERSON",
                start_pos=0,
                end_pos=10,
                confidence=0.9,
            ),
            ExtractedEntity(
                name="Acme Corp",
                type="ORGANIZATION",
                start_pos=18,
                end_pos=27,
                confidence=0.85,
            ),
        ]

        result = extractor._entities_to_glirel_format(entities, _FakeDoc(text))

        # Tokens: John(0) Smith(1) joined(2) Acme(3) Corp(4) in(5) 2020(6) .(7)
        assert result == [
            [0, 1, "PERSON", "John Smith"],
            [3, 4, "ORGANIZATION", "Acme Corp"],
        ]

    def test_entities_to_glirel_format_locates_entities_without_offsets(self):
        """Entities without offsets are placed by name; unplaceable ones are dropped."""
        extractor = GLiRELExtractor()
        text = "Maya Chen leads Northstar Robotics."
        entities = [
            ExtractedEntity(name="Northstar Robotics", type="ORGANIZATION", confidence=0.9),
            ExtractedEntity(name="Maya Chen", type="PERSON", confidence=0.9),
            ExtractedEntity(name="Denver", type="LOCATION", confidence=0.9),
        ]

        result = extractor._entities_to_glirel_format(entities, _FakeDoc(text))

        assert result == [
            [3, 4, "ORGANIZATION", "Northstar Robotics"],
            [0, 1, "PERSON", "Maya Chen"],
        ]

    def test_entities_to_glirel_format_matches_spacy_tokens(self):
        """The spans index the tokens of a real spaCy tokenizer."""
        spacy = pytest.importorskip("spacy")
        extractor = GLiRELExtractor()
        text = "Maya Chen is CEO of Northstar Robotics. Northstar Robotics is in Denver."
        entities = [
            ExtractedEntity(name="Maya Chen", type="PERSON", start_pos=0, end_pos=9),
            ExtractedEntity(
                name="Northstar Robotics", type="ORGANIZATION", start_pos=20, end_pos=38
            ),
            ExtractedEntity(name="Denver", type="LOCATION", start_pos=65, end_pos=71),
        ]
        doc = spacy.blank("en")(text)

        result = extractor._entities_to_glirel_format(entities, doc)

        tokens = [token.text for token in doc]
        for start, end, _type, name in result:
            assert " ".join(tokens[start : end + 1]) == name
        assert [entry[:2] for entry in result] == [[0, 1], [5, 6], [12, 12]]

    @pytest.mark.asyncio
    async def test_extract_relations_passes_token_spans_and_joins_token_text(self):
        """GLiREL gets token spans and its token-list head/tail text becomes entity names."""
        extractor = GLiRELExtractor(relation_types=["ceo_of", "located_in"])
        extractor._nlp = _FakeDoc
        model = _FakeGLiREL(
            [
                {
                    "head_pos": [0, 2],
                    "tail_pos": [5, 7],
                    "head_text": ["Maya", "Chen"],
                    "tail_text": ["Northstar", "Robotics"],
                    "label": "ceo of",
                    "score": 0.9,
                },
                {
                    # A span that matches no supplied entity falls back to its tokens.
                    "head_pos": [5, 6],
                    "tail_pos": [12, 13],
                    "head_text": ["Northstar"],
                    "tail_text": ["Denver"],
                    "label": "located_in",
                    "score": 0.7,
                },
            ]
        )
        extractor._model = model
        text = "Maya Chen is CEO of Northstar Robotics. Northstar Robotics is in Denver."
        entities = [
            ExtractedEntity(name="Maya Chen", type="PERSON", start_pos=0, end_pos=9),
            ExtractedEntity(
                name="Northstar Robotics", type="ORGANIZATION", start_pos=20, end_pos=38
            ),
            ExtractedEntity(name="Denver", type="LOCATION", start_pos=65, end_pos=71),
        ]

        relations = await extractor.extract_relations(text, entities)

        assert model.calls[0]["tokens"][:3] == ["Maya", "Chen", "is"]
        assert model.calls[0]["ner"] == [
            [0, 1, "PERSON", "Maya Chen"],
            [5, 6, "ORGANIZATION", "Northstar Robotics"],
            [12, 12, "LOCATION", "Denver"],
        ]
        assert relations == [
            ExtractedRelation(
                source="Maya Chen",
                target="Northstar Robotics",
                relation_type="CEO_OF",
                confidence=0.9,
            ),
            ExtractedRelation(
                source="Northstar",
                target="Denver",
                relation_type="LOCATED_IN",
                confidence=0.7,
            ),
        ]

    @pytest.mark.asyncio
    async def test_extract_relations_accepts_token_list_text_without_positions(self):
        """Token-list head/tail text is joined into a string, never passed through as a list."""
        extractor = GLiRELExtractor()
        extractor._nlp = _FakeDoc
        extractor._model = _FakeGLiREL(
            [
                {
                    "head_text": ["Maya", "Chen"],
                    "tail_text": ["Northstar", "Robotics"],
                    "label": "works_at",
                    "score": 0.2,
                }
            ]
        )
        text = "Maya Chen works at Northstar Robotics."
        entities = [
            ExtractedEntity(name="Maya Chen", type="PERSON"),
            ExtractedEntity(name="Northstar Robotics", type="ORGANIZATION"),
        ]

        relations = await extractor.extract_relations(text, entities)

        assert [(r.source, r.target) for r in relations] == [("Maya Chen", "Northstar Robotics")]

    @pytest.mark.asyncio
    async def test_extract_relations_skips_model_when_fewer_than_two_entities_place(self):
        extractor = GLiRELExtractor()
        extractor._nlp = _FakeDoc
        model = _FakeGLiREL([])
        extractor._model = model
        entities = [
            ExtractedEntity(name="Maya Chen", type="PERSON"),
            ExtractedEntity(name="Nowhere Inc", type="ORGANIZATION"),
        ]

        assert await extractor.extract_relations("Maya Chen spoke.", entities) == []
        assert model.calls == []

    @pytest.mark.asyncio
    async def test_extract_relations_empty_text(self):
        """Test extraction with empty text returns empty list."""
        extractor = GLiRELExtractor()
        entities = [
            ExtractedEntity(name="John", type="PERSON", confidence=0.9),
        ]

        result = await extractor.extract_relations("", entities)
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_relations_no_entities(self):
        """Test extraction with no entities returns empty list."""
        extractor = GLiRELExtractor()

        result = await extractor.extract_relations("Some text", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_relations_single_entity(self):
        """Test extraction with single entity returns empty list."""
        extractor = GLiRELExtractor()
        entities = [
            ExtractedEntity(name="John", type="PERSON", confidence=0.9),
        ]

        result = await extractor.extract_relations("John is here.", entities)
        assert result == []


class TestGLiNERWithRelationsExtractor:
    """Tests for GLiNERWithRelationsExtractor."""

    @pytest.fixture
    def mock_entity_extractor(self):
        """Create a mock entity extractor."""
        from neo4j_agent_memory.extraction.base import ExtractionResult

        extractor = MagicMock()
        extractor.extract = AsyncMock(
            return_value=ExtractionResult(
                entities=[
                    ExtractedEntity(
                        name="John Smith",
                        type="PERSON",
                        start_pos=0,
                        end_pos=10,
                        confidence=0.9,
                    ),
                    ExtractedEntity(
                        name="Acme Corp",
                        type="ORGANIZATION",
                        start_pos=20,
                        end_pos=29,
                        confidence=0.85,
                    ),
                ],
                relations=[],
                preferences=[],
                source_text="John Smith works at Acme Corp.",
            )
        )
        return extractor

    @pytest.fixture
    def mock_relation_extractor(self):
        """Create a mock relation extractor."""
        extractor = MagicMock()
        extractor.extract_relations = AsyncMock(
            return_value=[
                ExtractedRelation(
                    source="John Smith",
                    target="Acme Corp",
                    relation_type="WORKS_AT",
                    confidence=0.88,
                ),
            ]
        )
        return extractor

    @pytest.mark.asyncio
    async def test_extract_entities_and_relations(
        self, mock_entity_extractor, mock_relation_extractor
    ):
        """Test combined extraction."""
        extractor = GLiNERWithRelationsExtractor(
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
        )

        result = await extractor.extract("John Smith works at Acme Corp.")

        assert len(result.entities) == 2
        assert len(result.relations) == 1
        assert result.relations[0].source == "John Smith"
        assert result.relations[0].target == "Acme Corp"
        assert result.relations[0].relation_type == "WORKS_AT"

    @pytest.mark.asyncio
    async def test_extract_without_relations(self, mock_entity_extractor, mock_relation_extractor):
        """Test extraction with relations disabled."""
        extractor = GLiNERWithRelationsExtractor(
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
        )

        result = await extractor.extract(
            "John Smith works at Acme Corp.",
            extract_relations=False,
        )

        assert len(result.entities) == 2
        assert len(result.relations) == 0
        mock_relation_extractor.extract_relations.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_empty_text(self, mock_entity_extractor, mock_relation_extractor):
        """Test extraction with empty text."""
        extractor = GLiNERWithRelationsExtractor(
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
        )

        result = await extractor.extract("")

        assert len(result.entities) == 0
        assert len(result.relations) == 0

    @pytest.mark.asyncio
    async def test_extract_filters_entity_types(
        self, mock_entity_extractor, mock_relation_extractor
    ):
        """Test extraction with entity type filter."""
        extractor = GLiNERWithRelationsExtractor(
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
        )

        await extractor.extract(
            "John Smith works at Acme Corp.",
            entity_types=["PERSON"],
        )

        # Entity extractor should be called with entity_types
        mock_entity_extractor.extract.assert_called_once()
        call_kwargs = mock_entity_extractor.extract.call_args[1]
        assert call_kwargs["entity_types"] == ["PERSON"]

    @pytest.mark.asyncio
    async def test_extract_filters_relation_types(
        self, mock_entity_extractor, mock_relation_extractor
    ):
        """Test extraction with relation type filter."""
        extractor = GLiNERWithRelationsExtractor(
            entity_extractor=mock_entity_extractor,
            relation_extractor=mock_relation_extractor,
        )

        await extractor.extract(
            "John Smith works at Acme Corp.",
            relation_types=["works_at"],
        )

        # Relation extractor should be called with relation_types
        mock_relation_extractor.extract_relations.assert_called_once()
        call_kwargs = mock_relation_extractor.extract_relations.call_args[1]
        assert call_kwargs["relation_types"] == ["works_at"]


class TestGLiNERWithRelationsExtractorFactoryMethods:
    """Tests for factory methods."""

    def test_for_schema_creates_extractors(self):
        """Test for_schema creates both extractors."""
        # This will fail if GLiNER is not installed, which is expected
        # We're testing the factory method logic
        with (
            patch(
                "neo4j_agent_memory.extraction.gliner_extractor.GLiNEREntityExtractor.for_schema"
            ) as mock_gliner,
            patch("neo4j_agent_memory.extraction.gliner_extractor.GLiRELExtractor") as mock_glirel,
        ):
            mock_gliner.return_value = MagicMock()
            mock_glirel.return_value = MagicMock()

            extractor = GLiNERWithRelationsExtractor.for_schema(
                "poleo",
                entity_threshold=0.6,
                relation_threshold=0.7,
                device="cuda",
            )

            mock_gliner.assert_called_once_with(
                "poleo",
                model="gliner-community/gliner_medium-v2.5",
                threshold=0.6,
                device="cuda",
            )
            mock_glirel.assert_called_once()
            glirel_kwargs = mock_glirel.call_args[1]
            assert glirel_kwargs["threshold"] == 0.7
            assert glirel_kwargs["device"] == "cuda"

    def test_for_poleo_uses_poleo_schema(self):
        """Test for_poleo uses poleo schema."""
        with patch.object(GLiNERWithRelationsExtractor, "for_schema") as mock_for_schema:
            mock_for_schema.return_value = MagicMock()

            GLiNERWithRelationsExtractor.for_poleo(
                entity_threshold=0.5,
                relation_threshold=0.6,
            )

            mock_for_schema.assert_called_once()
            call_args = mock_for_schema.call_args
            assert call_args[0][0] == "poleo"
            assert call_args[1]["entity_threshold"] == 0.5
            assert call_args[1]["relation_threshold"] == 0.6
