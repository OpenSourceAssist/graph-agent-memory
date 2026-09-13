"""Offline regressions for the documentation's actual maintained programs.

No credentials, service writes, provider calls, or model downloads are used.
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import httpx
import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "docs/modules/ROOT/examples"


def load_fixture(name):
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


helpers = load_fixture("hosted_tutorial_helpers")
skills = load_fixture("skills_quickstart")
nams = load_fixture("nams_quickstart")


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, duration):
        self.now += duration


def test_skill_poll_waits_through_queued_and_running():
    states = iter(
        [
            {"status": "queued"},
            {"status": "running"},
            {"status": "completed", "outcome": "Created", "skillId": "returned-skill"},
        ]
    )
    seen = []

    async def fetch():
        state = next(states)
        seen.append(state)
        return state

    clock = Clock()
    result = asyncio.run(helpers.poll_skill_run(fetch, clock=clock, sleep=clock.sleep))
    assert result["skillId"] == "returned-skill"
    assert len(seen) == 3


@pytest.mark.parametrize("outcome", ["Withheld", "Failed"])
def test_skill_terminal_outcomes_do_not_require_a_skill(outcome):
    async def fetch():
        return {"outcome": outcome}

    assert asyncio.run(helpers.poll_skill_run(fetch))["outcome"] == outcome


@pytest.mark.parametrize(
    "state",
    [
        {"status": "completed"},
        {"status": "cancelled"},
        {"outcome": "Created"},
        {"outcome": "Unexpected", "status": "running"},
    ],
)
def test_skill_unknown_or_incomplete_terminal_response_is_not_success(state):
    async def fetch():
        return state

    with pytest.raises(RuntimeError):
        asyncio.run(helpers.poll_skill_run(fetch))


def test_skill_poll_timeout_is_finite_while_queued():
    clock = Clock()
    count = 0

    async def fetch():
        nonlocal count
        count += 1
        return {"status": "queued"}

    with pytest.raises(TimeoutError):
        asyncio.run(
            helpers.poll_skill_run(fetch, timeout=5, interval=2, clock=clock, sleep=clock.sleep)
        )
    assert count == 3
    assert clock.now == 5


class Ontology:
    def __init__(self, previous="previous-version", fail_restore=False):
        self.previous = previous
        self.active = previous
        self.calls = []
        self.fail_restore = fail_restore

    async def get_active(self):
        self.calls.append(("get_active", self.active))
        return SimpleNamespace(
            version_id=self.active,
            validation_mode="strict" if self.active == "strict-version" else "permissive",
        )

    async def clone(self, template):
        self.calls.append(("clone", template))
        return SimpleNamespace(ontology_id="new-clone", document="fixture-document")

    async def update(self, ontology_id, document, **kwargs):
        assert (ontology_id, document, kwargs) == (
            "new-clone",
            "fixture-document",
            {"validation_mode": "strict"},
        )
        self.calls.append(("update", ontology_id))
        return SimpleNamespace(id="strict-version")

    async def activate(self, version):
        self.calls.append(("activate", version))
        if self.fail_restore and version == self.previous:
            raise RuntimeError("restoration failed")
        self.active = version

    async def delete(self, ontology_id):
        self.calls.append(("delete", ontology_id))


def test_ontology_restores_then_verifies_before_delete_even_on_body_failure():
    ontology = Ontology()

    async def run():
        async with helpers.temporary_strict_ontology(ontology, "healthcare"):
            raise ValueError("exercise failed")

    with pytest.raises(ValueError, match="exercise failed"):
        asyncio.run(run())
    assert ontology.calls[-3:] == [
        ("activate", "previous-version"),
        ("get_active", "previous-version"),
        ("delete", "new-clone"),
    ]


def test_ontology_missing_prior_id_stops_before_clone():
    ontology = Ontology(previous=None)

    async def run():
        async with helpers.temporary_strict_ontology(ontology, "healthcare"):
            pytest.fail("must not enter the exercise")

    with pytest.raises(RuntimeError, match="No restorable"):
        asyncio.run(run())
    assert ontology.calls == [("get_active", None)]


def test_ontology_failed_restoration_keeps_clone():
    ontology = Ontology(fail_restore=True)

    async def run():
        async with helpers.temporary_strict_ontology(ontology, "healthcare"):
            pass

    with pytest.raises(RuntimeError, match="restoration failed"):
        asyncio.run(run())
    assert not any(call[0] == "delete" for call in ontology.calls)


class ShortTerm:
    def __init__(self):
        self.messages = []
        self.ids = []

    async def create_conversation(self, name):
        return SimpleNamespace(id="server-conversation-id")

    async def bulk_add_messages(self, conversation_id, transcript):
        self.ids.append(conversation_id)
        self.messages = [SimpleNamespace(content=row["content"]) for row in transcript]
        return self.messages

    async def get_conversation(self, conversation_id):
        self.ids.append(conversation_id)
        return SimpleNamespace(messages=self.messages)


class Reasoning:
    def __init__(self):
        self.steps = []
        self.sessions = []

    async def start_trace(self, session_id, task):
        self.sessions.append(session_id)
        return SimpleNamespace(id="returned-trace")

    async def add_step(self, trace_id, **kwargs):
        assert trace_id == "returned-trace"
        step = SimpleNamespace(id=f"returned-step-{len(self.steps)}", tool_calls=[])
        self.steps.append(step)
        return step

    async def record_tool_call(self, step_id, tool_name, arguments, result):
        assert step_id == self.steps[-1].id
        self.steps[-1].tool_calls.append(SimpleNamespace(tool_name=tool_name))

    async def complete_trace(self, trace_id, **kwargs):
        assert trace_id == "returned-trace"

    async def get_session_traces(self, conversation_id):
        self.sessions.append(conversation_id)
        return [SimpleNamespace(steps=self.steps)]


def test_hosted_exercise_reuses_server_ids_and_checks_reads():
    short_term, reasoning = ShortTerm(), Reasoning()
    seen = []

    async def wait(**kwargs):
        seen.append(kwargs)
        return True

    async def search(*args, **kwargs):
        return []  # An empty candidate set is not invented as entity provenance.

    client = SimpleNamespace(
        short_term=short_term,
        reasoning=reasoning,
        long_term=SimpleNamespace(wait_for_extraction=wait, search_entities=search),
    )
    assert asyncio.run(nams.exercise(client)) == "server-conversation-id"
    assert set(short_term.ids + reasoning.sessions) == {"server-conversation-id"}
    assert seen[0]["session_id"] == "server-conversation-id"
    assert seen[0]["timeout"] == 60.0


def test_hosted_extraction_timeout_stops_before_reasoning():
    async def wait(**kwargs):
        return False

    client = SimpleNamespace(
        short_term=ShortTerm(),
        reasoning=Reasoning(),
        long_term=SimpleNamespace(wait_for_extraction=wait),
    )
    with pytest.raises(TimeoutError):
        asyncio.run(nams.exercise(client))
    assert not client.reasoning.sessions


def test_skills_fixture_is_one_procedure_and_records_real_conversation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = SimpleNamespace(short_term=ShortTerm(), reasoning=Reasoning())
    asyncio.run(skills.seed(client, "https://service.invalid/v1"))
    state = json.loads(skills.STATE.read_text())
    assert state["seed_verified"] is True
    assert state["conversation_id"] == "server-conversation-id"
    assert len(client.reasoning.steps) == 9
    assert {call.tool_name for step in client.reasoning.steps for call in step.tool_calls} == {
        "lookup_order",
        "check_return_policy",
        "record_refund_decision",
    }


def test_skills_routes_preserve_v1_and_returned_ids(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    payload = io.BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("SKILL.md", "# Simulated procedure")

    def handle(request):
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/generate"):
            return httpx.Response(202, json={"runId": "actual-run", "status": "queued"})
        if path.endswith("/runs/actual-run"):
            return httpx.Response(200, json={"outcome": "Created", "skillId": "actual-skill"})
        if path.endswith("/download"):
            return httpx.Response(200, content=payload.getvalue())
        return httpx.Response(200, json={"fixture": True})

    async def run():
        state = {"seed_verified": True, "endpoint": "https://service.invalid/v1"}
        async with httpx.AsyncClient(
            base_url=state["endpoint"] + "/", transport=httpx.MockTransport(handle)
        ) as http:
            for command in ["generate", "inspect"]:
                await skills.run_command(http, command, state)
            assert not any(path.endswith("/publish") for _, path in calls)
            for command in ["publish", "download"]:
                await skills.run_command(http, command, state)
        return state

    state = asyncio.run(run())
    assert state["run_id"] == "actual-run"
    assert state["skill_id"] == "actual-skill"
    assert all(path.startswith("/v1/skills/") for _, path in calls)
    assert Path("simulated-refund-skill.zip").exists()


def test_skills_withheld_and_http_failure_do_not_publish(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []

    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={"outcome": "Withheld"})

    async def run():
        async with httpx.AsyncClient(
            base_url="https://service.invalid/v1/", transport=httpx.MockTransport(handle)
        ) as http:
            with pytest.raises(RuntimeError, match="No skill to publish"):
                await skills.run_command(http, "inspect", {"run_id": "returned-run"})
        async with httpx.AsyncClient(
            base_url="https://service.invalid/v1/",
            transport=httpx.MockTransport(lambda _request: httpx.Response(403)),
        ) as http:
            with pytest.raises(httpx.HTTPStatusError):
                await skills.run_command(http, "generate", {"seed_verified": True})

    asyncio.run(run())
    assert calls == ["/v1/skills/runs/returned-run"]


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.py")), ids=lambda path: path.name)
def test_complete_tutorial_programs_compile(path):
    compile(path.read_text(), str(path), "exec")


def load_lifecycle_example():
    path = EXAMPLES.parents[3] / "examples/ontology-lifecycle/main.py"
    spec = importlib.util.spec_from_file_location("docs_ontology_lifecycle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("status,errored", [("failed", 0), ("completed", 1)])
def test_failed_migration_stops_before_real_migration(status, errored):
    lifecycle = load_lifecycle_example()
    calls = []

    async def migrate(*args, **kwargs):
        calls.append(kwargs["dry_run"])
        return SimpleNamespace(
            id="returned-job",
            status=status,
            errored=errored,
            error_message="fixture failure",
            processed=0,
        )

    async def run():
        client = SimpleNamespace(ontology=SimpleNamespace(migrate=migrate))
        for dry_run in [True, False]:
            await lifecycle.run_migration(
                client,
                ontology_id="returned-ontology",
                from_version=SimpleNamespace(id="returned-v1"),
                to_version=SimpleNamespace(id="returned-v2"),
                dry_run=dry_run,
            )

    with pytest.raises(RuntimeError, match="returned-job"):
        asyncio.run(run())
    assert calls == [True]


def test_migration_deadline_stops_before_following_operation(monkeypatch):
    lifecycle = load_lifecycle_example()
    monkeypatch.setattr(lifecycle, "MIGRATION_TIMEOUT", 0)
    calls = []

    async def migrate(*args, **kwargs):
        calls.append(kwargs["dry_run"])
        return SimpleNamespace(id="queued-job", status="pending")

    async def run():
        client = SimpleNamespace(ontology=SimpleNamespace(migrate=migrate))
        for dry_run in [True, False]:
            await lifecycle.run_migration(
                client,
                ontology_id="returned-ontology",
                from_version=SimpleNamespace(id="returned-v1"),
                to_version=SimpleNamespace(id="returned-v2"),
                dry_run=dry_run,
            )

    with pytest.raises(TimeoutError, match="queued-job"):
        asyncio.run(run())
    assert calls == [True]


def test_tutorial_readback_method_exists_on_both_backends():
    from neo4j_agent_memory.memory.short_term import ShortTermMemory
    from neo4j_agent_memory.nams.short_term import NamsShortTermMemory

    assert callable(ShortTermMemory.get_conversation)
    assert callable(NamsShortTermMemory.get_conversation)
    for name in ["anthropic_local_memory", "nams_quickstart", "microsoft_shopping_tutorial"]:
        source = (EXAMPLES / f"{name}.py").read_text()
        assert ".get_messages(" not in source
