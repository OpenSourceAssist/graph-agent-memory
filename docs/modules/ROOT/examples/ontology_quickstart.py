"""Current-checkout NAMS exercise with restoration before clone deletion."""

from __future__ import annotations

import asyncio

from hosted_tutorial_helpers import temporary_strict_ontology


async def exercise(client):
    from neo4j_agent_memory.core.exceptions import ValidationError

    async with temporary_strict_ontology(client.ontology, "healthcare") as strict:
        labels = [item.label for item in strict.document.entity_types]
        print(f"Strict schema entity labels: {', '.join(labels)}")
        invalid_type = "DocsTutorialUnknownType"
        if invalid_type in labels:
            raise RuntimeError("Fixture type unexpectedly exists in the selected schema")
        try:
            entity = await client.long_term.add_entity(
                "Ontology tutorial invalid fixture", entity_type=invalid_type
            )
        except ValidationError:
            print("Verified: strict validation rejected the unknown type")
        else:
            # A service that accepts the write must not be described as verified.
            raise RuntimeError(
                f"Strict rejection was not observed; inspect unexpected entity {entity.id}"
            )


async def main():
    from neo4j_agent_memory import NamsSettings, connect

    client = await connect(NamsSettings())
    try:
        await exercise(client)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
