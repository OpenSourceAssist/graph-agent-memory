"""Known embedding model dimensions.

Neo4j vector indexes are sized at creation time, and dimension mismatches
between the configured embedder and an existing index produce runtime
errors on first insert. To avoid that, every
:class:`~neo4j_agent_memory.llm.protocol.EmbeddingProvider` has a required
``dimensions`` field. To minimize the friction this creates, this module
provides a lookup of known model strings to their dimensions, so adapters
can auto-populate ``dimensions`` when the user passes a recognized model.

When a model is not in this table the user must pass an explicit
``dimensions=N`` parameter to the adapter constructor. Adapters raise
``ValueError`` with a clear message in that case (silent dimension
mismatches are very hard to debug).

The keys here use the same string format as the
:func:`~neo4j_agent_memory.llm.factory.from_provider` factory:
``"<provider>/<model>"`` for cloud providers, or just ``"<org>/<model>"``
for HuggingFace-style sentence-transformers IDs.
"""

from __future__ import annotations

EMBEDDING_DIMENSIONS: dict[str, int] = {
    # ---- OpenAI ----
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002": 1536,
    # ---- Cohere (via LiteLLM, or direct via [cohere]) ----
    "cohere/embed-english-v3.0": 1024,
    "cohere/embed-english-light-v3.0": 384,
    "cohere/embed-multilingual-v3.0": 1024,
    "cohere/embed-multilingual-light-v3.0": 384,
    # ---- Voyage AI (via LiteLLM) ----
    "voyage/voyage-3": 1024,
    "voyage/voyage-3-lite": 512,
    "voyage/voyage-large-2": 1536,
    "voyage/voyage-code-2": 1536,
    # ---- Google Vertex AI ----
    "vertex_ai/textembedding-gecko": 768,
    "vertex_ai/textembedding-gecko@001": 768,
    "vertex_ai/textembedding-gecko@002": 768,
    "vertex_ai/textembedding-gecko@003": 768,
    "vertex_ai/text-embedding-004": 768,
    "vertex_ai/textembedding-gecko-multilingual@001": 768,
    # ---- AWS Bedrock ----
    "bedrock/amazon.titan-embed-text-v2:0": 1024,
    "bedrock/amazon.titan-embed-text-v1": 1536,
    "bedrock/cohere.embed-english-v3": 1024,
    "bedrock/cohere.embed-multilingual-v3": 1024,
    # ---- Sentence Transformers (HuggingFace IDs) ----
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-m3": 1024,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-MiniLM-L12-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "sentence-transformers/all-distilroberta-v1": 768,
    "sentence-transformers/paraphrase-MiniLM-L6-v2": 384,
    "sentence-transformers/multi-qa-MiniLM-L6-cos-v1": 384,
    "mixedbread-ai/mxbai-embed-large-v1": 1024,
    "mixedbread-ai/mxbai-embed-2d-large-v1": 1024,
    "nomic-ai/nomic-embed-text-v1": 768,
    "nomic-ai/nomic-embed-text-v1.5": 768,
    "intfloat/e5-small-v2": 384,
    "intfloat/e5-base-v2": 768,
    "intfloat/e5-large-v2": 1024,
}


def lookup_embedding_dimensions(model: str) -> int | None:
    """Return known dimensions for ``model``, or ``None`` if not in the table.

    Lookup is tolerant of the provider prefix: both
    ``"openai/text-embedding-3-small"`` and ``"text-embedding-3-small"``
    return ``1536``. For HuggingFace-style IDs (``"BAAI/bge-small-en-v1.5"``)
    the slash is part of the ID and must be present.
    """
    # Direct hit (provider-prefixed)
    if model in EMBEDDING_DIMENSIONS:
        return EMBEDDING_DIMENSIONS[model]

    # If the user passed just the model name without a provider prefix,
    # try searching for any provider-prefixed match.
    if "/" not in model:
        for key, dim in EMBEDDING_DIMENSIONS.items():
            if key.endswith("/" + model):
                return dim
        return None

    # If the user passed a provider-prefixed string but it wasn't a direct
    # hit, the bare model id might still match a HuggingFace-style entry.
    _, _, bare = model.partition("/")
    return EMBEDDING_DIMENSIONS.get(bare)


__all__ = [
    "EMBEDDING_DIMENSIONS",
    "lookup_embedding_dimensions",
]
