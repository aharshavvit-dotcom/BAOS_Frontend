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

## 🚀 Quick Start

### Prerequisites

- **Node.js** ≥ 18 (for frontend)
- **Python** ≥ 3.10 (for backend)
- **PostgreSQL** ≥ 14 (optional — app works with demo mode)

### 1. Frontend (Next.js)

```bash
cd frontend-next
npm install
npm run dev
```

App runs at **http://localhost:3000**

### 2. Backend (FastAPI) — Optional

```bash
cd backend
pip install -r requirements.txt

# Configure database in backend/.env or backend/config.py
# Seed database
python -m database.seed

# Run server
python run.py
```

Backend runs at **http://localhost:8001**

### 3. Initial Credentials for Testing (Demo Mode)

When the backend (PostgreSQL/FastAPI) is not running, the application automatically enters **demo mode** (client-side simulation). You can use the following default test credentials to log in:

- **Admin Account:**
  - **Email:** `admin@baos.ai`
  - **Password:** `admin123`

- **Operator Account:**
  - **Email:** `operator@baos.ai`
  - **Password:** `operator123`

*(Note: In demo mode, any valid email format with a password of at least 4 characters will also work as a guest account.)*

---

## ✨ Features

### 🚢 Multi-Vessel Optimizer (CP-SAT)
- Configure N vessels with LOA, beam, draft, cargo type, vessel type, ETA
- **Global Levers**: 10+ optimization weights (waiting cost, SLA penalty, demurrage, throughput, UKC margin)
- **Per Ship Type Levers**: 2-step workflow — select vessel type → select berths → apply custom lever config
- **Interactive Berth Timeline**: Hoverable/clickable Gantt chart with vessel details tooltip
- **Feasibility Matrix**: Color-coded grid with rich floating tooltips showing:
  - LOA/draft/beam clearances with exact margins
  - UKC (under-keel clearance) analysis with tide access status
  - Equipment compatibility (crane types, handling capacity)
  - Cargo handling match with throughput (TPH) estimates
  - Turnaround time projections
- **AI Agentic Explanations**: Multi-paragraph, decision-grade reasoning per assignment covering:
  - Physical fit analysis (LOA margin, UKC, beam coverage)
  - Equipment & cargo infrastructure matching
  - Wait time impact & cost analysis
  - Confidence score breakdown
- **Next-Optimal Berth Selection**: Change berth from both Schedule Assignments AND Cost Breakdown views
- **Undo/Redo**: Revert all manual overrides to solver-optimal solution

### 🧠 Get Recommendation
- Enter vessel details → receive top 3 ranked berth recommendations
- **Interactive Berth Allocation Timeline**: Shows wait periods (hatched) and service periods with hover tooltips
- **Rich Pros/Cons**: Equipment types, throughput rates, logistics context, dollar amounts
- **AI Agentic Explanations**: Expandable "DECISION ANALYSIS" blocks per recommendation with:
  - Multi-factor scoring breakdown
  - Trade-off comparisons between options
  - Conditional recommendations ("Choose this if...")

### 📊 Dashboard
- Real-time KPIs: vessel count, revenue, cost, utilization, SLA compliance
- Charts: monthly comparison, utilization trend, vessel distribution, cost breakdown
- Recent recommendations with accept/reject workflow

### 💰 Commercial Intelligence
- Revenue analytics per berth/vessel type
- Contract performance monitoring
- Pattern discovery insights

---

## 🛠 Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, TypeScript, Tailwind CSS, Recharts, Zustand, Axios |
| **Backend** | FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Database** | PostgreSQL 14+ with `psycopg[binary]` driver |
| **Real-time** | Socket.IO (WebSocket) |
| **Auth** | JWT tokens (access + refresh), bcrypt password hashing |
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
DB_PASS=your_password
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=ML_APP
JWT_SECRET_KEY=your-secret-key
```

---

## 📁 Data Sources

| File | Description |
|---|---|
| `sample_data/PortCall_LogData-Chennai-2025June-Dec.xlsx` | Historical port call data from Chennai |
| `test_data/dataset_1_normal_ops.xlsx` | Normal operations scenario |
| `test_data/dataset_2_congestion.xlsx` | Port congestion scenario |
| `test_data/dataset_3_large_draft.xlsx` | Deep draft vessel scenario |
| `test_data/dataset_4_equipment_constraint.xlsx` | Equipment limitation scenario |
| `test_data/dataset_5_mixed_priority.xlsx` | Mixed vessel priority scenario |

---

## 🧪 Testing

```bash
# Backend unit tests
cd backend && python -m pytest tests/ -v

# Frontend build verification
cd frontend-next && npx next build
```

---

## 📝 Design Decisions

1. **Demo Mode Fallback**: Frontend works fully without backend — uses client-side simulation for optimizer/recommendations and demo auth. This allows instant demos without infrastructure setup.

2. **Rich Feasibility Data**: Each berth has 11 properties (max LOA/draft/beam, channel depth, equipment list, cargo types, throughput TPH, rail access, hazmat certification, terminal name) enabling decision-grade tooltips.

3. **Change Berth Everywhere**: Users can change vessel-berth assignments from both the Schedule Assignments table AND the Cost Breakdown table, not just one place.

4. **White Theme**: Clean, professional white/light aesthetic across all pages. No dark mode.

5. **Modular Engine Architecture**: Each engine (cost, decision, explanation, KPI, learning, optimization, etc.) is an independent Python package with its own `__init__.py`, enabling unit testing and future microservice decomposition.

---

## 📄 License

Proprietary — Chennai Port Authority / BAOS AI Team
