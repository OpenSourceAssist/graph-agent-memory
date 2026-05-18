"""Shared fixtures for NAMS integration / conformance tests.

These tests exercise the **live hosted NAMS service** (or a TCK reference
implementation). They skip cleanly when neither is reachable — see
``tests/integration/nams/README.md`` for setup.

Test isolation strategy
=======================

The hosted sandbox is a shared, stateful environment. Every test:

* Uses a UUID-suffixed ``session_id`` so it never collides with another
  test's data.
* Uses UUID-suffixed entity / preference / fact names where applicable.
* Registers any session_id / entity_id it creates with the
  ``cleanup_registry`` fixture, which best-effort tears down on
  fixture finalization.

Resilience to spec drift
========================

Several endpoint shapes in ``src/neo4j_agent_memory/nams/*.py`` are
marked ``TODO(nams-spec)`` — they were inferred from REST conventions
and have not been verified against a live NAMS server. When a test
fails on the first live run, the failure mode is usually one of:

* 404 — wrong path. Check the ``TODO(nams-spec)`` marker for the
  Protocol method, fix the ``rest_path`` in ``EndpointSpec``, retry.
* 400 — wrong request body shape. Inspect the response details and
  align the request builder in the relevant ``Nams*Memory`` method.
* `KeyError` / `ValidationError` on response parsing — NAMS returned
  a different field name or wrapper shape than expected.

These are *expected* findings; the integration suite exists to surface
them. Don't panic on the first red CI run.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, NamsConfig

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Credentials + skip gate
# -----------------------------------------------------------------------------


def _resolve_endpoint_and_key() -> tuple[str, str] | None:
    """Return (endpoint, api_key) if a sandbox or TCK is reachable, else None."""
    if (key := os.environ.get("NAMS_SANDBOX_KEY")) and (
        url := os.environ.get("NAMS_SANDBOX_URL", "https://memory.neo4jlabs.com/v1")
    ):
        return url, key
    if (url := os.environ.get("NAMS_TCK_URL")) and (
        key := os.environ.get("NAMS_TCK_KEY", "test-tck-key")
    ):
        return url, key
    return None


@pytest.fixture(scope="session")
def nams_credentials() -> tuple[str, str]:
    """Sandbox / TCK endpoint + key. Skips the whole module if unset."""
    creds = _resolve_endpoint_and_key()
    if creds is None:
        pytest.skip(
            "No NAMS sandbox or TCK reachable. Set NAMS_SANDBOX_KEY (and "
            "optionally NAMS_SANDBOX_URL) or NAMS_TCK_URL to enable these tests."
        )
    return creds


# -----------------------------------------------------------------------------
# Config + client
# -----------------------------------------------------------------------------


@pytest.fixture
def nams_config(nams_credentials: tuple[str, str]) -> NamsConfig:
    """Per-test NamsConfig pointing at the sandbox. ``validate_on_connect`` off
    so individual tests can opt into the probe (or skip it for write-only flows)."""
    endpoint, api_key = nams_credentials
    return NamsConfig(
        endpoint=endpoint,
        api_key=SecretStr(api_key),
        validate_on_connect=False,
        max_retries=2,
        retry_backoff_seconds=0.5,
        timeout=20.0,
    )


@pytest_asyncio.fixture
async def nams_client(nams_config: NamsConfig) -> AsyncIterator[MemoryClient]:
    """Connected NAMS-backed MemoryClient. Closes on test exit."""
    settings = MemorySettings(backend="nams", nams=nams_config)
    async with MemoryClient(settings) as client:
        yield client


# -----------------------------------------------------------------------------
# Per-test unique IDs
# -----------------------------------------------------------------------------


@pytest.fixture
def test_run_id() -> str:
    """A short UUID prefix unique to this test invocation.

    Use to namespace session_ids, entity names, preference categories,
    etc. so concurrent CI runs don't trample each other in the shared
    sandbox.
    """
    return f"itest-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def session_id(test_run_id: str) -> str:
    """A unique session_id for this test."""
    return f"{test_run_id}-session"


@pytest.fixture
def unique_name(test_run_id: str) -> str:
    """Helper: returns a fresh unique name on each call.

    Usage::

        def test_x(unique_name):
            entity1 = unique_name()  # itest-abc-1
            entity2 = unique_name()  # itest-abc-2
    """
    counter = {"n": 0}

    def _make(prefix: str = "entity") -> str:
        counter["n"] += 1
        return f"{test_run_id}-{prefix}-{counter['n']}"

    return _make  # type: ignore[return-value]


# -----------------------------------------------------------------------------
# Cleanup registry — best-effort teardown
# -----------------------------------------------------------------------------


class _CleanupRegistry:
    """Tracks resources created during a test for best-effort cleanup.

    Failure during cleanup is logged but does not fail the test — the
    point is to limit sandbox pollution, not to assert on teardown
    behavior.
    """

    def __init__(self, client: MemoryClient) -> None:
        self._client = client
        self._sessions: set[str] = set()

    def track_session(self, session_id: str) -> None:
        """Register a session for ``clear_session()`` on teardown."""
        self._sessions.add(session_id)

    async def run(self) -> None:
        for sid in self._sessions:
            try:
                await self._client.short_term.clear_session(sid)
            except Exception as e:  # noqa: BLE001 — best-effort teardown
                logger.debug("Cleanup of session %s failed: %s", sid, e)


@pytest_asyncio.fixture
async def cleanup_registry(nams_client: MemoryClient) -> AsyncIterator[_CleanupRegistry]:
    """Cleanup registry — yields, then best-effort teardown on test exit."""
    reg = _CleanupRegistry(nams_client)
    try:
        yield reg
    finally:
        await reg.run()
