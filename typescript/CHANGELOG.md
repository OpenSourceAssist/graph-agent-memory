# Changelog

All notable changes to `@neo4j-labs/agent-memory` will be documented in
this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project follows [Semantic Versioning](https://semver.org).

This is a Neo4j Labs project under Beta status — breaking changes may
appear in minor versions with a callout in this file.

## [Unreleased]

### Changed

- Repository moved from
  [`neo4j-labs/agent-memory-tck`](https://github.com/neo4j-labs/agent-memory-tck)
  (source SHA `4603b91f`) to
  [`neo4j-labs/agent-memory`](https://github.com/neo4j-labs/agent-memory),
  alongside the Python SDK. No code changes — `package.json` repository
  and homepage fields point at the new location.
- Documentation is now served from
  [neo4j.com/labs/agent-memory/](https://neo4j.com/labs/agent-memory/)
  under the unified Antora site. TypeDoc API reference is published at
  [neo4j-labs.github.io/agent-memory/typescript/](https://neo4j-labs.github.io/agent-memory/typescript/).
- Release tags are now namespaced as `typescript-v*` (e.g.
  `typescript-v0.3.0`); the Python SDK uses `python-v*`.

## 0.3.0 — Beta launch

Beta launch release for the hosted-service-first TypeScript client.

### Added

- `MemoryClient` with `shortTerm`, `longTerm`, `reasoning`, `query`, and
  `auth` subclients
- Featured framework integrations:
  - `@neo4j-labs/agent-memory/middleware/vercel-ai` — Vercel AI SDK
    middleware with three-tier context injection and automatic
    persistence
  - `@neo4j-labs/agent-memory/mcp` — the 12 standard MCP tool
    definitions plus a dispatcher
  - `@neo4j-labs/agent-memory/integrations/langchain` —
    `Neo4jChatMessageHistory` and `Neo4jEntityRetriever` (duck-typed)
  - `@neo4j-labs/agent-memory/integrations/mastra` — `Neo4jMastraMemory`
    provider (duck-typed)
  - `@neo4j-labs/agent-memory/integrations/strands` — AWS Strands Agents
    integration: `Neo4jSessionStorage` (SnapshotStorage backend),
    `Neo4jConversationManager` (three-tier context injection layered on
    top of an inner manager), `registerReasoningHooks` + `connectMemoryToAgent`
    factory. Compatible with `@strands-agents/sdk@^1.2.0`.
- `@neo4j-labs/agent-memory/testing` — `BridgeTransport` for TCK
  conformance testing
- Zero-config construction: defaults endpoint to
  `https://memory.neo4jlabs.com/v1`; reads `MEMORY_API_KEY` from
  environment
- Lazy `connect()`: the first request acts as the implicit auth check;
  explicit `connect()` is supported for fail-fast startups
- Auto User-Agent header with caller override
- `requestId` propagated onto every `MemoryError` from the
  `x-request-id` (or equivalent) response header
- `logger` constructor option emitting typed `request` / `response` /
  `error` events
- Edge runtime support: Cloudflare Workers, Vercel Edge (with explicit
  `apiKey` pattern)
- TCK Bronze conformance via the polyglot test suite

### Breaking

- `BridgeTransport` is no longer exported from the package root. Import it
  from `@neo4j-labs/agent-memory/testing` instead.
- Deprecated `HttpTransport` / `HttpTransportOptions` aliases were removed.
