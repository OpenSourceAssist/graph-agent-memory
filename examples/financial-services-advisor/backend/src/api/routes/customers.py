"""Customer API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...models import Customer, CustomerCreate, CustomerNetwork, CustomerRisk, RiskLevel
from ...services.memory_service import get_memory_service
from ...services.risk_service import get_risk_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["customers"])

# In-memory store for demo purposes
# In production, this would be a database
_customers: dict[str, Customer] = {}


class CustomerSummary(BaseModel):
    """Condensed customer information."""

    id: str
    name: str
    type: str
    jurisdiction: str
    risk_level: RiskLevel
    alerts_count: int


class CustomerListResponse(BaseModel):
    """Response for customer list endpoint."""

    customers: list[CustomerSummary]
    total: int
    page: int
    page_size: int


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    risk_level: RiskLevel | None = Query(None, description="Filter by risk level"),
    search: str | None = Query(None, description="Search by name"),
) -> CustomerListResponse:
    """List all customers with optional filtering.

    Args:
        page: Page number for pagination
        page_size: Number of items per page
        risk_level: Optional risk level filter
        search: Optional name search

    Returns:
        Paginated list of customers
    """
    customers = list(_customers.values())

    # Apply filters
    if risk_level:
        customers = [c for c in customers if c.risk_level == risk_level]

    if search:
        search_lower = search.lower()
        customers = [c for c in customers if search_lower in c.name.lower()]

    # Pagination
    total = len(customers)
    start = (page - 1) * page_size
    end = start + page_size
    page_customers = customers[start:end]

    return CustomerListResponse(
        customers=[
            CustomerSummary(
                id=c.id,
                name=c.name,
                type=c.type.value,
                jurisdiction=c.jurisdiction,
                risk_level=c.risk_level,
                alerts_count=c.alerts_count,
            )
            for c in page_customers
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=Customer, status_code=201)
async def create_customer(request: CustomerCreate) -> Customer:
    """Create a new customer.

    This will create the customer record and add them to the Context Graph
    for relationship tracking.

    Args:
        request: Customer creation data

    Returns:
        Created customer with ID
    """
    customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"

    customer = Customer(
        id=customer_id,
        **request.model_dump(),
    )

    # Store in memory
    _customers[customer_id] = customer

    # Add to Context Graph
    try:
        memory_service = get_memory_service()
        await memory_service.add_customer(
            customer_id=customer_id,
            name=customer.name,
            customer_type=customer.type.value,
            jurisdiction=customer.jurisdiction,
            industry=customer.industry,
            metadata=customer.metadata,
        )
        logger.info(f"Added customer {customer_id} to Context Graph")
    except Exception as e:
        logger.error(f"Failed to add customer to graph: {e}")
        # Customer is still created locally

    return customer


@router.get("/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str) -> Customer:
    """Get customer details by ID.

    Args:
        customer_id: The customer identifier

    Returns:
        Customer details
    """
    if customer_id not in _customers:
        raise HTTPException(status_code=404, detail="Customer not found")

    return _customers[customer_id]


@router.put("/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, request: CustomerCreate) -> Customer:
    """Update customer information.

    Args:
        customer_id: The customer identifier
        request: Updated customer data

    Returns:
        Updated customer
    """
    if customer_id not in _customers:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing = _customers[customer_id]
    updated = Customer(
        id=customer_id,
        onboarding_date=existing.onboarding_date,
        last_review_date=existing.last_review_date,
        alerts_count=existing.alerts_count,
        **request.model_dump(),
    )

    _customers[customer_id] = updated
    return updated


@router.get("/{customer_id}/risk", response_model=CustomerRisk)
async def get_customer_risk(
    customer_id: str,
    include_network: bool = Query(True, description="Include network analysis"),
) -> CustomerRisk:
    """Get risk assessment for a customer.

    This calculates a comprehensive risk score based on:
    - Geographic risk factors
    - Customer type and structure
    - Transaction patterns
    - Network relationships

    Args:
        customer_id: The customer identifier
        include_network: Whether to include network risk analysis

    Returns:
        Comprehensive risk assessment
    """
    if customer_id not in _customers:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer = _customers[customer_id]
    risk_service = get_risk_service()

    # Get network data if requested
    network_data = None
    if include_network:
        try:
            memory_service = get_memory_service()
            network = await memory_service.get_customer_network(customer_id)
            # Calculate network statistics
            network_data = {
                "total_connections": len(network.get("nodes", [])),
                "high_risk_count": sum(
                    1
                    for n in network.get("nodes", [])
                    if n.get("attributes", {}).get("risk_level") == "high"
                ),
                "pep_count": 0,  # Would be calculated from graph
                "sanctioned_count": 0,
                "shell_company_count": 0,
            }
        except Exception as e:
            logger.warning(f"Could not fetch network data: {e}")

    risk_assessment = risk_service.assess_customer_risk(
        customer_id=customer_id,
        customer_type=customer.type.value,
        jurisdiction=customer.jurisdiction,
        industry=customer.industry,
        network_data=network_data,
    )

    # Update customer risk level
    customer.risk_level = risk_assessment.overall_risk
    _customers[customer_id] = customer

    return risk_assessment


@router.get("/{customer_id}/network")
async def get_customer_network(
    customer_id: str,
    depth: int = Query(2, ge=1, le=4, description="Network traversal depth"),
    include_transactions: bool = Query(False, description="Include transaction nodes"),
) -> dict[str, Any]:
    """Get the relationship network for a customer.

    Uses the Context Graph to map customer relationships including
    connected organizations, accounts, and other entities.

    Args:
        customer_id: The customer identifier
        depth: How many hops to traverse
        include_transactions: Whether to include transaction nodes

    Returns:
        Network graph data for visualization
    """
    if customer_id not in _customers:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        memory_service = get_memory_service()
        network = await memory_service.get_customer_network(
            customer_id=customer_id,
            depth=depth,
            include_transactions=include_transactions,
        )
        return network

    except Exception as e:
        logger.error(f"Error fetching network: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_customers(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
) -> list[dict[str, Any]]:
    """Search customers using semantic search.

    Uses the Context Graph's semantic search to find customers
    matching the query based on their profiles and descriptions.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        Matching customers with relevance scores
    """
    try:
        memory_service = get_memory_service()
        results = await memory_service.search_customers(query=query, limit=limit)
        return results

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
