"""Tests for nams/_serialization.py — JSON ↔ Pydantic conversions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import BaseModel

from neo4j_agent_memory.nams._serialization import (
    json_safe,
    model_to_payload,
    parse_datetime,
    parse_uuid,
    payload_to_model,
)


class TestJsonSafe:
    def test_primitives_pass_through(self):
        assert json_safe("hello") == "hello"
        assert json_safe(42) == 42
        assert json_safe(3.14) == 3.14
        assert json_safe(True) is True
        assert json_safe(None) is None

    def test_uuid_coerced_to_string(self):
        uid = UUID("12345678-1234-5678-1234-567812345678")
        assert json_safe(uid) == "12345678-1234-5678-1234-567812345678"

    def test_aware_datetime_isoformatted(self):
        dt = datetime(2026, 5, 17, 12, 30, 0, tzinfo=timezone.utc)
        assert json_safe(dt) == "2026-05-17T12:30:00+00:00"

    def test_naive_datetime_treated_as_utc(self):
        dt = datetime(2026, 5, 17, 12, 30, 0)
        assert json_safe(dt) == "2026-05-17T12:30:00+00:00"

    def test_nested_dict(self):
        uid = UUID(int=1)
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        out = json_safe({"id": uid, "when": dt, "name": "x"})
        assert out["id"] == str(uid)
        assert out["when"] == "2026-01-01T00:00:00+00:00"
        assert out["name"] == "x"

    def test_list(self):
        uid = UUID(int=2)
        assert json_safe([uid, "x", 1]) == [str(uid), "x", 1]

    def test_tuple_becomes_list(self):
        assert json_safe((1, 2, 3)) == [1, 2, 3]


class _SampleModel(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    optional: str | None = None


class TestModelToPayload:
    def test_basic_dump(self):
        m = _SampleModel(
            id=UUID(int=42),
            name="alice",
            created_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
        )
        payload = model_to_payload(m)
        assert payload["id"] == "00000000-0000-0000-0000-00000000002a"
        assert payload["name"] == "alice"
        assert payload["created_at"] == "2026-05-17T00:00:00Z"
        # exclude_none default drops the optional field
        assert "optional" not in payload

    def test_keep_nones_when_exclude_none_false(self):
        m = _SampleModel(
            id=UUID(int=1),
            name="bob",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        payload = model_to_payload(m, exclude_none=False)
        assert "optional" in payload
        assert payload["optional"] is None

    def test_exclude_specific_field(self):
        m = _SampleModel(
            id=UUID(int=1),
            name="bob",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        payload = model_to_payload(m, exclude={"created_at"})
        assert "created_at" not in payload
        assert "name" in payload


class TestPayloadToModel:
    def test_round_trip(self):
        original = _SampleModel(
            id=UUID(int=99),
            name="charlie",
            created_at=datetime(2026, 5, 17, 10, 0, tzinfo=timezone.utc),
        )
        payload = model_to_payload(original)
        roundtripped = payload_to_model(payload, _SampleModel)
        assert roundtripped == original

    def test_string_uuid_coerced(self):
        payload = {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": "x",
            "created_at": "2026-01-01T00:00:00Z",
        }
        m = payload_to_model(payload, _SampleModel)
        assert m.id == UUID(int=1)


class TestParseDatetime:
    def test_z_suffix(self):
        dt = parse_datetime("2026-05-17T12:00:00Z")
        assert dt == datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)

    def test_offset_suffix(self):
        dt = parse_datetime("2026-05-17T12:00:00+00:00")
        assert dt == datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)

    def test_passthrough_existing_datetime(self):
        existing = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert parse_datetime(existing) is existing


class TestParseUuid:
    def test_string(self):
        assert parse_uuid("00000000-0000-0000-0000-000000000007") == UUID(int=7)

    def test_passthrough(self):
        uid = UUID(int=11)
        assert parse_uuid(uid) is uid

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_uuid("not-a-uuid")
