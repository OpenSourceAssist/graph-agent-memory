"""LLM-based entity and preference extraction."""

import json
from typing import TYPE_CHECKING, Any

from neo4j_agent_memory.core.exceptions import ExtractionError
from neo4j_agent_memory.extraction.base import (
    EntityExtractor,
    ExtractedEntity,
    ExtractedPreference,
    ExtractedRelation,
    ExtractionResult,
)

if TYPE_CHECKING:
    from openai import AsyncOpenAI


DEFAULT_ENTITY_TYPES = [
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "EVENT",
    "CONCEPT",
    "PREFERENCE",
]

DEFAULT_EXTRACTION_PROMPT = """Extract entities, relationships, and preferences from the following text.

Entity types to extract: {entity_types}

Return a JSON object with this structure:
{{
    "entities": [
        {{"name": "entity name", "type": "ENTITY_TYPE", "confidence": 0.9}}
    ],
    "relations": [
        {{"source": "entity1", "target": "entity2", "relation_type": "relationship type", "confidence": 0.8}}
    ],
    "preferences": [
        {{"category": "category", "preference": "the preference", "context": "when/where it applies", "confidence": 0.85}}
    ]
}}

Guidelines:
- Extract all named entities matching the types above
- For relations, identify how entities are connected
- For preferences, identify user preferences, likes, dislikes, and opinions
- Confidence should be 0.0-1.0 based on how certain the extraction is
- Only include relations between entities that appear in the entities list

Text to analyze:
{text}

Return only valid JSON, no other text."""


class LLMEntityExtractor(EntityExtractor):
    """
    LLM-based entity and preference extraction.

    Uses OpenAI's structured output capabilities for reliable extraction.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        *,
        api_key: str | None = None,
        entity_types: list[str] | None = None,
        extraction_prompt: str | None = None,
        temperature: float = 0.0,
    ):
        """
        Initialize LLM extractor.

        Args:
            model: OpenAI model to use
            api_key: OpenAI API key
            entity_types: Entity types to extract
            extraction_prompt: Custom extraction prompt
            temperature: LLM temperature
        """
        self._model = model
        self._api_key = api_key
        self._entity_types = entity_types or DEFAULT_ENTITY_TYPES
        self._prompt = extraction_prompt or DEFAULT_EXTRACTION_PROMPT
        self._temperature = temperature
        self._client: "AsyncOpenAI | None" = None

    def _ensure_client(self) -> "AsyncOpenAI":
        """Ensure the OpenAI client is initialized."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ExtractionError(
                    "OpenAI package not installed. Install with: pip install neo4j-agent-memory[openai]"
                )
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def extract(
        self,
        text: str,
        *,
        entity_types: list[str] | None = None,
        extract_relations: bool = True,
        extract_preferences: bool = True,
    ) -> ExtractionResult:
        """Extract entities, relations, and preferences from text."""
        if not text.strip():
            return ExtractionResult(source_text=text)

        client = self._ensure_client()
        types_to_use = entity_types or self._entity_types

        prompt = self._prompt.format(
            entity_types=", ".join(types_to_use),
            text=text,
        )

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured information from text. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                return ExtractionResult(source_text=text)

            data = json.loads(content)
            return self._parse_extraction_result(data, text, extract_relations, extract_preferences)

        except json.JSONDecodeError as e:
            raise ExtractionError(f"Failed to parse LLM response as JSON: {e}") from e
        except Exception as e:
            raise ExtractionError(f"Failed to extract entities: {e}") from e

    def _parse_extraction_result(
        self,
        data: dict[str, Any],
        source_text: str,
        include_relations: bool,
        include_preferences: bool,
    ) -> ExtractionResult:
        """Parse LLM response into ExtractionResult."""
        entities: list[ExtractedEntity] = []
        relations: list[ExtractedRelation] = []
        preferences: list[ExtractedPreference] = []

        # Parse entities
        for entity_data in data.get("entities", []):
            try:
                entities.append(
                    ExtractedEntity(
                        name=entity_data.get("name", ""),
                        type=entity_data.get("type", "UNKNOWN").upper(),
                        confidence=float(entity_data.get("confidence", 1.0)),
                    )
                )
            except (ValueError, TypeError):
                continue

        # Parse relations
        if include_relations:
            for relation_data in data.get("relations", []):
                try:
                    relations.append(
                        ExtractedRelation(
                            source=relation_data.get("source", ""),
                            target=relation_data.get("target", ""),
                            relation_type=relation_data.get("relation_type", "RELATED_TO"),
                            confidence=float(relation_data.get("confidence", 1.0)),
                        )
                    )
                except (ValueError, TypeError):
                    continue

        # Parse preferences
        if include_preferences:
            for pref_data in data.get("preferences", []):
                try:
                    preferences.append(
                        ExtractedPreference(
                            category=pref_data.get("category", "general"),
                            preference=pref_data.get("preference", ""),
                            context=pref_data.get("context"),
                            confidence=float(pref_data.get("confidence", 1.0)),
                        )
                    )
                except (ValueError, TypeError):
                    continue

        return ExtractionResult(
            entities=entities,
            relations=relations,
            preferences=preferences,
            source_text=source_text,
        )
