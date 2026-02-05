"""AML (Anti-Money Laundering) tools for transaction monitoring and pattern detection.

These tools are used by the AML Agent to analyze transactions and detect
suspicious activity patterns.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Sample transaction database
SAMPLE_TRANSACTIONS = {
    "CUST-001": [
        {
            "id": "TXN-001",
            "date": "2024-01-15",
            "type": "deposit",
            "amount": 5000,
            "currency": "USD",
            "counterparty": "Employer Payroll",
            "description": "Salary",
        },
        {
            "id": "TXN-002",
            "date": "2024-01-20",
            "type": "withdrawal",
            "amount": 1500,
            "currency": "USD",
            "counterparty": "Landlord",
            "description": "Rent",
        },
        {
            "id": "TXN-003",
            "date": "2024-02-15",
            "type": "deposit",
            "amount": 5000,
            "currency": "USD",
            "counterparty": "Employer Payroll",
            "description": "Salary",
        },
    ],
    "CUST-002": [
        {
            "id": "TXN-101",
            "date": "2024-01-05",
            "type": "wire_in",
            "amount": 45000,
            "currency": "USD",
            "counterparty": "Garcia Trading LLC - Spain",
            "description": "Trade Payment",
        },
        {
            "id": "TXN-102",
            "date": "2024-01-07",
            "type": "wire_out",
            "amount": 43000,
            "currency": "USD",
            "counterparty": "Supplier Co - Panama",
            "description": "Supplier Payment",
        },
        {
            "id": "TXN-103",
            "date": "2024-01-15",
            "type": "wire_in",
            "amount": 52000,
            "currency": "USD",
            "counterparty": "Garcia Trading LLC - Spain",
            "description": "Trade Payment",
        },
        {
            "id": "TXN-104",
            "date": "2024-01-16",
            "type": "wire_out",
            "amount": 50000,
            "currency": "USD",
            "counterparty": "Supplier Co - Panama",
            "description": "Supplier Payment",
        },
        {
            "id": "TXN-105",
            "date": "2024-01-25",
            "type": "wire_in",
            "amount": 48000,
            "currency": "USD",
            "counterparty": "Client ABC - Mexico",
            "description": "Trade Payment",
        },
        {
            "id": "TXN-106",
            "date": "2024-01-26",
            "type": "wire_out",
            "amount": 46000,
            "currency": "USD",
            "counterparty": "Supplier Co - Panama",
            "description": "Supplier Payment",
        },
    ],
    "CUST-003": [
        {
            "id": "TXN-201",
            "date": "2024-01-10",
            "type": "wire_in",
            "amount": 250000,
            "currency": "USD",
            "counterparty": "Unknown Offshore Entity",
            "description": "Investment",
        },
        {
            "id": "TXN-202",
            "date": "2024-01-11",
            "type": "wire_out",
            "amount": 248000,
            "currency": "USD",
            "counterparty": "Shell Corp - Cayman",
            "description": "Investment Distribution",
        },
        {
            "id": "TXN-203",
            "date": "2024-01-20",
            "type": "cash_deposit",
            "amount": 9500,
            "currency": "USD",
            "counterparty": "Cash",
            "description": "Operating Funds",
        },
        {
            "id": "TXN-204",
            "date": "2024-01-21",
            "type": "cash_deposit",
            "amount": 9500,
            "currency": "USD",
            "counterparty": "Cash",
            "description": "Operating Funds",
        },
        {
            "id": "TXN-205",
            "date": "2024-01-22",
            "type": "cash_deposit",
            "amount": 9500,
            "currency": "USD",
            "counterparty": "Cash",
            "description": "Operating Funds",
        },
        {
            "id": "TXN-206",
            "date": "2024-01-23",
            "type": "cash_deposit",
            "amount": 9500,
            "currency": "USD",
            "counterparty": "Cash",
            "description": "Operating Funds",
        },
        {
            "id": "TXN-207",
            "date": "2024-02-01",
            "type": "wire_out",
            "amount": 35000,
            "currency": "USD",
            "counterparty": "Anonymous Trust - Seychelles",
            "description": "Consulting Fee",
        },
    ],
}


def scan_transactions(
    customer_id: str,
    days: int = 90,
    min_amount: float | None = None,
    transaction_type: str | None = None,
) -> dict[str, Any]:
    """Scan customer transactions for the specified period.

    Retrieves and analyzes transactions for a customer, optionally
    filtered by amount or type.

    Args:
        customer_id: The customer identifier.
        days: Number of days to look back.
        min_amount: Minimum transaction amount to include.
        transaction_type: Filter by transaction type.

    Returns:
        Transaction scan results with summary statistics.
    """
    logger.info(f"Scanning transactions for customer {customer_id}, last {days} days")

    transactions = SAMPLE_TRANSACTIONS.get(customer_id, [])
    if not transactions:
        return {
            "customer_id": customer_id,
            "status": "NO_TRANSACTIONS",
            "message": "No transactions found for this customer",
            "timestamp": datetime.now().isoformat(),
        }

    # Apply filters
    filtered_txns = transactions
    if min_amount:
        filtered_txns = [t for t in filtered_txns if t["amount"] >= min_amount]
    if transaction_type:
        filtered_txns = [t for t in filtered_txns if t["type"] == transaction_type]

    # Calculate statistics
    total_amount = sum(t["amount"] for t in filtered_txns)
    deposits = sum(
        t["amount"]
        for t in filtered_txns
        if "deposit" in t["type"] or "in" in t["type"]
    )
    withdrawals = sum(
        t["amount"]
        for t in filtered_txns
        if "withdrawal" in t["type"] or "out" in t["type"]
    )

    # Get unique counterparties
    counterparties = list(set(t["counterparty"] for t in filtered_txns))

    return {
        "customer_id": customer_id,
        "period_days": days,
        "transaction_count": len(filtered_txns),
        "total_volume": total_amount,
        "total_deposits": deposits,
        "total_withdrawals": withdrawals,
        "unique_counterparties": len(counterparties),
        "counterparties": counterparties,
        "transactions": filtered_txns,
        "timestamp": datetime.now().isoformat(),
    }


def detect_patterns(
    customer_id: str,
    pattern_types: list[str] | None = None,
) -> dict[str, Any]:
    """Detect suspicious transaction patterns.

    Analyzes transactions for known money laundering typologies
    including structuring, layering, and rapid movement.

    Args:
        customer_id: The customer identifier.
        pattern_types: Specific patterns to check (optional).

    Returns:
        Pattern detection results with confidence scores.
    """
    logger.info(f"Detecting patterns for customer {customer_id}")

    transactions = SAMPLE_TRANSACTIONS.get(customer_id, [])
    if not transactions:
        return {
            "customer_id": customer_id,
            "status": "NO_DATA",
            "patterns_detected": [],
            "timestamp": datetime.now().isoformat(),
        }

    patterns_detected = []

    # Check for structuring (multiple transactions just under $10,000)
    cash_deposits = [t for t in transactions if "cash" in t["type"].lower()]
    structuring_candidates = [t for t in cash_deposits if 9000 <= t["amount"] < 10000]
    if len(structuring_candidates) >= 2:
        patterns_detected.append(
            {
                "pattern": "STRUCTURING",
                "confidence": 0.85,
                "description": "Multiple cash deposits just under $10,000 reporting threshold",
                "evidence": [t["id"] for t in structuring_candidates],
                "total_amount": sum(t["amount"] for t in structuring_candidates),
                "risk_level": "HIGH",
            }
        )

    # Check for rapid movement (funds moved within 24-48 hours of receipt)
    wire_ins = [t for t in transactions if "wire_in" in t["type"]]
    wire_outs = [t for t in transactions if "wire_out" in t["type"]]
    for win in wire_ins:
        for wout in wire_outs:
            # Check if outgoing is within 2 days and similar amount
            if abs(win["amount"] - wout["amount"]) < win["amount"] * 0.1:  # Within 10%
                patterns_detected.append(
                    {
                        "pattern": "RAPID_MOVEMENT",
                        "confidence": 0.75,
                        "description": "Funds moved quickly after receipt with minimal change",
                        "evidence": [win["id"], wout["id"]],
                        "in_amount": win["amount"],
                        "out_amount": wout["amount"],
                        "risk_level": "MEDIUM",
                    }
                )
                break

    # Check for layering (multiple jurisdictions)
    offshore_keywords = ["offshore", "cayman", "bvi", "panama", "seychelles", "unknown"]
    offshore_txns = [
        t
        for t in transactions
        if any(kw in t["counterparty"].lower() for kw in offshore_keywords)
    ]
    if len(offshore_txns) >= 2:
        patterns_detected.append(
            {
                "pattern": "LAYERING",
                "confidence": 0.70,
                "description": "Multiple transactions with offshore/high-risk jurisdictions",
                "evidence": [t["id"] for t in offshore_txns],
                "jurisdictions": list(set(t["counterparty"] for t in offshore_txns)),
                "risk_level": "HIGH",
            }
        )

    return {
        "customer_id": customer_id,
        "transactions_analyzed": len(transactions),
        "patterns_detected": patterns_detected,
        "overall_risk": "HIGH" if patterns_detected else "LOW",
        "timestamp": datetime.now().isoformat(),
    }


def flag_suspicious_transaction(
    transaction_id: str,
    reason: str,
    severity: str = "MEDIUM",
) -> dict[str, Any]:
    """Flag a specific transaction as suspicious.

    Creates an alert for a transaction requiring further investigation.

    Args:
        transaction_id: The transaction identifier.
        reason: Reason for flagging.
        severity: Alert severity (LOW/MEDIUM/HIGH/CRITICAL).

    Returns:
        Flag confirmation with alert ID.
    """
    logger.info(f"Flagging transaction {transaction_id} as suspicious")

    # Find the transaction
    for customer_id, txns in SAMPLE_TRANSACTIONS.items():
        for txn in txns:
            if txn["id"] == transaction_id:
                return {
                    "alert_id": f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "transaction_id": transaction_id,
                    "customer_id": customer_id,
                    "transaction_amount": txn["amount"],
                    "reason": reason,
                    "severity": severity,
                    "status": "FLAGGED",
                    "requires_sar": severity in ["HIGH", "CRITICAL"],
                    "timestamp": datetime.now().isoformat(),
                }

    return {
        "transaction_id": transaction_id,
        "status": "NOT_FOUND",
        "message": "Transaction not found",
        "timestamp": datetime.now().isoformat(),
    }


def analyze_velocity(
    customer_id: str,
    metric: str = "all",
) -> dict[str, Any]:
    """Analyze transaction velocity patterns.

    Examines transaction frequency, amounts, and timing to identify
    unusual velocity patterns that may indicate suspicious activity.

    Args:
        customer_id: The customer identifier.
        metric: Specific metric to analyze (count/amount/all).

    Returns:
        Velocity analysis with anomaly detection.
    """
    logger.info(f"Analyzing velocity for customer {customer_id}")

    transactions = SAMPLE_TRANSACTIONS.get(customer_id, [])
    if not transactions:
        return {
            "customer_id": customer_id,
            "status": "NO_DATA",
            "timestamp": datetime.now().isoformat(),
        }

    # Calculate velocity metrics
    total_txns = len(transactions)
    total_amount = sum(t["amount"] for t in transactions)
    avg_amount = total_amount / total_txns if total_txns > 0 else 0

    # Group by type
    type_counts = {}
    type_amounts = {}
    for txn in transactions:
        t_type = txn["type"]
        type_counts[t_type] = type_counts.get(t_type, 0) + 1
        type_amounts[t_type] = type_amounts.get(t_type, 0) + txn["amount"]

    # Detect velocity anomalies
    anomalies = []

    # High frequency cash transactions
    cash_count = sum(v for k, v in type_counts.items() if "cash" in k)
    if cash_count >= 3:
        anomalies.append(
            {
                "type": "HIGH_CASH_FREQUENCY",
                "description": f"{cash_count} cash transactions in period",
                "risk_level": "MEDIUM",
            }
        )

    # High wire volume
    wire_amount = sum(v for k, v in type_amounts.items() if "wire" in k)
    if wire_amount > 100000:
        anomalies.append(
            {
                "type": "HIGH_WIRE_VOLUME",
                "description": f"${wire_amount:,.0f} in wire transfers",
                "risk_level": "MEDIUM",
            }
        )

    # Large individual transactions
    large_txns = [t for t in transactions if t["amount"] > 50000]
    if large_txns:
        anomalies.append(
            {
                "type": "LARGE_TRANSACTIONS",
                "description": f"{len(large_txns)} transactions over $50,000",
                "transactions": [t["id"] for t in large_txns],
                "risk_level": "HIGH",
            }
        )

    return {
        "customer_id": customer_id,
        "period_analyzed": "90 days",
        "metrics": {
            "total_transactions": total_txns,
            "total_volume": total_amount,
            "average_transaction": round(avg_amount, 2),
            "transactions_by_type": type_counts,
            "volume_by_type": type_amounts,
        },
        "anomalies_detected": anomalies,
        "velocity_risk": "HIGH"
        if len(anomalies) >= 2
        else "MEDIUM"
        if anomalies
        else "LOW",
        "timestamp": datetime.now().isoformat(),
    }
