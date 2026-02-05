"""Customer API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...models.customer import Customer, CustomerCreate, CustomerRisk, RiskLevel
from ...tools.kyc_tools import (
    SAMPLE_CUSTOMERS,
    assess_customer_risk,
    verify_identity,
)
from ...tools.relationship_tools import find_connections

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[Customer])
async def list_customers(
    type: str | None = Query(None, description="Filter by customer type"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[Customer]:
    """List all customers with optional filtering."""
    customers = []

    for cust_id, cust_data in SAMPLE_CUSTOMERS.items():
        # Apply filters
        if type and cust_data.get("type") != type:
            continue

        # Get risk assessment
        risk = assess_customer_risk(cust_id)
        cust_risk_level = risk.get("risk_level", "MEDIUM")

        if risk_level and cust_risk_level != risk_level:
            continue

        customer = Customer(
            id=cust_id,
            name=cust_data.get("name", "Unknown"),
            type=cust_data.get("type", "individual"),
            nationality=cust_data.get("nationality"),
            address=cust_data.get("address") or cust_data.get("registered_address"),
            occupation=cust_data.get("occupation"),
            employer=cust_data.get("employer"),
            jurisdiction=cust_data.get("jurisdiction"),
            business_type=cust_data.get("business_type"),
            kyc_status=cust_data.get("kyc_status", "pending"),
            risk_level=RiskLevel(cust_risk_level),
            risk_score=risk.get("risk_score", 0),
            risk_factors=cust_data.get("risk_factors", []),
        )
        customers.append(customer)

    # Apply pagination
    return customers[offset : offset + limit]


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str) -> Customer:
    """Get a specific customer by ID."""
    cust_data = SAMPLE_CUSTOMERS.get(customer_id)
    if not cust_data:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    # Get risk assessment
    risk = assess_customer_risk(customer_id)

    return Customer(
        id=customer_id,
        name=cust_data.get("name", "Unknown"),
        type=cust_data.get("type", "individual"),
        nationality=cust_data.get("nationality"),
        address=cust_data.get("address") or cust_data.get("registered_address"),
        occupation=cust_data.get("occupation"),
        employer=cust_data.get("employer"),
        jurisdiction=cust_data.get("jurisdiction"),
        business_type=cust_data.get("business_type"),
        kyc_status=cust_data.get("kyc_status", "pending"),
        risk_level=RiskLevel(risk.get("risk_level", "MEDIUM")),
        risk_score=risk.get("risk_score", 0),
        risk_factors=cust_data.get("risk_factors", []),
    )


@router.get("/{customer_id}/risk", response_model=CustomerRisk)
async def get_customer_risk(customer_id: str) -> CustomerRisk:
    """Get risk assessment for a customer."""
    if customer_id not in SAMPLE_CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    risk = assess_customer_risk(customer_id)

    return CustomerRisk(
        customer_id=customer_id,
        customer_name=risk.get("customer_name", "Unknown"),
        risk_score=risk.get("risk_score", 0),
        risk_level=RiskLevel(risk.get("risk_level", "MEDIUM")),
        contributing_factors=risk.get("contributing_factors", []),
        kyc_status=risk.get("kyc_status", "pending"),
        recommendation=risk.get("recommendation", "Review required"),
    )


@router.get("/{customer_id}/network")
async def get_customer_network(
    customer_id: str,
    depth: int = Query(2, ge=1, le=3, description="Network traversal depth"),
) -> dict[str, Any]:
    """Get the relationship network for a customer.

    Returns nodes and edges for graph visualization.
    """
    if customer_id not in SAMPLE_CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    # Get connections
    connections = find_connections(customer_id, depth=depth)

    if connections.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Customer not found in network")

    # Format for visualization
    nodes = [
        {
            "id": customer_id,
            "label": connections.get("entity_name", customer_id),
            "type": connections.get("entity_type", "UNKNOWN"),
            "isRoot": True,
        }
    ]

    edges = []

    for conn in connections.get("connections", []):
        nodes.append(
            {
                "id": conn.get("entity_id", conn.get("name")),
                "label": conn.get("name"),
                "type": conn.get("type"),
                "jurisdiction": conn.get("jurisdiction"),
                "distance": conn.get("distance"),
            }
        )

        edges.append(
            {
                "from": customer_id if conn.get("distance") == 1 else None,
                "to": conn.get("entity_id", conn.get("name")),
                "relationship": conn.get("relationship"),
            }
        )

    return {
        "customer_id": customer_id,
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
        "total_connections": connections.get("connections_found", 0),
    }


@router.get("/{customer_id}/verify")
async def verify_customer(customer_id: str) -> dict[str, Any]:
    """Verify customer identity."""
    if customer_id not in SAMPLE_CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    return verify_identity(customer_id)


@router.post("", response_model=Customer)
async def create_customer(customer: CustomerCreate) -> Customer:
    """Create a new customer (demo - not persisted)."""
    import uuid

    customer_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"

    return Customer(
        id=customer_id,
        name=customer.name,
        type=customer.type,
        email=customer.email,
        phone=customer.phone,
        nationality=customer.nationality,
        address=customer.address,
        occupation=customer.occupation,
        employer=customer.employer,
        jurisdiction=customer.jurisdiction,
        business_type=customer.business_type,
        kyc_status="pending",
        risk_level=RiskLevel.MEDIUM,
        risk_score=20,
    )
