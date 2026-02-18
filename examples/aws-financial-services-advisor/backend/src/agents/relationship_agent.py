"""Relationship Agent for network analysis and connection mapping."""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from neo4j_agent_memory.integrations.strands import StrandsConfig, context_graph_tools
from strands import Agent, tool
from strands.models import BedrockModel

from ..config import get_settings
from .prompts import RELATIONSHIP_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Global agent instance
_relationship_agent: Agent | None = None

# Shell company indicators
SHELL_COMPANY_INDICATORS = [
    "no_physical_presence",
    "nominee_directors",
    "bearer_shares",
    "registered_agent_address",
    "no_employees",
    "minimal_operations",
    "circular_ownership",
    "offshore_jurisdiction",
    "recently_incorporated",
    "frequent_ownership_changes",
]


@tool
def find_connections(
    entity_id: str,
    depth: int = 2,
    relationship_types: list[str] | None = None,
    include_risk_assessment: bool = True,
) -> dict[str, Any]:
    """Discover connections between entities in the Context Graph.

    Use this tool to map relationships and find hidden connections
    between customers, organizations, and other entities.

    Args:
        entity_id: The entity to analyze
        depth: How many relationship hops to traverse (1-3)
        relationship_types: Filter to specific relationship types
        include_risk_assessment: Whether to assess risk of connections

    Returns:
        Network map with entities, relationships, and risk indicators
    """
    logger.info(f"Finding connections for entity {entity_id}, depth {depth}")

    # Simulated network data - in production, query the graph
    entity_count = random.randint(5, 15) * depth
    relationship_count = random.randint(entity_count, entity_count * 2)

    entities = []
    relationships = []

    entity_types = ["CUSTOMER", "ORGANIZATION", "PERSON", "ACCOUNT", "LOCATION"]
    rel_types = relationship_types or [
        "WORKS_AT",
        "OWNS",
        "CONTROLS",
        "CONNECTED_TO",
        "TRANSACTS_WITH",
        "DIRECTOR_OF",
    ]

    # Generate sample entities
    for i in range(entity_count):
        entity_type = random.choice(entity_types)
        risk_level = random.choice(["low", "low", "medium", "medium", "high"])

        entities.append(
            {
                "id": f"entity-{i}",
                "name": f"Entity {i}",
                "type": entity_type,
                "risk_level": risk_level if include_risk_assessment else None,
                "distance_from_source": random.randint(1, depth),
            }
        )

    # Generate sample relationships
    for i in range(relationship_count):
        relationships.append(
            {
                "id": f"rel-{i}",
                "source": f"entity-{random.randint(0, entity_count - 1)}",
                "target": f"entity-{random.randint(0, entity_count - 1)}",
                "type": random.choice(rel_types),
                "strength": random.uniform(0.5, 1.0),
            }
        )

    # Calculate network statistics
    high_risk_count = sum(1 for e in entities if e.get("risk_level") == "high")
    pep_connections = random.randint(0, 2)
    sanctioned_connections = 0 if random.random() > 0.1 else 1

    return {
        "source_entity_id": entity_id,
        "depth": depth,
        "network": {
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "entities": entities,
            "relationships": relationships,
        },
        "risk_summary": {
            "high_risk_entities": high_risk_count,
            "pep_connections": pep_connections,
            "sanctioned_connections": sanctioned_connections,
            "overall_network_risk": (
                "critical"
                if sanctioned_connections > 0
                else "high"
                if high_risk_count > 3 or pep_connections > 1
                else "medium"
                if high_risk_count > 0
                else "low"
            ),
        },
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


@tool
def analyze_network_risk(
    entity_id: str,
    include_transaction_links: bool = True,
    include_ownership_links: bool = True,
) -> dict[str, Any]:
    """Assess risk based on network relationships and connections.

    Use this tool to calculate aggregate risk from an entity's network,
    considering the risk levels of connected entities.

    Args:
        entity_id: The central entity to analyze
        include_transaction_links: Include transaction-based relationships
        include_ownership_links: Include ownership/control relationships

    Returns:
        Network risk assessment with contributing factors
    """
    logger.info(f"Analyzing network risk for entity {entity_id}")

    # Simulated risk analysis
    direct_connections = random.randint(5, 20)
    indirect_connections = random.randint(10, 50)

    risk_factors = []
    risk_score = 0

    # Check for various risk indicators
    if random.random() > 0.7:
        risk_factors.append("Connected to high-risk jurisdiction entities")
        risk_score += 25

    if random.random() > 0.8:
        pep_count = random.randint(1, 3)
        risk_factors.append(f"Connected to {pep_count} PEP(s)")
        risk_score += 20 * pep_count

    if random.random() > 0.9:
        risk_factors.append("Connected to sanctioned entity (indirect)")
        risk_score += 50

    if include_ownership_links and random.random() > 0.7:
        risk_factors.append("Complex ownership structure detected")
        risk_score += 15

    if include_transaction_links and random.random() > 0.6:
        risk_factors.append("High-value transactions with risky counterparties")
        risk_score += 20

    risk_score = min(risk_score, 100)

    if risk_score >= 70:
        risk_level = "critical"
    elif risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "entity_id": entity_id,
        "network_statistics": {
            "direct_connections": direct_connections,
            "indirect_connections": indirect_connections,
            "total_network_size": direct_connections + indirect_connections,
        },
        "risk_assessment": {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
        },
        "analysis_parameters": {
            "include_transaction_links": include_transaction_links,
            "include_ownership_links": include_ownership_links,
        },
        "recommendations": (
            [
                "Conduct enhanced due diligence",
                "Review all connected high-risk entities",
            ]
            if risk_level in ("high", "critical")
            else ["Continue standard monitoring"]
        ),
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


@tool
def detect_shell_companies(
    entity_id: str,
    depth: int = 2,
) -> dict[str, Any]:
    """Identify potential shell company structures in entity network.

    Use this tool to detect entities that exhibit shell company characteristics
    such as no operations, nominee directors, or circular ownership.

    Args:
        entity_id: The entity to investigate
        depth: Network depth to analyze

    Returns:
        Shell company detection results with indicator matches
    """
    logger.info(f"Detecting shell companies connected to {entity_id}")

    # Simulated shell company detection
    entities_analyzed = random.randint(5, 20)
    potential_shells = []

    for i in range(random.randint(0, min(3, entities_analyzed // 3))):
        # Randomly select indicators
        matched_indicators = random.sample(
            SHELL_COMPANY_INDICATORS, k=random.randint(3, 6)
        )

        confidence = len(matched_indicators) / len(SHELL_COMPANY_INDICATORS)

        potential_shells.append(
            {
                "entity_id": f"entity-shell-{i}",
                "entity_name": f"Potential Shell Entity {i}",
                "jurisdiction": random.choice(
                    ["BVI", "Cayman Islands", "Panama", "Delaware"]
                ),
                "matched_indicators": matched_indicators,
                "indicator_count": len(matched_indicators),
                "confidence_score": round(confidence, 3),
                "incorporation_date": f"20{random.randint(18, 24)}-{random.randint(1, 12):02d}-01",
                "relationship_to_subject": random.choice(
                    [
                        "direct_ownership",
                        "indirect_ownership",
                        "transaction_counterparty",
                        "shared_director",
                    ]
                ),
            }
        )

    # Sort by confidence
    potential_shells.sort(key=lambda x: x["confidence_score"], reverse=True)

    return {
        "subject_entity_id": entity_id,
        "analysis_depth": depth,
        "entities_analyzed": entities_analyzed,
        "shell_companies_detected": len(potential_shells),
        "potential_shell_companies": potential_shells,
        "risk_level": (
            "high"
            if len(potential_shells) > 1
            else "medium"
            if potential_shells
            else "low"
        ),
        "recommendations": (
            [
                "Investigate beneficial ownership chain",
                "Request additional documentation on flagged entities",
                "Consider enhanced due diligence",
            ]
            if potential_shells
            else ["No shell company concerns identified"]
        ),
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


@tool
def map_beneficial_ownership(
    entity_id: str,
    ownership_threshold: float = 0.25,
) -> dict[str, Any]:
    """Trace ownership chains to identify ultimate beneficial owners.

    Use this tool to map the ownership structure and identify individuals
    or entities with significant control.

    Args:
        entity_id: The entity to trace ownership for
        ownership_threshold: Minimum ownership percentage to include (0-1)

    Returns:
        Ownership chain with beneficial owners and control percentages
    """
    logger.info(f"Mapping beneficial ownership for {entity_id}")

    # Simulated ownership structure
    ownership_layers = random.randint(1, 4)
    is_complex = ownership_layers > 2

    ownership_chain = []
    current_layer_entities = [
        {"id": entity_id, "name": "Subject Entity", "ownership": 1.0}
    ]

    for layer in range(ownership_layers):
        layer_data = {
            "layer": layer,
            "entities": current_layer_entities,
        }
        ownership_chain.append(layer_data)

        # Generate next layer
        next_layer = []
        for entity in current_layer_entities:
            if random.random() > 0.3:  # Some entities have identified owners
                owner_count = random.randint(1, 3)
                for j in range(owner_count):
                    ownership_pct = random.uniform(0.1, 0.6)
                    if ownership_pct >= ownership_threshold:
                        is_individual = (
                            layer == ownership_layers - 1 or random.random() > 0.5
                        )
                        next_layer.append(
                            {
                                "id": f"owner-{layer}-{j}",
                                "name": f"{'Individual' if is_individual else 'Entity'} Owner {layer}-{j}",
                                "type": "individual" if is_individual else "corporate",
                                "ownership": round(ownership_pct, 3),
                                "jurisdiction": random.choice(
                                    ["US", "UK", "BVI", "Switzerland"]
                                ),
                                "pep_status": random.random() > 0.9,
                            }
                        )

        current_layer_entities = next_layer
        if not next_layer:
            break

    # Identify ultimate beneficial owners (individuals at end of chain)
    ubos = [
        e
        for layer in ownership_chain
        for e in layer["entities"]
        if isinstance(e, dict) and e.get("type") == "individual"
    ]

    # Check for concerning patterns
    pep_owners = [o for o in ubos if o.get("pep_status")]
    high_risk_jurisdictions = sum(
        1
        for layer in ownership_chain
        for e in layer["entities"]
        if isinstance(e, dict)
        and e.get("jurisdiction") in ["BVI", "Panama", "Cayman Islands"]
    )

    return {
        "subject_entity_id": entity_id,
        "ownership_threshold": ownership_threshold,
        "ownership_structure": {
            "total_layers": len(ownership_chain),
            "is_complex": is_complex,
            "chain": ownership_chain,
        },
        "ultimate_beneficial_owners": ubos,
        "ubo_count": len(ubos),
        "risk_indicators": {
            "pep_owners": len(pep_owners),
            "high_risk_jurisdictions": high_risk_jurisdictions,
            "complex_structure": is_complex,
            "nominee_structure_suspected": random.random() > 0.8,
        },
        "risk_level": (
            "high"
            if pep_owners or high_risk_jurisdictions > 2 or is_complex
            else "medium"
            if high_risk_jurisdictions > 0
            else "low"
        ),
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


def create_relationship_agent() -> Agent:
    """Create the Relationship Agent for network analysis.

    Returns:
        Configured Strands Agent for relationship analysis
    """
    settings = get_settings()

    # Load Context Graph tools for direct graph access
    config = StrandsConfig.from_env()
    memory_tools = context_graph_tools(**config.to_dict())

    relationship_tools = [
        find_connections,
        analyze_network_risk,
        detect_shell_companies,
        map_beneficial_ownership,
    ]

    # Combine memory tools with relationship-specific tools
    all_tools = memory_tools + relationship_tools

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock.model_id,
            region_name=settings.aws.region,
        ),
        tools=all_tools,
        system_prompt=RELATIONSHIP_AGENT_SYSTEM_PROMPT,
    )


def get_relationship_agent() -> Agent:
    """Get or create the global Relationship Agent instance.

    Returns:
        Relationship Agent instance
    """
    global _relationship_agent
    if _relationship_agent is None:
        _relationship_agent = create_relationship_agent()
    return _relationship_agent
