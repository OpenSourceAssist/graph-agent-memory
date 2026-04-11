"""Tool implementations for the Financial Services Advisor agents.

All tools accept neo4j_service as a keyword-only argument for Neo4j access.
The bind_tool() utility hides this parameter from the Strands Agent's
tool signature so the LLM only sees user-facing parameters.
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable


def bind_tool(func: Callable, neo4j_service: Any) -> Callable:
    """Bind a neo4j_service instance to a tool function, hiding it from the agent.

    Strands @tool inspects function signatures to determine LLM-visible parameters.
    This wrapper removes neo4j_service from the visible signature while still
    passing it during execution.
    """
    sig = inspect.signature(func)
    new_params = [
        p for name, p in sig.parameters.items() if name != "neo4j_service"
    ]

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        kwargs["neo4j_service"] = neo4j_service
        return await func(*args, **kwargs)

    wrapper.__signature__ = sig.replace(parameters=new_params)  # type: ignore[attr-defined]
    return wrapper
