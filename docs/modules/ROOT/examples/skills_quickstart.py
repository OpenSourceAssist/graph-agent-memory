"""Current-checkout skills exercise; commands separate review from publication.

The fixture records a simulated, repeatable procedure. It performs no refunds.
The service can withhold a skill; that result is not a successful download.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from hosted_tutorial_helpers import poll_skill_run

STATE = Path("skills-tutorial-state.json")


def save(state):
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def read_state(endpoint):
    state = json.loads(STATE.read_text())
    if state["endpoint"] != endpoint:
        raise RuntimeError("Endpoint differs from the workspace used to seed this exercise")
    return state


async def seed(client, endpoint):
    if STATE.exists():
        raise RuntimeError("State file already exists; inspect the prior exercise before rerunning")
    conversation = await client.short_term.create_conversation(f"docs-skill-{uuid4().hex[:8]}")
    conversation_id = str(conversation.id)
    state = {"endpoint": endpoint, "conversation_id": conversation_id}
    save(state)  # Keep the returned ID even if a later fixture write fails.
    await client.short_term.bulk_add_messages(
        conversation_id,
        [
            {
                "role": "user",
                "content": "Fixture procedure: look up the order, check the return policy, record a refund decision. All orders and actions below are simulated.",
            },
            {
                "role": "assistant",
                "content": "Each fixture uses a delivered order, a confirmed damaged item, and a return window of 30 days. Record the decision without issuing a payment.",
            },
        ],
    )
    for order in ("FIXTURE-104", "FIXTURE-105", "FIXTURE-106"):
        trace = await client.reasoning.start_trace(
            session_id=conversation_id, task=f"Simulated refund decision for {order}"
        )
        for tool, arguments, result in [
            ("lookup_order", {"order_id": order}, {"delivered": True, "days_since_delivery": 4}),
            (
                "check_return_policy",
                {"damage_confirmed": True, "return_window_days": 30},
                {"eligible": True},
            ),
            (
                "record_refund_decision",
                {"order_id": order},
                {"decision": "approve", "payment_issued": False},
            ),
        ]:
            step = await client.reasoning.add_step(
                trace.id, action=tool, observation=json.dumps(result)
            )
            await client.reasoning.record_tool_call(
                step.id,
                tool_name=tool,
                arguments=arguments,
                result={**result, "simulated": True},
            )
        await client.reasoning.complete_trace(
            trace.id, outcome="Simulated decision recorded", success=True
        )
    traces = await client.reasoning.get_session_traces(conversation_id)
    steps = [step for trace in traces for step in trace.steps]
    if len(steps) < 9:
        raise RuntimeError("Expected nine recorded fixture steps in server readback")
    state["seed_verified"] = True
    save(state)
    print(f"Verified fixture: conversation {conversation_id}; {len(steps)} recorded steps")


async def request_json(http, method, route, **kwargs):
    response = await http.request(method, route, **kwargs)
    response.raise_for_status()
    return response.json()


async def run_command(http, command, state):
    if command == "generate":
        if not state.get("seed_verified"):
            raise RuntimeError("Run seed successfully before generating")
        if state.get("run_id"):
            raise RuntimeError("A run already exists; use inspect instead of generating another")
        run = await request_json(
            http,
            "POST",
            "skills/generate",
            json={"name": "simulated-refund-decision", "scope": {"type": "workspace"}},
        )
        run_id = run.get("runId")
        if not run_id:
            raise RuntimeError("Generation response is missing runId")
        state["run_id"] = run_id
        save(state)
        print(f"Saved run ID: {run_id}; run inspect next")
        return
    if command == "inspect":
        run_id = state["run_id"]

        async def fetch():
            return await request_json(http, "GET", f"skills/runs/{run_id}")

        run = await poll_skill_run(fetch)
        state["run"] = run
        save(state)
        if run["outcome"] != "Created":
            raise RuntimeError(f"No skill to publish: {json.dumps(run)}")
        state["skill_id"] = run["skillId"]
        save(state)
        detail = await request_json(http, "GET", f"skills/{state['skill_id']}")
        provenance = await request_json(
            http, "GET", f"skills/{state['skill_id']}/explain-provenance"
        )
        Path("skills-tutorial-review.json").write_text(
            json.dumps({"skill": detail, "provenance": provenance}, indent=2)
        )
        print("Inspect skills-tutorial-review.json before running publish")
        return
    skill_id = state["skill_id"]
    if command == "publish":
        # The reader invokes this command only after inspecting the saved review.
        response = await http.post(f"skills/{skill_id}/review", json={"decision": "approve"})
        response.raise_for_status()
        response = await http.post(f"skills/{skill_id}/publish")
        response.raise_for_status()
        state["published"] = True
        save(state)
        print(f"Published skill ID: {skill_id}")
    elif command == "download":
        if not state.get("published"):
            raise RuntimeError("Publish the reviewed skill first")
        verification = await request_json(http, "GET", f"skills/{skill_id}/verify")
        Path("skills-tutorial-attestation.json").write_text(json.dumps(verification, indent=2))
        response = await http.get(f"skills/{skill_id}/download")
        response.raise_for_status()
        with ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
            if not any(Path(name).name == "SKILL.md" for name in names):
                raise RuntimeError("Downloaded archive has no SKILL.md")
        Path("simulated-refund-skill.zip").write_bytes(response.content)
        print("Verified ZIP contains SKILL.md; saved simulated-refund-skill.zip")
        print(
            "Inspect skills-tutorial-attestation.json; ZIP validation does not verify its signature"
        )


async def main():
    import httpx

    from neo4j_agent_memory import NamsSettings, connect

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed", "generate", "inspect", "publish", "download"])
    command = parser.parse_args().command
    settings = NamsSettings()
    endpoint = str(settings.nams.endpoint).rstrip("/")
    if command == "seed":
        client = await connect(settings)
        try:
            await seed(client, endpoint)
        finally:
            await client.close()
        return
    state = read_state(endpoint)
    headers = {"Authorization": f"Bearer {os.environ['MEMORY_API_KEY']}"}
    async with httpx.AsyncClient(base_url=endpoint + "/", headers=headers, timeout=30.0) as http:
        await run_command(http, command, state)


if __name__ == "__main__":
    asyncio.run(main())
