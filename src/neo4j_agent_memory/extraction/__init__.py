"""Entity and relation extraction from text.

This module provides multiple extraction approaches:
- SpacyEntityExtractor: Fast statistical NER using spaCy
- GLiNEREntityExtractor: Zero-shot NER for custom entity types
- LLMEntityExtractor: LLM-based extraction (most accurate)
- ExtractionPipeline: Multi-stage pipeline combining multiple extractors

The default configuration uses a pipeline approach:
1. spaCy for fast initial extraction of common entities
2. GLiNER for domain-specific entity types
3. LLM as fallback for complex cases and relation extraction
"""

from neo4j_agent_memory.extraction.base import (
    EntityExtractor,
    ExtractedEntity,
    ExtractedPreference,
    ExtractedRelation,
    ExtractionResult,
    NoOpExtractor,
)
from neo4j_agent_memory.extraction.factory import (
    ExtractorBuilder,
    create_extraction_pipeline,
    create_extractor,
    create_gliner_extractor,
    create_llm_extractor,
    create_spacy_extractor,
)
from neo4j_agent_memory.extraction.pipeline import (
    ConditionalPipeline,
    ExtractionPipeline,
    ExtractorStage,
    MergeStrategy,
    PipelineResult,
    StageResult,
    merge_extraction_results,
)

__all__ = [
    # Base classes
    "EntityExtractor",
    "ExtractedEntity",
    "ExtractedPreference",
    "ExtractedRelation",
    "ExtractionResult",
    "NoOpExtractor",
    # Pipeline
    "ExtractionPipeline",
    "ConditionalPipeline",
    "ExtractorStage",
    "MergeStrategy",
    "PipelineResult",
    "StageResult",
    "merge_extraction_results",
    # Factory
    "ExtractorBuilder",
    "create_extractor",
    "create_extraction_pipeline",
    "create_gliner_extractor",
    "create_llm_extractor",
    "create_spacy_extractor",
]


# Lazy imports for optional extractors
def __getattr__(name: str):
    """Lazy import optional extractors."""
    if name == "SpacyEntityExtractor":
        from neo4j_agent_memory.extraction.spacy_extractor import SpacyEntityExtractor

        return SpacyEntityExtractor
    elif name == "GLiNEREntityExtractor":
        from neo4j_agent_memory.extraction.gliner_extractor import GLiNEREntityExtractor

        return GLiNEREntityExtractor
    elif name == "LLMEntityExtractor":
        from neo4j_agent_memory.extraction.llm_extractor import LLMEntityExtractor

        return LLMEntityExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
