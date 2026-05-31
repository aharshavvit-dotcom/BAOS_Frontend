# BAOS AI — Maritime Decision Intelligence Platform

BAOS (Berth Allocation & Optimization System) is a production-grade FastAPI + Next.js monorepo for intelligent berth allocation, ML-backed recommendations, constraint optimization, and port analytics.

## Quick Start (Manual PowerShell)

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r backend\requirements.txt

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Setup database, migrate, and seed
python -m database.setup
alembic upgrade head
python -m database.seed

# 4. Start development servers (in separate terminal sessions or tabs)
# Start FastAPI backend (http://localhost:8001)
python run.py

# Start Next.js frontend (http://localhost:3000)
cd frontend
npm run dev
```

The runtime flow is database-first:

1. **Database creation** via `python -m database.setup` (creates the `baos` database, idempotent).
2. **Schema migration** via `alembic upgrade head` (applies all schema changes).
3. **Data seeding** via `python -m database.seed` (seeds the DB with demo data and users).
4. **Backend initialization** via `python run.py` (checks database connection and model registry).
5. **Automatic Model Training**: If valid data is seeded/ingested and ML model files are missing or stale, the backend trains them on startup.
6. **Frontend launch** via `npm run dev` (run from the `frontend/` directory).

> [!NOTE]
> If you have `make` installed and prefer shorthand commands, you can run `make setup`, `make dev-backend`, `make dev-frontend`, or `make dev`.

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- PostgreSQL 12 or newer (port `5433` by default)
- *Optional:* `make` for shortcut commands

Ensure database connection details in `backend/.env` are configured correctly before running setup commands.

## Development Commands

| Action | Manual PowerShell Command | Makefile Shortcut | Description |
|---|---|---|---|
| **Full Setup** | `python -m database.setup; alembic upgrade head; python -m database.seed` | `make setup` | Create DB → migrate → seed |
| **Create DB** | `python -m database.setup` | `make db-create` | Create `baos` database (idempotent) |
| **Migrate Schema** | `alembic upgrade head` | `make migrate` | Run Alembic migrations |
| **Seed Database** | `python -m database.seed` | `make seed` | Seed database with demo data and users |
| **Run Backend** | `python run.py` | `make dev-backend` | Start FastAPI backend (port 8001) |
| **Run Frontend** | `cd frontend; npm run dev` | `make dev-frontend` | Start Next.js frontend (port 3000) |
| **Run Parallel** | *Open two terminal tabs and run backend & frontend separately* | `make dev` | Start backend + frontend in parallel |
| **Run Tests** | `pytest tests/ -v` | `make test` | Run Python tests |
| **Build Frontend** | `cd frontend; npm run build` | `make build` | Build frontend for production |
| **Lint Code** | `cd frontend; npm run lint; cd ..; ruff check backend/ engines/` | `make lint` | Lint frontend (ESLint) + backend (ruff) |
| **Train ML Models** | `Invoke-RestMethod -Method Post -Uri http://localhost:8001/api/v1/training/trigger` | `make train` | Trigger ML model training via API |
| **Health Check** | `Invoke-RestMethod -Uri http://localhost:8001/api/v1/ports/INMAA/status` | `make check` | Health check: GET /api/v1/ports/INMAA/status |
| **Clean Project** | *See cache cleaning commands below* | `make clean` | Remove caches and build artifacts |
| **Import Map** | `python -c "import subprocess, pathlib; r = subprocess.run(['git', 'grep', '-nI', 'import '], capture_output=True, text=True); pathlib.Path('docs/import_map.txt').write_text(r.stdout, encoding='utf-8')"` | `make import-map` | Regenerate docs/import_map.txt |
| **Show Help** | *Check the Makefile directly* | `make help` | Show all available Makefile commands |

### Cleaning Caches manually (PowerShell)

To clean up build cache files, Python compiled files, and logs manually, run the following:
```powershell
# Remove Python __pycache__ folders
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Remove compiled Python files
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue

# Remove frontend build caches and test caches
Remove-Item -Recurse -Force frontend/.next, frontend/out, .pytest_cache -ErrorAction SilentlyContinue
```

### Seeded Login Accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@baos.ai` | `admin123` |
| Operator | `operator@baos.ai` | `operator123` |

## Project Layout

```text
.
├── run.py                         # Root backend launcher
├── database/                      # DB setup + seed wrapper (python -m database.setup/seed)
├── backend/                       # FastAPI backend
│   ├── main.py                    # App factory: lifespan, CORS, route mounting
│   ├── run.py                     # Uvicorn runner
│   ├── config/                    # Pydantic Settings, port configuration
│   ├── auth/                      # JWT helpers, password hashing, dependencies
│   ├── routes/                    # API route modules and registry
│   ├── services/                  # Domain services (auth, dashboard, training)
│   ├── handlers/                  # Request handling and response shaping
│   ├── db/
│   │   ├── models/                # SQLAlchemy ORM (app_models + baos_models)
│   │   ├── repositories/          # Database and port-store repositories
│   │   └── session.py             # Engine/session factories
│   ├── middleware/                 # Error handlers and middleware
│   ├── schemas/                   # Pydantic API schemas
│   ├── migrations/                # Alembic migration package and SQL assets
│   └── utils/                     # Shared backend utilities
├── engines/                       # ML, optimization, ingestion, and analytics
│   ├── base_engine.py             # ABC base with processor pattern
│   ├── core/                      # Inference: berth_suitability, decision, delay, service_time
│   ├── analytics/                 # KPI, commercial, cost, explanation engines
│   ├── simulation/                # Optimization (CP-SAT), scenario, uncertainty
│   ├── learning/                  # Training, RL, data prep
│   ├── ingestion/                 # Excel ingestion and spec transforms
│   └── ports/                     # Port-specific model artifacts and data
├── frontend/                      # Next.js 16 frontend
│   ├── src/app/                   # App Router pages (dashboard, login, etc.)
│   ├── src/components/            # UI, layout, charts, feature components
│   ├── src/hooks/                 # React data/auth hooks
│   ├── src/services/              # API clients and domain services
│   ├── src/store/                 # Zustand stores (auth, dashboard, port, UI)
│   ├── src/types/                 # Shared TypeScript types
│   └── src/lib/                   # Constants, formatters, demo data, socket
├── docs/                          # Architecture docs, specs, import map
├── archive/                       # Archived legacy code (api/, etc.)
├── sample_data/                   # Excel source files for ingestion
├── sql/migrations/                # Versioned SQL migration files
├── scripts/                       # Utility scripts (Excel ingestion)
├── db/                            # Legacy connection pool and seed data
├── alembic.ini                    # Alembic configuration
├── tests/                         # Python tests
├── Makefile                       # Development shortcuts
└── requirements.txt               # Shared Python dependencies
```

## Useful URLs

| URL | Description |
|---|---|
| `http://localhost:3000` | Frontend |
| `http://localhost:8001/docs` | Swagger UI (API docs) |
| `http://localhost:8001/redoc` | ReDoc (API docs) |
| `http://localhost:8001/health` | Health check |
| `http://localhost:8001/api/v1/ports/INMAA/status` | Port status |

Use port code `INMAA` for Chennai in API calls and frontend state.

## Verification Checklist

- [ ] Database setup completes (`python -m database.setup; alembic upgrade head; python -m database.seed`)
- [ ] Backend starts (`python run.py`) and backend log shows `✅ Database tables ready`
- [ ] Health check status returns valid JSON (`Invoke-RestMethod -Uri http://localhost:8001/api/v1/ports/INMAA/status`)
- [ ] Login works with admin credentials: `admin@baos.ai` / `admin123`
- [ ] Frontend build succeeds (`cd frontend; npm run build`)
- [ ] Python tests pass (`pytest tests/ -v`)

## Database

The application uses PostgreSQL with two schema layers:

- **Public schema** — Users, sessions, ports, berths, vessels, assignments, recommendations, KPIs, audit logs
- **`baos` schema** — Domain-specific: port calls, berth capabilities, ingestion batches, ML model registry, optimization runs, training runs

Database name: `baos` (previously `ML_APP` — renamed in Phase 1).

## ML Pipeline

Four models are trained automatically when sufficient data exists:

| Model | Type | Output |
|---|---|---|
| **ServiceTimePredictor** | Quantile GBR | P25/P50/P75 berth occupancy hours |
| **DelayPredictor** | Quantile GBR | P25/P50/P75 waiting/delay hours |
| **BerthSuitabilityModel** | Random Forest Classifier | P(berth | vessel) probabilities |
| **DecisionRanker** | Weighted scorer | Combined ranked berth recommendations |

Models are saved with feature hash validation to prevent stale-model inference.
