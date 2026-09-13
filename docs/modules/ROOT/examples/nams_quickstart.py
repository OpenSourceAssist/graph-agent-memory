"""Current-checkout NAMS exercise: persist and read back a conversation and trace."""

from __future__ import annotations

import asyncio
from uuid import uuid4


async def exercise(client):
    # NAMS creates the conversation ID; a display name is not its identifier.
    conversation = await client.short_term.create_conversation(f"docs-nams-{uuid4().hex[:8]}")
    conversation_id = str(conversation.id)
    print(f"Conversation ID: {conversation_id}")
    transcript = [
        {"role": "user", "content": "Maya Chen is preparing a robotics workshop in Denver."},
        {"role": "assistant", "content": "The workshop checklist includes testing the sensor."},
    ]
    stored = await client.short_term.bulk_add_messages(conversation_id, transcript)
    if len(stored) != len(transcript):
        raise RuntimeError("Message write did not return both records")
    history = (await client.short_term.get_conversation(conversation_id)).messages
    if not all(item["content"] in [m.content for m in history] for item in transcript):
        raise RuntimeError("Stored messages were missing from readback")
    print("Verified: both messages were read back")

    settled = await client.long_term.wait_for_extraction(
        session_id=conversation_id, timeout=60.0, interval=1.0
    )
    if not settled:
        raise TimeoutError(f"Extraction still pending for conversation {conversation_id}")
    entities = await client.long_term.search_entities("robotics workshop Denver", limit=5)
    print(f"Extraction settled; workspace search returned {len(entities)} candidate(s)")
    # Search is workspace-scoped; these are not asserted to originate in this run.
    for entity in entities:
        print(f"  {entity.display_name} ({entity.full_type})")

    trace = await client.reasoning.start_trace(
        session_id=conversation_id, task="Record the workshop checklist example"
    )
    step = await client.reasoning.add_step(
        trace.id, action="Check the sensor", observation="Simulated check passed"
    )
    await client.reasoning.record_tool_call(
        step.id,
        tool_name="fixture_sensor_check",
        arguments={"sensor": "workshop-sensor"},
        result={"simulated": True, "passed": True},
    )
    await client.reasoning.complete_trace(trace.id, outcome="Fixture recorded", success=True)
    traces = await client.reasoning.get_session_traces(conversation_id)
    steps = [step for trace in traces for step in trace.steps]
    if not any(
        call.tool_name == "fixture_sensor_check" for step in steps for call in step.tool_calls
    ):
        raise RuntimeError("Recorded tool call was missing from readback")
    print("Verified: the simulated tool call was read back")
    print(f"Retained tutorial conversation: {conversation_id}")
    return conversation_id


async def main():
    from neo4j_agent_memory import NamsSettings, connect

    client = await connect(NamsSettings())
    try:
        await exercise(client)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
