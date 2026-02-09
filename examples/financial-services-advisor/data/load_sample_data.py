#!/usr/bin/env python3
"""Load sample data into the Neo4j Context Graph.

This script loads sample customers, organizations, and transactions
into the Context Graph for demonstration purposes.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.config import EmbeddingConfig, EmbeddingProvider, Neo4jConfig


async def load_sample_data():
    """Load all sample data into the Context Graph."""
    # Initialize memory client
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            username=os.environ.get("NEO4J_USER", "neo4j"),
            password=os.environ.get("NEO4J_PASSWORD", "password"),
            database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        ),
        embedding=EmbeddingConfig(
            provider=EmbeddingProvider.BEDROCK,
            model=os.environ.get(
                "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
            ),
        ),
    )

    client = MemoryClient(settings)
    await client.initialize()

    print("Connected to Neo4j. Loading sample data...")

    data_dir = Path(__file__).parent

    # Load customers
    customers_file = data_dir / "customers.json"
    if customers_file.exists():
        with open(customers_file) as f:
            customers = json.load(f)

        print(f"\nLoading {len(customers)} customers...")
        customer_entities = {}

        for customer in customers:
            # Create customer entity
            description = f"{customer['type'].title()} customer {customer['name']} in {customer['jurisdiction']}"
            if customer.get("industry"):
                description += f", {customer['industry']} sector"

            entity = await client.long_term.add_entity(
                name=customer["name"],
                entity_type="CUSTOMER",
                description=description,
                attributes={
                    "customer_id": customer["id"],
                    "customer_type": customer["type"],
                    "jurisdiction": customer["jurisdiction"],
                    "risk_level": customer.get("risk_level", "unknown"),
                    "industry": customer.get("industry"),
                    "tax_id": customer.get("tax_id"),
                },
            )
            customer_entities[customer["id"]] = entity.id
            print(f"  Created customer: {customer['name']}")

            # Create account entities
            for account in customer.get("accounts", []):
                account_entity = await client.long_term.add_entity(
                    name=f"Account {account['id']}",
                    entity_type="ACCOUNT",
                    description=f"{account['type']} account in {account['currency']}",
                    attributes={
                        "account_id": account["id"],
                        "account_type": account["type"],
                        "currency": account["currency"],
                        "status": account.get("status", "active"),
                    },
                )

                # Link account to customer
                await client.long_term.add_relationship(
                    source_entity_id=entity.id,
                    target_entity_id=account_entity.id,
                    relationship_type="HAS_ACCOUNT",
                    attributes={},
                )
                print(f"    Linked account: {account['id']}")

            # Create contact entities
            for contact in customer.get("contacts", []):
                contact_entity = await client.long_term.add_entity(
                    name=contact["name"],
                    entity_type="PERSON",
                    description=f"{contact['role']} at {customer['name']}",
                    attributes={
                        "role": contact["role"],
                        "email": contact.get("email"),
                        "phone": contact.get("phone"),
                        "pep_status": contact.get("pep_status", False),
                    },
                )

                # Link contact to customer
                await client.long_term.add_relationship(
                    source_entity_id=contact_entity.id,
                    target_entity_id=entity.id,
                    relationship_type="WORKS_AT",
                    attributes={"role": contact["role"]},
                )
                print(f"    Linked contact: {contact['name']}")

    # Load organizations
    orgs_file = data_dir / "organizations.json"
    if orgs_file.exists():
        with open(orgs_file) as f:
            organizations = json.load(f)

        print(f"\nLoading {len(organizations)} organizations...")
        for org in organizations:
            entity = await client.long_term.add_entity(
                name=org["name"],
                entity_type="ORGANIZATION",
                description=f"{org['type'].replace('_', ' ').title()} in {org['jurisdiction']}, {org['industry']} sector",
                attributes={
                    "organization_type": org["type"],
                    "jurisdiction": org["jurisdiction"],
                    "industry": org["industry"],
                    "registration_number": org.get("registration_number"),
                    "incorporation_date": org.get("incorporation_date"),
                    "address": org.get("address"),
                    "shell_indicators": org.get("shell_indicators", []),
                },
            )
            print(f"  Created organization: {org['name']}")

    # Load transactions
    txns_file = data_dir / "transactions.json"
    if txns_file.exists():
        with open(txns_file) as f:
            transactions = json.load(f)

        print(f"\nLoading {len(transactions)} transactions...")
        for txn in transactions:
            beneficiary_info = ""
            if txn.get("beneficiary"):
                beneficiary_info = f" to {txn['beneficiary']['name']}"

            entity = await client.long_term.add_entity(
                name=f"TXN-{txn['id']}",
                entity_type="TRANSACTION",
                description=f"{txn['type'].replace('_', ' ').title()} of {txn['amount']} {txn['currency']}{beneficiary_info}",
                attributes={
                    "transaction_id": txn["id"],
                    "from_account": txn["from_account"],
                    "to_account": txn.get("to_account"),
                    "amount": txn["amount"],
                    "currency": txn["currency"],
                    "transaction_type": txn["type"],
                    "timestamp": txn["timestamp"],
                    "description": txn.get("description"),
                    "beneficiary": txn.get("beneficiary"),
                },
            )
            print(f"  Created transaction: {txn['id']}")

    print("\n✅ Sample data loaded successfully!")
    print("\nData summary:")
    print(f"  - Customers: {len(customers) if 'customers' in dir() else 0}")
    print(f"  - Organizations: {len(organizations) if 'organizations' in dir() else 0}")
    print(f"  - Transactions: {len(transactions) if 'transactions' in dir() else 0}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(load_sample_data())
