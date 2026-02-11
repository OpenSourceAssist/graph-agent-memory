"""FastAPI routes for Google Cloud Financial Advisor."""

from .routes import alerts, chat, customers, graph, investigations

__all__ = [
    "chat",
    "customers",
    "investigations",
    "alerts",
    "graph",
]
