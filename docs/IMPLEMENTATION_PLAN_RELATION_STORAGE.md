# Implementation Plan: Store Extracted Relations in Short-Term Memory

> **Status: IMPLEMENTED** - This feature has been implemented. See the Implementation Summary section at the end of this document.

## Problem Statement

The neo4j-agent-memory library's entity extraction pipeline extracts **both entities AND relations**, but only entities are stored. Relations are silently discarded, which means:

- `RELATED_TO` relationships are never created between entities
- The knowledge graph only has `Message -[:MENTIONS]-> Entity` connections
- Entity-to-entity relationships like "Brian Chesky FOUNDED Airbnb" are lost
- The `get_graph()` method warns about missing `RELATED_TO` relationship type

## Current Data Flow

```
Text
  │
  ▼
Extractor.extract(text)
  │
  ▼
ExtractionResult {
  entities: [ExtractedEntity, ...],    ← STORED
  relations: [ExtractedRelation, ...], ← DISCARDED
  preferences: [...]                   ← Handled separately
}
  │
  ▼
ShortTermMemory._extract_and_link_entities()
  │
  ├──► Creates Entity nodes (via LongTermMemory.add_entity or direct Cypher)
  └──► Creates MENTIONS relationships (Message → Entity)
       ❌ Never processes result.relations
```

## Proposed Data Flow

```
Text
  │
  ▼
Extractor.extract(text)
  │
  ▼
ExtractionResult {
  entities: [ExtractedEntity, ...],
  relations: [ExtractedRelation, ...],
  preferences: [...]
}
  │
  ▼
ShortTermMemory._extract_and_link_entities()
  │
  ├──► Creates Entity nodes
  ├──► Creates MENTIONS relationships (Message → Entity)
  └──► NEW: Creates RELATED_TO relationships (Entity → Entity)
```

## Implementation Steps

### Phase 1: Core Library Changes

#### 1.1 Modify `ShortTermMemory._extract_and_link_entities()`

**File:** `neo4j_agent_memory/memory/short_term.py`

**Current code (around line 780):**
```python
async def _extract_and_link_entities(self, message: Message) -> None:
    """Extract entities from message and link them."""
    if self._extractor is None:
        return

    result = await self._extractor.extract(message.content)
    result = result.filter_invalid_entities()

    for entity in result.entities:
        # ... create entity and MENTIONS relationship
        pass
    # ❌ result.relations is NEVER processed
```

**Proposed change:**
```python
async def _extract_and_link_entities(self, message: Message) -> None:
    """Extract entities from message and link them."""
    if self._extractor is None:
        return

    result = await self._extractor.extract(message.content)
    result = result.filter_invalid_entities()

    # Track entity name to ID mapping for relation linking
    entity_name_to_id: dict[str, str] = {}

    for entity in result.entities:
        entity_id = str(uuid4())
        entity_subtype = getattr(entity, "subtype", None)
        create_query = build_create_entity_query(entity.type, entity_subtype)
        
        await self._client.execute_write(
            create_query,
            {
                "id": entity_id,
                "name": entity.name,
                # ... other fields
            },
        )
        
        # Store mapping for relation linking
        entity_name_to_id[entity.name.lower().strip()] = entity_id

        # Link message to entity (MENTIONS relationship)
        await self._client.execute_write(
            queries.LINK_MESSAGE_TO_ENTITY,
            {
                "message_id": str(message.id),
                "entity_id": entity_id,
                # ... other fields
            },
        )

    # NEW: Store extracted relations
    await self._store_relations(result.relations, entity_name_to_id)
```

#### 1.2 Add New Method `_store_relations()`

**File:** `neo4j_agent_memory/memory/short_term.py`

```python
async def _store_relations(
    self,
    relations: list[ExtractedRelation],
    entity_name_to_id: dict[str, str],
) -> None:
    """Store extracted relations as RELATED_TO relationships between entities.
    
    Args:
        relations: List of extracted relations from the extractor
        entity_name_to_id: Mapping of lowercase entity names to their IDs
    """
    if not relations:
        return

    for relation in relations:
        source_name = relation.source.lower().strip()
        target_name = relation.target.lower().strip()
        
        # Get entity IDs from the mapping
        source_id = entity_name_to_id.get(source_name)
        target_id = entity_name_to_id.get(target_name)
        
        if source_id and target_id:
            # Create RELATED_TO relationship
            await self._client.execute_write(
                queries.CREATE_ENTITY_RELATION,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation_type": relation.relation_type,
                    "confidence": relation.confidence,
                },
            )
```

#### 1.3 Add New Cypher Query

**File:** `neo4j_agent_memory/graph/queries.py`

```python
CREATE_ENTITY_RELATION = """
MATCH (source:Entity {id: $source_id})
MATCH (target:Entity {id: $target_id})
MERGE (source)-[r:RELATED_TO {relation_type: $relation_type}]->(target)
SET r.confidence = $confidence,
    r.updated_at = datetime()
RETURN r
"""
```

#### 1.4 Update `extract_entities_from_session()`

**File:** `neo4j_agent_memory/memory/short_term.py`

The batch extraction method also needs to store relations. Modify the processing loop:

```python
async def extract_entities_from_session(
    self,
    session_id: str,
    *,
    batch_size: int = 50,
    skip_existing: bool = True,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    # ... existing code ...

    relations_extracted = 0  # NEW: Track relation count

    for i in range(0, total, batch_size):
        batch = results[i : i + batch_size]

        for row in batch:
            message_id = row["id"]
            content = row["content"]

            extraction_result = await self._extractor.extract(content)
            extraction_result = extraction_result.filter_invalid_entities()

            # Track entity name to ID mapping
            entity_name_to_id: dict[str, str] = {}

            for entity in extraction_result.entities:
                entity_id = str(uuid4())
                # ... create entity ...
                entity_name_to_id[entity.name.lower().strip()] = entity_id
                # ... link to message ...
                entities_extracted += 1

            # NEW: Store relations
            for relation in extraction_result.relations:
                source_id = entity_name_to_id.get(relation.source.lower().strip())
                target_id = entity_name_to_id.get(relation.target.lower().strip())
                
                if source_id and target_id:
                    await self._client.execute_write(
                        queries.CREATE_ENTITY_RELATION,
                        {
                            "source_id": source_id,
                            "target_id": target_id,
                            "relation_type": relation.relation_type,
                            "confidence": relation.confidence,
                        },
                    )
                    relations_extracted += 1

            processed += 1

    return {
        "messages_processed": processed,
        "entities_extracted": entities_extracted,
        "relations_extracted": relations_extracted,  # NEW
    }
```

### Phase 2: Handle Existing Entities

The current implementation creates new entity nodes for each extraction. However, entities may already exist. We need to handle this by:

1. **Looking up existing entities by name** before creating new ones
2. **Using MERGE** instead of CREATE for entities
3. **Returning the entity ID** whether existing or new

#### 2.1 Modify Entity Creation to Use MERGE

**File:** `neo4j_agent_memory/graph/query_builder.py`

The `build_create_entity_query()` function should use `MERGE` on the entity name to avoid duplicates:

```python
def build_create_entity_query(entity_type: str, subtype: str | None = None) -> str:
    """Build MERGE query for entity creation."""
    # ... existing label building logic ...
    
    return f"""
    MERGE (e:Entity {{name: $name}})
    ON CREATE SET
        e.id = $id,
        e.type = $type,
        e.subtype = $subtype,
        e.canonical_name = $canonical_name,
        e.description = $description,
        e.embedding = $embedding,
        e.confidence = $confidence,
        e.metadata = $metadata,
        e.created_at = datetime()
    ON MATCH SET
        e.confidence = CASE 
            WHEN e.confidence < $confidence THEN $confidence 
            ELSE e.confidence 
        END
    {additional_labels}
    RETURN e.id AS id
    """
```

#### 2.2 Update _extract_and_link_entities to Use Returned ID

```python
async def _extract_and_link_entities(self, message: Message) -> None:
    # ...
    for entity in result.entities:
        entity_id = str(uuid4())
        create_query = build_create_entity_query(entity.type, entity_subtype)
        
        result = await self._client.execute_write(
            create_query,
            {"id": entity_id, "name": entity.name, ...},
        )
        
        # Use the returned ID (may be existing entity's ID)
        actual_entity_id = result[0]["id"] if result else entity_id
        entity_name_to_id[entity.name.lower().strip()] = actual_entity_id
```

### Phase 3: Cross-Message Relations

Relations may reference entities from different messages. To handle this:

#### 3.1 Add Entity Lookup Before Creating Relations

```python
async def _store_relations(
    self,
    relations: list[ExtractedRelation],
    entity_name_to_id: dict[str, str],
) -> None:
    for relation in relations:
        source_name = relation.source.lower().strip()
        target_name = relation.target.lower().strip()
        
        # First try the local mapping
        source_id = entity_name_to_id.get(source_name)
        target_id = entity_name_to_id.get(target_name)
        
        # If not found locally, look up in database
        if not source_id:
            existing = await self._client.execute_read(
                "MATCH (e:Entity) WHERE toLower(e.name) = $name RETURN e.id AS id",
                {"name": source_name}
            )
            if existing:
                source_id = existing[0]["id"]
        
        if not target_id:
            existing = await self._client.execute_read(
                "MATCH (e:Entity) WHERE toLower(e.name) = $name RETURN e.id AS id",
                {"name": target_name}
            )
            if existing:
                target_id = existing[0]["id"]
        
        if source_id and target_id:
            await self._client.execute_write(
                queries.CREATE_ENTITY_RELATION,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation_type": relation.relation_type,
                    "confidence": relation.confidence,
                },
            )
```

### Phase 4: Configuration Options

#### 4.1 Add Configuration Parameters

```python
async def add_message(
    self,
    session_id: str,
    role: MessageRole | str,
    content: str,
    *,
    extract_entities: bool = True,
    extract_relations: bool = True,  # NEW
    generate_embedding: bool = True,
    metadata: dict[str, Any] | None = None,
) -> Message:
```

#### 4.2 Add to Batch Methods

```python
async def add_messages_batch(
    self,
    session_id: str,
    messages: list[dict[str, Any]],
    *,
    extract_entities: bool = False,
    extract_relations: bool = True,  # NEW (only applies when extract_entities=True)
    # ...
) -> list[Message]:
```

### Phase 5: Tests

#### 5.1 Unit Tests

**File:** `tests/test_short_term.py`

```python
@pytest.mark.asyncio
async def test_extract_and_store_relations():
    """Test that relations are extracted and stored."""
    # Setup with mock extractor that returns relations
    mock_extractor = MockExtractor(
        entities=[
            ExtractedEntity(name="Brian Chesky", type="PERSON"),
            ExtractedEntity(name="Airbnb", type="ORGANIZATION"),
        ],
        relations=[
            ExtractedRelation(
                source="Brian Chesky",
                target="Airbnb",
                relation_type="FOUNDED",
                confidence=0.95,
            ),
        ],
    )
    
    memory = ShortTermMemory(client, extractor=mock_extractor)
    await memory.add_message("test-session", "user", "Brian Chesky founded Airbnb")
    
    # Verify RELATED_TO relationship was created
    results = await client.execute_read("""
        MATCH (p:Entity {name: 'Brian Chesky'})-[r:RELATED_TO]->(o:Entity {name: 'Airbnb'})
        RETURN r.relation_type AS type, r.confidence AS confidence
    """)
    
    assert len(results) == 1
    assert results[0]["type"] == "FOUNDED"
    assert results[0]["confidence"] == 0.95


@pytest.mark.asyncio
async def test_batch_extraction_with_relations():
    """Test batch extraction stores relations."""
    # Similar test for extract_entities_from_session()


@pytest.mark.asyncio
async def test_relation_to_existing_entity():
    """Test relation can reference entity from previous message."""
```

### Phase 6: Workaround for Lenny's Memory

Until the library is updated, Lenny's Memory can use a post-processing script:

**File:** `backend/scripts/extract_relations.py`

```python
"""
Post-processing script to extract relations from existing podcast data.

This is a workaround until neo4j-agent-memory stores relations natively.
"""

import asyncio
from neo4j import AsyncGraphDatabase

async def extract_relations_from_messages():
    """Re-process messages to extract and store relations."""
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    async with driver.session() as session:
        # Get messages with their extracted entities
        messages = await session.run("""
            MATCH (m:Message)-[:MENTIONS]->(e:Entity)
            WHERE m.content IS NOT NULL
            WITH m, collect(e.name) as entities
            WHERE size(entities) >= 2
            RETURN m.id as id, m.content as content, entities
            ORDER BY m.timestamp
        """)
        
        for record in messages:
            # Use LLM or rule-based extraction for relations
            content = record["content"]
            entities = record["entities"]
            
            # Extract relations between co-occurring entities
            relations = await extract_relations(content, entities)
            
            for relation in relations:
                # Store RELATED_TO relationship
                await session.run("""
                    MATCH (source:Entity {name: $source})
                    MATCH (target:Entity {name: $target})
                    MERGE (source)-[r:RELATED_TO {relation_type: $type}]->(target)
                    SET r.confidence = $confidence
                """, {
                    "source": relation.source,
                    "target": relation.target,
                    "type": relation.relation_type,
                    "confidence": relation.confidence,
                })
    
    await driver.close()


if __name__ == "__main__":
    asyncio.run(extract_relations_from_messages())
```

---

## Summary

| Phase | Description | Effort | Priority |
|-------|-------------|--------|----------|
| 1 | Core library changes to store relations | Medium | HIGH |
| 2 | Handle existing entities (MERGE) | Low | HIGH |
| 3 | Cross-message relation support | Low | MEDIUM |
| 4 | Configuration options | Low | MEDIUM |
| 5 | Tests | Medium | HIGH |
| 6 | Lenny's Memory workaround | Low | MEDIUM |

## Files to Modify

**Library (neo4j-agent-memory):**
- `src/neo4j_agent_memory/memory/short_term.py` - Core changes
- `src/neo4j_agent_memory/graph/queries.py` - New Cypher query
- `src/neo4j_agent_memory/graph/query_builder.py` - MERGE instead of CREATE
- `tests/test_short_term.py` - New tests

**Demo App (Lenny's Memory):**
- `backend/scripts/extract_relations.py` - Workaround script (optional)

## Expected Outcome

After implementation:

1. `RELATED_TO` relationships will be created between entities
2. Knowledge graph will capture semantic relationships like "FOUNDED", "WORKS_AT", "LOCATED_IN"
3. The `get_graph()` method will no longer warn about missing relationship types
4. Tools like `find_related_entities` will return richer results
5. Graph visualization will show entity-to-entity connections

---

## Implementation Summary

**Status: COMPLETED**

### Files Modified

**1. `src/neo4j_agent_memory/graph/queries.py`**
- Added `CREATE_ENTITY_RELATION_BY_NAME` - Cypher query to create RELATED_TO relationships by looking up entities by name (for cross-message relations)
- Added `CREATE_ENTITY_RELATION_BY_ID` - Cypher query to create RELATED_TO relationships by entity ID (for same-message relations)

**2. `src/neo4j_agent_memory/memory/short_term.py`**
- Modified `_extract_and_link_entities()` to accept `extract_relations` parameter and store relations
- Added new `_store_relations()` method that:
  - Uses ID-based queries when both entities are in the local mapping (same message)
  - Falls back to name-based queries for cross-message relations
- Updated `extract_entities_from_session()` to:
  - Accept `extract_relations` parameter (default: `True`)
  - Return `relations_extracted` count in the result dict
- Updated `add_message()` to accept `extract_relations` parameter (default: `True`)
- Updated `add_messages_batch()` to accept `extract_relations` parameter (default: `True`)

**3. `tests/unit/test_relation_storage.py`** (new file)
- 12 unit tests covering:
  - Relation storage in `_extract_and_link_entities()`
  - Skipping relations when `extract_relations=False`
  - ID-based vs name-based query selection
  - `add_message()` with relation extraction
  - `extract_entities_from_session()` with relation extraction
  - Cypher query existence validation

### API Usage

```python
# add_message with relation extraction (default: True)
await memory.add_message(
    session_id="test",
    role="user",
    content="Brian Chesky founded Airbnb",
    extract_entities=True,
    extract_relations=True,  # default
)

# add_messages_batch with relation extraction (default: True, but only applies when extract_entities=True)
await memory.add_messages_batch(
    session_id="test",
    messages=[...],
    extract_entities=True,  # must be True for relations to be extracted
    extract_relations=True,  # default
)

# extract_entities_from_session returns relations count
result = await memory.extract_entities_from_session(
    "test-session",
    extract_relations=True,  # default
)
# result = {"messages_processed": 10, "entities_extracted": 25, "relations_extracted": 8}
```

### Test Results
- **12 new tests**: All passing
- **533 existing unit tests**: All passing
