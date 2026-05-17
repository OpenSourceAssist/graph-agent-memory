"""Tests for nams/auth.py — StaticApiKeyAuth + AuthProvider Protocol."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from neo4j_agent_memory.config.settings import NamsConfig
from neo4j_agent_memory.core.exceptions import AuthenticationError
from neo4j_agent_memory.nams import AuthProvider, StaticApiKeyAuth


class TestStaticApiKeyAuth:
    async def test_apply_adds_bearer_header(self):
        auth = StaticApiKeyAuth("nams_secret")
        headers = await auth.apply({})
        assert headers["Authorization"] == "Bearer nams_secret"

    async def test_apply_preserves_existing_headers(self):
        auth = StaticApiKeyAuth("nams_secret")
        headers = await auth.apply({"User-Agent": "test/1.0"})
        assert headers["User-Agent"] == "test/1.0"
        assert headers["Authorization"] == "Bearer nams_secret"

    async def test_apply_overwrites_existing_auth_header(self):
        auth = StaticApiKeyAuth("new_key")
        headers = await auth.apply({"Authorization": "Bearer old_key"})
        assert headers["Authorization"] == "Bearer new_key"

    def test_empty_key_rejected(self):
        with pytest.raises(AuthenticationError, match="Empty API key"):
            StaticApiKeyAuth("")

    def test_repr_does_not_leak_key(self):
        auth = StaticApiKeyAuth("super_secret_nams_key")
        assert "super_secret" not in repr(auth)
        assert "***" in repr(auth)


class TestFromConfig:
    def test_from_config_with_key(self):
        config = NamsConfig(api_key=SecretStr("nams_test"))
        auth = StaticApiKeyAuth.from_config(config)
        # Verify by applying — the key is private otherwise.
        import asyncio

        headers = asyncio.run(auth.apply({}))
        assert headers["Authorization"] == "Bearer nams_test"

    def test_from_config_without_key_raises(self):
        config = NamsConfig()  # api_key defaults to None
        with pytest.raises(AuthenticationError, match="API key"):
            StaticApiKeyAuth.from_config(config)


class TestProtocolConformance:
    """StaticApiKeyAuth structurally implements AuthProvider."""

    def test_is_auth_provider(self):
        auth = StaticApiKeyAuth("k")
        assert isinstance(auth, AuthProvider)
