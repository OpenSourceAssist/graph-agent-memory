"""Tests for nams/endpoints.py — wire-protocol detection and URL builders."""

from __future__ import annotations

import pytest

from neo4j_agent_memory.nams import EndpointSpec, build_url, detect_protocol, expand_path


class TestDetectProtocol:
    def test_hosted_url_is_rest(self):
        assert detect_protocol("https://memory.neo4jlabs.com/v1") == "rest"

    def test_v2_is_rest(self):
        assert detect_protocol("https://api.example.com/v2") == "rest"

    def test_v10_is_rest(self):
        assert detect_protocol("https://example.com/v10") == "rest"

    def test_v1_with_trailing_slash_is_rest(self):
        assert detect_protocol("https://memory.test/v1/") == "rest"

    def test_localhost_no_version_is_bridge(self):
        assert detect_protocol("http://localhost:8000") == "bridge"

    def test_version_word_is_bridge(self):
        # ``/version`` ≠ ``/v<N>``
        assert detect_protocol("https://example.com/version") == "bridge"

    def test_v_without_digit_is_bridge(self):
        assert detect_protocol("https://example.com/v/") == "bridge"

    def test_explicit_rest_override(self):
        # Bridge-shaped URL forced to REST.
        assert detect_protocol("http://localhost:8000", "rest") == "rest"

    def test_explicit_bridge_override(self):
        # REST-shaped URL forced to bridge.
        assert detect_protocol("https://memory.neo4jlabs.com/v1", "bridge") == "bridge"


class TestBuildUrl:
    def test_rest_url(self):
        url = build_url(
            "https://memory.test/v1",
            rest_path="/conversations/abc/messages",
            bridge_method="add_message",
            protocol="rest",
        )
        assert url == "https://memory.test/v1/conversations/abc/messages"

    def test_rest_strips_trailing_slash_on_endpoint(self):
        url = build_url(
            "https://memory.test/v1/",
            rest_path="/messages",
            bridge_method="add_message",
            protocol="rest",
        )
        assert url == "https://memory.test/v1/messages"

    def test_bridge_url(self):
        url = build_url(
            "https://memory.test",
            rest_path=None,
            bridge_method="add_message",
            protocol="bridge",
        )
        assert url == "https://memory.test/add_message"

    def test_bridge_strips_trailing_slash(self):
        url = build_url(
            "https://memory.test/",
            rest_path=None,
            bridge_method="add_message",
            protocol="bridge",
        )
        assert url == "https://memory.test/add_message"

    def test_rest_requires_path(self):
        with pytest.raises(ValueError, match="REST protocol selected but no rest_path"):
            build_url(
                "https://memory.test/v1",
                rest_path=None,
                bridge_method="add_message",
                protocol="rest",
            )

    def test_rest_path_must_start_with_slash(self):
        with pytest.raises(ValueError, match="rest_path must begin with"):
            build_url(
                "https://memory.test/v1",
                rest_path="conversations",  # missing leading /
                bridge_method="add_message",
                protocol="rest",
            )

    def test_bridge_method_no_slashes(self):
        with pytest.raises(ValueError, match="bridge_method must not contain"):
            build_url(
                "https://memory.test",
                rest_path=None,
                bridge_method="add/message",
                protocol="bridge",
            )


class TestExpandPath:
    def test_substitution(self):
        assert expand_path(
            "/conversations/{session_id}/messages", session_id="abc"
        ) == "/conversations/abc/messages"

    def test_multiple_placeholders(self):
        assert expand_path(
            "/traces/{trace_id}/messages/{msg_id}",
            trace_id="t1",
            msg_id="m2",
        ) == "/traces/t1/messages/m2"

    def test_no_placeholders_passes_through(self):
        assert expand_path("/conversations") == "/conversations"

    def test_extra_params_ignored(self):
        # ``str.format`` ignores extras as long as required keys are present.
        assert expand_path(
            "/x/{id}", id="1", unused="oops"
        ) == "/x/1"

    def test_missing_placeholder_raises(self):
        with pytest.raises(KeyError):
            expand_path("/x/{id}")


class TestEndpointSpec:
    """``EndpointSpec.resolve`` is the workhorse used by Phase 3 memory impls."""

    spec = EndpointSpec(
        rest_method="POST",
        rest_path="/conversations/{session_id}/messages",
        bridge_method="add_message",
    )

    def test_rest_resolution(self):
        method, url = self.spec.resolve(
            "https://memory.test/v1",
            "rest",
            {"session_id": "abc"},
        )
        assert method == "POST"
        assert url == "https://memory.test/v1/conversations/abc/messages"

    def test_bridge_resolution_always_post(self):
        method, url = self.spec.resolve(
            "https://memory.test",
            "bridge",
            {"session_id": "abc"},  # ignored in bridge mode
        )
        assert method == "POST"
        assert url == "https://memory.test/add_message"

    def test_get_method_preserved_in_rest(self):
        spec = EndpointSpec(
            rest_method="GET",
            rest_path="/sessions",
            bridge_method="list_sessions",
        )
        method, url = spec.resolve("https://memory.test/v1", "rest")
        assert method == "GET"
        assert url == "https://memory.test/v1/sessions"

    def test_bridge_only_spec_in_rest_raises(self):
        bridge_only = EndpointSpec(
            rest_method="POST",  # ignored
            rest_path=None,
            bridge_method="some_legacy_method",
        )
        with pytest.raises(ValueError, match="bridge-only"):
            bridge_only.resolve("https://memory.test/v1", "rest")
