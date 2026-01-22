.PHONY: help install load-sample load-full load-fast load-resume load-dry-run run-backend run-frontend neo4j clean

# Default target
help:
	@echo "Lenny's Memory - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install all dependencies (backend + frontend)"
	@echo "  make neo4j          Start Neo4j in Docker"
	@echo ""
	@echo "Data Loading:"
	@echo "  make load-sample    Load 5 sample transcripts (for testing)"
	@echo "  make load-full      Load all 299 transcripts"
	@echo "  make load-fast      Load all transcripts without entity extraction (faster)"
	@echo "  make load-resume    Resume loading (skip already loaded transcripts)"
	@echo "  make load-dry-run   Preview what would be loaded without loading"
	@echo ""
	@echo "Development:"
	@echo "  make run-backend    Start FastAPI backend (port 8000)"
	@echo "  make run-frontend   Start Next.js frontend (port 3000)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove generated files and dependencies"

# Install all dependencies
install: install-backend install-frontend

install-backend:
	cd backend && uv sync

install-frontend:
	cd frontend && npm install

# Start Neo4j
neo4j:
	docker compose up -d
	@echo "Waiting for Neo4j to start..."
	@sleep 10
	@echo "Neo4j available at http://localhost:7474"

# Environment variables to suppress warnings during loading
LOAD_ENV = PYTHONWARNINGS="ignore" HF_HUB_DISABLE_PROGRESS_BARS=1 TOKENIZERS_PARALLELISM=false

# Load sample transcripts (5 files for quick testing)
load-sample:
	cd backend && $(LOAD_ENV) uv run python ../scripts/load_transcripts.py \
		--data-dir ../data \
		--sample 5

# Load all transcripts (full dataset)
load-full:
	cd backend && $(LOAD_ENV) uv run python ../scripts/load_transcripts.py \
		--data-dir ../data

# Load all transcripts without entity extraction (faster)
load-fast:
	cd backend && $(LOAD_ENV) uv run python ../scripts/load_transcripts.py \
		--data-dir ../data \
		--no-entities

# Resume loading (skip already loaded transcripts)
load-resume:
	cd backend && $(LOAD_ENV) uv run python ../scripts/load_transcripts.py \
		--data-dir ../data \
		--resume

# Preview what would be loaded (dry run)
load-dry-run:
	cd backend && $(LOAD_ENV) uv run python ../scripts/load_transcripts.py \
		--data-dir ../data \
		--dry-run

# Run backend
run-backend:
	cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend
run-frontend:
	cd frontend && npm run dev

# Clean up
clean:
	rm -rf backend/.venv
	rm -rf frontend/node_modules
	rm -rf frontend/.next
