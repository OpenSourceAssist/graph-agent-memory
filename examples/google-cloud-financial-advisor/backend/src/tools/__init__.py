"""Tools for Google ADK Financial Advisor agents."""

from .aml_tools import (
    analyze_velocity,
    detect_patterns,
    flag_suspicious_transaction,
    scan_transactions,
)
from .compliance_tools import (
    assess_regulatory_requirements,
    check_sanctions,
    generate_sar_report,
    verify_pep_status,
)
from .kyc_tools import (
    assess_customer_risk,
    check_adverse_media,
    check_documents,
    verify_identity,
)
from .relationship_tools import (
    analyze_network_risk,
    detect_shell_companies,
    find_connections,
    map_beneficial_ownership,
)

__all__ = [
    # KYC tools
    "verify_identity",
    "check_documents",
    "assess_customer_risk",
    "check_adverse_media",
    # AML tools
    "scan_transactions",
    "detect_patterns",
    "flag_suspicious_transaction",
    "analyze_velocity",
    # Relationship tools
    "find_connections",
    "analyze_network_risk",
    "detect_shell_companies",
    "map_beneficial_ownership",
    # Compliance tools
    "check_sanctions",
    "verify_pep_status",
    "generate_sar_report",
    "assess_regulatory_requirements",
]
