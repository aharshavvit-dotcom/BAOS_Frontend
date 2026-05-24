# BAOS AI — Maritime Decision Intelligence Platform

> AI-powered berth allocation optimization for modern ports. Reduce turnaround time, maximize revenue, and ensure SLA compliance.

---

## 🏗 Architecture

```
berth_optimization_poc_app/
├── frontend-next/          # Next.js 16 + TypeScript + Tailwind CSS + Recharts
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                 # Landing page
│   │   │   ├── login/page.tsx           # Login page
│   │   │   ├── signup/page.tsx          # Sign up page
│   │   │   ├── globals.css              # Design system (CSS tokens)
│   │   │   └── dashboard/
│   │   │       ├── layout.tsx           # Sidebar + Topbar layout
│   │   │       ├── page.tsx             # Dashboard overview
│   │   │       ├── optimizer/
│   │   │       │   ├── page.tsx         # CP-SAT Multi-Vessel Optimizer
│   │   │       │   └── types.ts         # Optimizer types + feasibility engine
│   │   │       ├── recommend/page.tsx   # AI Recommendation Engine
│   │   │       └── commercial/page.tsx  # Commercial Intelligence
│   │   ├── store/                       # Zustand state stores
│   │   ├── hooks/                       # Custom React hooks (WebSocket)
│   │   ├── lib/                         # API client, socket client
│   │   └── types/                       # TypeScript interfaces
│   └── .env.local                       # API URL config
│
├── backend/                # FastAPI + SQLAlchemy + PostgreSQL
│   ├── main.py             # FastAPI application entry
│   ├── run.py              # Uvicorn runner (Windows async fix)
│   ├── config.py           # Pydantic settings (DB, JWT, CORS)
│   ├── routes/             # API endpoints (auth, recommendations, dashboard)
│   ├── services/           # Business logic layer
│   ├── database/           # SQLAlchemy models + migrations + seed
│   ├── auth/               # JWT authentication dependencies
│   ├── schemas/            # Pydantic request/response models
│   └── middleware/          # CORS, logging middleware
│
├── optimization_engine/    # CP-SAT constraint solver
├── commercial_engine/      # XGBoost ranking + pattern discovery
├── cost_engine/            # Waiting/fuel/SLA cost calculations
├── decision_engine/        # Multi-factor decision fusion
├── explanation_engine/     # Natural language explanations
├── kpi_engine/             # KPI aggregation & dashboards
├── learning_engine/        # Outcome tracking + adaptive learning
├── simulation_engine/      # What-if scenario analysis
├── uncertainty_engine/     # Confidence interval estimation
├── training_engine/        # Model training pipelines
├── rl_engine/              # Reinforcement learning agent
├── scenario_engine/        # Scenario planning
│
├── api/                    # Legacy endpoint layer
├── db/                     # Legacy database layer (schema, seed)
├── data_layer/             # Data access layer
├── ports/                  # Port-specific configuration (Chennai)
├── sample_data/            # Original data sources (Excel, docs)
├── test_data/              # QA test datasets (5 scenarios)
├── tests/                  # Unit & integration tests
├── config.py               # Root-level config (legacy)
├── models.py               # Root-level models (legacy)
└── requirements.txt        # Python dependencies
```

---

## 🚀 Quick Start & Database Setup

### Prerequisites

- **Node.js** ≥ 18 (for frontend)
- **Python** ≥ 3.10 (for backend)
- **PostgreSQL** ≥ 12 (configured on port `5433` by default)

### 1. Database Schema & Ingestion

BAOS now uses a **database-first architecture** with the `baos` schema inside PostgreSQL. All port configs, berth capabilities, operational assumptions, and port-call histories are stored in the database.

To initialize the schema and ingest Excel/CSV source files:

1. Ensure PostgreSQL is running on port `5433` (or update credentials in `backend/.env`).
2. Run the ingestion command:
   ```bash
   python scripts/ingest_excel_to_db.py \
       --port-code INMAA \
       --port-name "Chennai Port" \
       --berth-config sample_data/Berth_configurations.xlsx \
       --berth-capability sample_data/Operational_Capability_of_Berth.xlsx \
       --port-call-log sample_data/Chennai_PORTLOG2025JUN-DEC.xlsx
   ```

*Note: The CLI script automatically creates the `baos` schema, executes schema creation (`sql/001_create_baos_schema.sql`), seeds operational assumptions (`sql/002_seed_assumptions.sql`), sets up database indexes (`sql/003_create_indexes.sql`), and loads your Excel sheets idempotently.*

### 2. Backend (FastAPI)

```bash
cd backend
# Install dependencies
pip install -r requirements.txt

# Run seed script for user management/commercial tables (if needed)
python -m database.seed

# Run FastAPI server
python run.py
```

Backend runs at **http://localhost:8001** (or port specified in `run.py`).

### 3. Frontend (Next.js)

```bash
cd frontend-next
npm install
npm run dev
```

App runs at **http://localhost:3000**. No authentication redirects are enforced on internal dashboard paths (auth is only required on the `/login` landing page).

---

## ✨ Features

### 🚢 Multi-Vessel Optimizer (CP-SAT)
- Configure N vessels with LOA, beam, draft, cargo type, vessel type, ETA
- **Global Levers**: 10+ optimization weights (waiting cost, SLA penalty, demurrage, throughput, UKC margin)
- **Per Ship Type Levers**: 2-step workflow — select vessel type → select berths → apply custom lever config
- **Interactive Berth Timeline**: Hoverable/clickable Gantt chart with vessel details tooltip (showing berth name rather than internal berth code)
- **Feasibility Matrix**: Color-coded grid with rich floating tooltips showing:
  - LOA/draft/beam clearances with exact margins
  - UKC (under-keel clearance) analysis with tide access status
  - Equipment compatibility (crane types, handling capacity)
  - Cargo handling match with throughput (TPH) estimates
  - Turnaround time projections
- **AI Agentic Explanations**: Multi-paragraph, decision-grade reasoning per assignment covering physical fit, equipment matching, and confidence score
- **Next-Optimal Berth Selection**: Change berth from Schedule Assignments AND Cost Breakdown views
- **Undo/Redo**: Revert all manual overrides to solver-optimal solution

### 🧠 Get Recommendation
- Enter vessel details → receive top 3 ranked berth recommendations
- **Interactive Berth Allocation Timeline**: Shows wait periods and service periods with hover tooltips
- **Rich Pros/Cons**: Equipment types, throughput rates, logistics context, dollar amounts
- **AI Agentic Explanations**: Expandable "DECISION ANALYSIS" blocks per recommendation with scoring breakdown and trade-off comparisons

### 📊 Dashboard & Assumptions
- Real-time KPIs: vessel count, revenue, cost, utilization, SLA compliance
- Charts: monthly comparison, utilization trend, vessel distribution, cost breakdown
- **Assumptions Panel**: Modify demurrage rates, wait/fuel costs, and pilot parameters at runtime via backend endpoints. Changes affect optimization cost engine instantly without requiring restart or file changes.

---

## 🛠 Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, TypeScript, Tailwind CSS, Recharts, Zustand, Axios |
| **Backend** | FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Database** | PostgreSQL 12+ with `psycopg2` (sync) and `asyncpg` (async) |
| **Real-time** | Socket.IO (WebSocket) |
| **Auth** | JWT tokens (access + refresh), bcrypt password hashing (restricted only to login) |
| **Optimization** | OR-Tools CP-SAT Solver, XGBoost ranking model |
| **ML/AI** | scikit-learn, pattern discovery engine, adaptive learning |

---

## 🔧 Environment Variables

### Frontend (`frontend-next/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=http://localhost:8001
```

### Backend (`backend/.env`)
```
DB_USER=postgres
DB_PASS=postgres@123
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=ML_APP
DATABASE_URL=postgresql+asyncpg://postgres:postgres%40123@localhost:5433/ML_APP
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres%40123@localhost:5433/ML_APP
JWT_SECRET_KEY=baos-ai-super-secret-key-change-in-production-2026
```

---

## 📁 Data Sources

| File | Description |
|---|---|
| `sample_data/Berth_configurations.xlsx` | Master berth dimensional specs & restrictions |
| `sample_data/Operational_Capability_of_Berth.xlsx` | Allowed vessel types and commodity groups per berth |
| `sample_data/Chennai_PORTLOG2025JUN-DEC.xlsx` | Historical port call log data from Chennai |

---

## 🧪 Testing

The codebase features a robust, tiered testing hierarchy covering ingestion, repositories, constraints, optimization, and integration.

Run the test suites using the virtual environment:

```bash
# 1. Core Optimizer & Scenario Tests
python tests/run_tests.py

# 2. Spec-Based Data Pipeline Tests
python tests/test_spec_pipeline.py

# 3. Data Ingestion Pipeline Unit Tests
python tests/test_ingestion.py

# 4. Database Repositories Unit Tests
python tests/test_repositories.py

# 5. End-to-End Integration Tests
python tests/test_integration.py
```

---

## 📝 Design Decisions

1. **Database-First Ingestion**: Port operators load specifications and call histories via a dedicated admin utility CLI (`ingest_excel_to_db.py`). The runtime application operates directly on the SQL database (`baos` schema), eliminating local Excel reads during decision-making.

2. **Berth Code vs Name representation**: Internal components process logical strings (e.g. `berth_code`), while all visual schedules, timeline tooltips, and recommendation matrices display user-friendly `berth_name` strings.

3. **No Auth guards on internal dashboard pages**: For seamless operations inside the port network, authentication redirects are removed from dashboard layouts, enabling immediate entry without token checks.

4. **White Theme**: Clean, professional white/light premium aesthetic across all pages.

5. **Modular Engine Architecture**: Each engine (cost, decision, explanation, KPI, learning, optimization, simulation, etc.) is a self-contained package to allow isolated unit testing and future microservice migration.

---

## 📄 License

Proprietary — Chennai Port Authority / BAOS AI Team
