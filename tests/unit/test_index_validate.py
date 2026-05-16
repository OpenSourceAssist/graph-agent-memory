"""Tests for SchemaManager.validate_vector_index_dimensions (WP-INDEX-VALIDATE).

We don't have a live Neo4j connection in unit tests, so the tests stub
out :meth:`Neo4jClient.execute_read` to return canned ``SHOW VECTOR
INDEXES`` results and assert the validator's branching is correct.
"""

from __future__ import annotations

from typing import Any

import pytest

from neo4j_agent_memory.graph.schema import SchemaManager, _extract_vector_dimensions
from neo4j_agent_memory.llm.errors import EmbeddingDimensionMismatchError

# ---------------------------------------------------------------------------
# _extract_vector_dimensions helper
# ---------------------------------------------------------------------------


def test_extract_dimensions_happy_path():
    options = {
        "indexConfig": {
            "vector.dimensions": 384,
            "vector.similarity_function": "cosine",
        },
        "indexProvider": "vector-1.0",
    }
    assert _extract_vector_dimensions(options) == 384


def test_extract_dimensions_returns_none_for_non_dict():
    assert _extract_vector_dimensions(None) is None
    assert _extract_vector_dimensions("nope") is None
    assert _extract_vector_dimensions(42) is None


def test_extract_dimensions_returns_none_for_missing_indexConfig():
    assert _extract_vector_dimensions({"indexProvider": "vector-1.0"}) is None


def test_extract_dimensions_returns_none_for_zero_or_negative():
    options = {"indexConfig": {"vector.dimensions": 0}}
    assert _extract_vector_dimensions(options) is None
    options = {"indexConfig": {"vector.dimensions": -1}}
    assert _extract_vector_dimensions(options) is None


# ---------------------------------------------------------------------------
# SchemaManager.validate_vector_index_dimensions
# ---------------------------------------------------------------------------


class _StubClient:
    """Minimal Neo4jClient stand-in returning canned rows for execute_read."""

    def __init__(
        self,
        rows: list[dict[str, Any]] | None = None,
        error_on_read: Exception | None = None,
    ) -> None:
        self._rows = rows or []
        self._error = error_on_read

    async def execute_read(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if self._error is not None:
            raise self._error
        return self._rows


async def test_validate_passes_when_all_managed_indexes_match():
    rows = [
        {
            "name": "message_embedding_idx",
            "options": {"indexConfig": {"vector.dimensions": 1536}},
        },
        {
            "name": "entity_embedding_idx",
            "options": {"indexConfig": {"vector.dimensions": 1536}},
        },
    ]
    mgr = SchemaManager(_StubClient(rows=rows), vector_dimensions=1536)  # type: ignore[arg-type]
    # No exception expected.
    await mgr.validate_vector_index_dimensions(1536)


async def test_validate_raises_on_mismatch():
    rows = [
        {
            "name": "message_embedding_idx",
            "options": {"indexConfig": {"vector.dimensions": 1536}},
        },
    ]
    mgr = SchemaManager(_StubClient(rows=rows), vector_dimensions=384)  # type: ignore[arg-type]
    with pytest.raises(EmbeddingDimensionMismatchError) as excinfo:
        await mgr.validate_vector_index_dimensions(384)
    assert excinfo.value.expected_dimensions == 384
    assert excinfo.value.actual_dimensions == 1536
    assert excinfo.value.index_name == "message_embedding_idx"
    # Message references the runbook so users know where to look.
    assert "migrate-embedding-model" in str(excinfo.value)


async def test_validate_lists_every_mismatching_index():
    rows = [
        {
            "name": "message_embedding_idx",
            "options": {"indexConfig": {"vector.dimensions": 1536}},
        },
        {
            "name": "entity_embedding_idx",
            "options": {"indexConfig": {"vector.dimensions": 1536}},
        },
        {
            "name": "preference_embedding_idx",
            "options": {"indexConfig": {"vector.dimensions": 1536}},
        },
    ]
    mgr = SchemaManager(_StubClient(rows=rows), vector_dimensions=384)  # type: ignore[arg-type]
    with pytest.raises(EmbeddingDimensionMismatchError) as excinfo:
        await mgr.validate_vector_index_dimensions(384)
    # All three names appear in the error message so users see the full scope.
    msg = str(excinfo.value)
    for name in (
        "message_embedding_idx",
        "entity_embedding_idx",
        "preference_embedding_idx",
    ):
        assert name in msg


async def test_validate_ignores_unmanaged_indexes():
    rows = [
        # An out-of-library vector index with a different size — must be skipped.
        {
            "name": "user_custom_idx",
            "options": {"indexConfig": {"vector.dimensions": 768}},
        },
    ]
    mgr = SchemaManager(_StubClient(rows=rows), vector_dimensions=1536)  # type: ignore[arg-type]
    # No mismatch should be raised because the unmanaged index is filtered.
    await mgr.validate_vector_index_dimensions(1536)


async def test_validate_silently_skips_when_show_query_unsupported():
    # ``SHOW VECTOR INDEXES`` does not exist on Neo4j < 5.11. The validator
    # must swallow the error and skip validation (rather than crashing the
    # connect() path).
    unsupported = RuntimeError("simulated syntax error")
    unsupported.code = "Neo.ClientError.Statement.SyntaxError"  # type: ignore[attr-defined]
    mgr = SchemaManager(_StubClient(error_on_read=unsupported), vector_dimensions=1536)  # type: ignore[arg-type]
    await mgr.validate_vector_index_dimensions(1536)


async def test_validate_reraises_unexpected_show_query_failures():
    mgr = SchemaManager(
        _StubClient(error_on_read=RuntimeError("simulated server error")),
        vector_dimensions=1536,
    )  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="simulated server error"):
        await mgr.validate_vector_index_dimensions(1536)
