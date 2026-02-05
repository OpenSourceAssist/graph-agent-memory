"""Relationship analysis tools for network investigation and beneficial ownership.

These tools are used by the Relationship Agent to analyze entity networks,
trace ownership structures, and detect shell companies using the Neo4j
Context Graph.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Sample entity network (in production, this would query Neo4j)
SAMPLE_NETWORK = {
    "entities": {
        "CUST-001": {
            "id": "CUST-001",
            "name": "John Smith",
            "type": "PERSON",
            "connections": ["Tech Corp Inc"],
        },
        "CUST-002": {
            "id": "CUST-002",
            "name": "Maria Garcia",
            "type": "PERSON",
            "connections": ["Garcia Trading LLC", "Garcia Family Trust"],
        },
        "CUST-003": {
            "id": "CUST-003",
            "name": "Global Holdings Ltd",
            "type": "ORGANIZATION",
            "connections": [
                "Shell Corp - Cayman",
                "Anonymous Trust - Seychelles",
                "Nominee Director Services Ltd",
                "BVI Registered Agent Co",
            ],
        },
        "Garcia Trading LLC": {
            "id": "ORG-001",
            "name": "Garcia Trading LLC",
            "type": "ORGANIZATION",
            "jurisdiction": "US-FL",
            "connections": [
                "Maria Garcia",
                "Garcia Family Trust",
                "Supplier Co - Panama",
            ],
        },
        "Shell Corp - Cayman": {
            "id": "ORG-002",
            "name": "Shell Corp - Cayman",
            "type": "ORGANIZATION",
            "jurisdiction": "KY",
            "connections": ["Global Holdings Ltd", "Anonymous Trust - Seychelles"],
            "shell_indicators": ["no_employees", "po_box_address", "nominee_directors"],
        },
        "Anonymous Trust - Seychelles": {
            "id": "ORG-003",
            "name": "Anonymous Trust - Seychelles",
            "type": "ORGANIZATION",
            "jurisdiction": "SC",
            "connections": [
                "Shell Corp - Cayman",
                "Global Holdings Ltd",
                "Unknown Beneficial Owner",
            ],
            "shell_indicators": ["opaque_structure", "high_risk_jurisdiction"],
        },
        "Nominee Director Services Ltd": {
            "id": "ORG-004",
            "name": "Nominee Director Services Ltd",
            "type": "ORGANIZATION",
            "connections": ["Global Holdings Ltd", "Shell Corp - Cayman"],
            "role": "nominee_services",
        },
    },
    "relationships": [
        {
            "from": "CUST-002",
            "to": "Garcia Trading LLC",
            "type": "OWNS",
            "percentage": 100,
        },
        {"from": "CUST-002", "to": "Garcia Family Trust", "type": "BENEFICIARY_OF"},
        {
            "from": "Garcia Trading LLC",
            "to": "Supplier Co - Panama",
            "type": "TRADES_WITH",
        },
        {"from": "CUST-003", "to": "Shell Corp - Cayman", "type": "CONTROLS"},
        {
            "from": "CUST-003",
            "to": "Nominee Director Services Ltd",
            "type": "DIRECTED_BY",
        },
        {
            "from": "Shell Corp - Cayman",
            "to": "Anonymous Trust - Seychelles",
            "type": "LINKED_TO",
        },
        {
            "from": "Anonymous Trust - Seychelles",
            "to": "Unknown Beneficial Owner",
            "type": "BENEFITS",
        },
    ],
}


def find_connections(
    entity_id: str,
    depth: int = 2,
    relationship_types: list[str] | None = None,
) -> dict[str, Any]:
    """Find all connections for an entity in the graph.

    Traverses the relationship network to discover connected entities
    up to the specified depth.

    Args:
        entity_id: The entity identifier to start from.
        depth: Maximum traversal depth (1-3 recommended).
        relationship_types: Filter by specific relationship types.

    Returns:
        Network of connected entities with relationship details.
    """
    logger.info(f"Finding connections for entity {entity_id}, depth={depth}")

    entity = SAMPLE_NETWORK["entities"].get(entity_id)
    if not entity:
        # Try to find by name
        for ent_id, ent in SAMPLE_NETWORK["entities"].items():
            if ent["name"] == entity_id:
                entity = ent
                entity_id = ent_id
                break

    if not entity:
        return {
            "entity_id": entity_id,
            "status": "NOT_FOUND",
            "message": f"Entity {entity_id} not found in network",
            "timestamp": datetime.now().isoformat(),
        }

    # Gather connections (simplified - production would use Cypher)
    connections = []
    visited = {entity_id}

    def traverse(current_id: str, current_depth: int):
        if current_depth > depth:
            return

        current = SAMPLE_NETWORK["entities"].get(current_id)
        if not current:
            return

        for connected_name in current.get("connections", []):
            # Find the connected entity
            connected = None
            connected_id = None
            for ent_id, ent in SAMPLE_NETWORK["entities"].items():
                if ent["name"] == connected_name or ent_id == connected_name:
                    connected = ent
                    connected_id = ent_id
                    break

            if connected and connected_id not in visited:
                visited.add(connected_id)

                # Find the relationship
                rel = None
                for r in SAMPLE_NETWORK["relationships"]:
                    if (r["from"] == current_id and r["to"] == connected_id) or (
                        r["to"] == current_id and r["from"] == connected_id
                    ):
                        rel = r
                        break

                connections.append(
                    {
                        "entity_id": connected_id,
                        "name": connected["name"],
                        "type": connected["type"],
                        "relationship": rel["type"] if rel else "CONNECTED_TO",
                        "distance": current_depth,
                        "jurisdiction": connected.get("jurisdiction"),
                    }
                )

                traverse(connected_id, current_depth + 1)

    traverse(entity_id, 1)

    return {
        "entity_id": entity_id,
        "entity_name": entity["name"],
        "entity_type": entity["type"],
        "depth_searched": depth,
        "connections_found": len(connections),
        "connections": connections,
        "timestamp": datetime.now().isoformat(),
    }


def analyze_network_risk(
    entity_id: str,
    include_indirect: bool = True,
) -> dict[str, Any]:
    """Analyze network-level risk for an entity.

    Evaluates risk based on the entity's network connections,
    jurisdictions involved, and relationship patterns.

    Args:
        entity_id: The entity identifier.
        include_indirect: Whether to include indirect connections.

    Returns:
        Network risk assessment with contributing factors.
    """
    logger.info(f"Analyzing network risk for {entity_id}")

    # First get connections
    connections = find_connections(entity_id, depth=2 if include_indirect else 1)

    if connections.get("status") == "NOT_FOUND":
        return connections

    risk_factors = []
    risk_score = 0

    # High-risk jurisdictions
    high_risk_jurisdictions = [
        "KY",
        "BVI",
        "SC",
        "PA",
    ]  # Cayman, BVI, Seychelles, Panama
    jurisdictions = [
        c.get("jurisdiction")
        for c in connections.get("connections", [])
        if c.get("jurisdiction")
    ]

    high_risk_count = sum(1 for j in jurisdictions if j in high_risk_jurisdictions)
    if high_risk_count > 0:
        risk_score += high_risk_count * 15
        risk_factors.append(
            {
                "factor": "HIGH_RISK_JURISDICTIONS",
                "count": high_risk_count,
                "jurisdictions": [
                    j for j in jurisdictions if j in high_risk_jurisdictions
                ],
                "weight": high_risk_count * 15,
            }
        )

    # Shell company connections
    shell_connections = []
    for conn in connections.get("connections", []):
        entity = SAMPLE_NETWORK["entities"].get(conn["entity_id"])
        if entity and entity.get("shell_indicators"):
            shell_connections.append(conn["name"])

    if shell_connections:
        risk_score += len(shell_connections) * 20
        risk_factors.append(
            {
                "factor": "SHELL_COMPANY_CONNECTIONS",
                "count": len(shell_connections),
                "entities": shell_connections,
                "weight": len(shell_connections) * 20,
            }
        )

    # Nominee service connections
    nominee_connections = [
        c for c in connections.get("connections", []) if "nominee" in c["name"].lower()
    ]
    if nominee_connections:
        risk_score += 15
        risk_factors.append(
            {
                "factor": "NOMINEE_SERVICES",
                "entities": [c["name"] for c in nominee_connections],
                "weight": 15,
            }
        )

    # Network complexity
    if connections["connections_found"] > 5:
        risk_score += 10
        risk_factors.append(
            {
                "factor": "COMPLEX_NETWORK",
                "connection_count": connections["connections_found"],
                "weight": 10,
            }
        )

    # Determine risk level
    if risk_score >= 60:
        risk_level = "CRITICAL"
    elif risk_score >= 40:
        risk_level = "HIGH"
    elif risk_score >= 20:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "entity_id": entity_id,
        "entity_name": connections["entity_name"],
        "network_risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "total_connections": connections["connections_found"],
        "include_indirect": include_indirect,
        "timestamp": datetime.now().isoformat(),
    }


def detect_shell_companies(
    entity_id: str,
) -> dict[str, Any]:
    """Detect potential shell companies in an entity's network.

    Analyzes connected entities for shell company indicators such as
    nominee directors, missing business activity, and opaque structures.

    Args:
        entity_id: The entity identifier to investigate.

    Returns:
        Shell company detection results with evidence.
    """
    logger.info(f"Detecting shell companies for {entity_id}")

    connections = find_connections(entity_id, depth=2)

    if connections.get("status") == "NOT_FOUND":
        return connections

    shell_indicators = {
        "no_employees": "No employees on record",
        "po_box_address": "PO Box or virtual address only",
        "nominee_directors": "Directors are nominee services",
        "opaque_structure": "Ownership structure not transparent",
        "high_risk_jurisdiction": "Registered in secrecy jurisdiction",
        "minimal_activity": "Little to no business activity",
    }

    detected_shells = []

    for conn in connections.get("connections", []):
        entity = SAMPLE_NETWORK["entities"].get(conn["entity_id"])
        if entity and entity.get("shell_indicators"):
            indicators = entity["shell_indicators"]
            detected_shells.append(
                {
                    "entity_id": conn["entity_id"],
                    "name": conn["name"],
                    "jurisdiction": entity.get("jurisdiction"),
                    "indicators": [
                        {"code": ind, "description": shell_indicators.get(ind, ind)}
                        for ind in indicators
                    ],
                    "indicator_count": len(indicators),
                    "confidence": min(0.5 + len(indicators) * 0.15, 0.95),
                }
            )

    # Check the entity itself
    main_entity = SAMPLE_NETWORK["entities"].get(entity_id)
    if main_entity and main_entity.get("shell_indicators"):
        indicators = main_entity["shell_indicators"]
        detected_shells.insert(
            0,
            {
                "entity_id": entity_id,
                "name": main_entity["name"],
                "jurisdiction": main_entity.get("jurisdiction"),
                "indicators": [
                    {"code": ind, "description": shell_indicators.get(ind, ind)}
                    for ind in indicators
                ],
                "indicator_count": len(indicators),
                "confidence": min(0.5 + len(indicators) * 0.15, 0.95),
                "is_subject": True,
            },
        )

    return {
        "entity_id": entity_id,
        "entity_name": connections["entity_name"],
        "shell_companies_detected": len(detected_shells),
        "shell_companies": detected_shells,
        "risk_level": "CRITICAL" if detected_shells else "LOW",
        "timestamp": datetime.now().isoformat(),
    }


def map_beneficial_ownership(
    entity_id: str,
    threshold_percentage: float = 25.0,
) -> dict[str, Any]:
    """Map beneficial ownership structure for an entity.

    Traces ownership chains to identify ultimate beneficial owners
    with significant control or ownership interest.

    Args:
        entity_id: The entity identifier.
        threshold_percentage: Minimum ownership percentage to trace.

    Returns:
        Beneficial ownership map with ownership chains.
    """
    logger.info(f"Mapping beneficial ownership for {entity_id}")

    entity = SAMPLE_NETWORK["entities"].get(entity_id)
    if not entity:
        return {
            "entity_id": entity_id,
            "status": "NOT_FOUND",
            "timestamp": datetime.now().isoformat(),
        }

    ownership_chains = []
    ubos = []  # Ultimate Beneficial Owners

    # Find ownership relationships
    for rel in SAMPLE_NETWORK["relationships"]:
        if rel["to"] == entity_id and rel["type"] in [
            "OWNS",
            "CONTROLS",
            "BENEFICIARY_OF",
        ]:
            owner_id = rel["from"]
            owner = SAMPLE_NETWORK["entities"].get(owner_id)

            if owner:
                chain = {
                    "owner_id": owner_id,
                    "owner_name": owner["name"],
                    "owner_type": owner["type"],
                    "relationship": rel["type"],
                    "percentage": rel.get("percentage"),
                }

                ownership_chains.append(chain)

                # If owner is a person, they're a potential UBO
                if owner["type"] == "PERSON":
                    ubos.append(
                        {
                            "id": owner_id,
                            "name": owner["name"],
                            "ownership_type": "DIRECT",
                            "percentage": rel.get("percentage"),
                        }
                    )

    # Check for opaque ownership
    opaque_indicators = []
    for chain in ownership_chains:
        owner = SAMPLE_NETWORK["entities"].get(chain["owner_id"])
        if owner and owner.get("shell_indicators"):
            opaque_indicators.append(
                {
                    "entity": chain["owner_name"],
                    "reason": "Owner has shell company indicators",
                }
            )

    if not ubos:
        opaque_indicators.append(
            {
                "entity": entity["name"],
                "reason": "No identifiable ultimate beneficial owner",
            }
        )

    return {
        "entity_id": entity_id,
        "entity_name": entity["name"],
        "ownership_threshold": threshold_percentage,
        "ownership_chains": ownership_chains,
        "ultimate_beneficial_owners": ubos,
        "ubo_identified": len(ubos) > 0,
        "opaque_indicators": opaque_indicators,
        "transparency_risk": "HIGH" if opaque_indicators else "LOW",
        "timestamp": datetime.now().isoformat(),
    }
