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


# Named environment presets. Select one with ``NAMS_ENV=<name>`` instead of
# memorizing a URL. An explicit ``NAMS_SANDBOX_URL`` / ``MEMORY_ENDPOINT``
# always wins over the preset.
_NAMS_ENV_PRESETS = {
    "staging": "https://nams.development.neo4jsandbox.com/v1",
    "development": "https://nams.development.neo4jsandbox.com/v1",  # alias of staging
    "sandbox": "https://memory.neo4jlabs.com/v1",
    "local": "http://localhost:8765",
}

# Default environment when neither NAMS_SANDBOX_URL nor NAMS_ENV is set.
_DEFAULT_NAMS_ENV = "staging"

# Default endpoint this suite targets. Override with NAMS_SANDBOX_URL /
# MEMORY_ENDPOINT (raw URL), or NAMS_ENV=<name> (named preset).
_DEFAULT_SANDBOX_URL = _NAMS_ENV_PRESETS[_DEFAULT_NAMS_ENV]


def _resolve_endpoint() -> str:
    """Resolve the NAMS endpoint URL with this precedence:

    1. Explicit raw URL — ``NAMS_SANDBOX_URL`` or ``MEMORY_ENDPOINT``.
    2. Named preset — ``NAMS_ENV`` mapped through ``_NAMS_ENV_PRESETS``
       (e.g. ``staging``, ``sandbox``, ``local``).
    3. The default preset (``staging``).

    An unrecognized ``NAMS_ENV`` value fails loudly rather than silently
    falling back, so a typo can't quietly target the wrong environment.
    """
    explicit = os.environ.get("NAMS_SANDBOX_URL") or os.environ.get("MEMORY_ENDPOINT")
    if explicit:
        return explicit
    env = os.environ.get("NAMS_ENV")
    if env:
        key = env.strip().lower()
        if key not in _NAMS_ENV_PRESETS:
            valid = ", ".join(sorted(_NAMS_ENV_PRESETS))
            pytest.fail(
                f"Unknown NAMS_ENV={env!r}. Valid presets: {valid}. "
                f"Or set NAMS_SANDBOX_URL to a raw endpoint URL.",
                pytrace=False,
            )
        return _NAMS_ENV_PRESETS[key]
    return _DEFAULT_SANDBOX_URL


def _resolve_credentials() -> tuple[str, str, str | None] | None:
    """Return (endpoint, api_key, workspace_id) if reachable, else None.

    Recognizes the integration-test env family
    ``NAMS_SANDBOX_URL`` / ``NAMS_SANDBOX_KEY`` / ``NAMS_SANDBOX_WORKSPACE_ID``
    and the user-facing aliases ``MEMORY_ENDPOINT`` / ``MEMORY_API_KEY`` /
    ``MEMORY_WORKSPACE_ID``. The endpoint can also be chosen by named
    preset via ``NAMS_ENV`` (see ``_resolve_endpoint``). The workspace is
    resolved into the ``X-Workspace-Id`` header by the client itself (no
    manual header injection in fixtures) — required by the header-scoped
    staging deployment.
    """
    key = os.environ.get("NAMS_SANDBOX_KEY") or os.environ.get("MEMORY_API_KEY")
    workspace = os.environ.get("NAMS_SANDBOX_WORKSPACE_ID") or os.environ.get("MEMORY_WORKSPACE_ID")
    if key:
        return _resolve_endpoint(), key, workspace
    if (url := os.environ.get("NAMS_TCK_URL")) and (
        key := os.environ.get("NAMS_TCK_KEY", "test-tck-key")
    ):
        # TCK reference implementation scopes by key, not header.
        return url, key, None
    return None


@pytest.fixture(scope="session")
def nams_credentials() -> tuple[str, str, str | None]:
    """Sandbox / TCK endpoint + key + workspace. Skips the module if unset."""
    creds = _resolve_credentials()
    if creds is None:
        pytest.skip(
            "No NAMS sandbox or TCK reachable. Set NAMS_SANDBOX_KEY (and "
            "optionally NAMS_SANDBOX_URL / NAMS_SANDBOX_WORKSPACE_ID), or the "
            "MEMORY_API_KEY / MEMORY_ENDPOINT / MEMORY_WORKSPACE_ID aliases, or "
            "NAMS_TCK_URL to enable these tests."
        )
    return creds


# -----------------------------------------------------------------------------
# Config + client
# -----------------------------------------------------------------------------


@pytest.fixture
def nams_config(nams_credentials: tuple[str, str, str | None]) -> NamsConfig:
    """Per-test NamsConfig pointing at the sandbox. ``validate_on_connect`` off
    so individual tests can opt into the probe (or skip it for write-only flows).

    The workspace is supplied as ``workspace_id`` — the client transmits it as
    ``X-Workspace-Id`` automatically. No manual header injection.
    """
    endpoint, api_key, workspace_id = nams_credentials
    return NamsConfig(
        endpoint=endpoint,
        api_key=SecretStr(api_key),
        workspace_id=workspace_id,
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


@pytest_asyncio.fixture
async def nams_session(
    nams_client: MemoryClient,
    session_id: str,
    cleanup_registry: _CleanupRegistry,
) -> str:
    """A pre-created NAMS conversation. Yields the canonical conversation id.

    NAMS (unlike bolt) does **not** auto-create conversations on the
    first ``add_message`` — see ``test_smoke.py`` for the discovery.
    This fixture handles the Platinum-tier ``create_conversation`` dance
    so individual tests don't repeat it.

    Behavior:

    * Tries ``create_conversation(session_id)``. If the SPEC method
      isn't available or 4xx-rejects, falls back to the raw
      ``session_id`` — the test will then either succeed (server
      auto-creates on POST) or surface the failure as a normal
      assertion.
    * Returns whatever id NAMS expects for subsequent calls — preferring
      the returned ``conv.id`` (UUID) over the original session_id
      string, since NAMS may generate its own canonical id.
    * Registers the canonical id with ``cleanup_registry``.

    Use this fixture in tests that need to round-trip messages through
    NAMS. Tests that don't need a pre-existing conversation (e.g.
    entity-only or fact-only tests) can keep using the bare
    ``session_id`` fixture.
    """
    canonical_id = session_id
    try:
        conv = await nams_client.short_term.create_conversation(
            session_id,
            user_identifier=session_id,
            title="Integration test conversation",
        )
        # NAMS may return a Conversation with a generated UUID *or* echo
        # the supplied session_id. Prefer whatever id field looks
        # canonical, fall back to session_id.
        if conv.id is not None:
            canonical_id = str(conv.id)
        elif conv.session_id:
            canonical_id = conv.session_id
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "create_conversation failed (%s); using bare session_id and "
            "hoping for auto-create. If the test then 404s on read, NAMS "
            "needs an explicit conversation creation step.",
            e,
        )

    cleanup_registry.track_session(canonical_id)
    # Also track the original session_id in case NAMS dual-keyed it.
    if canonical_id != session_id:
        cleanup_registry.track_session(session_id)
    return canonical_id
