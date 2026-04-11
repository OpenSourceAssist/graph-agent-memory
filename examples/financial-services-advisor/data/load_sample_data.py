#!/usr/bin/env python3
"""Load sample financial data into Neo4j for the Financial Services Advisor.

This script loads customers, organizations, transactions, documents,
sanctions, PEPs, and alerts into Neo4j to create a sample knowledge
graph for testing the financial advisor (shared by AWS and GCP examples).

Usage:
    python load_sample_data.py [--uri URI] [--user USER] [--password PASSWORD]

    # From either example's backend directory:
    cd backend && uv run python ../../data/load_sample_data.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Load .env from multiple possible locations
for _env_candidate in [
    Path(__file__).resolve().parent.parent / ".env",             # financial-services-advisor/.env
    Path(__file__).resolve().parent.parent / "aws-financial-services-advisor" / "backend" / ".env",
    Path(__file__).resolve().parent.parent / "google-cloud-financial-advisor" / "backend" / ".env",
]:
    if _env_candidate.exists():
        load_dotenv(_env_candidate)
        break

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent


async def load_data(uri: str, user: str, password: str) -> None:
    """Load sample data into Neo4j."""
    logger.info(f"Connecting to Neo4j at {uri}")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async with driver.session() as session:
        # Clear existing data
        logger.info("Clearing existing data...")
        await session.run("MATCH (n) DETACH DELETE n")

        # Create constraints
        logger.info("Creating constraints...")
        constraints = [
            "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (a:Alert) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT sanctioned_entity_name IF NOT EXISTS FOR (s:SanctionedEntity) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT pep_name IF NOT EXISTS FOR (p:PEP) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT investigation_id IF NOT EXISTS FOR (i:Investigation) REQUIRE i.id IS UNIQUE",
        ]
        for constraint in constraints:
            try:
                await session.run(constraint)
            except Exception as e:
                logger.warning(f"Constraint may already exist: {e}")

        # Load customers
        logger.info("Loading customers...")
        with open(DATA_DIR / "customers.json") as f:
            customers = json.load(f)

        for customer in customers:
            cust_type = customer.get("type", "individual")
            label = "Person" if cust_type == "individual" else "Organization"

            if cust_type == "individual":
                await session.run(
                    f"""
                    CREATE (c:Customer:{label} {{
                        id: $id, name: $name, type: $type,
                        date_of_birth: $date_of_birth, nationality: $nationality,
                        address: $address, occupation: $occupation, employer: $employer,
                        account_opened: $account_opened,
                        risk_factors: $risk_factors, kyc_status: $kyc_status
                    }})
                    """,
                    id=customer["id"], name=customer["name"], type=cust_type,
                    date_of_birth=customer.get("date_of_birth"),
                    nationality=customer.get("nationality"),
                    address=customer.get("address"),
                    occupation=customer.get("occupation"),
                    employer=customer.get("employer"),
                    account_opened=customer.get("account_opened"),
                    risk_factors=customer.get("risk_factors", []),
                    kyc_status=customer.get("kyc_status", "pending"),
                )
            else:
                await session.run(
                    f"""
                    CREATE (c:Customer:{label} {{
                        id: $id, name: $name, type: $type,
                        incorporation_date: $incorporation_date,
                        jurisdiction: $jurisdiction,
                        registered_address: $registered_address,
                        business_type: $business_type, directors: $directors,
                        account_opened: $account_opened,
                        risk_factors: $risk_factors, kyc_status: $kyc_status
                    }})
                    """,
                    id=customer["id"], name=customer["name"], type=cust_type,
                    incorporation_date=customer.get("incorporation_date"),
                    jurisdiction=customer.get("jurisdiction"),
                    registered_address=customer.get("registered_address"),
                    business_type=customer.get("business_type"),
                    directors=customer.get("directors", []),
                    account_opened=customer.get("account_opened"),
                    risk_factors=customer.get("risk_factors", []),
                    kyc_status=customer.get("kyc_status", "pending"),
                )

            # Create document nodes
            for doc_type, doc_info in customer.get("documents", {}).items():
                doc_id = f"{customer['id']}-{doc_type}"
                await session.run(
                    """
                    CREATE (d:Document {
                        id: $doc_id, type: $doc_type,
                        status: $status, expiry_date: $expiry_date,
                        submission_date: $submission_date
                    })
                    WITH d
                    MATCH (c:Customer {id: $customer_id})
                    MERGE (c)-[:HAS_DOCUMENT]->(d)
                    """,
                    doc_id=doc_id, doc_type=doc_type,
                    status=doc_info.get("status", "pending"),
                    expiry_date=doc_info.get("expiry"),
                    submission_date=doc_info.get("date"),
                    customer_id=customer["id"],
                )

            logger.info(f"  Created customer: {customer['name']}")

        # Load organizations
        logger.info("Loading organizations...")
        with open(DATA_DIR / "organizations.json") as f:
            organizations = json.load(f)

        for org in organizations:
            await session.run(
                """
                MERGE (o:Organization {id: $id})
                SET o.name = $name, o.jurisdiction = $jurisdiction,
                    o.business_type = $business_type,
                    o.shell_indicators = $shell_indicators, o.role = $role
                """,
                id=org["id"], name=org["name"],
                jurisdiction=org.get("jurisdiction"),
                business_type=org.get("business_type"),
                shell_indicators=org.get("shell_indicators", []),
                role=org.get("role"),
            )

        # Create org relationships
        logger.info("Creating relationships...")
        for org in organizations:
            for conn in org.get("connections", []):
                await session.run(
                    """
                    MATCH (o:Organization {id: $org_id})
                    OPTIONAL MATCH (c:Customer {id: $conn_id})
                    OPTIONAL MATCH (c2:Customer {name: $conn_name})
                    OPTIONAL MATCH (o2:Organization {name: $conn_name})
                    WITH o, COALESCE(c, c2, o2) as target
                    WHERE target IS NOT NULL
                    MERGE (o)-[:CONNECTED_TO]->(target)
                    """,
                    org_id=org["id"], conn_id=conn, conn_name=conn,
                )

            for owner_id in org.get("owners", []):
                await session.run(
                    """
                    MATCH (o:Organization {id: $org_id})
                    MATCH (c:Customer {id: $owner_id})
                    MERGE (c)-[:OWNS {percentage: 100}]->(o)
                    """,
                    org_id=org["id"], owner_id=owner_id,
                )

        # Load transactions
        logger.info("Loading transactions...")
        with open(DATA_DIR / "transactions.json") as f:
            transactions = json.load(f)

        for txn in transactions:
            await session.run(
                """
                CREATE (t:Transaction {
                    id: $id, date: $date, type: $type, amount: $amount,
                    currency: $currency, counterparty: $counterparty,
                    description: $description
                })
                WITH t
                MATCH (c:Customer {id: $customer_id})
                MERGE (c)-[:HAS_TRANSACTION]->(t)
                """,
                id=txn["id"], date=txn["date"], type=txn["type"],
                amount=txn["amount"], currency=txn.get("currency", "USD"),
                counterparty=txn.get("counterparty"),
                description=txn.get("description"),
                customer_id=txn["customer_id"],
            )
        logger.info(f"  Created {len(transactions)} transactions")

        # Additional entity relationships
        logger.info("Creating entity relationships...")
        for cypher in [
            "MATCH (c:Customer {id: 'CUST-003'}), (o:Organization) WHERE o.name IN ['Shell Corp - Cayman', 'Anonymous Trust - Seychelles'] MERGE (c)-[:CONTROLS]->(o)",
            "MATCH (c:Customer {id: 'CUST-003'}), (o:Organization {name: 'Nominee Director Services Ltd'}) MERGE (c)-[:DIRECTED_BY]->(o)",
            "MATCH (o1:Organization {name: 'Shell Corp - Cayman'}), (o2:Organization {name: 'Anonymous Trust - Seychelles'}) MERGE (o1)-[:LINKED_TO]->(o2)",
            "MATCH (g:Organization {name: 'Garcia Trading LLC'}), (s:Organization {name: 'Supplier Co - Panama'}) MERGE (g)-[:TRADES_WITH]->(s)",
            "MATCH (c:Customer {id: 'CUST-001'}), (o:Organization {name: 'Tech Corp Inc'}) MERGE (c)-[:EMPLOYED_BY]->(o)",
        ]:
            await session.run(cypher)

        # Load sanctions
        logger.info("Loading sanctions data...")
        with open(DATA_DIR / "sanctions.json") as f:
            sanctions = json.load(f)

        for entity in sanctions:
            await session.run(
                "CREATE (s:SanctionedEntity {name: $name, list: $list, reason: $reason, added: $added})",
                name=entity["name"], list=entity["list"],
                reason=entity["reason"], added=entity["added"],
            )
            for alias in entity.get("aliases", []):
                await session.run(
                    """
                    MATCH (s:SanctionedEntity {name: $entity_name})
                    CREATE (a:SanctionAlias {name: $alias})
                    MERGE (a)-[:ALIAS_OF]->(s)
                    """,
                    entity_name=entity["name"], alias=alias,
                )
        logger.info(f"  Created {len(sanctions)} sanctioned entities")

        # Load PEPs
        logger.info("Loading PEP data...")
        with open(DATA_DIR / "pep.json") as f:
            pep_data = json.load(f)

        for pep in pep_data["peps"]:
            await session.run(
                "CREATE (p:PEP {name: $name, position: $position, country: $country, tier: $tier})",
                name=pep["name"], position=pep["position"],
                country=pep["country"], tier=pep["tier"],
            )

        for relative in pep_data.get("pep_relatives", []):
            await session.run(
                """
                CREATE (r:PEPRelative {name: $name, relation: $relation})
                WITH r
                MATCH (p:PEP {name: $pep_name})
                MERGE (r)-[:RELATIVE_OF]->(p)
                """,
                name=relative["name"], relation=relative["relation"],
                pep_name=relative["pep"],
            )
        logger.info(f"  Created {len(pep_data['peps'])} PEPs")

        # Load alerts
        logger.info("Loading alerts...")
        with open(DATA_DIR / "alerts.json") as f:
            alerts = json.load(f)

        for alert in alerts:
            await session.run(
                """
                CREATE (a:Alert {
                    id: $id, type: $type, severity: $severity, status: $status,
                    title: $title, description: $description, evidence: $evidence,
                    requires_sar: $requires_sar, auto_generated: $auto_generated,
                    created_at: datetime()
                })
                WITH a
                MATCH (c:Customer {id: $customer_id})
                MERGE (c)-[:HAS_ALERT]->(a)
                """,
                id=alert["id"], type=alert["type"], severity=alert["severity"],
                status=alert["status"], title=alert["title"],
                description=alert["description"], evidence=alert.get("evidence", []),
                requires_sar=alert.get("requires_sar", False),
                auto_generated=alert.get("auto_generated", True),
                customer_id=alert["customer_id"],
            )
            for txn_id in alert.get("transaction_ids", []):
                await session.run(
                    "MATCH (a:Alert {id: $aid}), (t:Transaction {id: $tid}) MERGE (a)-[:RELATED_TO_TRANSACTION]->(t)",
                    aid=alert["id"], tid=txn_id,
                )
        logger.info(f"  Created {len(alerts)} alerts")

        # Verify
        result = await session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY label")
        records = await result.data()
        logger.info("Data loaded:")
        for record in records:
            logger.info(f"  {record['label']}: {record['count']}")

    await driver.close()
    logger.info("Done!")


def main():
    parser = argparse.ArgumentParser(description="Load sample data into Neo4j")
    parser.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "password"))
    args = parser.parse_args()
    asyncio.run(load_data(args.uri, args.user, args.password))


if __name__ == "__main__":
    main()
