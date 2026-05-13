"""LlamaIndex integration for neo4j-agent-memory."""

from typing import Any

from neo4j_agent_memory.integrations._passthrough import (
    llm_provider_from_framework_model as _passthrough,
)


def llm_provider_from_llamaindex(model: Any) -> Any:
    """Translate a LlamaIndex ``LLM`` into an :class:`LLMProvider`.

    LlamaIndex LLM classes expose ``model``; class names like
    ``OpenAI`` (in ``llama_index.llms.openai``) and ``Anthropic`` (in
    ``llama_index.llms.anthropic``) drive provider detection.
    """
    return _passthrough(model)


try:
    from neo4j_agent_memory.integrations.llamaindex.memory import Neo4jLlamaIndexMemory

    __all__ = [
        "Neo4jLlamaIndexMemory",
        "llm_provider_from_llamaindex",
    ]
except ImportError:
    __all__ = ["llm_provider_from_llamaindex"]
