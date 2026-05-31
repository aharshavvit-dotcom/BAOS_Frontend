# Makefile - BAOS development commands

.PHONY: seed migrate dev test build lint check dev-backend dev-frontend

seed:
	python -m database.seed

migrate:
	alembic upgrade head

dev-backend:
	python run.py

dev-frontend:
	cd frontend && npm run dev

dev:
	make -j2 dev-backend dev-frontend

test:
	pytest tests/ -v

build:
	cd frontend && npm run build

lint:
	cd frontend && npm run lint
	ruff check backend/ engines/

check:
	curl -s http://localhost:8001/api/v1/ports/INMAA/status | python -m json.tool
