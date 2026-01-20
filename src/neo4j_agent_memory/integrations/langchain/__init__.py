"""LangChain integration for neo4j-agent-memory."""

from neo4j_agent_memory.integrations.langchain.memory import Neo4jAgentMemory

try:
    from neo4j_agent_memory.integrations.langchain.retriever import Neo4jMemoryRetriever

    __all__ = [
        "Neo4jAgentMemory",
        "Neo4jMemoryRetriever",
    ]
except ImportError:
    # langchain_core not installed for retriever
    __all__ = [
        "Neo4jAgentMemory",
    ]
