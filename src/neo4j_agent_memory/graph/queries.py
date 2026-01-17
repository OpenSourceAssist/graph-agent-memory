"""Cypher query templates for memory operations."""

# =============================================================================
# EPISODIC MEMORY QUERIES
# =============================================================================

CREATE_CONVERSATION = """
CREATE (c:Conversation {
    id: $id,
    session_id: $session_id,
    title: $title,
    created_at: datetime(),
    updated_at: datetime()
})
RETURN c
"""

GET_CONVERSATION = """
MATCH (c:Conversation {id: $id})
RETURN c
"""

GET_CONVERSATION_BY_SESSION = """
MATCH (c:Conversation {session_id: $session_id})
RETURN c
ORDER BY c.created_at DESC
LIMIT 1
"""

LIST_CONVERSATIONS = """
MATCH (c:Conversation {session_id: $session_id})
RETURN c
ORDER BY c.updated_at DESC
LIMIT $limit
"""

CREATE_MESSAGE = """
MATCH (c:Conversation {id: $conversation_id})
CREATE (m:Message {
    id: $id,
    role: $role,
    content: $content,
    embedding: $embedding,
    timestamp: datetime(),
    metadata: $metadata
})
CREATE (c)-[:HAS_MESSAGE]->(m)
SET c.updated_at = datetime()
RETURN m
"""

GET_CONVERSATION_MESSAGES = """
MATCH (c:Conversation {id: $conversation_id})-[:HAS_MESSAGE]->(m:Message)
RETURN m
ORDER BY m.timestamp ASC
LIMIT $limit
"""

SEARCH_MESSAGES_BY_EMBEDDING = """
CALL db.index.vector.queryNodes('message_embedding_idx', $limit, $embedding)
YIELD node, score
WHERE score >= $threshold
RETURN node AS m, score
ORDER BY score DESC
"""

# =============================================================================
# SEMANTIC MEMORY QUERIES
# =============================================================================

CREATE_ENTITY = """
MERGE (e:Entity {name: $name, type: $type})
ON CREATE SET
    e.id = $id,
    e.canonical_name = $canonical_name,
    e.description = $description,
    e.embedding = $embedding,
    e.confidence = $confidence,
    e.created_at = datetime(),
    e.metadata = $metadata
ON MATCH SET
    e.canonical_name = COALESCE($canonical_name, e.canonical_name),
    e.description = COALESCE($description, e.description),
    e.embedding = COALESCE($embedding, e.embedding),
    e.updated_at = datetime()
RETURN e
"""

GET_ENTITY = """
MATCH (e:Entity {id: $id})
RETURN e
"""

GET_ENTITY_BY_NAME = """
MATCH (e:Entity)
WHERE e.name = $name OR e.canonical_name = $name OR $name IN e.aliases
RETURN e
LIMIT 1
"""

SEARCH_ENTITIES_BY_EMBEDDING = """
CALL db.index.vector.queryNodes('entity_embedding_idx', $limit, $embedding)
YIELD node, score
WHERE score >= $threshold
RETURN node AS e, score
ORDER BY score DESC
"""

SEARCH_ENTITIES_BY_TYPE = """
MATCH (e:Entity {type: $type})
RETURN e
ORDER BY e.created_at DESC
LIMIT $limit
"""

CREATE_PREFERENCE = """
CREATE (p:Preference {
    id: $id,
    category: $category,
    preference: $preference,
    context: $context,
    confidence: $confidence,
    embedding: $embedding,
    created_at: datetime(),
    metadata: $metadata
})
RETURN p
"""

SEARCH_PREFERENCES_BY_EMBEDDING = """
CALL db.index.vector.queryNodes('preference_embedding_idx', $limit, $embedding)
YIELD node, score
WHERE score >= $threshold
RETURN node AS p, score
ORDER BY score DESC
"""

SEARCH_PREFERENCES_BY_CATEGORY = """
MATCH (p:Preference {category: $category})
RETURN p
ORDER BY p.confidence DESC, p.created_at DESC
LIMIT $limit
"""

CREATE_FACT = """
CREATE (f:Fact {
    id: $id,
    subject: $subject,
    predicate: $predicate,
    object: $object,
    confidence: $confidence,
    embedding: $embedding,
    valid_from: $valid_from,
    valid_until: $valid_until,
    created_at: datetime(),
    metadata: $metadata
})
RETURN f
"""

CREATE_ENTITY_RELATIONSHIP = """
MATCH (e1:Entity {id: $source_id})
MATCH (e2:Entity {id: $target_id})
MERGE (e1)-[r:RELATED_TO {type: $relation_type}]->(e2)
ON CREATE SET
    r.id = $id,
    r.description = $description,
    r.confidence = $confidence,
    r.valid_from = $valid_from,
    r.valid_until = $valid_until,
    r.created_at = datetime()
RETURN r
"""

GET_FACTS_BY_SUBJECT = """
MATCH (f:Fact)
WHERE f.subject = $subject
RETURN f
ORDER BY f.confidence DESC, f.created_at DESC
LIMIT $limit
"""

SEARCH_FACTS_BY_EMBEDDING = """
CALL db.index.vector.queryNodes('fact_embedding_idx', $limit, $embedding)
YIELD node, score
WHERE score >= $threshold
RETURN node AS f, score
ORDER BY score DESC
"""

GET_ENTITY_RELATIONSHIPS = """
MATCH (e:Entity {id: $entity_id})-[r:RELATED_TO]-(other:Entity)
RETURN e, r, other
"""

LINK_MESSAGE_TO_ENTITY = """
MATCH (m:Message {id: $message_id})
MATCH (e:Entity {id: $entity_id})
MERGE (m)-[r:MENTIONS]->(e)
ON CREATE SET
    r.confidence = $confidence,
    r.start_pos = $start_pos,
    r.end_pos = $end_pos
RETURN r
"""

LINK_PREFERENCE_TO_ENTITY = """
MATCH (p:Preference {id: $preference_id})
MATCH (e:Entity {id: $entity_id})
MERGE (p)-[r:ABOUT]->(e)
RETURN r
"""

# =============================================================================
# PROCEDURAL MEMORY QUERIES
# =============================================================================

CREATE_REASONING_TRACE = """
CREATE (rt:ReasoningTrace {
    id: $id,
    session_id: $session_id,
    task: $task,
    task_embedding: $task_embedding,
    outcome: $outcome,
    success: $success,
    started_at: datetime(),
    completed_at: $completed_at,
    metadata: $metadata
})
RETURN rt
"""

UPDATE_REASONING_TRACE = """
MATCH (rt:ReasoningTrace {id: $id})
SET rt.outcome = $outcome,
    rt.success = $success,
    rt.completed_at = datetime()
RETURN rt
"""

CREATE_REASONING_STEP = """
MATCH (rt:ReasoningTrace {id: $trace_id})
CREATE (rs:ReasoningStep {
    id: $id,
    step_number: $step_number,
    thought: $thought,
    action: $action,
    observation: $observation,
    embedding: $embedding,
    timestamp: datetime(),
    metadata: $metadata
})
CREATE (rt)-[:HAS_STEP {order: $step_number}]->(rs)
RETURN rs
"""

CREATE_TOOL_CALL = """
MATCH (rs:ReasoningStep {id: $step_id})
MERGE (t:Tool {name: $tool_name})
ON CREATE SET t.created_at = datetime(), t.total_calls = 0
CREATE (tc:ToolCall {
    id: $id,
    tool_name: $tool_name,
    arguments: $arguments,
    result: $result,
    status: $status,
    duration_ms: $duration_ms,
    error: $error,
    timestamp: datetime()
})
CREATE (rs)-[:USES_TOOL]->(tc)
CREATE (tc)-[:INSTANCE_OF]->(t)
WITH t, tc
SET t.total_calls = t.total_calls + 1,
    t.last_used_at = datetime()
RETURN tc
"""

GET_TOOL_STATS = """
MATCH (t:Tool)
OPTIONAL MATCH (t)<-[:INSTANCE_OF]-(tc:ToolCall)
WITH t,
     count(tc) AS total_calls,
     sum(CASE WHEN tc.status = 'success' THEN 1 ELSE 0 END) AS successful_calls,
     avg(tc.duration_ms) AS avg_duration
RETURN t.name AS name,
       t.description AS description,
       total_calls,
       CASE WHEN total_calls > 0 THEN toFloat(successful_calls) / total_calls ELSE 0.0 END AS success_rate,
       avg_duration
ORDER BY total_calls DESC
"""

SEARCH_TRACES_BY_EMBEDDING = """
CALL db.index.vector.queryNodes('task_embedding_idx', $limit, $embedding)
YIELD node, score
WHERE score >= $threshold AND ($success_only = false OR node.success = true)
RETURN node AS rt, score
ORDER BY score DESC
"""

GET_TRACE_WITH_STEPS = """
MATCH (rt:ReasoningTrace {id: $id})
OPTIONAL MATCH (rt)-[:HAS_STEP]->(rs:ReasoningStep)
OPTIONAL MATCH (rs)-[:USES_TOOL]->(tc:ToolCall)
RETURN rt,
       collect(DISTINCT rs) AS steps,
       collect(DISTINCT tc) AS tool_calls
"""

# =============================================================================
# CROSS-MEMORY QUERIES
# =============================================================================

LINK_CONVERSATION_TO_TRACE = """
MATCH (c:Conversation {id: $conversation_id})
MATCH (rt:ReasoningTrace {id: $trace_id})
MERGE (c)-[:HAS_TRACE]->(rt)
RETURN c, rt
"""

GET_SESSION_CONTEXT = """
MATCH (c:Conversation {session_id: $session_id})-[:HAS_MESSAGE]->(m:Message)
WITH m ORDER BY m.timestamp DESC LIMIT $message_limit
OPTIONAL MATCH (m)-[:MENTIONS]->(e:Entity)
WITH collect(DISTINCT m) AS messages, collect(DISTINCT e) AS entities
OPTIONAL MATCH (p:Preference)
WHERE p.created_at > datetime() - duration({days: $preference_days})
RETURN messages, entities, collect(DISTINCT p) AS preferences
"""

# =============================================================================
# UTILITY QUERIES
# =============================================================================

DELETE_SESSION_DATA = """
MATCH (c:Conversation {session_id: $session_id})
OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
OPTIONAL MATCH (c)-[:HAS_TRACE]->(rt:ReasoningTrace)
OPTIONAL MATCH (rt)-[:HAS_STEP]->(rs:ReasoningStep)
OPTIONAL MATCH (rs)-[:USES_TOOL]->(tc:ToolCall)
DETACH DELETE c, m, rt, rs, tc
"""

GET_MEMORY_STATS = """
OPTIONAL MATCH (c:Conversation) WITH count(c) AS conversations
OPTIONAL MATCH (m:Message) WITH conversations, count(m) AS messages
OPTIONAL MATCH (e:Entity) WITH conversations, messages, count(e) AS entities
OPTIONAL MATCH (p:Preference) WITH conversations, messages, entities, count(p) AS preferences
OPTIONAL MATCH (f:Fact) WITH conversations, messages, entities, preferences, count(f) AS facts
OPTIONAL MATCH (rt:ReasoningTrace) WITH conversations, messages, entities, preferences, facts, count(rt) AS traces
RETURN conversations, messages, entities, preferences, facts, traces
"""
