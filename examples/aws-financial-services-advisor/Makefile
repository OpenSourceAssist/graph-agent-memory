.PHONY: help install install-backend install-frontend run run-backend run-frontend build test lint clean deploy destroy load-data

# Default target
help:
	@echo "Financial Services Advisor - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies (backend + frontend)"
	@echo "  make install-backend  Install backend Python dependencies"
	@echo "  make install-frontend Install frontend Node dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run              Start both backend and frontend (recommended)"
	@echo "  make run-backend      Start FastAPI backend only (port 8000)"
	@echo "  make run-frontend     Start Vite frontend only (port 5173)"
	@echo "  make load-data        Load sample data into Neo4j"
	@echo ""
	@echo "Quality:"
	@echo "  make test             Run backend tests"
	@echo "  make lint             Run linters (backend + frontend)"
	@echo ""
	@echo "Production:"
	@echo "  make build            Build frontend for production"
	@echo "  make deploy           Deploy to AWS using CDK"
	@echo "  make destroy          Remove all AWS resources"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove generated files and dependencies"
	@echo ""
	@echo "Configure Neo4j connection in backend/.env (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)"

# Install all dependencies
install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm install

# Run both backend and frontend concurrently
run:
	@echo "Starting Financial Services Advisor..."
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Press Ctrl+C to stop both servers."
	@echo ""
	@trap 'kill 0' INT; \
	(cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

# Run backend only
run-backend:
	cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend only
run-frontend:
	cd frontend && npm run dev

# Load sample data into Neo4j
load-data:
	cd backend && uv run python ../scripts/load_sample_data.py

# Build frontend for production
build:
	cd frontend && npm run build

# Testing
test:
	cd backend && uv run pytest tests/ -v

# Linting
lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check src/

lint-frontend:
	cd frontend && npm run lint

# Deploy to AWS
deploy: build
	cd infrastructure && npm install && npm run cdk deploy --all

# Destroy AWS resources
destroy:
	cd infrastructure && npm run cdk destroy --all

# Clean up
clean:
	rm -rf backend/.venv
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf infrastructure/node_modules
	rm -rf infrastructure/cdk.out
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
