"""Live-NAMS integration tests — error paths and NotSupported boundaries.

Verifies that the client correctly surfaces typed exceptions for the
HTTP error cases NAMS actually emits (404, 400, 401 on a bad call),
and that bolt-only features raise :class:`NotSupportedError` cleanly
when the active backend is NAMS.
"""

from __future__ import annotations

import pytest

from neo4j_agent_memory import MemoryClient
from neo4j_agent_memory.core.exceptions import NotSupportedError

pytestmark = pytest.mark.integration


# =============================================================================
# 404 / not-found behavior
# =============================================================================


@pytest.mark.asyncio
async def test_get_entity_by_name_unknown_returns_none(
    nams_client: MemoryClient, test_run_id: str
) -> None:
    """Unknown name returns ``None`` (404 mapped to None by the impl)."""
    missing = f"{test_run_id}-nonexistent-entity-zzz"
    result = await nams_client.long_term.get_entity_by_name(missing)
    assert result is None


@pytest.mark.asyncio
async def test_get_trace_unknown_returns_none(nams_client: MemoryClient) -> None:
    """Unknown trace id returns ``None`` (404 mapped to None)."""
    from uuid import uuid4

    result = await nams_client.reasoning.get_trace(str(uuid4()))
    assert result is None


@pytest.mark.asyncio
async def test_get_trace_with_steps_unknown_returns_none(
    nams_client: MemoryClient,
) -> None:
    """Unknown trace id returns ``None`` for ``get_trace_with_steps``."""
    from uuid import uuid4

    result = await nams_client.reasoning.get_trace_with_steps(str(uuid4()))
    assert result is None


# =============================================================================
# NotSupportedError boundaries on the NAMS-mode MemoryClient
# =============================================================================


@pytest.mark.asyncio
async def test_client_graph_raises_not_supported(nams_client: MemoryClient) -> None:
    """``client.graph`` raises :class:`NotSupportedError` on NAMS."""
    with pytest.raises(NotSupportedError) as exc_info:
        _ = nams_client.graph
    assert exc_info.value.backend == "nams"
    assert exc_info.value.method == "client.graph"
    assert "client.query.cypher" in (exc_info.value.workaround or "")


@pytest.mark.asyncio
async def test_client_users_method_call_raises_not_supported(
    nams_client: MemoryClient,
) -> None:
    """``client.users.upsert_user(...)`` raises via the ``_NamsUnsupported`` shim."""
    with pytest.raises(NotSupportedError) as exc_info:
        await nams_client.users.upsert_user(identifier="alice")
    assert exc_info.value.method == "users.upsert_user"
    assert exc_info.value.backend == "nams"


@pytest.mark.asyncio
async def test_client_buffered_method_call_raises_not_supported(
    nams_client: MemoryClient,
) -> None:
    """``client.buffered.submit(...)`` raises via the shim."""
    with pytest.raises(NotSupportedError):
        await nams_client.buffered.submit("CREATE (n:Test)")


@pytest.mark.asyncio
async def test_client_consolidation_method_call_raises_not_supported(
    nams_client: MemoryClient,
) -> None:
    """``client.consolidation.dedupe_entities()`` raises via the shim."""
    with pytest.raises(NotSupportedError):
        await nams_client.consolidation.dedupe_entities()


@pytest.mark.asyncio
async def test_client_schema_adopt_existing_graph_raises_not_supported(
    nams_client: MemoryClient,
) -> None:
    """``client.schema.adopt_existing_graph(...)`` raises via the schema shim."""
    with pytest.raises(NotSupportedError) as exc_info:
        await nams_client.schema.adopt_existing_graph()
    assert exc_info.value.method == "schema.adopt_existing_graph"


@pytest.mark.asyncio
async def test_get_stats_raises_not_supported(nams_client: MemoryClient) -> None:
    """Top-level ``client.get_stats()`` is bolt-only."""
    with pytest.raises(NotSupportedError) as exc_info:
        await nams_client.get_stats()
    assert exc_info.value.method == "get_stats"


@pytest.mark.asyncio
async def test_get_graph_raises_not_supported(nams_client: MemoryClient) -> None:
    """Top-level ``client.get_graph()`` is bolt-only."""
    with pytest.raises(NotSupportedError):
        await nams_client.get_graph()


@pytest.mark.asyncio
async def test_get_locations_raises_not_supported(nams_client: MemoryClient) -> None:
    """Top-level ``client.get_locations()`` is bolt-only."""
    with pytest.raises(NotSupportedError):
        await nams_client.get_locations()


# =============================================================================
# Write-Cypher rejection
# =============================================================================


@pytest.mark.asyncio
async def test_cypher_rejects_write_keywords(nams_client: MemoryClient) -> None:
    """``client.query.cypher`` rejects writes client-side with :class:`ValueError`."""
    for write_query in (
        "CREATE (n:X)",
        "MERGE (n:X)",
        "MATCH (n) DELETE n",
        "MATCH (n) SET n.x = 1",
        "MATCH (n) REMOVE n.x",
    ):
        with pytest.raises(ValueError, match="read-only"):
            await nams_client.query.cypher(write_query)


# =============================================================================
# Warn-and-ignore for client-side layers (smoke against live)
# =============================================================================


@pytest.mark.asyncio
async def test_warning_when_extraction_explicitly_configured(
    nams_credentials: tuple[str, str],
) -> None:
    """Setting ``extraction=`` explicitly with NAMS emits a single ``UserWarning``."""
    import warnings as _w

    from pydantic import SecretStr

    from neo4j_agent_memory import MemorySettings, NamsConfig
    from neo4j_agent_memory.config.settings import ExtractionConfig

    endpoint, api_key = nams_credentials
    settings = MemorySettings(
        backend="nams",
        nams=NamsConfig(
            endpoint=endpoint,
            api_key=SecretStr(api_key),
            validate_on_connect=False,
        ),
        extraction=ExtractionConfig(),  # explicit → in model_fields_set
    )

    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always", UserWarning)
        async with MemoryClient(settings):
            pass

    nams_warnings = [w for w in caught if "NAMS backend ignores" in str(w.message)]
    assert len(nams_warnings) == 1, f"Expected 1 warning, got {len(nams_warnings)}"
    assert "extraction" in str(nams_warnings[0].message)
