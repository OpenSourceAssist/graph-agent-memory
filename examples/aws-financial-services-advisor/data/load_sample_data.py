#!/usr/bin/env python3
"""Load sample financial data into Neo4j for the AWS Financial Services Advisor.

Usage:
    cd data && python load_sample_data.py
    # or from backend/:
    cd backend && uv run python ../data/load_sample_data.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load .env from multiple locations
for env_path in [Path(__file__).parent.parent / "backend" / ".env",
                 Path(__file__).parent.parent / ".env",
                 Path(".env")]:
    if env_path.exists():
        load_dotenv(env_path)
        break

DATA_DIR = Path(__file__).parent


def load_json(filename: str) -> list | dict:
    path = DATA_DIR / filename
    if not path.exists():
        logger.error(f"File not found: {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def clear_data(session):
    logger.info("Clearing existing data...")
    session.run("MATCH (n) DETACH DELETE n")


def create_constraints(session):
    logger.info("Creating constraints...")
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Alert) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:SanctionedEntity) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PEP) REQUIRE p.name IS UNIQUE",
    ]
    for c in constraints:
        session.run(c)


def load_customers(session, customers: list):
    logger.info(f"Loading {len(customers)} customers...")
    for c in customers:
        # Create customer node
        if c["type"] == "individual":
            session.run("""
                MERGE (c:Customer:Person {id: $id})
                SET c.name = $name, c.type = $type, c.date_of_birth = $dob,
                    c.nationality = $nationality, c.address = $address,
                    c.occupation = $occupation, c.employer = $employer,
                    c.account_opened = $account_opened,
                    c.risk_factors = $risk_factors, c.kyc_status = $kyc_status
            """, id=c["id"], name=c["name"], type=c["type"],
                dob=c.get("date_of_birth"), nationality=c.get("nationality"),
                address=c.get("address"), occupation=c.get("occupation"),
                employer=c.get("employer"), account_opened=c.get("account_opened"),
                risk_factors=c.get("risk_factors", []), kyc_status=c.get("kyc_status"))
        else:
            session.run("""
                MERGE (c:Customer:Organization {id: $id})
                SET c.name = $name, c.type = $type,
                    c.incorporation_date = $inc_date, c.jurisdiction = $jurisdiction,
                    c.registered_address = $address, c.business_type = $biz_type,
                    c.directors = $directors, c.account_opened = $account_opened,
                    c.risk_factors = $risk_factors, c.kyc_status = $kyc_status
            """, id=c["id"], name=c["name"], type=c["type"],
                inc_date=c.get("incorporation_date"), jurisdiction=c.get("jurisdiction"),
                address=c.get("registered_address"), biz_type=c.get("business_type"),
                directors=c.get("directors", []), account_opened=c.get("account_opened"),
                risk_factors=c.get("risk_factors", []), kyc_status=c.get("kyc_status"))

        # Create document nodes
        for doc_type, doc_info in c.get("documents", {}).items():
            session.run("""
                MATCH (c:Customer {id: $cid})
                MERGE (d:Document {type: $type, customer_id: $cid})
                SET d.status = $status, d.expiry_date = $expiry, d.submission_date = $date
                MERGE (c)-[:HAS_DOCUMENT]->(d)
            """, cid=c["id"], type=doc_type,
                status=doc_info.get("status"),
                expiry=doc_info.get("expiry"),
                date=doc_info.get("date"))


def load_organizations(session, orgs: list):
    logger.info(f"Loading {len(orgs)} organizations...")
    for o in orgs:
        session.run("""
            MERGE (org:Organization {id: $id})
            SET org.name = $name, org.type = $type, org.jurisdiction = $jurisdiction,
                org.business_type = $biz_type, org.role = $role,
                org.shell_indicators = $shell_indicators
        """, id=o["id"], name=o["name"], type=o.get("type", "ORGANIZATION"),
            jurisdiction=o.get("jurisdiction"), biz_type=o.get("business_type"),
            role=o.get("role", ""), shell_indicators=o.get("shell_indicators", []))


def load_transactions(session, transactions: list):
    logger.info(f"Loading {len(transactions)} transactions...")
    for t in transactions:
        session.run("""
            MATCH (c:Customer {id: $cid})
            MERGE (t:Transaction {id: $id})
            SET t.date = date($date), t.type = $type, t.amount = $amount,
                t.currency = $currency, t.counterparty = $counterparty,
                t.description = $description
            MERGE (c)-[:HAS_TRANSACTION]->(t)
        """, cid=t["customer_id"], id=t["id"], date=t["date"],
            type=t["type"], amount=t["amount"], currency=t.get("currency", "USD"),
            counterparty=t.get("counterparty", ""), description=t.get("description", ""))


def load_sanctions(session, sanctions: list):
    logger.info(f"Loading {len(sanctions)} sanctioned entities...")
    for s in sanctions:
        session.run("""
            MERGE (se:SanctionedEntity {name: $name})
            SET se.list = $list, se.reason = $reason, se.added = $added
        """, name=s["name"], list=s["list"], reason=s["reason"], added=s["added"])
        for alias in s.get("aliases", []):
            session.run("""
                MATCH (se:SanctionedEntity {name: $name})
                MERGE (a:SanctionAlias {name: $alias})
                MERGE (a)-[:ALIAS_OF]->(se)
            """, name=s["name"], alias=alias)


def load_peps(session, pep_data: dict):
    peps = pep_data.get("peps", [])
    relatives = pep_data.get("pep_relatives", [])
    logger.info(f"Loading {len(peps)} PEPs and {len(relatives)} relatives...")
    for p in peps:
        session.run("""
            MERGE (p:PEP {name: $name})
            SET p.position = $position, p.country = $country, p.tier = $tier
        """, name=p["name"], position=p["position"],
            country=p["country"], tier=p["tier"])
    for r in relatives:
        session.run("""
            MATCH (p:PEP {name: $pep_name})
            MERGE (r:PEPRelative {name: $name})
            SET r.relation = $relation
            MERGE (r)-[:RELATIVE_OF]->(p)
        """, pep_name=r["pep"], name=r["name"], relation=r["relation"])


def load_alerts(session, alerts: list):
    logger.info(f"Loading {len(alerts)} alerts...")
    for a in alerts:
        session.run("""
            MATCH (c:Customer {id: $cid})
            MERGE (al:Alert {id: $id})
            SET al.type = $type, al.severity = $severity, al.status = $status,
                al.title = $title, al.description = $description,
                al.evidence = $evidence, al.requires_sar = $requires_sar,
                al.auto_generated = $auto_generated, al.created_at = datetime()
            MERGE (c)-[:HAS_ALERT]->(al)
        """, cid=a["customer_id"], id=a["id"], type=a["type"],
            severity=a["severity"], status=a["status"], title=a["title"],
            description=a["description"], evidence=a.get("evidence", []),
            requires_sar=a.get("requires_sar", False),
            auto_generated=a.get("auto_generated", False))
        # Link to transactions
        for txn_id in a.get("transaction_ids", []):
            session.run("""
                MATCH (al:Alert {id: $aid}), (t:Transaction {id: $tid})
                MERGE (al)-[:RELATED_TO_TRANSACTION]->(t)
            """, aid=a["id"], tid=txn_id)


def create_relationships(session, customers: list, orgs: list):
    logger.info("Creating entity relationships...")

    # OWNS: customer -> org from owners
    for o in orgs:
        for owner_id in o.get("owners", []):
            session.run("""
                MATCH (c:Customer {id: $cid}), (org:Organization {id: $oid})
                MERGE (c)-[:OWNS]->(org)
            """, cid=owner_id, oid=o["id"])

    # CONNECTED_TO: org -> org/customer from connections
    for o in orgs:
        for conn in o.get("connections", []):
            session.run("""
                MATCH (org:Organization {id: $oid})
                OPTIONAL MATCH (target) WHERE target.id = $conn OR target.name = $conn
                WITH org, target WHERE target IS NOT NULL
                MERGE (org)-[:CONNECTED_TO]->(target)
            """, oid=o["id"], conn=conn)

    # DIRECTED_BY: customer -> nominee org from directors
    for c in customers:
        for director in c.get("directors", []):
            session.run("""
                MATCH (cust:Customer {id: $cid})
                OPTIONAL MATCH (d) WHERE d.name = $director
                WITH cust, d WHERE d IS NOT NULL
                MERGE (d)-[:DIRECTED_BY]->(cust)
            """, cid=c["id"], director=director)

    # EMPLOYED_BY: customer -> employer org
    for c in customers:
        employer = c.get("employer")
        if employer:
            session.run("""
                MATCH (cust:Customer {id: $cid})
                OPTIONAL MATCH (org) WHERE org.name = $employer
                WITH cust, org WHERE org IS NOT NULL
                MERGE (cust)-[:EMPLOYED_BY]->(org)
            """, cid=c["id"], employer=employer)


def verify_data(session):
    logger.info("Verifying loaded data...")
    result = session.run("""
        MATCH (n)
        RETURN labels(n)[0] AS label, count(*) AS count
        ORDER BY label
    """)
    for record in result:
        logger.info(f"  {record['label']}: {record['count']}")

    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(*) AS count
        ORDER BY type
    """)
    for record in result:
        logger.info(f"  -{record['type']}->: {record['count']}")


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    logger.info(f"Connecting to Neo4j at {uri}...")

    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        driver.verify_connectivity()
        logger.info("Connected to Neo4j")

        with driver.session(database=database) as session:
            clear_data(session)
            create_constraints(session)

            customers = load_json("customers.json")
            orgs = load_json("organizations.json")
            transactions = load_json("transactions.json")
            sanctions = load_json("sanctions.json")
            pep_data = load_json("pep.json")
            alerts = load_json("alerts.json")

            load_customers(session, customers)
            load_organizations(session, orgs)
            load_transactions(session, transactions)
            load_sanctions(session, sanctions)
            load_peps(session, pep_data)
            load_alerts(session, alerts)
            create_relationships(session, customers, orgs)
            verify_data(session)

        logger.info("Sample data loaded successfully!")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
