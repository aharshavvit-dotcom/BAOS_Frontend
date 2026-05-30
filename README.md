# BAOS AI Application

BAOS is a FastAPI + Next.js application for berth allocation, berth suitability recommendations, and port operations analytics.

The current runtime flow is database-first:

1. `python -m database.seed` creates/updates the database schema, seeds users, and ingests the bundled Excel sample data.
2. `python run.py` starts the backend and automatically checks the seeded data.
3. If valid data exists and active ML models are missing or stale, the backend trains and registers the required models automatically.
4. The frontend reads backend status and uses `port_code` values such as `INMAA` for all API calls.

No separate manual training command is required.

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- PostgreSQL 12 or newer
- A PostgreSQL database named `ML_APP`

The default backend database configuration expects PostgreSQL on port `5433`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres%40123@localhost:5433/ML_APP
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres%40123@localhost:5433/ML_APP
```

Update `backend/.env` if your local database user, password, host, port, or database name is different.

## Install Dependencies

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r backend\requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend-next
npm install
cd ..
```

## Seed the Database

Run this from the repository root:

```powershell
python -m database.seed
```

This command is idempotent. It creates or updates the `baos` schema, applies the SQL setup files, seeds application users, and ingests:

- `sample_data/Berth_configurations.xlsx` into `baos.berth`
- `sample_data/Operational_Capability_of_Berth.xlsx` into `baos.berth_capability`
- `sample_data/Chennai_PORTLOG2025JUN-DEC.xlsx` into `baos.port_call`

Seeded login accounts:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@baos.ai` | `admin123` |
| Operator | `operator@baos.ai` | `operator123` |

Email login is case-insensitive; emails are normalized to lowercase.

## Run the Backend

From the repository root:

```powershell
python run.py
```

The backend runs at `http://localhost:8001` by default.

If port `8001` is already in use:

```powershell
$env:BACKEND_PORT="8002"
python run.py
```

Useful backend URLs:

- API docs: `http://localhost:8001/docs`
- Port list and status: `http://localhost:8001/api/v1/ports`
- Chennai status: `http://localhost:8001/api/v1/ports/INMAA/status`

## Backend Startup Training

On startup, the backend checks these tables:

- `baos.berth`
- `baos.berth_capability`
- `baos.port_call`

When enough valid rows exist, it trains and registers these active models in `baos.ml_model_registry`:

- `berth_suitability`
- `service_time_predictor`
- `delay_predictor`

If training fails, the backend still starts. Status responses and the frontend will show one of these states:

- `Data Missing`
- `Data Loaded - Training Pending`
- `Training In Progress`
- `Trained`
- `Training Failed`
- `Insufficient Data`

## Run the Frontend

Check `frontend-next/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=http://localhost:8001
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_ENABLE_WEBSOCKET=false
```

If you started the backend on another port, update both URL values before starting the frontend.

Then run:

```powershell
cd frontend-next
npm run dev
```

Open `http://localhost:3000`.

## Build the Frontend

```powershell
cd frontend-next
npm run build
```

To run the production build:

```powershell
npm run start
```

## Normal Local Run Order

Use this order after dependencies are installed:

```powershell
python -m database.seed
python run.py
```

In a second terminal:

```powershell
cd frontend-next
npm run dev
```

Then log in at `http://localhost:3000/login` with `admin@baos.ai` and `admin123`.

## Port Code Rule

Use the port code `INMAA` for Chennai in API calls and frontend state. Do not use display names such as `Chennai Port` as API identifiers.

Examples:

```text
/api/v1/ports/INMAA/status
/api/v1/ports/INMAA/config
```

## Project Layout

```text
.
|-- run.py                         # Root backend launcher
|-- database/                      # Root compatibility wrapper for python -m database.seed
|-- backend/                       # FastAPI backend
|   |-- main.py                    # App startup and auto-training hook
|   |-- run.py                     # Uvicorn runner
|   |-- database/seed.py           # Schema, user seed, and Excel ingestion
|   |-- routes/                    # API routes
|   |-- services/                  # Auth, training, config, recommendation services
|   `-- .env                       # Backend environment
|-- frontend-next/                 # Next.js frontend
|   |-- src/app/                   # App Router pages
|   |-- src/lib/                   # API clients
|   |-- src/store/                 # Zustand stores
|   `-- .env.local                 # Frontend environment
|-- sample_data/                   # Excel source files
|-- sql/                           # BAOS schema and indexes
`-- requirements.txt               # Shared Python dependencies
```

## Troubleshooting

If login returns `401`, reseed the database and try the seeded credentials again:

```powershell
python -m database.seed
```

If the frontend cannot reach the backend, confirm `NEXT_PUBLIC_API_URL` matches the backend URL and restart `npm run dev`.

If model status is not `Trained`, check `http://localhost:8001/api/v1/ports/INMAA/status` for `training_message`, `models_missing`, `models_stale`, and `valid_training_rows`.

## Verification Checklist

Before handing off a local run, verify:

- `python -m database.seed` completes successfully.
- `python run.py` starts the backend without blocking startup on training failures.
- `GET /api/v1/ports/INMAA/status` reports the expected data/training status.
- Login works with `admin@baos.ai` / `admin123`.
- Frontend pages load at `http://localhost:3000`.
- `npm run build` passes inside `frontend-next`.
