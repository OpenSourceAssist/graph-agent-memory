"""Google ADK Agents for Financial Services Advisor."""

import inspect
from functools import wraps

from .aml_agent import create_aml_agent
from .compliance_agent import create_compliance_agent
from .kyc_agent import create_kyc_agent
from .relationship_agent import create_relationship_agent
from .supervisor import create_supervisor_agent, get_supervisor_agent

__all__ = [
    "bind_tool",
    "create_supervisor_agent",
    "get_supervisor_agent",
    "create_kyc_agent",
    "create_aml_agent",
    "create_relationship_agent",
    "create_compliance_agent",
]


def bind_tool(func, neo4j_service):
    """Create a wrapper that binds neo4j_service to a tool function.

    ADK FunctionTool inspects the function signature to determine which
    parameters the LLM should provide. We create a wrapper with a
    modified signature that hides neo4j_service entirely.
    """
    sig = inspect.signature(func)
    new_params = [p for name, p in sig.parameters.items() if name != "neo4j_service"]

    @wraps(func)
    async def wrapper(*args, **kwargs):
        kwargs["neo4j_service"] = neo4j_service
        return await func(*args, **kwargs)

    wrapper.__signature__ = sig.replace(parameters=new_params)
    return wrapper
