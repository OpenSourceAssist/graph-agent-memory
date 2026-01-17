.PHONY: help install install-all install-dev lint format typecheck test test-unit test-integration test-all coverage neo4j-start neo4j-stop neo4j-logs clean build publish docs

# Default target
help:
	@echo "neo4j-agent-memory Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install core dependencies"
	@echo "  make install-all      Install all dependencies including extras"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linter (ruff check)"
	@echo "  make format           Format code (ruff format)"
	@echo "  make typecheck        Run type checker (mypy)"
	@echo "  make check            Run all code quality checks"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run unit tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests (requires Neo4j)"
	@echo "  make test-all         Run all tests (unit + integration)"
	@echo "  make coverage         Run tests with coverage report"
	@echo ""
	@echo "Neo4j:"
	@echo "  make neo4j-start      Start Neo4j test container"
	@echo "  make neo4j-stop       Stop Neo4j test container"
	@echo "  make neo4j-logs       View Neo4j container logs"
	@echo "  make neo4j-status     Check Neo4j container status"
	@echo ""
	@echo "Build & Publish:"
	@echo "  make build            Build package"
	@echo "  make publish          Publish to PyPI (requires credentials)"
	@echo "  make clean            Remove build artifacts"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs             Build documentation"

# =============================================================================
# Setup
# =============================================================================

install:
	uv sync

install-all:
	uv sync --all-extras

install-dev:
	uv sync --extra dev

# =============================================================================
# Code Quality
# =============================================================================

lint:
	uv run ruff check src tests

lint-fix:
	uv run ruff check --fix src tests

format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

typecheck:
	uv run mypy src

check: lint format-check typecheck
	@echo "All code quality checks passed!"

# =============================================================================
# Testing
# =============================================================================

test: test-unit

test-unit:
	uv run pytest tests/unit -v

test-integration: neo4j-wait
	RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration -v

test-all: neo4j-wait
	RUN_INTEGRATION_TESTS=1 uv run pytest tests -v

coverage:
	uv run pytest tests/unit --cov=src/neo4j_agent_memory --cov-report=term-missing --cov-report=html

coverage-all: neo4j-wait
	RUN_INTEGRATION_TESTS=1 uv run pytest tests --cov=src/neo4j_agent_memory --cov-report=term-missing --cov-report=html

# =============================================================================
# Neo4j Docker Management
# =============================================================================

neo4j-start:
	docker compose -f docker-compose.test.yml up -d
	@echo "Neo4j starting... use 'make neo4j-wait' to wait for it to be ready"

neo4j-stop:
	docker compose -f docker-compose.test.yml down

neo4j-logs:
	docker compose -f docker-compose.test.yml logs -f

neo4j-status:
	@docker compose -f docker-compose.test.yml ps

neo4j-wait:
	@echo "Waiting for Neo4j to be ready..."
	@docker compose -f docker-compose.test.yml up -d
	@until docker compose -f docker-compose.test.yml exec -T neo4j cypher-shell -u neo4j -p test-password "RETURN 1" > /dev/null 2>&1; do \
		echo "Waiting for Neo4j..."; \
		sleep 2; \
	done
	@echo "Neo4j is ready!"

neo4j-clean:
	docker compose -f docker-compose.test.yml down -v
	@echo "Neo4j container and volumes removed"

# =============================================================================
# Build & Publish
# =============================================================================

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean
	uv build

publish: build
	uv publish

publish-test: build
	uv publish --repository testpypi

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "Documentation build not yet configured"
	@echo "Consider using mkdocs or sphinx"

# =============================================================================
# Development Shortcuts
# =============================================================================

# Run a quick check before committing
pre-commit: format lint typecheck test-unit
	@echo "Pre-commit checks passed!"

# Full CI simulation
ci: check test-all
	@echo "CI simulation passed!"

# Interactive Python shell with package loaded
shell:
	uv run python -c "from neo4j_agent_memory import *; import asyncio" -i

# Watch tests (requires pytest-watch)
watch:
	uv run pytest-watch tests/unit
