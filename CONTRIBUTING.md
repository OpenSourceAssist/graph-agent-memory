# Contributing to Neo4j Agent Memory

Contributions are welcome! Please read the guidelines below before submitting a pull request.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/neo4j-labs/agent-memory.git
cd agent-memory/neo4j-agent-memory

# Install with uv
uv sync --group dev

# Or use the Makefile
make install
```

## Using the Makefile

The project includes a comprehensive Makefile for common development tasks:

```bash
# Run all tests (unit + integration with auto-Docker)
make test

# Run unit tests only
make test-unit

# Run integration tests (auto-starts Neo4j via Docker)
make test-integration

# Code quality
make lint         # Run ruff linter
make format       # Format code with ruff
make typecheck    # Run mypy type checking
make check        # Run all checks (lint + typecheck + test)

# Docker management for Neo4j
make neo4j-start  # Start Neo4j container
make neo4j-stop   # Stop Neo4j container
make neo4j-logs   # View Neo4j logs
make neo4j-clean  # Stop and remove volumes

# Run examples
make example-basic      # Basic usage example
make example-resolution # Entity resolution example
make example-langchain  # LangChain integration example
make example-pydantic   # Pydantic AI integration example
make examples           # Run all examples

# Full-stack chat agent
make chat-agent-install  # Install backend + frontend dependencies
make chat-agent-backend  # Run FastAPI backend (port 8000)
make chat-agent-frontend # Run Next.js frontend (port 3000)
make chat-agent          # Show setup instructions
```

## Running Examples

Examples are located in `examples/` and demonstrate various features:

| Example | Description | Requirements |
|---------|-------------|--------------|
| [`lennys-memory/`](examples/lennys-memory/) | **Flagship demo**: Podcast knowledge graph with AI chat, graph visualization, map view, entity enrichment | Neo4j, OpenAI, Node.js |
| [`financial-services-advisor/`](examples/financial-services-advisor/) | **AWS Strands demo**: Multi-agent KYC/AML compliance with 5 specialized agents, CDK deployment | Neo4j Aura, AWS Bedrock, Node.js |
| `full-stack-chat-agent/` | Full-stack web app with FastAPI backend and Next.js frontend | Neo4j, OpenAI, Node.js |
| `basic_usage.py` | Core memory operations (short-term, long-term, reasoning) | Neo4j, OpenAI API key |
| `entity_resolution.py` | Entity matching strategies | None |
| `langchain_agent.py` | LangChain integration | Neo4j, OpenAI, langchain extra |
| `pydantic_ai_agent.py` | Pydantic AI integration | Neo4j, OpenAI, pydantic-ai extra |
| `domain-schemas/` | GLiNER2 domain schema examples (8 domains) | GLiNER extra, optional Neo4j |

### Environment Setup

Examples load environment variables from `examples/.env`. Copy the template:

```bash
cp examples/.env.example examples/.env
# Edit examples/.env with your settings
```

Key variables:
- `NEO4J_URI` - If set, uses this Neo4j; if not set, auto-starts Docker
- `NEO4J_PASSWORD` - Neo4j password (`test-password` for Docker)
- `OPENAI_API_KEY` - Required for OpenAI embeddings and LLM extraction

```bash
# Run with your own Neo4j (uses NEO4J_URI from .env)
make example-basic

# Or without .env (auto-starts Docker Neo4j)
rm examples/.env  # Ensure no .env file
make example-basic  # Will start Docker with test-password
```

## Testing

### Environment Variables

```bash
# Control integration test behavior
RUN_INTEGRATION_TESTS=1      # Enable integration tests
SKIP_INTEGRATION_TESTS=1     # Skip integration tests
AUTO_START_DOCKER=1          # Auto-start Neo4j via Docker (default: true)
AUTO_STOP_DOCKER=1           # Auto-stop Neo4j after tests (default: false)
```

### Integration Test Script

```bash
# Keep Neo4j running after tests (useful for debugging)
./scripts/run-integration-tests.sh --keep

# Run with verbose output
./scripts/run-integration-tests.sh --verbose

# Run specific test pattern
./scripts/run-integration-tests.sh --pattern "test_short_term"
```

### Test Categories

```bash
# Unit tests (fast, no external dependencies)
pytest tests/unit -v

# Integration tests (requires Neo4j)
pytest tests/integration -v

# Example validation tests
pytest tests/examples -v

# All tests with coverage
pytest --cov=neo4j_agent_memory --cov-report=html
```

## CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment.

### Workflow Overview

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** (`ci.yml`) | Push to `main`, PRs | Linting, type checking, tests, build validation |
| **Release** (`release.yml`) | Git tags (`v*`) | Build and publish to PyPI, create GitHub releases |

### CI Jobs

1. **Lint** - Code quality checks using Ruff (`ruff check` + `ruff format --check`)
2. **Type Check** - Static type analysis using mypy on `src/`
3. **Unit Tests** - Python 3.10, 3.11, 3.12, 3.13 with coverage (uploaded to Codecov)
4. **Integration Tests** - Neo4j 5.26 via GitHub Actions services, matrix across Python versions
5. **Example Tests** - Quick validation (no Neo4j) + full validation (with Neo4j)
6. **Build** - Package build validation, wheel/sdist, install + import check

### Running CI Locally

Before submitting a PR, run the same checks locally:

```bash
# Run all checks (recommended before PR)
make ci

# Or run individual checks:
make lint        # Ruff linting
make format      # Auto-format code
make typecheck   # Mypy type checking
make test        # Unit tests only
make test-all    # Unit + integration tests
```

### Pull Request Requirements

All PRs must pass these checks before merging:
- Lint (ruff check)
- Format (ruff format)
- Unit tests (all Python versions)
- Integration tests
- Build validation

## Code Style

- **Formatter**: Ruff (line length: 88)
- **Linter**: Ruff
- **Type Checker**: mypy (strict mode)
- **Docstrings**: Google style

## Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run `make ci` to validate
5. Commit with descriptive messages
6. Push and open a PR against `main`

## Publishing to PyPI

1. Update version in `pyproject.toml`
2. Create and push a tag:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. GitHub Actions will automatically build and publish to PyPI

## Documentation Guidelines (Diataxis Framework)

The documentation follows the [Diataxis framework](https://diataxis.fr/), which organizes content into four distinct types based on user needs:

| Type | Purpose | User Need | Location |
|------|---------|-----------|----------|
| **Tutorials** | Learning-oriented | "I want to learn" | `docs/tutorials/` |
| **How-To Guides** | Task-oriented | "I want to accomplish X" | `docs/how-to/` |
| **Reference** | Information-oriented | "I need to look up Y" | `docs/reference/` |
| **Explanation** | Understanding-oriented | "I want to understand why" | `docs/explanation/` |

### When to Include Documentation in a PR

- **New public API?** --> Update `docs/reference/` with method signatures
- **New user-facing feature?** --> Add how-to guide in `docs/how-to/`
- **Major new capability?** --> Consider adding a tutorial in `docs/tutorials/`
- **Architectural change?** --> Add explanation in `docs/explanation/`
- **Code examples compile?** --> Run `make test-docs-syntax`

### Building and Testing Documentation

```bash
# Build documentation locally
cd docs && npm install && npm run build

# Preview documentation
cd docs && npm run serve

# Run documentation tests
make test-docs           # All doc tests
make test-docs-syntax    # Validate Python code snippets compile
make test-docs-build     # Test build pipeline
make test-docs-links     # Validate internal links
```

### Diataxis Decision Tree

```
Is this about learning a concept from scratch?
  --> Yes: Tutorial (docs/tutorials/)
  --> No:

Is this about accomplishing a specific task?
  --> Yes: How-To Guide (docs/how-to/)
  --> No:

Is this describing what something is or how to use it?
  --> Yes: Reference (docs/reference/)
  --> No:

Is this explaining why something works the way it does?
  --> Yes: Explanation (docs/explanation/)
```
