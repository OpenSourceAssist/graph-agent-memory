# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.0.2]: https://github.com/neo4j-labs/agent-memory/releases/tag/v0.0.2
[0.0.1]: https://github.com/neo4j-labs/agent-memory/releases/tag/v0.0.1
