"""Live-NAMS integration tests — authentication and connection lifecycle.

Verifies that the auth path behaves correctly against the real hosted
service: a valid API key succeeds, a bad key raises
:class:`AuthenticationError`, and ``validate_on_connect=True`` performs
the fail-fast probe.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings, NamsConfig
from neo4j_agent_memory.core.exceptions import AuthenticationError

pytestmark = pytest.mark.integration


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_key_connects_and_probes(nams_config: NamsConfig) -> None:
    """A valid API key successfully connects with validate_on_connect=True."""
    settings = MemorySettings(
        backend="nams",
        nams=nams_config.model_copy(update={"validate_on_connect": True}),
    )
    async with MemoryClient(settings) as client:
        assert client.is_connected
        # The probe ran during __aenter__; reaching here means it succeeded.


@pytest.mark.asyncio
async def test_client_can_close_and_reopen(nams_config: NamsConfig) -> None:
    """A client's HTTP transport can be opened, closed, and re-opened."""
    settings = MemorySettings(backend="nams", nams=nams_config)
    client = MemoryClient(settings)

    await client.connect()
    assert client.is_connected
    await client.close()
    assert not client.is_connected

    await client.connect()
    assert client.is_connected
    await client.close()


# -----------------------------------------------------------------------------
# Auth failures
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_key_raises_authentication_error(nams_config: NamsConfig) -> None:
    """A bogus API key surfaces as :class:`AuthenticationError` on probe."""
    bad_config = nams_config.model_copy(
        update={
            "api_key": SecretStr("nams_obviously_invalid_for_tests_xyz"),
            "validate_on_connect": True,
        }
    )
    settings = MemorySettings(backend="nams", nams=bad_config)
    client = MemoryClient(settings)
    with pytest.raises(AuthenticationError):
        await client.connect()
    # Even on failure the transport may have been opened — clean up.
    await client.close()


def test_empty_api_key_rejected_at_construction(nams_config: NamsConfig) -> None:
    """An empty API key is rejected by :class:`StaticApiKeyAuth` at startup."""
    from neo4j_agent_memory.nams.auth import StaticApiKeyAuth

    empty_config = NamsConfig(endpoint=nams_config.endpoint, api_key=None)
    with pytest.raises(AuthenticationError):
        StaticApiKeyAuth.from_config(empty_config)


# -----------------------------------------------------------------------------
# Probe behavior
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_on_connect_false_skips_probe(nams_config: NamsConfig) -> None:
    """When ``validate_on_connect=False``, ``connect()`` does not block on a request."""
    # We can't easily assert "no probe happened" against a live server,
    # but we can assert that ``connect()`` succeeds even with a config
    # where the probe *would* fail if it ran. This test takes a key
    # we know is bad — connect should still succeed when probe is off.
    bad_config = nams_config.model_copy(
        update={
            "api_key": SecretStr("nams_invalid_skipped_probe"),
            "validate_on_connect": False,
        }
    )
    settings = MemorySettings(backend="nams", nams=bad_config)
    async with MemoryClient(settings) as client:
        assert client.is_connected
        # The first real request will fail with AuthenticationError, but
        # that's a different boundary — covered in test_errors.py.
