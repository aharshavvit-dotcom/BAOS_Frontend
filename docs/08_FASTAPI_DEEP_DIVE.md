# FASTAPI BACKEND DEEP DIVE — Production Architecture

> Complete code-level documentation of the BAOS AI backend

---

# 1. ARCHITECTURE OVERVIEW

The backend is a **production-grade FastAPI application** with:
- Async PostgreSQL via SQLAlchemy 2.0 + asyncpg
- JWT authentication with access + refresh tokens
- Real-time WebSocket via Socket.IO (ASGI mount)
- Dual API layer: modern routes + legacy engine endpoints
- Pydantic v2 request/response validation
- Service-layer business logic separation

```
backend/
├── main.py              # App factory — lifespan, CORS, route mounting, WS
├── run.py               # Uvicorn entry — Windows event loop fix
├── config.py            # Pydantic Settings — DB, JWT, CORS, Redis
├── .env                 # Secrets (DB_PASS, JWT_SECRET)
│
├── routes/              # ─── API Route Handlers ───
│   ├── auth.py          # /api/auth/* — login, signup, refresh, me, logout
│   ├── dashboard.py     # /api/dashboard/* — KPIs, charts, recommendations
│   ├── recommendations.py  # /api/recommendations/* — generate, list, update
│   └── websocket.py     # Socket.IO server — events + broadcast helpers
│
├── services/            # ─── Business Logic Layer ───
│   ├── auth_service.py  # User CRUD, password hashing, token creation
│   ├── dashboard_service.py  # KPI aggregation, chart data queries
│   └── recommendation_service.py  # Engine orchestration, DB persistence
│
├── auth/                # ─── Security Layer ───
│   ├── jwt_handler.py   # create_access_token(), verify_token()
│   ├── password.py      # hash_password(), verify_password() (bcrypt)
│   └── dependencies.py  # get_current_user() FastAPI dependency
│
├── database/            # ─── Data Access Layer ───
│   ├── connection.py    # AsyncSession factory, init_db(), close_db()
│   ├── models.py        # 8 SQLAlchemy ORM models (215 lines)
│   └── seed.py          # Demo data seeding
│
├── schemas/             # ─── Pydantic Models ───
│   ├── auth.py          # LoginRequest, SignupRequest, TokenResponse, etc.
│   ├── dashboard.py     # KPIResponse, ChartsResponse, etc.
│   └── recommendations.py  # RecommendationRequest, RecommendationResponse
│
├── middleware/
│   └── error_handler.py # Global exception handlers (HTTP, validation, DB)
│
└── tasks/               # ─── Background Tasks (Celery-ready) ───
    └── (stub)
```

---

# 2. APPLICATION LIFECYCLE (`main.py` — 147 lines)

## 2.1 Windows Async Fix

```python
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```
**Why:** `asyncpg` (PostgreSQL driver) requires `SelectorEventLoop` on Windows. The default `ProactorEventLoop` causes "NotImplementedError: Windows proactor event loop does not support SelectorEventLoop API" errors.

## 2.2 Lifespan Events

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 BAOS AI backend starting up...")
    await init_db()          # Create all tables, run migrations
    logger.info("✅ Database tables ready")
    yield
    logger.info("🛑 Shutting down...")
    await close_db()         # Dispose connection pool
```

## 2.3 App Construction

```python
app = FastAPI(
    title=settings.APP_NAME,       # "BAOS AI - Maritime Decision Intelligence"
    description="Production-grade FastAPI backend...",
    version=settings.APP_VERSION,  # "3.0.0"
    docs_url="/docs",              # Swagger UI
    redoc_url="/redoc",            # ReDoc
    lifespan=lifespan,
)
```

## 2.4 Middleware Stack

```python
# 1. CORS — allow frontend origin
app.add_middleware(CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # ["http://localhost:3000", ...]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Global error handlers
register_error_handlers(app)
```

## 2.5 Route Registration

```python
# Modern routes (authenticated, database-backed)
app.include_router(auth_router)            # /api/auth/*
app.include_router(dashboard_router)       # /api/dashboard/*
app.include_router(recommendations_router) # /api/recommendations/*

# Legacy engine endpoints (from parent project — backward compatible)
from api.endpoints import app as legacy_app
for route in legacy_app.routes:
    if route.path not in ("/docs", "/redoc", "/openapi.json"):
        app.routes.append(route)           # /api/v1/* (optimize, recommend, etc.)

# WebSocket mount
app.mount("/ws", socket_app)               # Socket.IO at /ws/socket.io
```

**Design Decision — Dual API Layer:** The legacy `api/endpoints.py` was built first for the Streamlit prototype. Rather than rewriting all endpoints during migration, they're mounted directly into the production app. This allows incremental migration — new features go through `backend/routes/`, legacy features work unchanged via `/api/v1/*`.

---

# 3. CONFIGURATION (`config.py` — 76 lines)

```python
class Settings(BaseSettings):
    # Database (individual parts for special character safety)
    DB_USER: str = "postgres"
    DB_PASS: str = "****"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5433
    DB_NAME: str = "baos"

    # JWT
    JWT_SECRET_KEY: str = "baos-ai-super-secret-key-..."
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440   # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Infrastructure
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8501"]'

    # App
    APP_NAME: str = "BAOS AI - Maritime Decision Intelligence"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True
```

**Key Design Decisions:**

1. **`DB_PASS` as separate field:** Database URLs with special characters (e.g., `@`, `#`) in passwords break standard URL parsing. Using `URL.create()` from SQLAlchemy properly escapes them.

2. **`CORS_ORIGINS` as JSON string:** Pydantic Settings reads from `.env` files where list types aren't native. A JSON-encoded string is parsed via `json.loads()` at runtime.

3. **24-hour access tokens:** Long-lived tokens reduce refresh overhead for single-user port operations. In multi-tenant production, this should be reduced to 15–30 minutes.

---

# 4. DATABASE LAYER

## 4.1 Connection (`database/connection.py`)

```python
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Design Decisions:**
- `expire_on_commit=False` — Prevents lazy-load exceptions after commit (common async ORM pitfall)
- Auto-commit/rollback in `get_db()` — Clean transaction lifecycle per request
- `create_all` at startup — Simple for development; production should use Alembic migrations

## 4.2 ORM Models (`database/models.py` — 215 lines)

### Entity Relationship Diagram

```
┌──────────┐ 1    N ┌──────────┐
│  User    │───────│ Session  │
│          │       └──────────┘
│ port_id──┼──┐
└──────────┘  │    ┌──────────┐ 1    N ┌──────────────┐
              └───▶│  Port    │───────│ Berth        │
                   │          │       │ (berths_     │
                   │          │       │  master)     │
                   │          │       └──────┬───────┘
                   │          │ 1    N       │
                   │          │───────┐      │
                   └──────────┘       │      │
                                      ▼      ▼
                              ┌──────────────────┐
                              │  Assignment       │
                              │  vessel_id (FK)   │
                              │  berth_id (FK)    │
                              │  port_id (FK)     │
                              │  assigned_by (FK) │
                              └──────────────────┘

┌──────────┐ 1    N ┌────────────────┐
│  Vessel  │───────│ Recommendation │
│          │       │ berth_code     │
│          │       │ confidence     │
│          │       │ reasoning_json │
│          │       │ vessel_data_json│
│          │       │ status         │
└──────────┘       └────────────────┘

┌──────────────┐
│  KPI         │
│ (snapshots)  │
│  port_id(FK) │
│  date        │
│  revenue     │
│  utilization │
│  data_json   │
└──────────────┘

┌──────────────┐
│  AuditLog    │
│  user_id(FK) │
│  action      │
│  changes_json│
│  ip_address  │
└──────────────┘
```

### Model Details

| Model | Table | PK | Key Columns | Relationships |
|---|---|---|---|---|
| **User** | `users` | UUID | email (unique, indexed), password_hash, role, port_id | → Port, → Sessions |
| **Session** | `sessions` | UUID | user_id, refresh_token (unique, indexed), expires_at | → User |
| **Port** | `ports` | UUID | name, code (unique, indexed), country, config_json (JSON) | → Users, → Berths, → KPIs |
| **Berth** | `berths_master` | UUID | port_id, code (indexed), max_loa/beam/draft_m, depth_m, equipment_types (JSON), allowed_vessel_types (JSON) | → Port, → Assignments |
| **Vessel** | `vessels` | UUID | name, vessel_type, loa/beam/draft_m, dwt, cargo_type, imo_number | → Assignments, → Recommendations |
| **Assignment** | `assignments` | UUID | vessel_id, berth_id, port_id, status, turnaround_hours, cost/revenue/profit, assigned_by | → Vessel, → Berth |
| **Recommendation** | `recommendations` | UUID | vessel_id, berth_code, port_code, status, confidence_score, reasoning_json (JSON), vessel_data_json (JSON) | → Vessel |
| **KPI** | `kpi_snapshots` | UUID | port_id, date (indexed), vessels_count, revenue, utilization_pct, data_json (JSON) | → Port |
| **AuditLog** | `audit_logs` | UUID | user_id, action, resource_type, changes_json (JSON), ip_address | — |

**Design Decisions:**
- **UUID primary keys** — Globally unique, safe for distributed systems, no sequential guessing
- **JSON columns** — `config_json`, `reasoning_json`, `data_json`, `equipment_types` — flexible schema for evolving requirements without migrations
- **`selectin` lazy loading** — User→Port uses `lazy="selectin"` to avoid N+1 queries on login
- **Separate Recommendation table** — Decoupled from assignments; recommendations can be `accepted`, `rejected`, or remain `recommended`

---

# 5. API ROUTES

## 5.1 Authentication Routes (`routes/auth.py` — 105 lines)

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | ❌ | Validate credentials → return `{access_token, refresh_token, user}` |
| `POST` | `/api/auth/signup` | ❌ | Create user → return tokens |
| `POST` | `/api/auth/refresh` | ❌ | Exchange refresh token → new access token |
| `GET` | `/api/auth/me` | ✅ | Return current user profile |
| `POST` | `/api/auth/logout` | ✅ | Revoke all sessions for user |

**Authentication Flow:**
```
Login Request (email, password)
    │
    ▼
authenticate_user(db, email, password)
    ├── SELECT user WHERE email = ?
    ├── bcrypt.verify(password, user.password_hash)
    └── Return User or None
    │
    ▼ (if authenticated)
create_tokens(db, user)
    ├── access_token = jwt.encode({sub: user.id, exp: now+24h}, SECRET, HS256)
    ├── refresh_token = jwt.encode({sub: user.id, type: refresh, exp: now+7d}, ...)
    ├── INSERT INTO sessions (user_id, refresh_token, expires_at)
    └── Return (access_token, refresh_token)
    │
    ▼
TokenResponse { access_token, refresh_token, user: UserResponse }
```

**Token Refresh Flow:**
```
Refresh Request (refresh_token)
    │
    ▼
refresh_access_token(db, refresh_token)
    ├── SELECT session WHERE refresh_token = ? AND expires_at > NOW()
    ├── Decode JWT → extract user_id
    ├── Generate new access_token
    └── Return new access_token (or None if expired)
```

## 5.2 Dashboard Routes (`routes/dashboard.py` — 56 lines)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/dashboard/kpis?port_code=INMAA` | ✅ | KPI cards (vessels, revenue, utilization, SLA) |
| `GET` | `/api/dashboard/charts?port_code=INMAA&time_range=30d` | ✅ | Chart datasets (monthly comparison, utilization trend, vessel distribution, cost breakdown) |
| `GET` | `/api/dashboard/recommendations?port_code=INMAA&status=all` | ✅ | Recent recommendations list |

All routes use `Depends(get_current_user)` — returns 401 if token invalid/expired.

## 5.3 Recommendation Routes (`routes/recommendations.py` — 125 lines)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/recommendations/get-recommendation` | ✅ | Generate berth recommendations for a vessel |
| `GET` | `/api/recommendations?port_code=INMAA&status=all&limit=20&offset=0` | ✅ | List recommendations with pagination |
| `PATCH` | `/api/recommendations/{recommendation_id}` | ✅ | Accept or reject a recommendation |

**Recommendation Generation Flow:**
```
POST /api/recommendations/get-recommendation
Body: { vessel_name, vessel_type, loa_m, beam_m, draft_m, dwt, cargo_type, cargo_tons, port_code }
    │
    ▼
generate_recommendation() (services/recommendation_service.py)
    │
    ├── Load port configuration from database
    ├── Build VesselInput from request parameters
    ├── Load trained ML models (pkl files)
    │
    ├── For each berth:
    │   ├── ConstraintLibrary.check_feasibility(vessel, berth)
    │   ├── compute_compatibility_score(vessel_type, cargo_type, equipment, allowed_types)
    │   ├── ServiceTimePredictor.predict_with_uncertainty(features) → P25/P50/P75
    │   ├── DelayPredictor.predict_with_uncertainty(features) → P25/P50/P75
    │   └── BerthSuitabilityModel.predict_proba(features) → P(berth|vessel)
    │
    ├── DecisionRanker.rank() → sorted berth options
    ├── ConfidenceCalculator.compute() → calibrated confidence
    ├── StructuredExplanationEngine.explain() → 4-category reasoning
    │
    ├── INSERT INTO recommendations (vessel_id, berth_code, confidence, reasoning_json)
    │
    └── Return: { recommendation_id, recommendations: BerthRecommendation[], vessel_name }
```

## 5.4 Legacy Engine API (`api/endpoints.py` — 541 lines)

Mounted directly into the production app for backward compatibility:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/optimize` | Multi-vessel CP-SAT optimization |
| `POST` | `/api/v1/recommend/{port}` | Legacy single vessel recommendation |
| `GET` | `/api/v1/schedule/{port_code}` | Last computed schedule |
| `POST` | `/api/v1/what-if` | Scenario comparison |
| `GET` | `/api/v1/kpis/{port_code}` | KPI dashboard |
| `POST` | `/api/v1/feasibility` | Feasibility matrix |
| `GET` | `/api/v1/ports` | Available ports |
| `POST` | `/api/v1/commercial/score` | Commercial scoring |
| `GET` | `/api/v1/partnerships` | Partnership list |
| `GET` | `/api/v1/berth-economics` | Berth economic profiles |
| `GET` | `/health` | Health check |

---

# 6. WEBSOCKET SERVER (`routes/websocket.py` — 92 lines)

## 6.1 Server Setup

```python
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=settings.DEBUG,
)
socket_app = socketio.ASGIApp(sio, socketio_path="/api/realtime")
```

## 6.2 Client Events

| Event | Direction | Description |
|---|---|---|
| `connect` | Client→Server | Log connection, send welcome notification |
| `disconnect` | Client→Server | Log disconnection |
| `subscribe_kpi` | Client→Server | Join room `kpi:{port_id}` for targeted updates |
| `unsubscribe_kpi` | Client→Server | Leave KPI room |
| `subscribe_recommendations` | Client→Server | Join `recommendations` room |
| `subscribe_vessel_status` | Client→Server | Join `vessel:{vessel_id}` room |

## 6.3 Broadcast Helpers

Called from services/tasks to push real-time updates:

```python
async def broadcast_kpi_update(port_id: str, kpi_data: dict):
    await sio.emit("kpi_updated", kpi_data, room=f"kpi:{port_id}")

async def broadcast_recommendation(recommendation_data: dict):
    await sio.emit("recommendation_generated", recommendation_data, room="recommendations")

async def broadcast_assignment_change(vessel_id: str, assignment_data: dict):
    await sio.emit("assignment_status_changed", assignment_data, room=f"vessel:{vessel_id}")
    await sio.emit("assignment_status_changed", assignment_data, room="recommendations")

async def broadcast_notification(message: str, msg_type: str = "info"):
    await sio.emit("notification", {"message": message, "type": msg_type})
```

**Room-based broadcasting** ensures targeted delivery — only subscribers of a specific port/vessel receive updates.

---

# 7. SECURITY ARCHITECTURE

## 7.1 Password Security

- **Hashing:** bcrypt with automatic salt generation
- **Verification:** Constant-time comparison (prevents timing attacks)
- **Storage:** Only `password_hash` stored in database; plaintext never persisted

## 7.2 JWT Token Architecture

| Token Type | Lifetime | Payload | Storage |
|---|---|---|---|
| **Access Token** | 24 hours | `{sub: user_id, exp: timestamp}` | Client localStorage |
| **Refresh Token** | 7 days | `{sub: user_id, type: "refresh", exp: timestamp}` | Client localStorage + DB sessions table |

**Security Properties:**
- Refresh tokens are stored in the `sessions` table — can be revoked server-side
- Logout revokes all sessions for the user (not just current)
- Expired refresh tokens are rejected at the database level (`expires_at > NOW()`)

## 7.3 Request Authentication

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(token)   # Decode JWT, check expiry
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Invalid credentials")
    return user
```

Every authenticated route includes `user: User = Depends(get_current_user)` — a clean FastAPI dependency injection pattern.

---

# 8. ERROR HANDLING

The `middleware/error_handler.py` registers global exception handlers:

| Exception | HTTP Code | Response |
|---|---|---|
| `HTTPException` | As specified | Standard FastAPI response |
| `RequestValidationError` | 422 | `{detail: "Validation error", errors: [...]}` |
| `SQLAlchemyError` | 500 | `{detail: "Database error"}` (no internal details leaked) |
| `Exception` (catch-all) | 500 | `{detail: "Internal server error"}` |

**Design Decision:** Database errors are caught and sanitized to prevent SQL/schema information leakage in production.

---

# 9. DEPENDENCY CHART

```
main.py
  ├── config.py (Settings)
  ├── database/connection.py (init_db, close_db, get_db)
  ├── middleware/error_handler.py
  ├── routes/
  │   ├── auth.py
  │   │   ├── auth/dependencies.py (get_current_user)
  │   │   ├── schemas/auth.py (LoginRequest, TokenResponse, ...)
  │   │   └── services/auth_service.py
  │   │       ├── auth/jwt_handler.py (create_access_token, verify_token)
  │   │       ├── auth/password.py (hash_password, verify_password)
  │   │       └── database/models.py (User, Session)
  │   ├── dashboard.py
  │   │   ├── schemas/dashboard.py
  │   │   └── services/dashboard_service.py
  │   │       └── database/models.py (KPI, Assignment)
  │   ├── recommendations.py
  │   │   ├── schemas/recommendations.py
  │   │   └── services/recommendation_service.py
  │   │       ├── database/models.py (Recommendation, Vessel)
  │   │       └── (parent project engines)
  │   │           ├── decision_engine/recommender.py
  │   │           ├── optimization_engine/feasibility_checker.py
  │   │           └── explanation_engine/structured_explanation.py
  │   └── websocket.py (Socket.IO server)
  └── api/endpoints.py (legacy routes, mounted at startup)
      ├── optimization_engine/constraint_model.py
      ├── optimization_engine/scheduler.py
      ├── cost_engine/cost_model.py
      ├── decision_engine/confidence.py
      ├── kpi_engine/kpi_calculator.py
      └── explanation_engine/explainer.py
```

---

# 10. RUNNING THE BACKEND

## Development
```bash
cd backend
python run.py    # → uvicorn main:app --reload --port 8001
```

## Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

## API Documentation
- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc
- **Health Check:** http://localhost:8001/health
