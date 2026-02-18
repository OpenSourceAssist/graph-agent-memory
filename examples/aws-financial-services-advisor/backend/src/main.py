"""FastAPI main application for Financial Services Advisor."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import alerts, chat, customers, graph, investigations, reports
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

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Financial Services Advisor...")

    settings = get_settings()
    logger.info(f"Environment: debug={settings.app.debug}")

    # Initialize memory service
    try:
        memory_service = get_memory_service()
        await memory_service.initialize()
        logger.info("Memory service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize memory service: {e}")
        logger.warning(
            "Running without Neo4j connection - some features will be limited"
        )

    logger.info("Financial Services Advisor started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Financial Services Advisor...")

    try:
        memory_service = get_memory_service()
        await memory_service.close()
        logger.info("Memory service closed")
    except Exception as e:
        logger.warning(f"Error closing memory service: {e}")

    logger.info("Financial Services Advisor shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Financial Services Advisor",
    description="""
    An intelligent financial compliance assistant powered by AWS Strands Agents
    and Neo4j Agent Memory Context Graphs.

    ## Features

    - **Multi-Agent Investigation**: Coordinated KYC, AML, and compliance analysis
    - **Context Graph Intelligence**: Relationship mapping and network analysis
    - **Explainable AI**: Full audit trails for regulatory compliance
    - **Real-time Monitoring**: Transaction and behavior pattern detection

    ## API Groups

    - **Chat**: Interact with the AI advisor
    - **Customers**: Customer management and risk assessment
    - **Investigations**: Compliance investigations with audit trails
    - **Alerts**: Alert management and escalation
    - **Graph**: Relationship visualization and exploration
    - **Reports**: SAR and compliance report generation
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(investigations.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Financial Services Advisor",
        "version": "0.1.0",
        "description": "AI-powered financial compliance assistant",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint.

    Returns the health status of the application and its dependencies.
    """
    health_status = {
        "status": "healthy",
        "version": "0.1.0",
        "components": {},
    }

    # Check memory service
    try:
        memory_service = get_memory_service()
        # Would perform actual health check in production
        health_status["components"]["neo4j"] = {
            "status": "healthy" if memory_service._initialized else "not_initialized",
        }
    except Exception as e:
        health_status["components"]["neo4j"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Check settings
    try:
        settings = get_settings()
        health_status["components"]["config"] = {
            "status": "healthy",
            "bedrock_model": settings.bedrock.model_id,
        }
    except Exception as e:
        health_status["components"]["config"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Overall status
    unhealthy = [
        c
        for c, s in health_status["components"].items()
        if s.get("status") != "healthy"
    ]
    if unhealthy:
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/info")
async def api_info() -> dict[str, Any]:
    """Get information about the API and available agents."""
    return {
        "api_version": "0.1.0",
        "agents": {
            "supervisor": {
                "description": "Orchestrates investigations by delegating to specialized agents",
                "capabilities": [
                    "Task delegation",
                    "Investigation coordination",
                    "Finding synthesis",
                ],
            },
            "kyc": {
                "description": "Customer identity verification and due diligence",
                "capabilities": [
                    "Identity verification",
                    "Document checking",
                    "Risk assessment",
                    "Adverse media screening",
                ],
            },
            "aml": {
                "description": "Anti-money laundering detection and analysis",
                "capabilities": [
                    "Transaction scanning",
                    "Pattern detection",
                    "Suspicious activity flagging",
                    "Velocity analysis",
                ],
            },
            "relationship": {
                "description": "Network analysis and relationship mapping",
                "capabilities": [
                    "Connection finding",
                    "Network risk analysis",
                    "Shell company detection",
                    "Beneficial ownership mapping",
                ],
            },
            "compliance": {
                "description": "Regulatory compliance and report generation",
                "capabilities": [
                    "Sanctions screening",
                    "PEP verification",
                    "Report generation",
                    "Regulatory assessment",
                ],
            },
        },
        "memory_types": {
            "short_term": "Conversation history and session context",
            "long_term": "Customer profiles, entities, and relationships",
            "reasoning": "Investigation traces and decision audit trails",
        },
        "supported_reports": [
            "Suspicious Activity Report (SAR)",
            "Risk Assessment Report",
            "Enhanced Due Diligence Report",
            "Periodic Review Report",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
