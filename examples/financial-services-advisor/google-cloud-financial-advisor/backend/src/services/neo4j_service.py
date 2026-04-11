"""Neo4j domain data service for the Financial Advisor.

Provides async methods to query domain-specific data (customers, transactions,
organizations, alerts, sanctions, PEPs) from Neo4j using the MemoryClient's
graph client for connection reuse.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class Neo4jDomainService:
    """Queries domain data from Neo4j via the MemoryClient graph client."""

    def __init__(self, graph_client):
        """Initialize with a Neo4jClient (from MemoryClient.graph)."""
        self._graph = graph_client

    # ── Customers ──────────────────────────────────────────────────────

    async def list_customers(
        self,
        *,
        customer_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List customers with optional type filter."""
        where = ""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if customer_type:
            where = "WHERE c.type = $type"
            params["type"] = customer_type

        query = f"""
        MATCH (c:Customer)
        {where}
        OPTIONAL MATCH (c)-[:HAS_DOCUMENT]->(d:Document)
        WITH c, collect(d {{.type, .status, .expiry_date, .submission_date}}) AS docs
        RETURN c {{.*, documents: docs}} AS customer
        ORDER BY c.id
        SKIP $offset LIMIT $limit
        """
        results = await self._graph.execute_read(query, params)
        return [r["customer"] for r in results]

    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Get a customer by ID with documents."""
        query = """
        MATCH (c:Customer {id: $id})
        OPTIONAL MATCH (c)-[:HAS_DOCUMENT]->(d:Document)
        WITH c, collect(d {.type, .status, .expiry_date, .submission_date}) AS docs
        RETURN c {.*, documents: docs} AS customer
        """
        results = await self._graph.execute_read(query, {"id": customer_id})
        return results[0]["customer"] if results else None

    async def get_customer_documents(
        self, customer_id: str, document_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Get documents for a customer, optionally filtered by type."""
        where = "WHERE c.id = $id"
        params: dict[str, Any] = {"id": customer_id}
        if document_type:
            where += " AND d.type = $doc_type"
            params["doc_type"] = document_type

        query = f"""
        MATCH (c:Customer)-[:HAS_DOCUMENT]->(d:Document)
        {where}
        RETURN d {{.*}} AS document
        """
        results = await self._graph.execute_read(query, params)
        return [r["document"] for r in results]

    # ── Transactions ───────────────────────────────────────────────────

    async def get_transactions(
        self,
        customer_id: str,
        *,
        days: int = 90,
        min_amount: float | None = None,
        transaction_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get transactions for a customer with optional filters."""
        filters = ["t.date >= date() - duration({days: $days})"]
        params: dict[str, Any] = {"id": customer_id, "days": days}

        if min_amount is not None:
            filters.append("t.amount >= $min_amount")
            params["min_amount"] = min_amount
        if transaction_type:
            filters.append("t.type = $tx_type")
            params["tx_type"] = transaction_type

        where_extra = "WHERE " + " AND ".join(filters)

        query = f"""
        MATCH (c:Customer {{id: $id}})-[:HAS_TRANSACTION]->(t:Transaction)
        {where_extra}
        RETURN t {{.*}} AS transaction
        ORDER BY t.date DESC
        """
        results = await self._graph.execute_read(query, params)
        return [r["transaction"] for r in results]

    async def get_transaction_stats(self, customer_id: str) -> dict[str, Any]:
        """Get aggregated transaction statistics for a customer."""
        query = """
        MATCH (c:Customer {id: $id})-[:HAS_TRANSACTION]->(t:Transaction)
        WITH t,
             CASE WHEN t.type IN ['deposit', 'wire_in', 'cash_deposit'] THEN t.amount ELSE 0 END AS deposit,
             CASE WHEN t.type IN ['withdrawal', 'wire_out'] THEN t.amount ELSE 0 END AS withdrawal
        RETURN count(t) AS transaction_count,
               sum(t.amount) AS total_volume,
               sum(deposit) AS total_deposits,
               sum(withdrawal) AS total_withdrawals,
               avg(t.amount) AS average_transaction,
               collect(DISTINCT t.counterparty) AS counterparties,
               collect(DISTINCT t.type) AS transaction_types
        """
        results = await self._graph.execute_read(query, {"id": customer_id})
        if not results:
            return {
                "transaction_count": 0,
                "total_volume": 0,
                "total_deposits": 0,
                "total_withdrawals": 0,
                "average_transaction": 0,
                "counterparties": [],
                "transaction_types": [],
            }
        return results[0]

    async def detect_structuring(self, customer_id: str) -> list[dict[str, Any]]:
        """Detect cash deposits just under $10K reporting threshold."""
        query = """
        MATCH (c:Customer {id: $id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.type = 'cash_deposit'
          AND t.amount >= 9000 AND t.amount < 10000
        RETURN t {.*} AS transaction
        ORDER BY t.date
        """
        results = await self._graph.execute_read(query, {"id": customer_id})
        return [r["transaction"] for r in results]

    async def detect_rapid_movement(self, customer_id: str) -> list[dict[str, Any]]:
        """Detect funds received and moved quickly with minimal loss."""
        query = """
        MATCH (c:Customer {id: $id})-[:HAS_TRANSACTION]->(t_in:Transaction)
        WHERE t_in.type IN ['wire_in', 'deposit']
        MATCH (c)-[:HAS_TRANSACTION]->(t_out:Transaction)
        WHERE t_out.type IN ['wire_out', 'withdrawal']
          AND t_out.date >= t_in.date
          AND date(t_out.date) <= date(t_in.date) + duration({days: 2})
          AND t_out.amount >= t_in.amount * 0.9
          AND t_out.amount <= t_in.amount
        RETURN t_in {.*} AS inbound, t_out {.*} AS outbound,
               t_in.amount - t_out.amount AS retained
        ORDER BY t_in.date
        """
        results = await self._graph.execute_read(query, {"id": customer_id})
        return results

    async def detect_layering(self, customer_id: str) -> list[dict[str, Any]]:
        """Detect layering: transactions involving multiple offshore jurisdictions."""
        query = """
        MATCH (c:Customer {id: $id})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.counterparty CONTAINS 'Offshore'
           OR t.counterparty CONTAINS 'Cayman'
           OR t.counterparty CONTAINS 'Seychelles'
           OR t.counterparty CONTAINS 'Panama'
           OR t.counterparty CONTAINS 'Shell Corp'
           OR t.counterparty CONTAINS 'Anonymous Trust'
        RETURN t {.*} AS transaction
        ORDER BY t.date
        """
        results = await self._graph.execute_read(query, {"id": customer_id})
        return [r["transaction"] for r in results]

    async def get_velocity_metrics(self, customer_id: str) -> dict[str, Any]:
        """Get transaction velocity metrics by type."""
        query = """
        MATCH (c:Customer {id: $id})-[:HAS_TRANSACTION]->(t:Transaction)
        WITH t.type AS tx_type, count(t) AS cnt, sum(t.amount) AS vol
        RETURN tx_type, cnt, vol
        ORDER BY tx_type
        """
        results = await self._graph.execute_read(query, {"id": customer_id})
        by_type = {r["tx_type"]: {"count": r["cnt"], "volume": r["vol"]} for r in results}
        total_txns = sum(r["cnt"] for r in results)
        total_vol = sum(r["vol"] for r in results)
        return {
            "total_transactions": total_txns,
            "total_volume": total_vol,
            "average_transaction": total_vol / total_txns if total_txns > 0 else 0,
            "transactions_by_type": {k: v["count"] for k, v in by_type.items()},
            "volume_by_type": {k: v["volume"] for k, v in by_type.items()},
        }

    # ── Network / Relationships ────────────────────────────────────────

    async def find_connections(self, entity_id: str, *, depth: int = 2) -> dict[str, Any]:
        """Find connected entities up to a given depth."""
        query = """
        MATCH (start {id: $id})
        CALL {
            WITH start
            MATCH path = (start)-[*1..$depth]-(connected)
            WHERE connected <> start
            RETURN DISTINCT connected,
                   length(path) AS distance,
                   [r IN relationships(path) | type(r)] AS rel_types
        }
        RETURN connected {.id, .name, .type, .jurisdiction, .shell_indicators, .business_type} AS entity,
               distance,
               rel_types
        ORDER BY distance, connected.name
        """
        # depth can't be parameterized in Neo4j variable-length paths
        actual_query = query.replace("$depth", str(min(depth, 3)))
        results = await self._graph.execute_read(actual_query, {"id": entity_id})
        return {
            "entity_id": entity_id,
            "connections": results,
        }

    async def detect_shell_companies(self, entity_id: str) -> list[dict[str, Any]]:
        """Find connected organizations with shell company indicators."""
        query = """
        MATCH (start {id: $id})-[*1..2]-(o:Organization)
        WHERE size(o.shell_indicators) > 0
        RETURN DISTINCT o {.id, .name, .jurisdiction, .business_type, .shell_indicators} AS org
        """
        results = await self._graph.execute_read(query, {"id": entity_id})
        return [r["org"] for r in results]

    async def trace_ownership(self, entity_id: str) -> dict[str, Any]:
        """Trace beneficial ownership chains."""
        query = """
        MATCH (target {id: $id})
        OPTIONAL MATCH path = (owner)-[:OWNS|CONTROLS|DIRECTED_BY*1..3]->(target)
        WHERE owner:Customer OR owner:Organization
        WITH target, path, owner,
             [r IN relationships(path) | type(r)] AS rel_types,
             length(path) AS chain_length
        RETURN owner {.id, .name, .type, .jurisdiction} AS owner,
               rel_types,
               chain_length
        ORDER BY chain_length
        """
        results = await self._graph.execute_read(query, {"id": entity_id})
        owners = [r for r in results if r["owner"] is not None]
        return {
            "entity_id": entity_id,
            "ownership_chains": owners,
            "ubo_identified": any(
                r["owner"].get("type") in ("individual", "PERSON") for r in owners
            ),
        }

    async def get_network_risk(self, entity_id: str) -> dict[str, Any]:
        """Calculate network risk based on connected entities."""
        high_risk_jurisdictions = {"KY", "BVI", "SC", "PA"}

        query = """
        MATCH (start {id: $id})-[*1..2]-(connected)
        WHERE connected <> start
        RETURN DISTINCT connected {
            .id, .name, .type, .jurisdiction, .shell_indicators, .role
        } AS entity
        """
        results = await self._graph.execute_read(query, {"id": entity_id})

        risk_score = 0
        risk_factors = []

        for r in results:
            entity = r["entity"]
            jurisdiction = entity.get("jurisdiction") or ""
            indicators = entity.get("shell_indicators") or []
            role = entity.get("role") or ""

            if jurisdiction in high_risk_jurisdictions:
                risk_score += 15
                risk_factors.append(
                    f"HIGH_RISK_JURISDICTION: {entity.get('name')} ({jurisdiction})"
                )
            if len(indicators) > 0:
                risk_score += 20
                risk_factors.append(
                    f"SHELL_COMPANY: {entity.get('name')} ({', '.join(indicators)})"
                )
            if role == "nominee_services":
                risk_score += 15
                risk_factors.append(f"NOMINEE_SERVICES: {entity.get('name')}")

        if len(results) > 5:
            risk_score += 10
            risk_factors.append(f"COMPLEX_NETWORK: {len(results)} connections")

        risk_score = min(risk_score, 100)
        risk_level = (
            "CRITICAL"
            if risk_score >= 75
            else "HIGH"
            if risk_score >= 50
            else "MEDIUM"
            if risk_score >= 25
            else "LOW"
        )

        return {
            "entity_id": entity_id,
            "network_risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "total_connections": len(results),
        }

    # ── Alerts ─────────────────────────────────────────────────────────

    async def list_alerts(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
        alert_type: str | None = None,
        customer_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List alerts with optional filters."""
        filters = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if status:
            filters.append("a.status = $status")
            params["status"] = status
        if severity:
            filters.append("a.severity = $severity")
            params["severity"] = severity
        if alert_type:
            filters.append("a.type = $alert_type")
            params["alert_type"] = alert_type
        if customer_id:
            filters.append("c.id = $customer_id")
            params["customer_id"] = customer_id

        where = ("WHERE " + " AND ".join(filters)) if filters else ""

        query = f"""
        MATCH (c:Customer)-[:HAS_ALERT]->(a:Alert)
        {where}
        RETURN a {{.*, customer_id: c.id, customer_name: c.name}} AS alert
        ORDER BY
            CASE a.severity
                WHEN 'CRITICAL' THEN 0
                WHEN 'HIGH' THEN 1
                WHEN 'MEDIUM' THEN 2
                WHEN 'LOW' THEN 3
            END,
            a.created_at DESC
        SKIP $offset LIMIT $limit
        """
        results = await self._graph.execute_read(query, params)
        return [r["alert"] for r in results]

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        """Get an alert by ID."""
        query = """
        MATCH (c:Customer)-[:HAS_ALERT]->(a:Alert {id: $id})
        OPTIONAL MATCH (a)-[:RELATED_TO_TRANSACTION]->(t:Transaction)
        WITH a, c, collect(t {.*}) AS txns
        RETURN a {.*, customer_id: c.id, customer_name: c.name,
                   transactions: txns} AS alert
        """
        results = await self._graph.execute_read(query, {"id": alert_id})
        return results[0]["alert"] if results else None

    async def create_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        """Create a new alert linked to a customer."""
        query = """
        MATCH (c:Customer {id: $customer_id})
        MERGE (a:Alert {id: $id})
        ON CREATE SET
            a.type = $type,
            a.severity = $severity,
            a.status = $status,
            a.title = $title,
            a.description = $description,
            a.evidence = $evidence,
            a.requires_sar = $requires_sar,
            a.auto_generated = $auto_generated,
            a.created_at = datetime()
        MERGE (c)-[:HAS_ALERT]->(a)
        RETURN a {.*, customer_id: c.id, customer_name: c.name} AS alert
        """
        alert_id = alert.get("id", f"ALERT-{uuid.uuid4().hex[:8].upper()}")
        results = await self._graph.execute_write(
            query,
            {
                "customer_id": alert["customer_id"],
                "id": alert_id,
                "type": alert.get("type", "AML"),
                "severity": alert.get("severity", "MEDIUM"),
                "status": alert.get("status", "NEW"),
                "title": alert["title"],
                "description": alert.get("description", ""),
                "evidence": alert.get("evidence", []),
                "requires_sar": alert.get("requires_sar", False),
                "auto_generated": alert.get("auto_generated", False),
            },
        )
        return results[0]["alert"] if results else alert

    async def update_alert(self, alert_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update alert properties."""
        set_clauses = []
        params: dict[str, Any] = {"id": alert_id}

        for key, value in updates.items():
            if key in ("status", "severity", "assigned_to", "resolution_notes"):
                set_clauses.append(f"a.{key} = ${key}")
                params[key] = value

        if updates.get("status") == "ACKNOWLEDGED":
            set_clauses.append("a.acknowledged_at = datetime()")
        elif updates.get("status") in ("RESOLVED", "FALSE_POSITIVE"):
            set_clauses.append("a.resolved_at = datetime()")

        if not set_clauses:
            return await self.get_alert(alert_id)

        query = f"""
        MATCH (c:Customer)-[:HAS_ALERT]->(a:Alert {{id: $id}})
        SET {", ".join(set_clauses)}
        RETURN a {{.*, customer_id: c.id, customer_name: c.name}} AS alert
        """
        results = await self._graph.execute_write(query, params)
        return results[0]["alert"] if results else None

    async def get_alert_summary(self) -> dict[str, Any]:
        """Get aggregated alert statistics."""
        query = """
        MATCH (c:Customer)-[:HAS_ALERT]->(a:Alert)
        WITH a.severity AS sev, a.status AS stat
        RETURN
            count(*) AS total,
            sum(CASE WHEN sev = 'CRITICAL' THEN 1 ELSE 0 END) AS critical,
            sum(CASE WHEN sev = 'HIGH' THEN 1 ELSE 0 END) AS high,
            sum(CASE WHEN sev = 'MEDIUM' THEN 1 ELSE 0 END) AS medium,
            sum(CASE WHEN sev = 'LOW' THEN 1 ELSE 0 END) AS low,
            sum(CASE WHEN stat = 'NEW' THEN 1 ELSE 0 END) AS new_count,
            sum(CASE WHEN stat = 'ACKNOWLEDGED' THEN 1 ELSE 0 END) AS acknowledged,
            sum(CASE WHEN stat = 'INVESTIGATING' THEN 1 ELSE 0 END) AS investigating,
            sum(CASE WHEN stat = 'ESCALATED' THEN 1 ELSE 0 END) AS escalated,
            sum(CASE WHEN stat = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved,
            sum(CASE WHEN sev = 'CRITICAL' AND NOT stat IN ['RESOLVED', 'FALSE_POSITIVE'] THEN 1 ELSE 0 END) AS critical_unresolved,
            sum(CASE WHEN sev = 'HIGH' AND NOT stat IN ['RESOLVED', 'FALSE_POSITIVE'] THEN 1 ELSE 0 END) AS high_unresolved
        """
        results = await self._graph.execute_read(query)
        if not results:
            return {
                "total": 0,
                "by_severity": {},
                "by_status": {},
                "critical_unresolved": 0,
                "high_unresolved": 0,
            }
        r = results[0]
        return {
            "total": r["total"],
            "by_severity": {
                "CRITICAL": r["critical"],
                "HIGH": r["high"],
                "MEDIUM": r["medium"],
                "LOW": r["low"],
            },
            "by_status": {
                "NEW": r["new_count"],
                "ACKNOWLEDGED": r["acknowledged"],
                "INVESTIGATING": r["investigating"],
                "ESCALATED": r["escalated"],
                "RESOLVED": r["resolved"],
            },
            "by_type": {},  # populated below
            "critical_unresolved": r["critical_unresolved"],
            "high_unresolved": r["high_unresolved"],
        }

    # ── Sanctions ──────────────────────────────────────────────────────

    async def check_sanctions(
        self, entity_name: str, *, include_aliases: bool = True
    ) -> list[dict[str, Any]]:
        """Check an entity name against the sanctions database."""
        name_lower = entity_name.lower()
        query = """
        MATCH (s:SanctionedEntity)
        OPTIONAL MATCH (alias:SanctionAlias)-[:ALIAS_OF]->(s)
        WITH s, collect(alias.name) AS aliases
        WHERE toLower(s.name) CONTAINS $name
           OR any(a IN aliases WHERE toLower(a) CONTAINS $name)
        RETURN s {.*, aliases: aliases} AS entity,
               CASE
                   WHEN toLower(s.name) = $name THEN 'EXACT'
                   WHEN any(a IN aliases WHERE toLower(a) = $name) THEN 'ALIAS'
                   ELSE 'PARTIAL'
               END AS match_type,
               CASE
                   WHEN toLower(s.name) = $name THEN 1.0
                   WHEN any(a IN aliases WHERE toLower(a) = $name) THEN 0.95
                   ELSE 0.7
               END AS confidence
        """
        results = await self._graph.execute_read(query, {"name": name_lower})
        return results

    # ── PEP ────────────────────────────────────────────────────────────

    async def check_pep(
        self, person_name: str, *, include_relatives: bool = True
    ) -> list[dict[str, Any]]:
        """Check a person name against the PEP database."""
        name_lower = person_name.lower()
        matches = []

        # Direct PEP match
        query = """
        MATCH (p:PEP)
        WHERE toLower(p.name) CONTAINS $name
        RETURN p {.*} AS pep,
               CASE WHEN toLower(p.name) = $name THEN 'DIRECT_PEP'
                    ELSE 'POTENTIAL_PEP' END AS match_type,
               CASE WHEN toLower(p.name) = $name THEN 1.0
                    ELSE 0.7 END AS confidence
        """
        results = await self._graph.execute_read(query, {"name": name_lower})
        matches.extend(results)

        # PEP relatives
        if include_relatives:
            query = """
            MATCH (r:PEPRelative)-[:RELATIVE_OF]->(p:PEP)
            WHERE toLower(r.name) CONTAINS $name
            RETURN r {.*, pep_name: p.name, pep_position: p.position} AS pep,
                   'PEP_RELATIVE' AS match_type,
                   0.95 AS confidence
            """
            results = await self._graph.execute_read(query, {"name": name_lower})
            matches.extend(results)

        return matches

    # ── Graph stats ────────────────────────────────────────────────────

    async def get_graph_stats(self) -> dict[str, Any]:
        """Get graph statistics (node and relationship counts)."""
        node_query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, count(*) AS count
        ORDER BY label
        """
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY type
        """
        nodes = await self._graph.execute_read(node_query)
        rels = await self._graph.execute_read(rel_query)

        total_nodes = sum(r["count"] for r in nodes)
        total_rels = sum(r["count"] for r in rels)

        return {
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "nodes_by_label": {r["label"]: r["count"] for r in nodes},
            "relationships_by_type": {r["type"]: r["count"] for r in rels},
        }
