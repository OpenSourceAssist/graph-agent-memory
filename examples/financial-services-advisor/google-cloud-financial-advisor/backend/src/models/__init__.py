"""Pydantic models for API requests and responses."""

from .alert import Alert, AlertCreate, AlertSeverity
from .chat import (
    AgentResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ToolCall,
)
from .customer import Customer, CustomerCreate, CustomerRisk
from .investigation import (
    AuditTrailEntry,
    Investigation,
    InvestigationCreate,
    InvestigationStatus,
)

__all__ = [
    # Customer models
    "Customer",
    "CustomerCreate",
    "CustomerRisk",
    # Investigation models
    "Investigation",
    "InvestigationCreate",
    "InvestigationStatus",
    "AuditTrailEntry",
    # Alert models
    "Alert",
    "AlertCreate",
    "AlertSeverity",
    # Chat models
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "AgentResponse",
    "ToolCall",
]
