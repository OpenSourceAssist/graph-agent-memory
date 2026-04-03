"""Memory service for Neo4j Agent Memory integration."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from neo4j_agent_memory import ExtractionConfig, MemoryClient, MemorySettings
from neo4j_agent_memory.config import EmbeddingConfig, EmbeddingProvider, Neo4jConfig
from neo4j_agent_memory.memory.long_term import DeduplicationConfig

from ..config import get_settings

logger = logging.getLogger(__name__)


class FinancialMemoryService:
    """Service for managing financial Context Graph operations.

    This service integrates with Neo4j Agent Memory to provide:
    - Long-term memory for customer entities and relationships
    - Short-term memory for conversation context
    - Reasoning memory for investigation audit trails
    """

    def __init__(self) -> None:
        """Initialize the memory service."""
        settings = get_settings()
        memory_settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=settings.neo4j.uri,
                username=settings.neo4j.user,
                password=settings.neo4j.password,
                database=settings.neo4j.database,
            ),
            embedding=EmbeddingConfig(
                provider=EmbeddingProvider.BEDROCK,
                model=settings.bedrock.embedding_model_id,
                aws_region=settings.aws.region,
            ),
            extraction=ExtractionConfig(),
        )
        # DeduplicationConfig is available for preventing duplicate customer entities.
        # Configure via LongTermMemory(deduplication=DeduplicationConfig(...))
        # to auto-merge or flag similar entities during add_entity() calls.
        self._client = MemoryClient(memory_settings)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory client and create indexes."""
        if not self._initialized:
            await self._client.connect()
            self._initialized = True
            logger.info("Financial Memory Service initialized")

    async def close(self) -> None:
        """Close the memory client connection."""
        await self._client.close()
        self._initialized = False
        logger.info("Financial Memory Service closed")

    # ==========================================================================
    # Customer Entity Management (Long-Term Memory)
    # ==========================================================================

    async def add_customer(
        self,
        customer_id: str,
        name: str,
        customer_type: str,
        jurisdiction: str,
        risk_level: str = "unknown",
        industry: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a customer entity to the Context Graph.

        Args:
            customer_id: Unique customer identifier
            name: Customer name
            customer_type: Type of customer (individual, corporate, etc.)
            jurisdiction: Primary jurisdiction
            risk_level: Current risk level
            industry: Industry sector (for corporate customers)
            metadata: Additional customer metadata

        Returns:
            The entity ID in the graph
        """
        attributes = {
            "customer_id": customer_id,
            "customer_type": customer_type,
            "jurisdiction": jurisdiction,
            "risk_level": risk_level,
            "onboarding_date": datetime.utcnow().isoformat(),
        }
        if industry:
            attributes["industry"] = industry
        if metadata:
            attributes.update(metadata)

        description = f"{customer_type.title()} customer {name} in {jurisdiction}"
        if industry:
            description += f", {industry} sector"

        entity = await self._client.long_term.add_entity(
            name=name,
            entity_type="CUSTOMER",
            description=description,
            attributes=attributes,
        )
        # Provenance tracking is available via link_entity_to_message()
        # and link_entity_to_extractor() to trace where entities originated.
        logger.info(f"Added customer entity: {name} ({customer_id})")
        return entity.id

    async def add_organization(
        self,
        name: str,
        org_type: str,
        jurisdiction: str,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """Add an organization entity to the graph.

        Args:
            name: Organization name
            org_type: Type of organization
            jurisdiction: Organization jurisdiction
            attributes: Additional attributes

        Returns:
            The entity ID
        """
        attrs = {
            "organization_type": org_type,
            "jurisdiction": jurisdiction,
            **(attributes or {}),
        }

        entity = await self._client.long_term.add_entity(
            name=name,
            entity_type="ORGANIZATION",
            description=f"{org_type} organization in {jurisdiction}",
            attributes=attrs,
        )
        return entity.id

    async def add_account(
        self,
        account_id: str,
        account_type: str,
        currency: str,
        customer_entity_id: str,
    ) -> str:
        """Add an account entity and link to customer.

        Args:
            account_id: Account identifier
            account_type: Type of account
            currency: Account currency
            customer_entity_id: Entity ID of the owning customer

        Returns:
            The account entity ID
        """
        entity = await self._client.long_term.add_entity(
            name=f"Account {account_id}",
            entity_type="ACCOUNT",
            description=f"{account_type} account in {currency}",
            attributes={
                "account_id": account_id,
                "account_type": account_type,
                "currency": currency,
                "status": "active",
            },
        )

        # Link account to customer
        await self._client.long_term.add_relationship(
            source_entity_id=customer_entity_id,
            target_entity_id=entity.id,
            relationship_type="HAS_ACCOUNT",
            attributes={"opened_date": datetime.utcnow().isoformat()},
        )

        return entity.id

    async def add_customer_relationship(
        self,
        source_customer_id: str,
        target_entity_id: str,
        relationship_type: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Add a relationship between entities.

        Args:
            source_customer_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship (WORKS_AT, CONNECTED_TO, etc.)
            attributes: Relationship attributes
        """
        await self._client.long_term.add_relationship(
            source_entity_id=source_customer_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            attributes=attributes or {},
        )

    async def get_customer_network(
        self,
        customer_id: str,
        depth: int = 2,
        include_transactions: bool = False,
    ) -> dict[str, Any]:
        """Get the relationship network for a customer.

        Args:
            customer_id: Customer identifier
            depth: How many hops to traverse
            include_transactions: Whether to include transaction nodes

        Returns:
            Network data with nodes and edges
        """
        # Search for the customer entity
        entities = await self._client.long_term.search_entities(
            query=customer_id,
            entity_types=["CUSTOMER"],
            limit=1,
        )

        if not entities:
            return {"nodes": [], "edges": [], "error": "Customer not found"}

        customer_entity = entities[0]

        # Get entity graph
        graph = await self._client.long_term.get_entity_graph(
            entity_id=customer_entity.id,
            max_depth=depth,
        )

        # Convert to visualization format
        nodes = []
        edges = []

        for entity in graph.entities:
            if not include_transactions and entity.entity_type == "TRANSACTION":
                continue

            nodes.append(
                {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.entity_type,
                    "attributes": entity.attributes,
                }
            )

        for rel in graph.relationships:
            edges.append(
                {
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relationship_type,
                    "attributes": rel.attributes,
                }
            )

        return {"nodes": nodes, "edges": edges}

    async def search_customers(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for customers by semantic query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching customer summaries
        """
        entities = await self._client.long_term.search_entities(
            query=query,
            entity_types=["CUSTOMER"],
            limit=limit,
        )

        return [
            {
                "id": e.id,
                "name": e.name,
                "customer_id": e.attributes.get("customer_id"),
                "risk_level": e.attributes.get("risk_level"),
                "jurisdiction": e.attributes.get("jurisdiction"),
            }
            for e in entities
        ]

    # ==========================================================================
    # Transaction Management
    # ==========================================================================

    async def add_transaction(
        self,
        transaction_id: str,
        from_account_id: str,
        to_account_id: str | None,
        amount: float,
        currency: str,
        transaction_type: str,
        timestamp: datetime,
        beneficiary: dict[str, Any] | None = None,
    ) -> str:
        """Add a transaction to the graph.

        Args:
            transaction_id: Transaction identifier
            from_account_id: Source account entity ID
            to_account_id: Destination account entity ID (if internal)
            amount: Transaction amount
            currency: Transaction currency
            transaction_type: Type of transaction
            timestamp: Transaction timestamp
            beneficiary: External beneficiary details

        Returns:
            Transaction entity ID
        """
        attrs = {
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": currency,
            "transaction_type": transaction_type,
            "timestamp": timestamp.isoformat(),
        }
        if beneficiary:
            attrs["beneficiary"] = beneficiary

        entity = await self._client.long_term.add_entity(
            name=f"TXN-{transaction_id}",
            entity_type="TRANSACTION",
            description=f"{transaction_type} of {amount} {currency}",
            attributes=attrs,
        )

        # Link from source account
        await self._client.long_term.add_relationship(
            source_entity_id=from_account_id,
            target_entity_id=entity.id,
            relationship_type="SENT",
            attributes={"timestamp": timestamp.isoformat()},
        )

        # Link to destination if internal
        if to_account_id:
            await self._client.long_term.add_relationship(
                source_entity_id=entity.id,
                target_entity_id=to_account_id,
                relationship_type="RECEIVED_BY",
                attributes={"timestamp": timestamp.isoformat()},
            )

        return entity.id

    # ==========================================================================
    # Alert Management
    # ==========================================================================

    async def add_alert(
        self,
        alert_id: str,
        alert_type: str,
        severity: str,
        customer_entity_id: str,
        description: str,
        evidence: dict[str, Any] | None = None,
    ) -> str:
        """Add an alert entity linked to a customer.

        Args:
            alert_id: Alert identifier
            alert_type: Type of alert
            severity: Alert severity
            customer_entity_id: Related customer entity ID
            description: Alert description
            evidence: Supporting evidence

        Returns:
            Alert entity ID
        """
        entity = await self._client.long_term.add_entity(
            name=f"Alert {alert_id}",
            entity_type="ALERT",
            description=description,
            attributes={
                "alert_id": alert_id,
                "alert_type": alert_type,
                "severity": severity,
                "status": "new",
                "created_at": datetime.utcnow().isoformat(),
                "evidence": evidence or {},
            },
        )

        # Link to customer
        await self._client.long_term.add_relationship(
            source_entity_id=customer_entity_id,
            target_entity_id=entity.id,
            relationship_type="HAS_ALERT",
            attributes={"triggered_at": datetime.utcnow().isoformat()},
        )

        return entity.id

    # ==========================================================================
    # Conversation Memory (Short-Term)
    # ==========================================================================

    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to conversation history.

        Args:
            session_id: Conversation session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional message metadata
        """
        await self._client.short_term.add_message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get conversation history for a session.

        Args:
            session_id: Conversation session ID
            limit: Maximum messages to return

        Returns:
            List of conversation messages
        """
        messages = await self._client.short_term.get_conversation(
            session_id=session_id,
            limit=limit,
        )
        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "metadata": m.metadata,
            }
            for m in messages
        ]

    async def search_conversations(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search conversation history semantically.

        Args:
            query: Search query
            session_id: Optional session to search within
            limit: Maximum results

        Returns:
            Matching conversation excerpts
        """
        results = await self._client.short_term.search(
            query=query,
            session_id=session_id,
            limit=limit,
        )
        return [
            {
                "content": r.content,
                "role": r.role,
                "session_id": r.session_id,
                "score": r.score,
            }
            for r in results
        ]

    # ==========================================================================
    # Reasoning Memory (Investigation Audit Trail)
    # ==========================================================================

    async def start_investigation_trace(
        self,
        session_id: str,
        investigation_id: str,
        task: str,
    ) -> str:
        """Start a reasoning trace for an investigation.

        Args:
            session_id: Session ID
            investigation_id: Investigation ID
            task: Investigation task description

        Returns:
            Trace ID
        """
        trace_id = f"trace-{investigation_id}-{uuid.uuid4().hex[:8]}"

        await self._client.reasoning.start_trace(
            session_id=session_id,
            trace_id=trace_id,
            task=task,
            metadata={
                "investigation_id": investigation_id,
                "started_at": datetime.utcnow().isoformat(),
            },
        )

        return trace_id

    async def add_reasoning_step(
        self,
        session_id: str,
        trace_id: str,
        agent: str,
        action: str,
        reasoning: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Add a reasoning step to an investigation trace.

        Args:
            session_id: Session ID
            trace_id: Trace ID
            agent: Agent that performed the action
            action: Action taken
            reasoning: Agent's reasoning
            result: Action result
        """
        await self._client.reasoning.add_step(
            session_id=session_id,
            trace_id=trace_id,
            action=action,
            reasoning=reasoning,
            result=result or {},
            metadata={
                "agent": agent,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def complete_investigation_trace(
        self,
        session_id: str,
        trace_id: str,
        conclusion: str,
        success: bool = True,
    ) -> None:
        """Complete an investigation reasoning trace.

        Args:
            session_id: Session ID
            trace_id: Trace ID
            conclusion: Final conclusion
            success: Whether investigation succeeded
        """
        await self._client.reasoning.complete_trace(
            session_id=session_id,
            trace_id=trace_id,
            conclusion=conclusion,
            success=success,
        )

    async def get_investigation_trace(
        self,
        session_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """Get the full reasoning trace for an investigation.

        Args:
            session_id: Session ID
            trace_id: Trace ID

        Returns:
            Full trace with all steps
        """
        trace = await self._client.reasoning.get_trace(
            session_id=session_id,
            trace_id=trace_id,
        )

        return {
            "trace_id": trace.trace_id,
            "task": trace.task,
            "status": trace.status,
            "conclusion": trace.conclusion,
            "steps": [
                {
                    "action": s.action,
                    "reasoning": s.reasoning,
                    "result": s.result,
                    "metadata": s.metadata,
                }
                for s in trace.steps
            ],
            "metadata": trace.metadata,
        }


# Global service instance
_memory_service: FinancialMemoryService | None = None


def get_memory_service() -> FinancialMemoryService:
    """Get the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = FinancialMemoryService()
    return _memory_service
