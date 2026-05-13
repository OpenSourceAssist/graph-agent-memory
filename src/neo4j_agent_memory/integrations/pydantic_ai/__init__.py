"""Pydantic AI integration for neo4j-agent-memory."""

from typing import Any

from neo4j_agent_memory.integrations._passthrough import (
    llm_provider_from_framework_model as _passthrough,
)


def llm_provider_from_pydantic_ai(model: Any) -> Any:
    """Translate a Pydantic AI ``Model`` into an :class:`LLMProvider`.

    Pydantic AI Models expose ``model_name``; class names like
    ``OpenAIModel`` / ``AnthropicModel`` provide the provider prefix::

        from pydantic_ai.models.anthropic import AnthropicModel
        from neo4j_agent_memory.integrations.pydantic_ai import (
            llm_provider_from_pydantic_ai,
        )

        model = AnthropicModel("claude-3-5-sonnet-latest")
        provider = llm_provider_from_pydantic_ai(model)
    """
    return _passthrough(model)


try:
    from neo4j_agent_memory.integrations.pydantic_ai.memory import (
        MemoryDependency,
        create_memory_tools,
        record_agent_trace,
    )

    __all__ = [
        "MemoryDependency",
        "create_memory_tools",
        "record_agent_trace",
        "llm_provider_from_pydantic_ai",
    ]
except ImportError:
    __all__ = ["llm_provider_from_pydantic_ai"]
