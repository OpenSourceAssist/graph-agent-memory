# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2026-02-18

### Added

- **AWS Integration**: Comprehensive Amazon Web Services ecosystem support
  - AWS Strands Agents integration with 4 context graph tools (search, entity graph, add memory, user preferences)
  - Amazon Bedrock embeddings (Titan Embed v2/v1, Cohere English/Multilingual v3) with batch support
  - AWS Bedrock AgentCore `MemoryProvider` for native AgentCore memory persistence
  - `HybridMemoryProvider` with intelligent routing strategies (auto, explicit, short-term-first, long-term-first)
- **Google Cloud Integration**: Comprehensive Google Cloud ecosystem support
  - Vertex AI embeddings (`text-embedding-004`, gecko models) with async non-blocking I/O
  - Google ADK `MemoryService` for native ADK agent memory persistence
- **MCP Server**: Model Context Protocol server with 6 tools (memory search, store, entity lookup, conversation history, graph query, reasoning traces)
  - Supports stdio and SSE transports, CLI command: `neo4j-memory mcp serve`
- **Cloud Run Deployment**: Production-ready Dockerfile, Cloud Build config, and Terraform templates
- **New Example Applications**:
  - Google Cloud Financial Advisor: Full-stack multi-agent compliance demo with AML, KYC, relationship, and compliance agents (FastAPI + React/TypeScript)
  - AWS Financial Services Advisor: Strands Agents multi-agent demo with Bedrock LLM and embeddings
  - Google ADK demo: Session storage with entity extraction and memory search
- **Documentation**: Antora-based docs restructuring, Strands Agent quickstart tutorial, Google Cloud and AWS integration guides

### Changed

- Centralized all Cypher queries into `graph/queries.py` module for maintainability
- Short-term memory now auto-links messages sequentially (`FIRST_MESSAGE`/`NEXT_MESSAGE` relationships)
- Optional dependency stubs now raise `ImportError` with install instructions instead of returning `None`

### Fixed

- MCP handler event dispatch fixes
- Entity type parameter error and APOC fallback handling
- Cypher query fixes for entity search, tool calls, and relationship extraction
- Lenny's Memory demo: improved initial loading speed, graph view, tool call result cards, mobile responsiveness, and entity enrichment

## [0.0.2] - 2026-01-29

### Added

- **Agent Framework Integrations**: Improved integration APIs for multiple AI frameworks
  - OpenAI Agents integration improvements
  - LangChain, Pydantic AI, LlamaIndex, and CrewAI support
  - Async handler context improvements
- **Reasoning Trace Search**: Fixed reasoning trace visibility in demo app search tools with improved exposure control for sensitive data
- **Documentation Improvements**: Comprehensive documentation restructuring using the Diataxis framework (tutorials, how-to guides, reference, explanation)
- **New Example Applications**:
  - Lenny's Podcast Memory Explorer demo with 299 episodes, 19 specialized tools, and interactive graph visualization
  - Full-Stack Chat Agent with FastAPI backend and Next.js frontend
  - Financial Services Advisor domain-specific example
  - Microsoft Agent Retail Assistant example
  - 8 domain schema examples (POLEO, podcast, news, scientific, business, entertainment, medical, legal)

### Changed

- Entity types now support string-based POLE+O classification with dynamic Neo4j label creation
- Improved deduplication configuration with auto-merge thresholds
- Enhanced provenance tracking for entity creation
- Refactored `procedural.*` memory abstraction to `reasoning.*` top level APIs

### Fixed

- Tracing API fixes for string/enum value support
- String serialization fixes in async handlers

## [0.0.1] - 2026-01-22

### Added

- Initial release of Neo4j Agent Memory
- **Three-Layer Memory Architecture**:
  - Short-Term Memory: Conversation history with temporal context and session management
  - Long-Term Memory: Entity and fact storage using POLE+O data model (Person, Object, Location, Event, Organization)
  - Reasoning Memory: Tool usage tracking and reasoning traces
- **Entity Extraction Pipeline**:
  - Multi-stage extraction with spaCy, GLiNER, and LLM fallback
  - Merge strategies: union, intersection, confidence-based, cascade, first-success
  - Batch and streaming extraction support
  - GLiNER2 domain schemas
  - GLiREL relation extraction
- **Entity Resolution & Deduplication**:
  - Multiple strategies: exact, fuzzy (RapidFuzz), semantic (embeddings), composite
  - Automatic deduplication on ingest
  - Duplicate review workflow with SAME_AS relationships
- **Vector + Graph Search**:
  - Semantic similarity search with embeddings
  - Graph traversal for relationship queries
  - Neo4j vector indexes (requires Neo4j 5.11+)
  - Metadata filtering with MongoDB-style syntax
- **Entity Enrichment**:
  - Wikipedia and Diffbot data enrichment
  - Background enrichment service
  - Geocoding with spatial indexing
- **Observability**:
  - OpenTelemetry integration
  - Opik tracing support
- **CLI Tool**: Command-line interface for entity extraction and schema management
- **Schema Persistence**: Store and version custom entity schemas in Neo4j

[0.0.3]: https://github.com/neo4j-labs/agent-memory/releases/tag/v0.0.3
[0.0.2]: https://github.com/neo4j-labs/agent-memory/releases/tag/v0.0.2
[0.0.1]: https://github.com/neo4j-labs/agent-memory/releases/tag/v0.0.1
