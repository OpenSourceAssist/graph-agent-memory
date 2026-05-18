"""Phase 5 tests: MemoryClient wired to the NAMS backend.

Covers:

* End-to-end ``async with MemoryClient(settings) as client:`` against
  respx-mocked NAMS.
* Accessor dispatch — ``client.short_term`` etc. resolve to NAMS impls.
* ``client.query.cypher(...)`` works.
* ``client.graph`` raises NotSupportedError on NAMS.
* ``client.users`` / ``buffered`` / ``consolidation`` return shims that
  raise NotSupportedError on method call.
* ``client.schema.adopt_existing_graph()`` raises NotSupportedError.
* ``client.get_stats`` / ``get_graph`` / ``get_locations`` raise
  NotSupportedError.
* Warn-and-ignore log emitted for inactive client-side layers.
* Auth probe runs on connect when ``validate_on_connect=True``.
* ``client.graph.execute_read`` on bolt emits a one-time
  DeprecationWarning.
"""

from __future__ import annotations

import warnings

import pytest
import respx
from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, NamsConfig
from neo4j_agent_memory.core.exceptions import (
    AuthenticationError,
    NotConnectedError,
    NotSupportedError,
)
from neo4j_agent_memory.core.protocols import (
    CypherQueryProtocol,
    LongTermProtocol,
    ReasoningProtocol,
    ShortTermProtocol,
)
from neo4j_agent_memory.nams import NamsShortTermMemory

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Strip MEMORY_* env so the backend resolver doesn't flip backends."""
    for key in list(__import__("os").environ.keys()):
        if key.startswith(("MEMORY_", "NAM_")):
            monkeypatch.delenv(key, raising=False)
    yield


def _make_nams_settings(*, validate_on_connect: bool = False) -> MemorySettings:
    return MemorySettings(
        backend="nams",
        nams=NamsConfig(
            endpoint="https://memory.test/v1",
            api_key=SecretStr("nams_test_key"),
            validate_on_connect=validate_on_connect,
            max_retries=0,
            retry_backoff_seconds=0.01,
        ),
    )


# -----------------------------------------------------------------------------
# Lifecycle + accessor dispatch
# -----------------------------------------------------------------------------


class TestLifecycle:
    @respx.mock
    async def test_context_manager_opens_and_closes(self):
        async with MemoryClient(_make_nams_settings()) as client:
            assert client.is_connected
        assert not client.is_connected

    @respx.mock
    async def test_validate_on_connect_runs_probe(self):
        route = respx.get("https://memory.test/v1/conversations").respond(200, json=[])
        async with MemoryClient(_make_nams_settings(validate_on_connect=True)):
            pass
        assert route.called
        assert route.calls[0].request.url.params["limit"] == "1"

    @respx.mock
    async def test_probe_failure_propagates_at_connect_time(self):
        respx.get("https://memory.test/v1/conversations").respond(
            401, json={"error": "invalid key"}
        )
        client = MemoryClient(_make_nams_settings(validate_on_connect=True))
        with pytest.raises(AuthenticationError):
            await client.connect()


class TestAccessorDispatch:
    """All polymorphic accessors resolve to NAMS implementations."""

    @respx.mock
    async def test_short_term_is_nams_impl(self):
        async with MemoryClient(_make_nams_settings()) as client:
            assert isinstance(client.short_term, NamsShortTermMemory)
            assert isinstance(client.short_term, ShortTermProtocol)

    @respx.mock
    async def test_long_term_satisfies_protocol(self):
        async with MemoryClient(_make_nams_settings()) as client:
            assert isinstance(client.long_term, LongTermProtocol)

    @respx.mock
    async def test_reasoning_satisfies_protocol(self):
        async with MemoryClient(_make_nams_settings()) as client:
            assert isinstance(client.reasoning, ReasoningProtocol)

    @respx.mock
    async def test_query_satisfies_protocol(self):
        async with MemoryClient(_make_nams_settings()) as client:
            assert isinstance(client.query, CypherQueryProtocol)

    @respx.mock
    async def test_end_to_end_add_message(self):
        """Full flow: connect, add_message via NAMS, parse response."""
        respx.post("https://memory.test/v1/conversations/s1/messages").respond(
            200,
            json={
                "id": "00000000-0000-0000-0000-000000000001",
                "role": "user",
                "content": "hi",
                "created_at": "2026-05-17T12:00:00Z",
                "metadata": {},
            },
        )
        async with MemoryClient(_make_nams_settings()) as client:
            msg = await client.short_term.add_message("s1", "user", "hi")
        assert msg.content == "hi"

    @respx.mock
    async def test_end_to_end_query_cypher(self):
        respx.post("https://memory.test/v1/query").respond(200, json=[{"n": 1}])
        async with MemoryClient(_make_nams_settings()) as client:
            rows = await client.query.cypher("MATCH (n) RETURN n LIMIT 1")
        assert rows == [{"n": 1}]


class TestNotConnectedGuards:
    async def test_short_term_raises_before_connect(self):
        client = MemoryClient(_make_nams_settings())
        with pytest.raises(NotConnectedError):
            _ = client.short_term

    async def test_query_raises_before_connect(self):
        client = MemoryClient(_make_nams_settings())
        with pytest.raises(NotConnectedError):
            _ = client.query

    @respx.mock
    async def test_short_term_raises_after_close(self):
        client = MemoryClient(_make_nams_settings())
        await client.connect()
        await client.close()
        with pytest.raises(NotConnectedError):
            _ = client.short_term


# -----------------------------------------------------------------------------
# Unsupported accessors on NAMS
# -----------------------------------------------------------------------------


class TestUnsupportedAccessors:
    @respx.mock
    async def test_graph_raises_not_supported(self):
        async with MemoryClient(_make_nams_settings()) as client:
            with pytest.raises(NotSupportedError) as exc_info:
                _ = client.graph
            assert exc_info.value.backend == "nams"
            assert exc_info.value.method == "client.graph"
            assert "client.query.cypher" in (exc_info.value.workaround or "")

    @respx.mock
    async def test_users_method_call_raises(self):
        async with MemoryClient(_make_nams_settings()) as client:
            # Property access returns shim (no raise yet).
            shim = client.users
            assert shim is not None
            # Method call raises.
            with pytest.raises(NotSupportedError) as exc_info:
                await shim.upsert_user(identifier="alice")
            assert exc_info.value.method == "users.upsert_user"

    @respx.mock
    async def test_buffered_method_call_raises(self):
        async with MemoryClient(_make_nams_settings()) as client:
            with pytest.raises(NotSupportedError) as exc_info:
                await client.buffered.submit("CREATE (n:Test)")
            assert exc_info.value.method == "buffered.submit"

    @respx.mock
    async def test_consolidation_method_call_raises(self):
        async with MemoryClient(_make_nams_settings()) as client:
            with pytest.raises(NotSupportedError):
                await client.consolidation.dedupe_entities()

    @respx.mock
    async def test_schema_method_call_raises(self):
        async with MemoryClient(_make_nams_settings()) as client:
            with pytest.raises(NotSupportedError) as exc_info:
                await client.schema.adopt_existing_graph()
            assert exc_info.value.method == "schema.adopt_existing_graph"


class TestUnsupportedTopLevelMethods:
    @respx.mock
    async def test_get_stats_raises(self):
        async with MemoryClient(_make_nams_settings()) as client:
            with pytest.raises(NotSupportedError) as exc_info:
                await client.get_stats()
            assert exc_info.value.method == "get_stats"
            assert "client.query.cypher" in (exc_info.value.workaround or "")

    @respx.mock
    async def test_get_graph_raises(self):
        async with MemoryClient(_make_nams_settings()) as client:
            with pytest.raises(NotSupportedError):
                await client.get_graph()

    @respx.mock
    async def test_get_locations_raises(self):
        async with MemoryClient(_make_nams_settings()) as client:
            with pytest.raises(NotSupportedError):
                await client.get_locations()


# -----------------------------------------------------------------------------
# Warn-and-ignore behavior for client-side layers
# -----------------------------------------------------------------------------


class TestWarnAndIgnore:
    @respx.mock
    async def test_no_warning_with_default_layers(self):
        """Default `embedding`/`extraction` configs are implicit — no warning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UserWarning)
            async with MemoryClient(_make_nams_settings()):
                pass
        nams_warnings = [w for w in caught if "NAMS backend ignores" in str(w.message)]
        assert nams_warnings == []

    @respx.mock
    async def test_warning_emitted_when_extraction_explicit(self):
        from neo4j_agent_memory.config.settings import ExtractionConfig

        settings = MemorySettings(
            backend="nams",
            nams=NamsConfig(
                endpoint="https://memory.test/v1",
                api_key=SecretStr("k"),
                validate_on_connect=False,
            ),
            extraction=ExtractionConfig(),  # explicit → in model_fields_set
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UserWarning)
            async with MemoryClient(settings):
                pass
        nams_warnings = [w for w in caught if "NAMS backend ignores" in str(w.message)]
        assert len(nams_warnings) == 1
        assert "extraction" in str(nams_warnings[0].message)

    @respx.mock
    async def test_warning_emitted_when_geocoding_enabled(self):
        from neo4j_agent_memory.config.settings import GeocodingConfig

        settings = MemorySettings(
            backend="nams",
            nams=NamsConfig(
                endpoint="https://memory.test/v1",
                api_key=SecretStr("k"),
                validate_on_connect=False,
            ),
            geocoding=GeocodingConfig(enabled=True),
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UserWarning)
            async with MemoryClient(settings):
                pass
        msgs = [str(w.message) for w in caught if "NAMS backend ignores" in str(w.message)]
        assert len(msgs) == 1
        assert "geocoding" in msgs[0]


# -----------------------------------------------------------------------------
# Bolt-path DeprecationWarning for client.graph.execute_read
# -----------------------------------------------------------------------------


class TestBoltGraphDeprecation:
    """The bolt-path proxy emits a one-time DeprecationWarning for execute_read.

    These tests don't need real Neo4j — we just construct a MemoryClient,
    wire ``_client`` to a stub, and exercise the proxy.
    """

    async def test_execute_read_emits_deprecation_warning(self):
        from unittest.mock import AsyncMock, MagicMock

        # Build a bolt-mode MemoryClient and inject a stub Neo4jClient.
        client = MemoryClient(MemorySettings(backend="bolt"))
        stub = MagicMock()
        stub.execute_read = AsyncMock(return_value=[{"n": 1}])
        client._client = stub  # bypass connect() for unit-test surgery

        # Reset the one-time guard so this test is deterministic in
        # whatever order it runs.
        from neo4j_agent_memory import _DeprecatedGraphProxy

        _DeprecatedGraphProxy._execute_read_warned = False

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            result = await client.graph.execute_read("MATCH (n) RETURN n")

        assert result == [{"n": 1}]
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 1
        assert "client.query.cypher" in str(dep_warnings[0].message)

    async def test_execute_read_warning_only_fires_once(self):
        from unittest.mock import AsyncMock, MagicMock

        client = MemoryClient(MemorySettings(backend="bolt"))
        stub = MagicMock()
        stub.execute_read = AsyncMock(return_value=[])
        client._client = stub

        from neo4j_agent_memory import _DeprecatedGraphProxy

        _DeprecatedGraphProxy._execute_read_warned = False

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            await client.graph.execute_read("MATCH (n) RETURN n")
            await client.graph.execute_read("MATCH (m) RETURN m")
            await client.graph.execute_read("MATCH (x) RETURN x")

        # Three calls, one warning.
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) == 1

    async def test_other_attrs_delegate_without_warning(self):
        """execute_write, vector_search, etc. pass through transparently."""
        from unittest.mock import AsyncMock, MagicMock

        client = MemoryClient(MemorySettings(backend="bolt"))
        stub = MagicMock()
        stub.execute_write = AsyncMock(return_value=[{"created": 1}])
        client._client = stub

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            result = await client.graph.execute_write("CREATE (n:X)")

        assert result == [{"created": 1}]
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        # No deprecation on execute_write.
        assert dep_warnings == []


# -----------------------------------------------------------------------------
# Bolt is unchanged
# -----------------------------------------------------------------------------


class TestBoltBackendUnchanged:
    """Spot-check that the bolt construction path is not broken by the refactor.

    These tests can't actually open a Neo4j connection, but they verify
    construction and accessor wiring choices.
    """

    def test_bolt_default_construction(self):
        client = MemoryClient(MemorySettings(backend="bolt"))
        # Pre-connect: all polymorphic accessors are None.
        assert client._short_term is None
        assert client._long_term is None
        assert client._query is None
        assert client._nams_backend is None

    def test_default_backend_is_bolt(self):
        # No MEMORY_API_KEY env, no explicit backend → bolt.
        client = MemoryClient()
        assert client._settings.backend == "bolt"
