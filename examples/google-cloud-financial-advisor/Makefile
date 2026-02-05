# Makefile for Google Cloud Financial Advisor

.PHONY: help install dev build start stop clean load-data deploy logs test lint format

help:
	@echo "Google Cloud Financial Advisor - Development Commands"
	@echo ""
	@echo "Local Development:"
	@echo "  make install     - Install backend (uv) and frontend (npm) dependencies"
	@echo "  make dev         - Start development servers (Neo4j + backend + frontend)"
	@echo "  make start       - Start all services with Docker Compose"
	@echo "  make stop        - Stop all services"
	@echo "  make logs        - View service logs"
	@echo "  make load-data   - Load sample data into Neo4j"
	@echo ""
	@echo "Code Quality:"
	@echo "  make test        - Run backend tests"
	@echo "  make lint        - Run linter (ruff)"
	@echo "  make format      - Format code (ruff)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build       - Build Docker images"
	@echo "  make deploy      - Deploy to Google Cloud Run"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Remove containers and volumes"

# Local Development
install:
	@echo "Installing backend dependencies with uv..."
	cd backend && uv sync
	@echo ""
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo ""
	@echo "Done! Run 'make dev' to start development servers."

dev:
	@echo "Starting development environment..."
	@echo "This will start Neo4j, backend, and frontend."
	@echo ""
	docker-compose up neo4j -d
	@echo "Waiting for Neo4j to be ready..."
	sleep 10
	@echo ""
	@echo "Starting backend (http://localhost:8000)..."
	cd backend && uv run uvicorn src.main:app --reload --port 8000 &
	@echo ""
	@echo "Starting frontend (http://localhost:5173)..."
	cd frontend && npm run dev

start:
	docker-compose up -d
	@echo ""
	@echo "Services started:"
	@echo "  Frontend:  http://localhost:5173"
	@echo "  Backend:   http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  Neo4j:     http://localhost:7474"
	@echo ""
	@echo "Run 'make logs' to view logs"

stop:
	docker-compose down

logs:
	docker-compose logs -f

load-data:
	@echo "Loading sample data into Neo4j..."
	docker-compose run --rm data-loader
	@echo "Done!"

# Code Quality
test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check src/

format:
	cd backend && uv run ruff format src/
	cd backend && uv run ruff check --fix src/

# Build
build:
	docker-compose build

# Deploy to Google Cloud
deploy:
	@echo "Deploying to Google Cloud Run..."
	./infrastructure/scripts/deploy.sh

setup-secrets:
	@echo "Setting up Google Cloud secrets..."
	./infrastructure/scripts/setup-secrets.sh

# Cleanup
clean:
	docker-compose down -v
	rm -rf backend/.venv backend/__pycache__ backend/src/__pycache__
	rm -rf frontend/node_modules frontend/dist
