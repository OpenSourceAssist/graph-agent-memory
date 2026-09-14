"""Activate and inspect a strict revision, then restore the exact prior binding."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from hosted_tutorial_helpers import (
    recover_ontology,
    temporary_strict_ontology,
    verify_ontology_restoration,
)
from hosted_tutorial_state import TutorialState


async def exercise(client, state):
    async with temporary_strict_ontology(client.ontology, "healthcare", state) as strict:
        labels = [item.label for item in strict.document.entity_types]
        print(f"Strict schema entity labels: {', '.join(labels)}")
        print("Verified: exact active revision, strict mode, and schema readback")


async def main(argv=None):
    from neo4j_agent_memory import NamsSettings, connect

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["seed", "inspect", "verify", "recover", "cleanup"])
    parser.add_argument("--state", type=Path, default=Path(".tutorial-state/ontology.json"))
    args = parser.parse_args(argv)
    settings = NamsSettings()
    state = (
        TutorialState.create(args.state, settings, "ontology")
        if args.command == "seed"
        else TutorialState.load(args.state, settings, "ontology")
    )
    if args.command == "inspect":
        print(json.dumps(state.inspect(), indent=2))
        return
    client = await connect(settings)
    try:
        if args.command == "seed":
            await exercise(client, state)
        elif args.command == "verify":
            await verify_ontology_restoration(client.ontology, state)
        else:
            await recover_ontology(client.ontology, state)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
