"""Concrete adapter implementations for the Provider Protocol.

Each adapter file in this package imports its underlying SDK only when
imported. The package's :mod:`__init__` deliberately does *not* re-export
any adapter classes — this preserves the property that bare
``import neo4j_agent_memory.llm.adapters`` works in the core install.

To use an adapter, import it explicitly::

    from neo4j_agent_memory.llm.adapters.openai import OpenAIProvider
    from neo4j_agent_memory.llm.adapters.anthropic import AnthropicProvider
    from neo4j_agent_memory.llm.adapters.litellm import LiteLLMProvider

Or, more commonly, use the factory::

    from neo4j_agent_memory.llm import from_provider
    llm = from_provider("anthropic/claude-3-5-sonnet-latest")
"""
