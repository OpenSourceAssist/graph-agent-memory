"""Shared fixtures for NAMS integration / conformance tests.

These tests are env-gated — they skip cleanly when neither
``NAMS_SANDBOX_KEY`` (real sandbox) nor a local TCK reference impl
are reachable. See ``tests/integration/nams/README.md`` for setup.
"""

from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from neo4j_agent_memory.config.settings import NamsConfig


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


@pytest.fixture
def nams_config(nams_credentials: tuple[str, str]) -> NamsConfig:
    endpoint, api_key = nams_credentials
    return NamsConfig(
        endpoint=endpoint,
        api_key=SecretStr(api_key),
        validate_on_connect=False,  # tests probe explicitly
        max_retries=2,
        retry_backoff_seconds=0.5,
    )
