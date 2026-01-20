"""Entity extraction using GLiNER zero-shot NER."""

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

from neo4j_agent_memory.extraction.base import (
    ExtractedEntity,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


# Default POLE+O labels for GLiNER (lowercase as GLiNER prefers)
DEFAULT_POLEO_LABELS = [
    "person",
    "organization",
    "location",
    "event",
    "object",
    # Common subtypes that GLiNER can recognize
    "vehicle",
    "phone number",
    "email address",
    "document",
    "device",
    "weapon",
    "address",
    "city",
    "country",
    "company",
    "meeting",
    "transaction",
]


class GLiNERConfig(BaseModel):
    """Configuration for GLiNER entity extractor."""

    model: str = Field(default="urchade/gliner_medium-v2.1", description="GLiNER model to use")
    entity_labels: list[str] = Field(
        default_factory=lambda: DEFAULT_POLEO_LABELS.copy(),
        description="Entity labels for zero-shot extraction",
    )
    threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence threshold for entities"
    )
    flat_ner: bool = Field(default=True, description="Use flat NER (no nested entities)")
    multi_label: bool = Field(default=False, description="Allow multiple labels per entity")
    device: str = Field(default="cpu", description="Device to run model on (cpu, cuda)")
    context_window: int = Field(
        default=50, ge=0, description="Characters of context to include around entities"
    )


class GLiNEREntityExtractor:
    """Entity extraction using GLiNER zero-shot Named Entity Recognition.

    GLiNER (Generalist and Lightweight Named Entity Recognition) provides
    zero-shot NER capabilities, allowing extraction of custom entity types
    without retraining. This is ideal for the POLE+O model where we need
    to extract domain-specific entities.

    Note: GLiNER does not extract relations or preferences - use in combination
    with other extractors (LLM) for full extraction.
    """

    # Mapping from GLiNER labels to POLE+O types
    DEFAULT_LABEL_MAPPING: dict[str, tuple[str, str | None]] = {
        # Person types -> (TYPE, SUBTYPE)
        "person": ("PERSON", None),
        "individual": ("PERSON", "INDIVIDUAL"),
        "alias": ("PERSON", "ALIAS"),
        # Organization types
        "organization": ("ORGANIZATION", None),
        "company": ("ORGANIZATION", "COMPANY"),
        "nonprofit": ("ORGANIZATION", "NONPROFIT"),
        "government": ("ORGANIZATION", "GOVERNMENT"),
        "educational institution": ("ORGANIZATION", "EDUCATIONAL"),
        # Location types
        "location": ("LOCATION", None),
        "address": ("LOCATION", "ADDRESS"),
        "city": ("LOCATION", "CITY"),
        "country": ("LOCATION", "COUNTRY"),
        "region": ("LOCATION", "REGION"),
        "landmark": ("LOCATION", "LANDMARK"),
        # Event types
        "event": ("EVENT", None),
        "incident": ("EVENT", "INCIDENT"),
        "meeting": ("EVENT", "MEETING"),
        "transaction": ("EVENT", "TRANSACTION"),
        "communication": ("EVENT", "COMMUNICATION"),
        # Object types
        "object": ("OBJECT", None),
        "vehicle": ("OBJECT", "VEHICLE"),
        "phone number": ("OBJECT", "PHONE"),
        "phone": ("OBJECT", "PHONE"),
        "email address": ("OBJECT", "EMAIL"),
        "email": ("OBJECT", "EMAIL"),
        "document": ("OBJECT", "DOCUMENT"),
        "device": ("OBJECT", "DEVICE"),
        "weapon": ("OBJECT", "WEAPON"),
        "product": ("OBJECT", "PRODUCT"),
    }

    def __init__(
        self,
        model: str = "urchade/gliner_medium-v2.1",
        entity_labels: list[str] | None = None,
        threshold: float = 0.5,
        flat_ner: bool = True,
        multi_label: bool = False,
        device: str = "cpu",
        context_window: int = 50,
        label_mapping: dict[str, tuple[str, str | None]] | None = None,
    ):
        """
        Initialize GLiNER entity extractor.

        Args:
            model: GLiNER model name from HuggingFace
            entity_labels: List of entity labels for zero-shot extraction
            threshold: Confidence threshold for including entities
            flat_ner: Use flat NER (no nested entities)
            multi_label: Allow multiple labels per entity
            device: Device to run on (cpu, cuda, mps)
            context_window: Characters of context to include around entities
            label_mapping: Custom mapping from GLiNER labels to (TYPE, SUBTYPE)
        """
        self._model_name = model
        self._model = None  # Lazy load
        self.entity_labels = entity_labels or DEFAULT_POLEO_LABELS.copy()
        self.threshold = threshold
        self.flat_ner = flat_ner
        self.multi_label = multi_label
        self.device = device
        self.context_window = context_window
        self.label_mapping = label_mapping or self.DEFAULT_LABEL_MAPPING.copy()

    @property
    def model(self) -> Any:
        """Lazy load GLiNER model."""
        if self._model is None:
            try:
                from gliner import GLiNER

                logger.info(f"Loading GLiNER model: {self._model_name}")
                self._model = GLiNER.from_pretrained(self._model_name)
                self._model.to(self.device)
                logger.info(f"GLiNER model loaded on {self.device}")
            except ImportError:
                raise ImportError(
                    "GLiNER is required for GLiNEREntityExtractor. Install with: pip install gliner"
                )
            except Exception as e:
                raise RuntimeError(f"Could not load GLiNER model '{self._model_name}': {e}") from e
        return self._model

    def _get_context(self, text: str, start: int, end: int) -> str:
        """Get surrounding context for an entity."""
        context_start = max(0, start - self.context_window)
        context_end = min(len(text), end + self.context_window)
        return text[context_start:context_end]

    def _map_label_to_poleo(self, label: str) -> tuple[str, str | None]:
        """Map GLiNER label to POLE+O type and subtype."""
        label_lower = label.lower()

        # Check direct mapping
        if label_lower in self.label_mapping:
            return self.label_mapping[label_lower]

        # Try to infer from label
        label_upper = label.upper()
        if label_upper in ["PERSON", "ORGANIZATION", "LOCATION", "EVENT", "OBJECT"]:
            return (label_upper, None)

        # Default to OBJECT
        return ("OBJECT", label_upper)

    def _extract_sync(
        self, text: str, entity_types: list[str] | None = None
    ) -> list[ExtractedEntity]:
        """Synchronous extraction."""
        # Determine which labels to use
        labels = self.entity_labels.copy()

        # If specific entity types requested, filter labels
        if entity_types:
            entity_types_lower = [t.lower() for t in entity_types]
            labels = [
                label
                for label in labels
                if label.lower() in entity_types_lower
                or self._map_label_to_poleo(label)[0] in entity_types
            ]

        if not labels:
            labels = self.entity_labels.copy()

        # Run GLiNER prediction
        predictions = self.model.predict_entities(
            text,
            labels,
            threshold=self.threshold,
            flat_ner=self.flat_ner,
            multi_label=self.multi_label,
        )

        entities = []
        for pred in predictions:
            # Map to POLE+O type
            entity_type, subtype = self._map_label_to_poleo(pred["label"])

            # Filter by requested types
            if entity_types and entity_type not in entity_types:
                continue

            entity = ExtractedEntity(
                name=pred["text"].strip(),
                type=entity_type,
                subtype=subtype,
                start_pos=pred["start"],
                end_pos=pred["end"],
                confidence=pred["score"],
                context=self._get_context(text, pred["start"], pred["end"]),
                extractor="gliner",
                attributes={
                    "gliner_label": pred["label"],
                    "gliner_score": pred["score"],
                },
            )
            entities.append(entity)

        return entities

    async def extract(
        self,
        text: str,
        *,
        entity_types: list[str] | None = None,
        extract_relations: bool = True,
        extract_preferences: bool = True,
    ) -> ExtractionResult:
        """
        Extract entities from text using GLiNER zero-shot NER.

        Note: GLiNER does not extract relations or preferences.
        For full extraction, combine with LLM extractor.

        Args:
            text: The text to extract from
            entity_types: Optional list of POLE+O entity types to extract
            extract_relations: Ignored (GLiNER doesn't extract relations)
            extract_preferences: Ignored (GLiNER doesn't extract preferences)

        Returns:
            ExtractionResult containing extracted entities
        """
        if not text or not text.strip():
            return ExtractionResult(source_text=text)

        # Run synchronous GLiNER in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        entities = await loop.run_in_executor(None, self._extract_sync, text, entity_types)

        logger.debug(f"GLiNER extracted {len(entities)} entities from text")

        return ExtractionResult(
            entities=entities,
            relations=[],  # GLiNER doesn't extract relations
            preferences=[],  # GLiNER doesn't extract preferences
            source_text=text,
        )

    def update_labels(self, labels: list[str]) -> None:
        """Update entity labels for extraction."""
        self.entity_labels = labels.copy()

    def add_label_mapping(self, label: str, entity_type: str, subtype: str | None = None) -> None:
        """Add a custom label mapping."""
        self.label_mapping[label.lower()] = (entity_type.upper(), subtype)

    @classmethod
    def from_config(cls, config: GLiNERConfig) -> "GLiNEREntityExtractor":
        """Create extractor from configuration."""
        return cls(
            model=config.model,
            entity_labels=config.entity_labels,
            threshold=config.threshold,
            flat_ner=config.flat_ner,
            multi_label=config.multi_label,
            device=config.device,
            context_window=config.context_window,
        )

    @classmethod
    def for_poleo(
        cls,
        model: str = "urchade/gliner_medium-v2.1",
        threshold: float = 0.5,
        device: str = "cpu",
    ) -> "GLiNEREntityExtractor":
        """Create extractor optimized for POLE+O entity extraction."""
        return cls(
            model=model,
            entity_labels=DEFAULT_POLEO_LABELS,
            threshold=threshold,
            device=device,
        )
