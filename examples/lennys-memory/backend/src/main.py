"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import chat, memory, threads
from src.config import get_settings
from src.memory.client import close_memory_client, init_memory_client, is_memory_connected

# Set OpenAI API key from settings early, before any agent initialization
_settings = get_settings()
if _settings.openai_api_key.get_secret_value():
    os.environ["OPENAI_API_KEY"] = _settings.openai_api_key.get_secret_value()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    await init_memory_client()
    yield
    # Shutdown
    await close_memory_client()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Lenny's Podcast Memory Explorer",
        description="An AI agent for exploring Lenny's Podcast content with memory",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(threads.router, prefix="/api", tags=["threads"])
    app.include_router(memory.router, prefix="/api", tags=["memory"])

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "memory_connected": is_memory_connected(),
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
