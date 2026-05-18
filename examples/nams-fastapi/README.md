# NAMS + FastAPI

Production wiring pattern: a FastAPI app that uses a hosted
**Neo4j Agent Memory Service (NAMS)** backend for conversation memory.

Demonstrates:

* **Lifespan-managed `MemoryClient`** — one HTTP transport pool shared
  across all requests; cleanly closed on shutdown.
* **Per-request `session_id`** — clients pass the session in the body.
* **Multi-tenant `X-User-Id` header** — forwarded as
  `user_identifier` so conversations are scoped per-user within your
  NAMS workspace.

## Setup

```bash
uv pip install -r requirements.txt
cp .env.example .env
# edit .env, set MEMORY_API_KEY
export MEMORY_API_KEY=nams_xxxxxxxxxxxx
```

## Run

```bash
uv run uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> for the auto-generated OpenAPI UI.

## Try it

```bash
# Health check
curl http://127.0.0.1:8000/health
# {"status": "ok"}

# Append a message
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -H 'X-User-Id: alice' \
  -d '{"message": "Hello there!", "session_id": "demo-session"}'
# {"session_id": "demo-session", "message_count": 1, "last_user_message": "Hello there!"}
```

## Production notes

* **One client per process.** `MemoryClient` is async-safe and shares an
  HTTP connection pool. Don't open a new client per request.
* **`validate_on_connect`** runs once at startup; reaching NAMS at boot
  fails the lifespan early with `AuthenticationError` or
  `TransportError` — fail-fast on bad config.
* **Retries** are built into the transport (429 honors `Retry-After`,
  5xx + network errors use exponential backoff). No app-side retry
  needed.
* **Graceful shutdown**: the lifespan handler closes the HTTP pool when
  uvicorn receives `SIGTERM`. Don't bypass this if you do custom signal
  handling.
* **OpenTelemetry**: configure a tracer in the app and pass it to
  `MemorySettings` — every NAMS request emits HTTP-semantic-convention
  span attributes (`http.method`, `http.url`, `http.status_code`,
  `nams.method`, `nams.protocol`).
