"""FastAPI application for Google Cloud Financial Advisor.

This is the main entry point for the backend API, which provides
endpoints for interacting with the multi-agent financial compliance
system powered by Google ADK and Neo4j Agent Memory.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import alerts, chat, customers, graph, investigations
from .config import get_settings
from .services.memory_service import get_memory_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info("Starting Google Cloud Financial Advisor...")

    # Initialize memory service
    memory_service = get_memory_service()
    try:
        await memory_service.initialize()
        logger.info("Memory service initialized")
    except Exception as e:
        logger.warning(f"Memory service initialization failed: {e}")
        logger.warning("Some features may be unavailable without Neo4j connection")

    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        await memory_service.close()
    except Exception as e:
        logger.warning(f"Error closing memory service: {e}")


# Create FastAPI app
app = FastAPI(
    title="Google Cloud Financial Advisor",
    description="""
AI-powered financial compliance assistant using Google ADK and Neo4j Agent Memory.

## Features
- **Multi-Agent System**: Coordinated KYC, AML, Relationship, and Compliance agents
- **Context Graph Intelligence**: Neo4j-powered relationship analysis
- **Vertex AI Integration**: Gemini for reasoning, text-embedding-004 for search
- **Explainable AI**: Full audit trails for regulatory compliance

## Agents
- **Supervisor**: Orchestrates investigations, synthesizes findings
- **KYC Agent**: Identity verification, document validation
- **AML Agent**: Transaction monitoring, pattern detection
- **Relationship Agent**: Network analysis, beneficial ownership
- **Compliance Agent**: Sanctions screening, PEP verification
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(chat.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(investigations.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(graph.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Google Cloud Financial Advisor",
        "version": "0.1.0",
        "description": "AI-powered financial compliance assistant",
        "platform": "Google Cloud",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "platform": "Google Cloud",
        "service": "financial-advisor",
    }


@app.get("/api/info")
async def api_info():
    """Get API information and available agents."""
    return {
        "agents": [
            {
                "name": "supervisor",
                "description": "Orchestrates multi-agent investigations",
            },
            {
                "name": "kyc_agent",
                "description": "Identity verification and customer due diligence",
            },
            {
                "name": "aml_agent",
                "description": "Transaction monitoring and suspicious activity detection",
            },
            {
                "name": "relationship_agent",
                "description": "Network analysis and beneficial ownership tracing",
            },
            {
                "name": "compliance_agent",
                "description": "Sanctions screening and regulatory reporting",
            },
        ],
        "memory_types": [
            "short_term (conversation history)",
            "long_term (entities, preferences, facts)",
            "reasoning (audit trails, tool usage)",
        ],
        "endpoints": {
            "chat": "/api/chat",
            "customers": "/api/customers",
            "investigations": "/api/investigations",
            "alerts": "/api/alerts",
            "graph": "/api/graph",
        },
    }
