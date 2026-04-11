# Makefile for Google Cloud Financial Advisor

.PHONY: help install dev run run-backend run-frontend build start stop clean load-data deploy logs test lint format

help:
	@echo "Google Cloud Financial Advisor - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install backend (uv) and frontend (npm) dependencies"
	@echo "  make load-data        - Load sample data into Neo4j"
	@echo ""
	@echo "Development:"
	@echo "  make run              - Start both backend and frontend (recommended)"
	@echo "  make run-backend      - Start FastAPI backend only (port 8000)"
	@echo "  make run-frontend     - Start Vite frontend only (port 5173)"
	@echo "  make dev              - Alias for 'make run'"
	@echo ""
	@echo "Docker:"
	@echo "  make start            - Start all services with Docker Compose"
	@echo "  make stop             - Stop all services"
	@echo "  make logs             - View service logs"
	@echo ""
	@echo "Code Quality:"
	@echo "  make test             - Run backend tests"
	@echo "  make lint             - Run linter (ruff)"
	@echo "  make format           - Format code (ruff)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build            - Build Docker images"
	@echo "  make deploy           - Deploy to Google Cloud Run"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove containers and volumes"

# Setup
install:
	@echo "Installing backend dependencies with uv..."
	cd backend && uv sync
	@echo ""
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo ""
	@echo "Done! Run 'make run' to start development servers."

# Run both backend and frontend concurrently
run:
	@echo "Starting Google Cloud Financial Advisor..."
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

# Alias for run
dev: run

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
	cd backend && uv run python ../../data/load_sample_data.py
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
