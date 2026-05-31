# ─────────────────────────────────────────────────────────
#  Makefile — BAOS AI Development Commands
# ─────────────────────────────────────────────────────────

.PHONY: help setup db-create seed migrate dev dev-backend dev-frontend \
        test build lint check train import-map clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────

setup: db-create migrate seed ## Full setup: create DB → migrate → seed
	@echo "✅ Setup complete"

db-create: ## Create 'baos' database (idempotent)
	python -m database.setup

seed: ## Seed database with demo users and data
	python -m database.seed

migrate: ## Run Alembic migrations (upgrade head)
	alembic upgrade head

# ── Development ──────────────────────────────────────────

dev-backend: ## Start FastAPI backend (port 8001)
	python run.py

dev-frontend: ## Start Next.js frontend (port 3000)
	cd frontend && npm run dev

dev: ## Start backend + frontend in parallel
	make -j2 dev-backend dev-frontend

# ── Quality ──────────────────────────────────────────────

test: ## Run Python tests
	pytest tests/ -v

build: ## Build frontend for production
	cd frontend && npm run build

lint: ## Lint frontend (ESLint) + backend (ruff)
	cd frontend && npm run lint
	ruff check backend/ engines/

# ── ML / Engines ─────────────────────────────────────────

train: ## Trigger ML model training via API
	curl -s -X POST http://localhost:8001/api/v1/training/trigger | python -m json.tool

# ── Utilities ────────────────────────────────────────────

check: ## Health check — GET /api/v1/ports/INMAA/status
	curl -s http://localhost:8001/api/v1/ports/INMAA/status | python -m json.tool

import-map: ## Regenerate docs/import_map.txt
	@echo "Regenerating import map..."
	@python -c "import subprocess, pathlib; \
		r = subprocess.run(['git', 'grep', '-nI', 'import '], capture_output=True, text=True); \
		pathlib.Path('docs/import_map.txt').write_text(r.stdout, encoding='utf-8'); \
		print(f'  ✓ {len(r.stdout.splitlines())} lines written to docs/import_map.txt')"

clean: ## Remove Python caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	rm -rf frontend/.next frontend/out .pytest_cache
