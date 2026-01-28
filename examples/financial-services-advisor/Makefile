# Financial Services Advisor Makefile

.PHONY: install dev build deploy clean test load-data

# Install all dependencies
install: install-backend install-frontend install-infra

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

install-infra:
	cd infrastructure && npm install

# Development
dev: dev-backend

dev-backend:
	cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Run both (requires separate terminals or use tmux)
dev-all:
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals"

# Build
build: build-frontend

build-frontend:
	cd frontend && npm run build

build-infra:
	cd infrastructure && npm run build

# Load sample data
load-data:
	cd data && python load_sample_data.py

# Deploy to AWS
deploy: build-infra
	cd infrastructure && npm run cdk deploy --all

deploy-backend:
	cd infrastructure && npm run cdk deploy financial-services-advisor-compute financial-services-advisor-api

deploy-frontend:
	cd infrastructure && npm run cdk deploy financial-services-advisor-api
	@echo "Upload frontend build to S3 bucket"

# Destroy AWS resources
destroy:
	cd infrastructure && npm run cdk destroy --all

# Testing
test: test-backend

test-backend:
	cd backend && pytest tests/ -v

test-frontend:
	cd frontend && npm test

# Linting
lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check src/

lint-frontend:
	cd frontend && npm run lint

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name cdk.out -exec rm -rf {} + 2>/dev/null || true

# Help
help:
	@echo "Financial Services Advisor - Available Commands:"
	@echo ""
	@echo "  install        - Install all dependencies"
	@echo "  dev            - Run backend in development mode"
	@echo "  dev-frontend   - Run frontend in development mode"
	@echo "  load-data      - Load sample data into Neo4j"
	@echo "  build          - Build frontend for production"
	@echo "  deploy         - Deploy to AWS using CDK"
	@echo "  destroy        - Remove all AWS resources"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run linters"
	@echo "  clean          - Clean build artifacts"
