# 6. BACKEND ARCHITECTURE (FastAPI)

## 6.1 Why FastAPI Was Chosen

| Criterion | Flask | FastAPI | Decision Rationale |
|---|---|---|---|
| **Async support** | Requires extensions | Native `async/await` | Port operations need concurrent I/O |
| **Type safety** | No built-in validation | Pydantic v2 models | Vessel/berth schemas are complex |
| **API docs** | Swagger via extension | Auto-generated OpenAPI | Critical for frontend integration |
| **Performance** | WSGI, synchronous | ASGI, 3–10x faster | Solver calls block for seconds |
| **WebSocket** | Flask-SocketIO | python-socketio mount | Real-time schedule updates |
| **Dependency injection** | Manual | Built-in `Depends()` | Clean auth middleware |

## 6.2 Backend Directory Structure

```
backend/
├── main.py              # FastAPI app entry — lifespan, CORS, route mounting
├── run.py               # Uvicorn runner (Windows async event loop fix)
├── config.py            # Pydantic Settings — DB URL, JWT secret, CORS origins
├── .env                 # Environment variables (DB_USER, DB_PASS, JWT_SECRET)
├── routes/
│   ├── auth.py          # POST /auth/login, /auth/register, /auth/refresh
│   ├── dashboard.py     # GET /dashboard/kpis, /dashboard/recent
│   ├── recommendations.py  # POST /recommend, GET /recommendations
│   └── websocket.py     # Socket.IO server — real-time events
├── services/            # Business logic layer
├── database/
│   ├── connection.py    # AsyncSession factory, init_db(), close_db()
│   ├── models.py        # SQLAlchemy ORM: User, Port, Berth, Vessel, Assignment, Recommendation, KPI, AuditLog
│   └── seed.py          # Database seeding — demo data, port configurations
├── auth/                # JWT token creation/verification, password hashing
├── schemas/             # Pydantic request/response models
├── middleware/
│   └── error_handler.py # Global exception handlers
└── tasks/               # Background task definitions (Celery-ready)
```

## 6.3 API Lifecycle

```
HTTP Request
    │
    ▼
FastAPI Router (route matching + Pydantic validation)
    │
    ▼
JWT Auth Middleware (Depends) → validates access token
    │
    ▼
Service Layer → orchestrates engine calls
    │
    ├──▶ Decision Engine (single vessel recommendation)
    ├──▶ Optimization Engine (multi-vessel CP-SAT)
    ├──▶ Cost Engine (financial analysis)
    ├──▶ KPI Engine (operational metrics)
    └──▶ Explanation Engine (AI reasoning)
    │
    ▼
Pydantic Response Model → serialized JSON response
    │
    ▼
WebSocket broadcast (if schedule changed)
```

## 6.4 Key API Endpoints

### Core Optimization API (`api/endpoints.py`)

| Method | Endpoint | Purpose | Request Body |
|---|---|---|---|
| `POST` | `/api/v1/optimize` | Multi-vessel CP-SAT optimization | `OptimizeRequest` (vessels, config, pilot/tug capacity) |
| `POST` | `/api/v1/recommend/{port}` | Single vessel ML recommendation | Vessel parameters (LOA, draft, beam, type, cargo) |
| `GET` | `/api/v1/schedule/{port_code}` | Last computed schedule | — |
| `POST` | `/api/v1/what-if` | Scenario comparison | Baseline vs. modified config |
| `GET` | `/api/v1/kpis/{port_code}` | KPI dashboard data | — |
| `POST` | `/api/v1/feasibility` | Feasibility matrix | Vessels list |
| `GET` | `/api/v1/ports` | Available ports + training status | — |

### Authentication API (`backend/routes/auth.py`)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/login` | JWT access + refresh token |
| `POST` | `/auth/register` | User registration |
| `POST` | `/auth/refresh` | Refresh expired access token |

### Commercial Intelligence API (`api/endpoints.py`)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/commercial/score` | Score berths with commercial factors |
| `GET` | `/api/v1/partnerships` | List partnership tiers |
| `POST` | `/api/v1/partnerships/{id}` | Upsert company partnership |
| `GET` | `/api/v1/berth-economics` | Berth economic profiles |

## 6.5 Async Processing

FastAPI's ASGI architecture enables:

- **Async database queries** via `asyncpg` + SQLAlchemy async sessions
- **Non-blocking I/O** for concurrent recommendation requests
- **WebSocket management** via `python-socketio` mounted at `/ws`

The CP-SAT solver itself is CPU-bound (runs in a C++ thread via OR-Tools), so solver calls are effectively synchronous within the request handler. For production scale, solver calls would be offloaded to Celery workers with Redis as the message broker (infrastructure defined in `backend/requirements.txt` but not yet deployed).

---

# 7. DATABASE ARCHITECTURE (PostgreSQL)

## 7.1 Why PostgreSQL

| Requirement | PostgreSQL Capability |
|---|---|
| **Relational integrity** | Foreign keys, cascading deletes, CHECK constraints |
| **ACID compliance** | Critical for financial data (costs, revenue, SLA records) |
| **JSON support** | `JSON` columns for flexible config, reasoning, vessel snapshots |
| **UUID primary keys** | `UUID(as_uuid=True)` for distributed-safe IDs |
| **Query power** | Window functions, CTEs for KPI aggregation |
| **Scalability** | Connection pooling, read replicas, partitioning |

## 7.2 Database Schema

### Core Tables (SQLAlchemy ORM — `backend/database/models.py`)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│    users     │     │    ports     │     │  berths_master   │
│──────────────│     │──────────────│     │──────────────────│
│ id (UUID PK) │     │ id (UUID PK) │◄────│ port_id (FK)     │
│ email        │     │ name         │     │ code             │
│ password_hash│     │ code (unique)│     │ name             │
│ full_name    │     │ country      │     │ max_loa_m        │
│ role         │     │ config_json  │     │ max_beam_m       │
│ port_id (FK)─┼────▶│              │     │ max_draft_m      │
│ is_active    │     │              │     │ depth_m          │
└──────┬───────┘     └──────┬───────┘     │ equipment (JSON) │
       │                    │             │ vessel_types(JSON)│
       │                    │             └────────┬─────────┘
┌──────▼───────┐     ┌──────▼───────┐            │
│   sessions   │     │     kpi_     │     ┌──────▼─────────┐
│──────────────│     │  snapshots   │     │  assignments   │
│ user_id (FK) │     │──────────────│     │────────────────│
│ refresh_token│     │ port_id (FK) │     │ vessel_id (FK) │
│ expires_at   │     │ date         │     │ berth_id (FK)  │
└──────────────┘     │ vessels_count│     │ port_id (FK)   │
                     │ revenue      │     │ eta            │
                     │ utilization  │     │ status         │
                     │ sla_pct      │     │ turnaround_hrs │
                     │ data_json    │     │ cost / revenue │
                     └──────────────┘     └────────────────┘

┌──────────────┐     ┌──────────────┐
│   vessels    │     │recommendations│
│──────────────│     │──────────────│
│ id (UUID PK) │     │ vessel_id(FK)│
│ name         │     │ berth_code   │
│ vessel_type  │     │ status       │
│ loa/beam/dft │     │ confidence   │
│ cargo_type   │     │ reasoning_json│
│ company      │     │ vessel_data  │
└──────────────┘     └──────────────┘

┌──────────────┐
│  audit_logs  │
│──────────────│
│ user_id (FK) │
│ action       │
│ resource_type│
│ changes_json │
│ ip_address   │
└──────────────┘
```

### Commercial Intelligence Tables (Raw SQL — `db/schema.sql`)

| Table | Purpose | Key Columns |
|---|---|---|
| `berth_economics` | Revenue model per berth | berth_class, specialization, rate schedules, profit margins, dynamic pricing thresholds |
| `vessel_companies` | Partnership management | tier (VIP/Premium/Standard), discount_percentage, annual_contract_value |
| `contract_obligations` | SLA commitments | guaranteed_berth_types, priority_level, sla_turnaround_hours |
| `pricing_rules` | Dynamic pricing logic | utilization thresholds, premium/discount percentages, hazmat premiums |
| `commercial_assignments` | Learning data | predicted vs. actual revenue/profit, SLA compliance tracking |

## 7.3 Indexing Strategy

```sql
CREATE INDEX idx_ca_vessel   ON commercial_assignments(vessel_company);
CREATE INDEX idx_ca_berth    ON commercial_assignments(berth_code);
CREATE INDEX idx_ca_tier     ON commercial_assignments(partnership_tier);
CREATE INDEX idx_ca_dt       ON commercial_assignments(assignment_dt DESC);
CREATE INDEX idx_vc_tier     ON vessel_companies(tier);
```

User email is indexed for login lookups. KPI date is indexed for time-range queries. Berth code is indexed across all tables for join performance.

## 7.4 ORM Layer

- **SQLAlchemy 2.0 (async)** — Declarative models with relationship loading strategies (`selectin` for eager loading, `lazy` for deferred)
- **Pydantic v2 schemas** — Request/response models separate from ORM models; explicit conversion prevents leaking internal state
- **Repository pattern** — `db/commercial_repository.py` abstracts database queries behind functions (`get_all_companies()`, `upsert_company()`, `get_recent_assignments()`)
