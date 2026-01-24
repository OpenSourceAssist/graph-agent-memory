#!/usr/bin/env python3
"""Medical Schema Example: Healthcare Document Analysis

This example demonstrates the medical schema for extracting entities from
clinical documents, medical research, and healthcare content.

The medical schema includes entity types like disease, drug, symptom, procedure,
body_part, gene, and organism commonly found in healthcare contexts.

Sample Data: Fictional clinical notes and medical literature
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

# Load environment from examples/.env
load_dotenv(Path(__file__).parent.parent / ".env")

from neo4j_agent_memory import MemoryClient, MemorySettings, Neo4jConfig
from neo4j_agent_memory.extraction import GLiNEREntityExtractor, is_gliner_available

# Sample medical documents - fictional clinical cases and research
MEDICAL_DOCUMENTS = [
    {
        "type": "Clinical Case Summary",
        "source": "Internal Medicine Case Report",
        "content": """
        Case Presentation: A 58-year-old male with a history of type 2 diabetes
        mellitus and hypertension presented to the emergency department with
        acute onset chest pain radiating to the left arm, accompanied by
        shortness of breath and diaphoresis.

        Physical examination revealed blood pressure of 165/95 mmHg, heart rate
        of 102 bpm, and bilateral crackles in the lung bases. An electrocardiogram
        showed ST-segment elevation in leads V1-V4, consistent with an anterior
        wall myocardial infarction.

        Laboratory findings included troponin I of 4.2 ng/mL (normal <0.04),
        BNP of 890 pg/mL, and creatinine of 1.4 mg/dL. The patient was started
        on aspirin, clopidogrel, and heparin infusion.

        Emergent cardiac catheterization revealed 95% occlusion of the left
        anterior descending artery. Percutaneous coronary intervention with
        drug-eluting stent placement was performed successfully.

        Post-procedure, the patient was started on atorvastatin, metoprolol,
        and lisinopril. Echocardiography showed left ventricular ejection
        fraction of 40% with anterior wall hypokinesis.

        Patient was discharged on day 4 with cardiac rehabilitation referral.
        """,
    },
    {
        "type": "Drug Development Report",
        "source": "Phase III Clinical Trial Summary",
        "content": """
        VELOXIB Phase III Results: Novel JAK Inhibitor for Rheumatoid Arthritis

        Primary Endpoint Met: Veloxib demonstrated superiority over placebo and
        non-inferiority to adalimumab (Humira) in patients with moderate-to-severe
        rheumatoid arthritis at 24 weeks.

        Study Population: 1,247 patients enrolled across 180 sites in North America
        and Europe. Patients had inadequate response to methotrexate and were
        TNF-naive.

        Efficacy Results:
        - ACR20 response: Veloxib 68% vs placebo 34% (p<0.001)
        - ACR50 response: Veloxib 42% vs adalimumab 39%
        - DAS28-CRP remission: 28% vs 24% (adalimumab)

        Safety Profile:
        - Most common adverse events: nasopharyngitis (12%), upper respiratory
          tract infection (9%), and headache (7%)
        - Serious infections occurred in 2.1% of patients
        - Two cases of herpes zoster reactivation
        - No cases of tuberculosis or opportunistic infections
        - Cardiovascular events: 0.8% (similar to adalimumab)

        Mechanism: Veloxib selectively inhibits JAK1 and JAK2, reducing
        inflammatory cytokine signaling including interleukin-6 and interferon-gamma.

        The FDA has granted Priority Review status. The PDUFA date is set for
        June 2025. Marketing applications have also been submitted to the EMA
        and Health Canada.
        """,
    },
    {
        "type": "Genomic Analysis Report",
        "source": "Cancer Genetics Laboratory",
        "content": """
        Comprehensive Genomic Profiling Report

        Patient: [Anonymized]
        Diagnosis: Metastatic Non-Small Cell Lung Cancer (Adenocarcinoma)
        Specimen: Lung biopsy (FFPE)

        Genomic Findings:

        1. EGFR Exon 19 Deletion (p.E746_A750del) - DETECTED
           Clinical significance: Sensitizing mutation. Patient is a candidate
           for EGFR tyrosine kinase inhibitors including osimertinib (Tagrisso),
           erlotinib (Tarceva), or gefitinib (Iressa).

        2. TP53 R248W Mutation - DETECTED
           Clinical significance: Loss of function mutation. Associated with
           worse prognosis but does not affect EGFR TKI response.

        3. MET Amplification (Copy Number: 8) - DETECTED
           Clinical significance: May confer resistance to EGFR TKIs. Consider
           combination therapy with MET inhibitor such as capmatinib (Tabrecta)
           or tepotinib (Tepmetko).

        4. PD-L1 Expression: 45% (TPS by 22C3 assay)
           Clinical significance: Qualifies for pembrolizumab (Keytruda)
           monotherapy if EGFR TKI resistance develops.

        Microsatellite Status: Stable (MSS)
        Tumor Mutational Burden: 6 mutations/Mb (Low)

        Recommended Next Steps:
        - Initiate osimertinib 80mg daily
        - Monitor for MET-driven resistance
        - Consider liquid biopsy for ctDNA monitoring
        """,
    },
]


async def main():
    """Run the medical document analysis example."""
    print("=" * 70)
    print("Medical Schema Example: Healthcare Document Analysis")
    print("=" * 70)
    print()

    # Create GLiNER extractor with medical schema
    print("Initializing GLiNER2 extractor with medical schema...")
    try:
        extractor = GLiNEREntityExtractor.for_schema("medical", threshold=0.4)
        print(f"  Model: {extractor._model_name}")
        print(f"  Entity types: {list(extractor.entity_labels.keys())}")
    except ImportError as e:
        print(f"\n  ERROR: {e}")
        print("\n  To run this example, install GLiNER:")
        print("    uv sync --all-extras")
        print("    # or: pip install gliner")
        return
    print()

    # Process each document
    all_entities = []

    for i, doc in enumerate(MEDICAL_DOCUMENTS, 1):
        print(f"Document {i}: {doc['type']}")
        print(f"Source: {doc['source']}")
        print("-" * 50)

        result = await extractor.extract(doc["content"])
        filtered = result.filter_invalid_entities()

        print(f"  Entities extracted: {filtered.entity_count}")

        # Group by type
        by_type = filtered.entities_by_type()
        for entity_type, entities in sorted(by_type.items()):
            if entities:
                print(f"\n  {entity_type}:")
                for entity in sorted(entities, key=lambda x: x.confidence or 0, reverse=True)[:8]:
                    conf = f"({entity.confidence:.0%})" if entity.confidence else ""
                    subtype = f" [{entity.subtype}]" if entity.subtype else ""
                    print(f"    - {entity.name}{subtype} {conf}")

        all_entities.extend(filtered.entities)
        print()

    # Summary
    print("=" * 70)
    print("MEDICAL KNOWLEDGE GRAPH SUMMARY")
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

    # Diseases
    print("\nDiseases & Conditions:")
    diseases = [
        e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "DISEASE"
    ]
    for disease in sorted(diseases, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {disease.name}")

    # Drugs
    print("\nDrugs & Medications:")
    drugs = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "DRUG"]
    for drug in sorted(drugs, key=lambda x: x.confidence or 0, reverse=True)[:10]:
        print(f"  - {drug.name}")

    # Symptoms
    print("\nSymptoms & Signs:")
    symptoms = [
        e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "SYMPTOM"
    ]
    for symptom in sorted(symptoms, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {symptom.name}")

    # Procedures
    print("\nProcedures & Interventions:")
    procedures = [
        e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "PROCEDURE"
    ]
    for proc in sorted(procedures, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {proc.name}")

    # Body parts
    print("\nBody Parts & Anatomy:")
    body_parts = [
        e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "BODY_PART"
    ]
    for part in sorted(body_parts, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {part.name}")

    # Genes
    print("\nGenes & Biomarkers:")
    genes = [e for e in unique_entities.values() if e.type == "OBJECT" and e.subtype == "GENE"]
    for gene in sorted(genes, key=lambda x: x.confidence or 0, reverse=True)[:8]:
        print(f"  - {gene.name}")

    print()
    print("=" * 70)
    print("Medical Knowledge Graph Use Cases:")
    print("=" * 70)
    print("""
    1. Clinical Decision Support:
       - Identify drug-drug interactions
       - Match patients to clinical trials
       - Suggest treatment options based on genomics

    2. Drug Discovery:
       - Map drug-target relationships
       - Identify repurposing opportunities
       - Track adverse event patterns

    3. Disease Understanding:
       - Connect symptoms to diseases
       - Map disease-gene relationships
       - Track disease progression patterns

    4. Treatment Optimization:
       - Match biomarkers to therapies
       - Identify resistance mechanisms
       - Personalize treatment plans

    5. Literature Mining:
       - Extract relationships from publications
       - Track emerging treatments
       - Identify research gaps

    IMPORTANT: This example uses fictional data for demonstration purposes.
    In real healthcare applications, ensure compliance with HIPAA, GDPR,
    and other applicable regulations.
    """)

    # Demonstrate Neo4j storage if configured
    neo4j_uri = os.getenv("NEO4J_URI")
    if neo4j_uri:
        print("\nNeo4j connection available. Storing medical entities...")

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
                        "source": "medical_documents",
                        "confidence": entity.confidence,
                    },
                )
                stored_count += 1

            print(f"Stored {stored_count} entities in Neo4j")
    else:
        print("\nSet NEO4J_URI to store entities in Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
