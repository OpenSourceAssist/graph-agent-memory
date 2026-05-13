"""Backward compatibility guard for the v0.3 settings refactor.

These tests verify that v0.2.x user code keeps working after the
``MemorySettings.embedding`` / ``MemorySettings.llm`` union refactor.
Failure here means we have broken a documented quickstart pattern and
must reconsider before release.
"""

from __future__ import annotations

import warnings

import pytest
from pydantic import SecretStr

from neo4j_agent_memory import MemorySettings
from neo4j_agent_memory.config.settings import (
    EmbeddingConfig,
    EmbeddingProvider,
    LLMConfig,
    LLMProvider,
)


def _password() -> SecretStr:
    return SecretStr("test-password")


# ---------------------------------------------------------------------------
# Defaults: no warning, no error, types unchanged
# ---------------------------------------------------------------------------


def test_default_settings_emit_no_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        settings = MemorySettings(neo4j={"password": _password()})
        # The implicit defaults (default_factory=EmbeddingConfig and default=None)
        # are not user-explicit choices, so no warning must fire.
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deprecations == [], [str(w.message) for w in deprecations]
    # Default embedding is still EmbeddingConfig — backward compat preserved.
    assert isinstance(settings.embedding, EmbeddingConfig)
    # Default extraction enables LLM fallback, so the lenient fallback in
    # _validate_llm_consistency materializes an LLMConfig.
    assert isinstance(settings.llm, LLMConfig)


# ---------------------------------------------------------------------------
# Legacy explicit configs: exactly one DeprecationWarning per field used
# ---------------------------------------------------------------------------


def test_legacy_embedding_config_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        MemorySettings(
            neo4j={"password": _password()},
            embedding=EmbeddingConfig(provider=EmbeddingProvider.OPENAI),
        )
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    # One warning for embedding; llm was not user-set so it does not warn.
    assert len(deprecations) == 1
    assert "EmbeddingConfig" in str(deprecations[0].message)


def test_legacy_llm_config_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        MemorySettings(
            neo4j={"password": _password()},
            llm=LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o-mini"),
        )
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    assert "LLMConfig" in str(deprecations[0].message)


def test_both_legacy_configs_emit_two_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        MemorySettings(
            neo4j={"password": _password()},
            embedding=EmbeddingConfig(),
            llm=LLMConfig(),
        )
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    # One per explicitly-set field.
    assert len(deprecations) == 2


# ---------------------------------------------------------------------------
# String shorthand: resolves to a provider, no warning, validator passes
# ---------------------------------------------------------------------------


def test_embedding_string_shorthand_resolves_via_factory(monkeypatch):
    """Provider string is handed to :func:`from_provider`.

    We monkeypatch the factory to avoid requiring the openai package to
    be installed in the unit-test env.
    """
    import neo4j_agent_memory.llm as llm_pkg

    captured: dict[str, object] = {}

    class StubEmbedder:
        model = "openai/text-embedding-3-small"
        dimensions = 1536

        async def embed(self, texts):  # pragma: no cover - not invoked
            return [[0.0] * self.dimensions for _ in texts]

        async def embed_one(self, text):  # pragma: no cover - not invoked
            return [0.0] * self.dimensions

    def fake_from_provider(model, *, kind="llm", **kwargs):
        captured["model"] = model
        captured["kind"] = kind
        return StubEmbedder()

    monkeypatch.setattr(llm_pkg, "from_provider", fake_from_provider)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        settings = MemorySettings(
            neo4j={"password": _password()},
            embedding="openai/text-embedding-3-small",
        )
    assert captured == {"model": "openai/text-embedding-3-small", "kind": "embedding"}
    # No deprecation for the string shorthand path.
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations == []
    # And the field resolved to the provider instance.
    assert isinstance(settings.embedding, StubEmbedder)


def test_llm_string_shorthand_resolves_via_factory(monkeypatch):
    import neo4j_agent_memory.llm as llm_pkg

    captured: dict[str, object] = {}

    class StubLLM:
        model = "anthropic/claude-3-5-sonnet-latest"

        async def complete(self, messages, **kwargs):  # pragma: no cover
            raise NotImplementedError

    def fake_from_provider(model, *, kind="llm", **kwargs):
        captured["model"] = model
        captured["kind"] = kind
        return StubLLM()

    monkeypatch.setattr(llm_pkg, "from_provider", fake_from_provider)

    settings = MemorySettings(
        neo4j={"password": _password()},
        llm="anthropic/claude-3-5-sonnet-latest",
    )
    assert captured == {"model": "anthropic/claude-3-5-sonnet-latest", "kind": "llm"}
    assert isinstance(settings.llm, StubLLM)


# ---------------------------------------------------------------------------
# Type guard: garbage input fails with a clear TypeError
# ---------------------------------------------------------------------------


def test_garbage_embedding_value_raises_type_error():
    with pytest.raises(Exception) as excinfo:
        MemorySettings(neo4j={"password": _password()}, embedding=42)
    # Pydantic wraps the TypeError from the model validator in a
    # ValidationError; either is acceptable as long as it surfaces.
    assert "embedding" in str(excinfo.value).lower() or "int" in str(excinfo.value)


def test_garbage_llm_value_raises_type_error():
    with pytest.raises(Exception) as excinfo:
        MemorySettings(neo4j={"password": _password()}, llm=42)
    assert "llm" in str(excinfo.value).lower() or "int" in str(excinfo.value)


# ---------------------------------------------------------------------------
# extra="forbid" still rejects typos
# ---------------------------------------------------------------------------


def test_typo_in_field_name_still_raises():
    # Sanity check that the field-type loosening did not weaken the
    # ``extra="forbid"`` typo guard.
    with pytest.raises(Exception):
        MemorySettings(neo4j={"password": _password()}, schema={})  # type: ignore[call-arg]
