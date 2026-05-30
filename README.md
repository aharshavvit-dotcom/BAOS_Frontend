# BAOS AI Application

BAOS is a FastAPI + Next.js monorepo for berth allocation, berth suitability recommendations, model-backed port operations, and analytics.

The runtime flow is database-first:

1. `make seed` creates or updates schema, users, and bundled sample data.
2. `make dev-backend` starts FastAPI and checks model readiness.
3. If valid data exists and active ML models are missing or stale, the backend trains and registers them automatically.
4. `make dev-frontend` starts the Next.js app.

No separate manual training command is required.

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- PostgreSQL 12 or newer
- A PostgreSQL database named `ML_APP`
- `make` for the shortcut commands, or run the underlying commands shown below

The default backend database configuration expects PostgreSQL on port `5433`. Update `backend/.env` if your local database user, password, host, port, or database name is different.

## Install Dependencies

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r backend\requirements.txt
cd frontend
npm install
cd ..
```

## Development Commands

```powershell
make seed
make dev-backend
make dev-frontend
make test
make build
make check
```

Equivalent commands without `make`:

```powershell
python -m database.seed
python run.py
cd frontend
npm run dev
npm run build
cd ..
pytest tests/ -v
```

Seeded login accounts:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@baos.ai` | `admin123` |
| Operator | `operator@baos.ai` | `operator123` |

## Project Layout

```text
.
|-- run.py                         # Root backend launcher
|-- database/                      # Root wrapper for python -m database.seed
|-- backend/                       # FastAPI backend
|   |-- main.py                    # App setup, middleware, router registry
|   |-- run.py                     # Uvicorn runner
|   |-- config/                    # Settings and port configuration
|   |-- auth/                      # Auth routes, dependencies, JWT helpers
|   |-- routes/                    # API route modules and registry
|   |-- services/                  # Domain services
|   |-- db/
|   |   |-- models/                # SQLAlchemy and domain/data models
|   |   |-- repositories/          # Database and port-store repositories
|   |   `-- session.py             # Engine/session factories
|   |-- middleware/                # Error handlers and middleware
|   |-- schemas/                   # Pydantic API schemas
|   |-- migrations/                # Alembic-ready migration package
|   `-- utils/                     # Shared backend utilities
|-- engines/                       # ML, optimization, ingestion, and analytics engines
|   |-- core/                      # Inference and decision engines
|   |-- analytics/                 # KPI, commercial, cost, explanation engines
|   |-- simulation/                # Scenario, optimization, uncertainty engines
|   |-- learning/                  # Training, refresh, RL, data prep
|   `-- ingestion/                 # Excel ingestion and spec transforms
|-- frontend/                      # Next.js frontend
|   |-- src/app/                   # App Router pages
|   |-- src/components/            # UI, layout, charts, feature components
|   |-- src/hooks/                 # React data/auth hooks
|   |-- src/services/              # API clients and domain services
|   |-- src/store/                 # Zustand stores
|   |-- src/types/                 # Shared TypeScript types
|   `-- src/lib/                   # Constants, formatters, demo data, socket
|-- docs/                          # Architecture docs, specs, reports, import map
|-- archive/                       # Archived legacy code
|-- sample_data/                   # Excel source files
|-- sql/                           # Existing SQL setup files
|-- tests/                         # Python tests
|-- Makefile                       # Development shortcuts
`-- requirements.txt               # Shared Python dependencies
```

## Useful URLs

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8001/docs`
- Health: `http://localhost:8001/health`
- Port status: `http://localhost:8001/api/v1/ports/INMAA/status`

Use the port code `INMAA` for Chennai in API calls and frontend state.

## Verification Checklist

- `make seed` completes successfully.
- `make dev-backend` starts the backend.
- `make check` returns valid JSON for `INMAA`.
- Login works with `admin@baos.ai` / `admin123`.
- `make build` passes in the frontend.
- `make test` passes or failures are triaged before release.
