.PHONY: dev build test lint setup clean seed

# Development
dev:
	docker-compose up --build

dev-backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Production
prod:
	docker-compose -f docker-compose.prod.yml up -d --build

prod-stop:
	docker-compose -f docker-compose.prod.yml down

# Testing
test:
	cd backend && python -m pytest tests/ -v --tb=short

test-cov:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=html

# Linting
lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint

lint-fix:
	cd backend && ruff check --fix . && ruff format .

# Type checking
typecheck:
	cd backend && mypy app/ --ignore-missing-imports
	cd frontend && npm run type-check

# Setup
setup:
	@echo "Setting up AgenticP1..."
	bash scripts/setup.sh

# Database
db-reset:
	rm -f data/agenticp1.db
	@echo "Database reset. Will be recreated on next startup."

# Seed demo data
seed:
	cd backend && python ../scripts/seed_demo.py

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	cd frontend && rm -rf .next node_modules/.cache

# Docker helpers
logs:
	docker-compose logs -f

ps:
	docker-compose ps

restart:
	docker-compose restart

help:
	@echo "AgenticP1 — AI Calling Agent Platform"
	@echo ""
	@echo "Commands:"
	@echo "  make dev          Start all services in development mode"
	@echo "  make prod         Start all services in production mode"
	@echo "  make test         Run backend tests"
	@echo "  make lint         Run linters"
	@echo "  make setup        Run setup script"
	@echo "  make seed         Seed demo data"
	@echo "  make clean        Clean build artifacts"
