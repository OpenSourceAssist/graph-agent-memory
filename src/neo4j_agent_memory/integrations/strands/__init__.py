"""Strands Agents SDK integration for neo4j-agent-memory.

This module provides tools for integrating Neo4j Agent Memory with AWS
Strands Agents SDK, enabling agents to use Context Graphs for semantic
memory and knowledge graph operations.

Example:
    from strands import Agent
    from neo4j_agent_memory.integrations.strands import context_graph_tools

    tools = context_graph_tools(
        neo4j_uri=os.environ["NEO4J_URI"],
        neo4j_password=os.environ["NEO4J_PASSWORD"],
        embedding_provider="bedrock",
    )

    agent = Agent(
        model="anthropic.claude-sonnet-4-20250514-v1:0",
        tools=tools,
    )

    response = agent("What do you know about our project?")
"""

try:
    from neo4j_agent_memory.integrations.strands.config import (
        BEDROCK_EMBEDDING_MODELS,
        BEDROCK_LLM_MODELS,
        StrandsConfig,
    )
    from neo4j_agent_memory.integrations.strands.tools import (
        clear_client_cache,
        context_graph_tools,
    )

    __all__ = [
        "context_graph_tools",
        "clear_client_cache",
        "StrandsConfig",
        "BEDROCK_EMBEDDING_MODELS",
        "BEDROCK_LLM_MODELS",
    ]
except ImportError:
    # strands-agents not installed
    __all__ = []
