"""Bounded control flow shared by the hosted documentation exercises.

These helpers know only the documented run outcomes and SDK ontology methods.
They do not contact a service at import time.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any


async def poll_skill_run(
    fetch: Callable[[], Awaitable[dict[str, Any]]],
    *,
    timeout: float = 120.0,
    interval: float = 2.0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, Any]:
    """Wait through queued/running; return a documented outcome or fail closed."""
    if timeout <= 0 or interval <= 0:
        raise ValueError("timeout and interval must be positive")
    deadline = clock() + timeout
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("Skill run did not settle before the tutorial deadline")
        run = await asyncio.wait_for(fetch(), timeout=remaining)
        outcome = run.get("outcome")
        if outcome in {"Created", "Withheld", "Failed"}:
            if outcome == "Created" and not run.get("skillId"):
                raise RuntimeError("Created run is missing its returned skillId")
            return run
        if outcome is not None or run.get("status") not in {"queued", "running"}:
            raise RuntimeError(f"Unrecognized skill run state: {run!r}")
        await sleep(min(interval, max(0.0, deadline - clock())))


@asynccontextmanager
async def temporary_strict_ontology(ontology: Any, template: str):
    """Restore the captured active version before deleting this exercise's clone.

    Missing prior-version metadata stops before mutation. If restoration cannot
    be verified, the clone remains for inspection instead of being deleted.
    """
    previous = await ontology.get_active()
    previous_id = previous.version_id
    if not previous_id:
        raise RuntimeError("No restorable active version ID; no ontology was changed")
    print(f"Previous active version: {previous_id}")
    clone = await ontology.clone(template)
    print(f"Exercise clone: {clone.ontology_id}")
    try:
        strict = await ontology.update(clone.ontology_id, clone.document, validation_mode="strict")
        await ontology.activate(strict.id)
        active = await ontology.get_active()
        if active.version_id != strict.id or active.validation_mode != "strict":
            raise RuntimeError("Active ontology readback did not match the strict version")
        yield strict
    finally:
        await ontology.activate(previous_id)
        restored = await ontology.get_active()
        if restored.version_id != previous_id:
            raise RuntimeError(
                f"Restoration not verified; retained clone {clone.ontology_id} for inspection"
            )
        print(f"Restored active version: {previous_id}")
        await ontology.delete(clone.ontology_id)
        print(f"Deleted exercise clone: {clone.ontology_id}")
