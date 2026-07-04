# ==============================================================
# MSME Financial Health Card — Makefile
# ==============================================================

.PHONY: help dev dev-backend dev-frontend test test-backend test-frontend \
        lint lint-backend lint-frontend build build-backend build-frontend \
        clean terraform-init terraform-plan terraform-apply fmt

# Default target
help:
	@echo ""
	@echo "MSME Financial Health Card — Developer Commands"
	@echo "================================================"
	@echo ""
	@echo "  make dev              Start all services locally (docker-compose up)"
	@echo "  make dev-backend      Start backend + postgres only"
	@echo "  make dev-frontend     Start frontend dev server only"
	@echo ""
	@echo "  make test             Run all tests (backend + frontend)"
	@echo "  make test-backend     Run backend tests (pytest)"
	@echo "  make test-frontend    Run frontend tests (vitest)"
	@echo ""
	@echo "  make lint             Run all linters (ruff, black, mypy, eslint)"
	@echo "  make lint-backend     Run backend linters"
	@echo "  make lint-frontend    Run frontend linters"
	@echo ""
	@echo "  make build            Build production Docker images"
	@echo "  make clean            Remove build artifacts and caches"
	@echo ""
	@echo "  make terraform-init   Initialize Terraform providers"
	@echo "  make terraform-plan   Preview Terraform changes"
	@echo "  make terraform-apply  Apply Terraform changes (GCP)"
	@echo ""

# ---- Local Development ----

dev:
	@echo ">> Starting all services with docker-compose..."
	docker compose up --build

dev-backend:
	@echo ">> Starting backend + postgres..."
	docker compose up --build backend postgres

dev-frontend:
	@echo ">> Starting frontend dev server..."
	cd frontend && npm run dev

# ---- Testing ----

test: test-backend test-frontend
	@echo ">> All tests complete."

test-backend:
	@echo ">> Running backend tests..."
	cd backend && python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=85

test-frontend:
	@echo ">> Running frontend tests..."
	cd frontend && npm run test

# ---- Linting ----

lint: lint-backend lint-frontend
	@echo ">> All linters passed."

lint-backend:
	@echo ">> Linting backend (ruff + black + mypy)..."
	cd backend && python -m ruff check app/ tests/
	cd backend && python -m black --check app/ tests/
	cd backend && python -m mypy app/ --ignore-missing-imports

lint-frontend:
	@echo ">> Linting frontend (eslint + prettier)..."
	cd frontend && npm run lint
	cd frontend && npm run type-check

fmt:
	@echo ">> Auto-formatting backend code..."
	cd backend && python -m black app/ tests/
	cd backend && python -m ruff check --fix app/ tests/
	@echo ">> Auto-formatting frontend code..."
	cd frontend && npm run format

# ---- Build ----

build: build-backend build-frontend
	@echo ">> Production images built."

build-backend:
	@echo ">> Building backend Docker image..."
	docker build -t msme-healthcard-backend:latest ./backend

build-frontend:
	@echo ">> Building frontend Docker image..."
	docker build -t msme-healthcard-frontend:latest ./frontend

# ---- Terraform ----

TERRAFORM_DIR := infra/terraform
ENV ?= dev

terraform-init:
	@echo ">> Initializing Terraform..."
	cd $(TERRAFORM_DIR)/environments/$(ENV) && terraform init

terraform-plan:
	@echo ">> Planning Terraform changes (env=$(ENV))..."
	cd $(TERRAFORM_DIR)/environments/$(ENV) && terraform plan -out=tfplan

terraform-apply:
	@echo ">> Applying Terraform changes (env=$(ENV))..."
	cd $(TERRAFORM_DIR)/environments/$(ENV) && terraform apply tfplan

terraform-destroy:
	@echo ">> Destroying Terraform resources (env=$(ENV)) — ARE YOU SURE?"
	cd $(TERRAFORM_DIR)/environments/$(ENV) && terraform destroy

# ---- Synthetic Data ----

generate-data:
	@echo ">> Generating synthetic MSME data..."
	cd backend && python -m app.synthetic.generator

# ---- Security Scans ----

security-scan:
	@echo ">> Running backend security scan (bandit)..."
	cd backend && python -m bandit -r app/ -ll
	@echo ">> Running frontend security audit..."
	cd frontend && npm audit --audit-level=high

# ---- Cleanup ----

clean:
	@echo ">> Cleaning build artifacts..."
	find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find backend -name "*.pyc" -delete 2>/dev/null || true
	find backend -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	find backend -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	find backend -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage 2>/dev/null || true
	rm -rf frontend/dist frontend/node_modules/.vite 2>/dev/null || true
	@echo ">> Clean complete."
