"""NAMS + FastAPI — chat endpoint backed by hosted Neo4j Agent Memory Service.

Demonstrates the production wiring pattern for a NAMS-backed FastAPI
app: lifespan-managed ``MemoryClient``, per-request conversation ids,
multi-tenant ``user_identifier`` scoping, and graceful shutdown of the
HTTP transport.

Run:

    export MEMORY_API_KEY=nams_xxxxx
    uv run uvicorn main:app --reload
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from neo4j_agent_memory import MemoryClient, MemorySettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one shared MemoryClient for the whole app lifetime.

    This is the recommended pattern — a single HTTP transport pool is
    reused across every request, so no per-request connection churn.
    """
    if not os.environ.get("MEMORY_API_KEY"):
        raise RuntimeError(
            "Set MEMORY_API_KEY env var to your NAMS API key. "
            "Sign up at https://memory.neo4jlabs.com."
        )

    client = MemoryClient(MemorySettings(backend="nams"))
    await client.connect()
    app.state.memory = client
    try:
        yield
    finally:
        await client.close()


app = FastAPI(lifespan=lifespan)


def get_memory() -> MemoryClient:
    """Dependency: return the shared MemoryClient.

    Imports app.state at call time so FastAPI can wire it after lifespan.
    """
    return app.state.memory  # type: ignore[no-any-return]


class ChatRequest(BaseModel):
    """Per-message request shape."""

    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    """Echo response shape — replace with your real agent output."""

    conversation_id: str
    message_count: int
    last_user_message: str


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    memory: Annotated[MemoryClient, Depends(get_memory)],
    user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> ChatResponse:
    """Append a user message and return the current conversation length.

    The ``X-User-Id`` header is forwarded to NAMS as ``user_identifier``
    so the conversation is scoped per-user within your NAMS workspace.
    If the caller omits ``conversation_id``, the server creates a new NAMS
    conversation and returns its canonical id.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        conversation_id = request.conversation_id
        if conversation_id is None:
            conversation_id = "fastapi-chat"
            create_conversation = getattr(memory.short_term, "create_conversation", None)
            if callable(create_conversation):
                conversation = await create_conversation(
                    conversation_id,
                    user_identifier=user_id,
                )
                conversation_id = str(conversation.id)
        await memory.short_term.add_message(
            conversation_id,
            "user",
            request.message,
            user_identifier=user_id,
        )
    except Exception as e:  # noqa: BLE001 — demo error path
        raise HTTPException(status_code=502, detail=f"NAMS error: {e}") from e

    conv = await memory.short_term.get_conversation(conversation_id)
    return ChatResponse(
        conversation_id=conversation_id,
        message_count=len(conv.messages),
        last_user_message=request.message,
    )


@app.get("/health")
async def health(memory: Annotated[MemoryClient, Depends(get_memory)]) -> dict[str, str]:
    """Liveness check — confirms the NAMS transport is open."""
    return {"status": "ok" if memory.is_connected else "disconnected"}


if __name__ == "__main__":
    # Allow direct ``python main.py`` for ad-hoc tests, though uvicorn
    # is the canonical entry point.
    import uvicorn

    asyncio.run(uvicorn.Server(uvicorn.Config(app)).serve())
