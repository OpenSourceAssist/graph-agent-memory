"""AML Agent for anti-money laundering detection and analysis."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

from strands import Agent, tool
from strands.models import BedrockModel

from ..config import get_settings
from .prompts import AML_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Global agent instance
_aml_agent: Agent | None = None

# Common money laundering patterns
ML_PATTERNS = {
    "structuring": {
        "name": "Structuring (Smurfing)",
        "description": "Multiple transactions just below reporting threshold",
        "threshold": 10000,
        "indicators": ["multiple_sub_threshold", "same_day_deposits", "round_amounts"],
    },
    "layering": {
        "name": "Layering",
        "description": "Rapid movement of funds through multiple accounts",
        "indicators": ["rapid_transfers", "multiple_intermediaries", "complex_paths"],
    },
    "round_tripping": {
        "name": "Round-Trip Transactions",
        "description": "Funds returning to origin through circuitous route",
        "indicators": [
            "circular_flow",
            "same_origin_destination",
            "shell_intermediaries",
        ],
    },
    "trade_based": {
        "name": "Trade-Based Money Laundering",
        "description": "Over/under invoicing in trade transactions",
        "indicators": [
            "price_discrepancies",
            "unusual_trade_terms",
            "mismatched_goods",
        ],
    },
    "shell_company": {
        "name": "Shell Company Usage",
        "description": "Transactions with entities showing shell company indicators",
        "indicators": ["no_operations", "nominee_directors", "offshore_jurisdiction"],
    },
}


@tool
def scan_transactions(
    customer_id: str,
    days: int = 90,
    min_amount: float | None = None,
    include_counterparties: bool = True,
) -> dict[str, Any]:
    """Analyze customer transactions for suspicious activity.

    Use this tool to scan transaction history for anomalies, unusual patterns,
    or indicators of money laundering.

    Args:
        customer_id: The customer identifier
        days: Number of days of history to analyze
        min_amount: Minimum transaction amount to include
        include_counterparties: Whether to analyze counterparty risk

    Returns:
        Transaction analysis with flagged items and statistics
    """
    logger.info(f"Scanning transactions for customer {customer_id}, last {days} days")

    # Simulated transaction data
    transaction_count = random.randint(20, 200)
    total_volume = random.uniform(50000, 2000000)

    # Generate sample flagged transactions
    flagged_count = random.randint(0, min(10, transaction_count // 10))
    flagged_transactions = []

    for i in range(flagged_count):
        flag_reason = random.choice(
            [
                "Unusual amount for customer profile",
                "High-risk jurisdiction counterparty",
                "Potential structuring pattern",
                "Rapid fund movement",
                "Round amount suspicious",
            ]
        )

        flagged_transactions.append(
            {
                "transaction_id": f"TXN-{random.randint(10000, 99999)}",
                "date": (
                    datetime.utcnow() - timedelta(days=random.randint(1, days))
                ).isoformat(),
                "amount": random.uniform(5000, 50000),
                "currency": "USD",
                "type": random.choice(["wire_transfer", "ach", "cash_deposit"]),
                "flag_reason": flag_reason,
                "risk_score": random.uniform(0.6, 0.95),
            }
        )

    # Calculate statistics
    avg_transaction = total_volume / transaction_count if transaction_count > 0 else 0
    cash_ratio = random.uniform(0.05, 0.35)
    high_risk_jurisdiction_ratio = random.uniform(0, 0.15)

    return {
        "customer_id": customer_id,
        "analysis_period": {
            "days": days,
            "start_date": (datetime.utcnow() - timedelta(days=days)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
        },
        "statistics": {
            "total_transactions": transaction_count,
            "total_volume": round(total_volume, 2),
            "average_transaction": round(avg_transaction, 2),
            "cash_transaction_ratio": round(cash_ratio, 3),
            "high_risk_jurisdiction_ratio": round(high_risk_jurisdiction_ratio, 3),
        },
        "flagged_transactions": flagged_transactions,
        "flagged_count": len(flagged_transactions),
        "risk_assessment": (
            "high"
            if len(flagged_transactions) > 5
            else "medium"
            if flagged_transactions
            else "low"
        ),
        "scan_timestamp": datetime.utcnow().isoformat(),
    }


@tool
def detect_patterns(
    customer_id: str,
    pattern_types: list[str] | None = None,
    sensitivity: str = "medium",
) -> dict[str, Any]:
    """Identify money laundering patterns in customer activity.

    Use this tool to detect known typologies like structuring, layering,
    or trade-based money laundering.

    Args:
        customer_id: The customer identifier
        pattern_types: Specific patterns to check (None = all patterns)
        sensitivity: Detection sensitivity (low, medium, high)

    Returns:
        Detected patterns with confidence scores and evidence
    """
    logger.info(f"Detecting patterns for customer {customer_id}")

    if pattern_types is None:
        pattern_types = list(ML_PATTERNS.keys())

    sensitivity_thresholds = {
        "low": 0.8,
        "medium": 0.6,
        "high": 0.4,
    }
    threshold = sensitivity_thresholds.get(sensitivity, 0.6)

    detected_patterns = []

    for pattern_type in pattern_types:
        if pattern_type not in ML_PATTERNS:
            continue

        pattern_info = ML_PATTERNS[pattern_type]

        # Simulate pattern detection
        confidence = random.uniform(0.3, 0.95)

        if confidence >= threshold:
            # Generate sample evidence
            indicator_matches = random.sample(
                pattern_info["indicators"],
                k=min(len(pattern_info["indicators"]), random.randint(1, 3)),
            )

            detected_patterns.append(
                {
                    "pattern_type": pattern_type,
                    "pattern_name": pattern_info["name"],
                    "description": pattern_info["description"],
                    "confidence": round(confidence, 3),
                    "matched_indicators": indicator_matches,
                    "sample_transactions": [
                        f"TXN-{random.randint(10000, 99999)}"
                        for _ in range(random.randint(2, 5))
                    ],
                    "estimated_exposure": round(random.uniform(10000, 500000), 2),
                    "first_detected": (
                        datetime.utcnow() - timedelta(days=random.randint(1, 30))
                    ).isoformat(),
                }
            )

    # Sort by confidence
    detected_patterns.sort(key=lambda x: x["confidence"], reverse=True)

    total_exposure = sum(p["estimated_exposure"] for p in detected_patterns)

    return {
        "customer_id": customer_id,
        "patterns_checked": pattern_types,
        "sensitivity": sensitivity,
        "detection_threshold": threshold,
        "patterns_detected": detected_patterns,
        "pattern_count": len(detected_patterns),
        "total_estimated_exposure": round(total_exposure, 2),
        "risk_level": (
            "critical"
            if len(detected_patterns) > 2
            else "high"
            if detected_patterns
            else "low"
        ),
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


@tool
def flag_suspicious(
    customer_id: str,
    transaction_ids: list[str],
    flag_type: str,
    description: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a suspicious activity flag with detailed documentation.

    Use this tool to formally flag transactions as suspicious, creating
    an audit trail for potential SAR filing.

    Args:
        customer_id: The customer identifier
        transaction_ids: List of transaction IDs to flag
        flag_type: Type of suspicious activity
        description: Detailed description of the suspicious activity
        evidence: Supporting evidence and documentation

    Returns:
        Flag creation confirmation with alert ID
    """
    logger.info(f"Flagging suspicious activity for customer {customer_id}")

    alert_id = f"ALT-{random.randint(100000, 999999)}"

    # Determine severity based on flag type
    severity_map = {
        "structuring": "high",
        "layering": "high",
        "sanctions_exposure": "critical",
        "unusual_pattern": "medium",
        "high_risk_counterparty": "medium",
        "velocity_breach": "medium",
    }
    severity = severity_map.get(flag_type, "medium")

    return {
        "alert_id": alert_id,
        "customer_id": customer_id,
        "transaction_ids": transaction_ids,
        "flag_type": flag_type,
        "severity": severity,
        "description": description,
        "evidence": evidence or {},
        "status": "new",
        "created_at": datetime.utcnow().isoformat(),
        "requires_sar": severity in ("high", "critical"),
        "escalation_required": severity == "critical",
        "next_steps": [
            "Review by compliance team",
            "Gather additional documentation",
            "Consider SAR filing"
            if severity in ("high", "critical")
            else "Monitor activity",
        ],
    }


@tool
def analyze_velocity(
    customer_id: str,
    metric: str = "transaction_count",
    period_hours: int = 24,
    compare_to_baseline: bool = True,
) -> dict[str, Any]:
    """Detect unusual transaction velocity or frequency.

    Use this tool to identify sudden spikes in transaction activity
    that may indicate suspicious behavior.

    Args:
        customer_id: The customer identifier
        metric: Velocity metric (transaction_count, volume, unique_counterparties)
        period_hours: Analysis period in hours
        compare_to_baseline: Whether to compare against historical baseline

    Returns:
        Velocity analysis with deviation from normal patterns
    """
    logger.info(f"Analyzing velocity for customer {customer_id}")

    # Simulated velocity metrics
    current_value = random.uniform(5, 50)
    baseline_value = random.uniform(10, 30)

    if compare_to_baseline:
        deviation = ((current_value - baseline_value) / baseline_value) * 100
        deviation_direction = "above" if deviation > 0 else "below"
    else:
        deviation = 0
        deviation_direction = "n/a"

    # Determine if velocity is suspicious
    is_suspicious = abs(deviation) > 100  # More than 100% deviation

    metric_labels = {
        "transaction_count": "transactions",
        "volume": "USD",
        "unique_counterparties": "counterparties",
    }

    return {
        "customer_id": customer_id,
        "metric": metric,
        "period_hours": period_hours,
        "current_value": round(current_value, 2),
        "current_unit": metric_labels.get(metric, "units"),
        "baseline_comparison": {
            "enabled": compare_to_baseline,
            "baseline_value": round(baseline_value, 2) if compare_to_baseline else None,
            "deviation_percentage": round(deviation, 2)
            if compare_to_baseline
            else None,
            "deviation_direction": deviation_direction,
        },
        "is_anomalous": is_suspicious,
        "anomaly_severity": (
            "high" if abs(deviation) > 200 else "medium" if is_suspicious else "low"
        ),
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "recommendation": (
            "Immediate review recommended - significant velocity anomaly"
            if is_suspicious
            else "Velocity within normal parameters"
        ),
    }


def create_aml_agent() -> Agent:
    """Create the AML Agent for money laundering detection.

    Returns:
        Configured Strands Agent for AML operations
    """
    settings = get_settings()

    aml_tools = [
        scan_transactions,
        detect_patterns,
        flag_suspicious,
        analyze_velocity,
    ]

    return Agent(
        model=BedrockModel(
            model_id=settings.bedrock.model_id,
            region_name=settings.aws.region,
        ),
        tools=aml_tools,
        system_prompt=AML_AGENT_SYSTEM_PROMPT,
    )


def get_aml_agent() -> Agent:
    """Get or create the global AML Agent instance.

    Returns:
        AML Agent instance
    """
    global _aml_agent
    if _aml_agent is None:
        _aml_agent = create_aml_agent()
    return _aml_agent
