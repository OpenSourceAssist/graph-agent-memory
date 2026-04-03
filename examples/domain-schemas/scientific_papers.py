#!/usr/bin/env python3
"""Scientific Schema Example: Research Paper Analysis

This example demonstrates the scientific schema for extracting entities from
research papers, academic publications, and scientific content.

The scientific schema includes entity types like author, institution, method,
dataset, metric, concept, and tool commonly found in academic literature.

Sample Data: Fictional ML research paper abstracts
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

# Load environment from examples/.env
load_dotenv(Path(__file__).parent.parent / ".env")

from neo4j_agent_memory import ExtractionConfig, MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.extraction import (
    StreamingExtractor,
    create_gliner_extractor,
    create_streaming_extractor,
    is_gliner_available,
)

# Sample research paper abstracts - fictional ML papers
RESEARCH_PAPERS = [
    {
        "title": "Efficient Transformer Architectures for Long-Context Understanding",
        "venue": "NeurIPS 2024",
        "content": """
        Abstract: We present LongFormer-X, a novel transformer architecture
        designed for efficient processing of documents exceeding 100,000 tokens.
        Building on the work of Beltagy et al. (2020) and the Longformer model,
        our approach introduces a hierarchical attention mechanism that reduces
        computational complexity from O(n^2) to O(n log n).

        We evaluate LongFormer-X on the SCROLLS benchmark, the Long Range Arena,
        and a new dataset we introduce called BookSum-Extended. Our model achieves
        state-of-the-art results on all benchmarks while using 40% less memory
        than comparable approaches.

        Key contributions: (1) A novel chunked attention pattern with learned
        routing, (2) An efficient implementation using FlashAttention-2, and
        (3) A comprehensive ablation study demonstrating the importance of
        each component.

        Our code and pretrained models are available on GitHub. All experiments
        were conducted on NVIDIA A100 GPUs at the Stanford AI Lab.

        Authors: Sarah Chen (Stanford University), Michael Roberts
        (Google DeepMind), and Yuki Tanaka (University of Tokyo).
        """,
    },
    {
        "title": "Constitutional AI: Training Language Models with Principles",
        "venue": "ICML 2024",
        "content": """
        Abstract: We introduce Constitutional AI Learning (CAIL), a method for
        training language models to follow a set of principles without extensive
        human feedback annotation. Unlike RLHF (Reinforcement Learning from Human
        Feedback), CAIL requires only a constitution of principles written in
        natural language.

        Our experiments on the Claude model family demonstrate that CAIL reduces
        harmful outputs by 73% compared to baseline, as measured on the HarmBench
        and ToxiGen evaluation suites. We also evaluate on the MMLU benchmark
        to ensure capability is preserved.

        The training pipeline uses a combination of supervised fine-tuning on
        principle-following demonstrations and a novel critique-revision loop.
        We implement this using PyTorch and the HuggingFace Transformers library.

        Our analysis reveals that the effectiveness of CAIL depends critically
        on the specificity and comprehensiveness of the constitutional principles.
        We provide guidelines for practitioners based on experiments with over
        200 different constitution variants.

        Authors: Dario Amodei (Anthropic), Amanda Askell (Anthropic),
        Tom Brown (OpenAI), and Jan Leike (OpenAI).

        Acknowledgments: This research was supported by grants from the
        Open Philanthropy Project and compute resources from Google Cloud.
        """,
    },
    {
        "title": "Graph Neural Networks for Drug Discovery: A Comprehensive Survey",
        "venue": "Nature Machine Intelligence, 2024",
        "content": """
        Abstract: This survey provides a comprehensive overview of graph neural
        network (GNN) applications in drug discovery. We review 247 papers
        published between 2018 and 2024, categorizing methods by their primary
        task: molecular property prediction, drug-target interaction, de novo
        design, and reaction prediction.

        Key architectures discussed include Message Passing Neural Networks
        (MPNNs), Graph Attention Networks (GATs), and the recently proposed
        Equivariant Graph Neural Networks (EGNNs). We benchmark 15 representative
        methods on MoleculeNet, PCBA, and the Therapeutics Data Commons (TDC).

        Our analysis reveals that GNN performance on molecular property prediction
        has plateaued, with newer architectures providing diminishing returns.
        However, we identify promising directions in geometric deep learning
        and multi-modal approaches combining molecular graphs with protein
        structures.

        We release DrugGNN-Bench, a standardized evaluation framework implemented
        in PyTorch Geometric with support for 50+ GNN architectures and 30+
        benchmark datasets.

        Authors: Lisa Wang (MIT CSAIL), David Park (Harvard Medical School),
        and Carlos Rodriguez (DeepMind).

        This work was supported by the NIH grant R01-GM130834 and conducted
        in collaboration with Novartis AG and Recursion Pharmaceuticals.
        """,
    },
]


async def main():
    """Run the scientific paper analysis example."""
    print("=" * 70)
    print("Scientific Schema Example: Research Paper Analysis")
    print("=" * 70)
    print()

    # Create GLiNER extractor with scientific schema using factory pattern
    print("Initializing GLiNER2 extractor with scientific schema (via factory)...")
    try:
        extraction_config = ExtractionConfig(
            gliner_schema="scientific",
            gliner_threshold=0.4,
        )
        extractor = create_gliner_extractor(extraction_config)
        print(f"  Model: {extractor._model_name}")
        print(f"  Entity types: {list(extractor.entity_labels.keys())}")
    except ImportError as e:
        print(f"\n  ERROR: {e}")
        print("\n  To run this example, install GLiNER:")
        print("    uv sync --all-extras")
        print("    # or: pip install gliner")
        return
    print()

    # Process each paper
    all_entities = []

    for i, paper in enumerate(RESEARCH_PAPERS, 1):
        print(f"Paper {i}: {paper['title']}")
        print(f"Venue: {paper['venue']}")
        print("-" * 50)

        result = await extractor.extract(paper["content"])
        filtered = result.filter_invalid_entities()

        print(f"  Entities extracted: {filtered.entity_count}")

        # Group by type
        by_type = filtered.entities_by_type()
        for entity_type, entities in sorted(by_type.items()):
            if entities:
                print(f"\n  {entity_type}:")
                for entity in sorted(entities, key=lambda x: x.confidence or 0, reverse=True)[:6]:
                    conf = f"({entity.confidence:.0%})" if entity.confidence else ""
                    subtype = f" [{entity.subtype}]" if entity.subtype else ""
                    print(f"    - {entity.name}{subtype} {conf}")

        all_entities.extend(filtered.entities)
        print()

    # Summary
    print("=" * 70)
    print("ACADEMIC KNOWLEDGE GRAPH SUMMARY")
    print("=" * 70)

    # Deduplicate entities
    unique_entities = {}
    for entity in all_entities:
        key = (entity.normalized_name, entity.type)
        if key not in unique_entities or (entity.confidence or 0) > (
            unique_entities[key].confidence or 0
        ):
            unique_entities[key] = entity

    print(f"\nTotal unique entities: {len(unique_entities)}")

    # Authors
    print("\nAuthors:")
    authors = [e for e in unique_entities.values() if e.type == "PERSON"]
    for author in sorted(authors, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {author.name}")

    # Institutions
    print("\nInstitutions:")
    institutions = [e for e in unique_entities.values() if e.type == "ORGANIZATION"]
    for inst in sorted(institutions, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {inst.name}")

    # Methods and techniques
    print("\nMethods & Techniques:")
    methods = [
        e
        for e in unique_entities.values()
        if e.type == "OBJECT" and e.subtype in ("METHOD", "CONCEPT")
    ]
    for method in sorted(methods, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {method.name}")

    # Datasets
    print("\nDatasets & Benchmarks:")
    datasets = [
        e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "DATASET"
    ]
    for dataset in sorted(datasets, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {dataset.name}")

    # Tools
    print("\nTools & Frameworks:")
    tools = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "TOOL"]
    for tool in sorted(tools, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {tool.name}")

    # Metrics
    print("\nMetrics:")
    metrics = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "METRIC"]
    for metric in sorted(metrics, key=lambda x: x.confidence or 0, reverse=True)[:5]:
        print(f"  - {metric.name}")

    print()
    print("=" * 70)
    print("Research Knowledge Graph Use Cases:")
    print("=" * 70)
    print("""
    1. Citation Network Analysis:
       - Track author collaborations
       - Identify research clusters by institution
       - Find influential papers by citation

    2. Method Genealogy:
       - Track evolution of techniques (RLHF -> CAIL)
       - Identify foundational methods
       - Discover method combinations

    3. Dataset Discovery:
       - Find papers using specific benchmarks
       - Track dataset adoption over time
       - Identify gaps in evaluation

    4. Tool Ecosystem:
       - Map framework dependencies
       - Track library adoption
       - Identify hardware requirements

    5. Collaboration Recommendations:
       - Find researchers with complementary expertise
       - Identify potential institutional partnerships
       - Discover cross-disciplinary opportunities
    """)

    # Demonstrate streaming extraction for long documents
    print("=" * 70)
    print("STREAMING EXTRACTION DEMO (for long documents)")
    print("=" * 70)
    print()

    # Combine all papers into a single long document to simulate a survey paper
    long_document = "\n\n---\n\n".join(
        f"# {paper['title']}\n{paper['content']}" for paper in RESEARCH_PAPERS
    )
    print(f"  Combined document length: {len(long_document)} characters")

    # Create streaming extractor - processes in chunks for memory efficiency
    streamer = create_streaming_extractor(
        extractor, chunk_size=2000, overlap=200
    )

    # Stream results chunk by chunk
    chunk_count = 0
    streaming_entities = 0
    async for chunk_result in streamer.extract_streaming(long_document):
        chunk_count += 1
        streaming_entities += chunk_result.entity_count
        print(
            f"  Chunk {chunk_result.chunk.index + 1}: "
            f"{chunk_result.entity_count} entities"
            f"{' (error: ' + chunk_result.error + ')' if not chunk_result.success else ''}"
        )

    print(f"\n  Total: {chunk_count} chunks, {streaming_entities} entities (before dedup)")

    # Or get complete result with automatic deduplication
    complete_result = await streamer.extract(long_document, deduplicate=True)
    print(
        f"  After deduplication: {complete_result.stats.deduplicated_entities} entities "
        f"(from {complete_result.stats.total_entities} raw)"
    )
    print()

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing research entities...")

        settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=neo4j_uri,
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=SecretStr(os.getenv("NEO4J_PASSWORD", "password")),
            )
        )

        async with MemoryClient(settings) as client:
            stored_count = 0
            for entity in list(unique_entities.values())[:30]:
                await client.long_term.add_entity(
                    name=entity.name,
                    entity_type=entity.type,
                    subtype=entity.subtype,
                    attributes={
                        "source": "research_papers",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
