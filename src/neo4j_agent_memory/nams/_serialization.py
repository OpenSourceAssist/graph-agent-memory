"""JSON ↔ Pydantic conversion helpers for the NAMS transport.

NAMS speaks JSON over HTTP; this package uses Pydantic models throughout
(``Message``, ``Entity``, ``ReasoningTrace``, ...). Pydantic v2 already
handles the bulk of the work via ``model_dump(mode="json")`` and
``model_validate(...)`` — this module adds the conventions that NAMS
expects on top:

* :class:`UUID` → string
* :class:`datetime` → ISO 8601 string
* ``None`` fields are dropped from outgoing payloads (server defaults
  win unless the client explicitly opted in)

Phase 3 memory implementations will use these helpers when constructing
request bodies and parsing responses. The functions are deliberately
small and stateless — no global registries of types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

if TYPE_CHECKING:
    from pydantic import BaseModel

M = TypeVar("M", bound="BaseModel")


def json_safe(value: Any) -> Any:
    """Recursively coerce a value to a JSON-encodable shape.

    Handles UUID and datetime; passes other primitives through unchanged.
    Lists and dicts are recursed. Pydantic models are not handled here —
    use :func:`model_to_payload` for those.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        # Normalize naive datetimes to UTC; emit ISO 8601 with timezone.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    # Last resort — let json.dumps decide whether to error.
    return value


def model_to_payload(
    model: BaseModel,
    *,
    exclude_none: bool = True,
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """Serialize a Pydantic model to a JSON-safe dict.

    Uses Pydantic's ``model_dump(mode="json", ...)`` which handles UUID,
    datetime, and ``SecretStr`` coercion automatically. Drops ``None``
    fields by default — NAMS treats absent fields as "use server
    default" rather than "explicitly null".

    Pass ``exclude={"embedding"}`` (or similar) to strip bolt-only
    fields that the server would reject or recompute.
    """
    return model.model_dump(
        mode="json",
        exclude_none=exclude_none,
        exclude=exclude,
    )


def payload_to_model(payload: dict[str, Any], model_cls: type[M]) -> M:
    """Parse a JSON-decoded dict into a Pydantic model instance.

    Pydantic handles UUID and datetime coercion automatically for fields
    typed as such. Validation errors propagate as
    :class:`pydantic.ValidationError`.
    """
    return model_cls.model_validate(payload)


def parse_datetime(value: str | datetime) -> datetime:
    """Parse an ISO 8601 string (or pass through an existing datetime).

    NAMS may return timestamps in a few shapes (``Z`` suffix, ``+00:00``,
    naive). :meth:`datetime.fromisoformat` handles all of these on
    Python 3.11+; for safety we normalize ``Z`` → ``+00:00`` manually.
    """
    if isinstance(value, datetime):
        return value
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def parse_uuid(value: str | UUID) -> UUID:
    """Parse a UUID string (or pass through an existing UUID)."""
    if isinstance(value, UUID):
        return value
    return UUID(value)


__all__ = [
    "json_safe",
    "model_to_payload",
    "payload_to_model",
    "parse_datetime",
    "parse_uuid",
]
