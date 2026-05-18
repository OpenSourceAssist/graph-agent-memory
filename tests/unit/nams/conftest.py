"""Shared fixtures for NAMS unit tests.

Keeps ``respx`` (HTTP-mocking) and ``httpx`` dependencies scoped to the
NAMS test directory — root :file:`tests/conftest.py` stays untouched so
non-NAMS contributors don't need these extras.
"""

from __future__ import annotations

import pytest
import respx
from pydantic import SecretStr

from neo4j_agent_memory.config.settings import NamsConfig
from neo4j_agent_memory.nams import StaticApiKeyAuth

# Test endpoints
REST_ENDPOINT = "https://memory.test/v1"
BRIDGE_ENDPOINT = "https://memory.test"


@pytest.fixture
def nams_config() -> NamsConfig:
    """Default NamsConfig pointing at the REST test endpoint."""
    return NamsConfig(
        endpoint=REST_ENDPOINT,
        api_key=SecretStr("nams_test_key"),
        validate_on_connect=False,
        # Shrink retry waits so tests stay fast even when retries trigger.
        max_retries=2,
        retry_backoff_seconds=0.01,
    )


@pytest.fixture
def bridge_config() -> NamsConfig:
    """NamsConfig pointing at a bridge-protocol endpoint."""
    return NamsConfig(
        endpoint=BRIDGE_ENDPOINT,
        api_key=SecretStr("nams_test_key"),
        validate_on_connect=False,
        max_retries=2,
        retry_backoff_seconds=0.01,
    )


@pytest.fixture
def auth(nams_config: NamsConfig) -> StaticApiKeyAuth:
    """Auth provider built from ``nams_config``."""
    return StaticApiKeyAuth.from_config(nams_config)


@pytest.fixture
def respx_mock():
    """Shorthand for ``respx.mock(...)``; yields the router for in-test setup."""
    with respx.mock(assert_all_called=False) as router:
        yield router
