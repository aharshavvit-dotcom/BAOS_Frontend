# 16. REAL-TIME USER EXPERIENCE

## 16.1 Dynamic UI Updates

The platform achieves real-time responsiveness through multiple mechanisms:

### WebSocket Integration (Socket.IO)

```
Backend (python-socketio) ◄──── WebSocket ────► Frontend (socket.io-client)
    │                                                │
    ├── schedule_updated event                       ├── useWebSocket hook
    ├── kpi_refresh event                            ├── Auto-reconnect logic
    └── vessel_status_change event                   └── Zustand store update
```

### State Synchronization Pattern

When a user changes a berth assignment in the Optimizer Dashboard:
1. **Local state update** — Zustand store updates immediately (optimistic UI)
2. **API call** — POST to `/api/v1/optimize` with manual override locked
3. **Solver execution** — CP-SAT re-solves with `add_manual_overrides([(vessel, new_berth)])`
4. **Response processing** — New assignments, costs, KPIs, explanations update simultaneously
5. **Cross-component consistency** — Timeline, feasibility matrix, cost table, confidence panel all reflect the new state
6. **Undo stack** — Previous state pushed to undo stack for revert

### Interactive Decision Making

The "Change Berth" feature is available in **two locations** (Schedule Assignments AND Cost Breakdown), ensuring operators can make decisions from whichever analytical context they're viewing. Each change triggers a full re-optimization with the manual override locked, providing:
- Updated cost breakdown for the new assignment
- Updated confidence score with delta explanation
- Updated explanations comparing original vs. override reasoning

---

# 17. DEPLOYMENT ARCHITECTURE

## 17.1 Current Production Stack

```
┌─────────────────────────┐
│   Client Browser        │
│   (Chrome, Firefox)     │
└────────┬────────────────┘
         │ HTTPS
┌────────▼────────────────┐
│   Frontend Hosting      │
│   Vercel / Nginx        │
│   Next.js 16 (SSR/SSG)  │
│   Port: 3000             │
└────────┬────────────────┘
         │ HTTP/WS (API calls)
┌────────▼────────────────┐
│   Backend Server        │
│   Uvicorn (ASGI)        │
│   FastAPI + Socket.IO   │
│   Port: 8001            │
└────────┬────────────────┘
         │ asyncpg
┌────────▼────────────────┐
│   PostgreSQL 14+        │
│   Port: 5433            │
│   Database: baos        │
└─────────────────────────┘
```

## 17.2 Environment Configuration

### Frontend (`frontend-next/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=http://localhost:8001
```

### Backend (`backend/.env`)
```
DB_USER=postgres
DB_PASS=****
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=baos
JWT_SECRET_KEY=****
CORS_ORIGINS=http://localhost:3000
```

## 17.3 Windows-Specific Configuration

The backend includes a Windows async event loop fix:
```python
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```
This is required because `asyncpg` (PostgreSQL driver) needs `SelectorEventLoop` on Windows, not the default `ProactorEventLoop`.

## 17.4 Future Infrastructure Roadmap

| Component | Current | Planned | Rationale |
|---|---|---|---|
| **Container Orchestration** | Manual | Kubernetes | Auto-scaling solver pods |
| **Cache** | None | Redis | Session store, solver result caching |
| **Message Queue** | None | Kafka/Redis | Async solver job queue via Celery |
| **Load Balancer** | Single Uvicorn | Nginx reverse proxy | SSL termination, rate limiting |
| **Monitoring** | Console logs | Prometheus + Grafana | KPI dashboards, alerting |
| **CI/CD** | Manual | GitHub Actions | Automated testing + deployment |

---

# 18. CURRENT LIMITATIONS

### Honest Technical Assessment

| # | Limitation | Impact | Planned Mitigation |
|---|---|---|---|
| 1 | **No true stochastic optimization** | Monte Carlo runs deterministic solver N times — not a stochastic programming formulation | Future: Two-stage stochastic programming with recourse |
| 2 | **Synthetic tide generation** | Tides are generated via `generate_sample_tides()` with semi-diurnal formula, not real tide data | Integration with hydrographic service APIs |
| 3 | **Limited real-time data** | No AIS feed, no live port occupancy, no real-time ETA updates | Future: AIS API integration for live vessel tracking |
| 4 | **No hydrographic integration** | Under-keel clearance uses static berth depth + synthetic tides | Integration with port hydrographic survey data |
| 5 | **RL agent is a stub** | `rl_engine/weight_agent.py` has the architecture but no trained policy | Future: Train RL agent to learn optimal weight configurations |
| 6 | **Resource approximation** | Tug/pilot availability uses simple capacity numbers, not individual resource scheduling | Future: Individual resource tracking with assignment optimization |
| 7 | **Single-port optimization** | System optimizes one port at a time; no multi-port corridor optimization | Future: Multi-port supply chain optimization |
| 8 | **No model monitoring** | No drift detection, no performance degradation alerts | Future: MLflow or similar for model lifecycle management |
| 9 | **Cost rates are defaults** | Most cost rates are hardcoded assumptions, not from port tariff schedules | Integration with port tariff databases |
| 10 | **No multi-user concurrency** | Solver runs synchronously in API handler | Future: Celery workers for async solver execution |

---

# 19. FUTURE ROADMAP

## 19.1 Short-Term (1–3 months)

| Initiative | Description |
|---|---|
| **Better confidence calibration** | Bayesian calibration using assignment outcome data |
| **Real-time APIs** | AIS vessel tracking integration for live ETA updates |
| **Improved cost optimization** | Port tariff schedule ingestion; dynamic rate loading |
| **Model monitoring** | Drift detection + automatic retraining triggers |
| **Celery workers** | Async solver execution for concurrent users |

## 19.2 Mid-Term (3–6 months)

| Initiative | Description |
|---|---|
| **ETA uncertainty modeling** | Bayesian ETA prediction with historical delay distributions |
| **Resource optimization** | Individual tug/pilot scheduling as part of the CP-SAT model |
| **Sensitivity analysis** | Automated exploration of how weight changes affect outcomes |
| **Multi-scenario planning** | Named scenario management with comparison dashboards |
| **Real tide data** | Integration with hydrographic service APIs |

## 19.3 Long-Term (6–12 months)

| Initiative | Description |
|---|---|
| **Reinforcement Learning** | Train RL agent to learn optimal optimizer weight configurations from outcomes |
| **Autonomous planning** | Fully automated berth planning with human-in-the-loop override only |
| **Multi-port optimization** | Corridor-level scheduling across connected ports |
| **Stochastic programming** | Two-stage optimization with recourse for ETA uncertainty |
| **Digital twin V2** | Physics-based port simulation with vessel dynamics |

---

# 20. KEY LIBRARIES & TECHNOLOGIES

| Library | Version | Purpose | Why Chosen |
|---|---|---|---|
| **React** | 19.2 | Frontend UI framework | Component model, virtual DOM, massive ecosystem |
| **Next.js** | 16.2 | React meta-framework | SSR, file-based routing, API routes, optimized builds |
| **TypeScript** | 5.x | Type-safe JavaScript | Catches schema mismatches at compile time |
| **Tailwind CSS** | 4.x | Utility-first CSS | Consistent design tokens, rapid prototyping |
| **Zustand** | 5.x | State management | Minimal boilerplate vs. Redux; hook-based API |
| **Recharts** | 3.x | React charting | Native React integration, responsive, accessible |
| **Axios** | 1.x | HTTP client | Interceptors for JWT refresh, cancellation tokens |
| **Socket.IO** | 4.x | WebSocket client | Auto-reconnect, fallback to polling, room support |
| **Framer Motion** | 12.x | Animations | Declarative animations, layout transitions |
| **FastAPI** | 0.110+ | Backend framework | Async, auto-docs, Pydantic, fastest Python framework |
| **SQLAlchemy** | 2.0+ | ORM | Async support, mature, relationship loading |
| **PostgreSQL** | 14+ | Relational database | ACID, JSON columns, UUID, production-grade |
| **Pydantic** | 2.0+ | Data validation | TypeDict-style models, fast validation |
| **scikit-learn** | 1.3+ | ML models | GBR, RFC, cross-validation, feature importance |
| **OR-Tools** | 9.9+ | CP-SAT solver | Google's constraint programming solver, industry-grade |
| **XGBoost** | 2.0+ | Gradient boosting | Ranking model for commercial intelligence |
| **pandas** | 2.0+ | Data processing | Excel ingestion, feature engineering, analysis |
| **NumPy** | 1.24+ | Numerical computing | Array operations, statistical computations |
| **python-jose** | 3.3+ | JWT tokens | Access + refresh token creation/verification |
| **bcrypt** | 4.0+ | Password hashing | Industry-standard password security |

---

# 21. COMPLETE END-TO-END SYSTEM FLOW

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OFFLINE PIPELINE                                │
│                                                                         │
│  Historical Excel Data                                                  │
│       │                                                                 │
│       ▼                                                                 │
│  Data Ingestion (data_layer/)                                          │
│  ├── spec_ingest.py → PortMaster (berth specs with provenance)         │
│  └── ingest.py → Cleaned DataFrame (port call history)                 │
│       │                                                                 │
│       ▼                                                                 │
│  Feature Engineering (training_engine/feature_builder.py)              │
│  └── Vessel features + berth features + derived features → X matrix    │
│       │                                                                 │
│       ▼                                                                 │
│  ML Training (training_engine/trainer.py)                              │
│  ├── ServiceTimePredictor → service_time.pkl (P25/P50/P75)            │
│  ├── DelayPredictor → delay_predictor.pkl (P25/P50/P75)               │
│  ├── BerthSuitabilityModel → berth_suitability.pkl                     │
│  └── DecisionRanker → decision_ranker.pkl                              │
│       │                                                                 │
│       ▼                                                                 │
│  ports/{port}/models/ → Serialized artifacts                           │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ (loaded at runtime)
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ONLINE PIPELINE                                  │
│                                                                         │
│  User Input (vessel parameters or multi-vessel configuration)           │
│       │                                                                 │
│       ▼                                                                 │
│  Feasibility Validation                                                │
│  ├── ConstraintLibrary.check_feasibility() — spec-backed hard checks   │
│  └── compute_compatibility_score() — vessel-berth type matching        │
│       │                                                                 │
│       ├── [Single Vessel] ────────────────────────────────────────────  │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  ML Inference                                                   │
│       │  ├── ServiceTimePredictor.predict_with_uncertainty()            │
│       │  ├── DelayPredictor.predict_with_uncertainty()                  │
│       │  └── BerthSuitabilityModel.predict_top_k()                     │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  DecisionRanker.rank() → Sorted berth options                  │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  ConfidenceCalculator.compute() → Calibrated confidence %      │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  StructuredExplanationEngine.explain() → 4-category reasoning  │
│       │                                                                 │
│       ├── [Multi Vessel] ─────────────────────────────────────────────  │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  CP-SAT Constraint Model                                       │
│       │  ├── Build variables: X[v,b], start[v], end[v], interval[v,b]  │
│       │  ├── Add constraints: C1-C17 (physical, temporal, resource)    │
│       │  ├── Build objective: weighted multi-objective function         │
│       │  └── Solve → OPTIMAL / FEASIBLE / INFEASIBLE                  │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  Cost Engine → Per-vessel cost breakdown                        │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  KPI Engine → Utilization, throughput, SLA compliance          │
│       │       │                                                         │
│       │       ▼                                                         │
│       │  Explanation Engine → AI reasoning per assignment               │
│       │                                                                 │
│       └──────────────────────────────────────────────────────────────── │
│               │                                                         │
│               ▼                                                         │
│  Frontend Visualization                                                │
│  ├── Interactive Gantt timeline                                        │
│  ├── Feasibility matrix with rich tooltips                             │
│  ├── Cost breakdown tables                                             │
│  ├── KPI dashboard cards + charts                                      │
│  ├── AI explanation panels                                             │
│  └── Confidence scoring display                                        │
│               │                                                         │
│               ▼                                                         │
│  User Simulation (drag-drop, change berth, undo/redo)                  │
│               │                                                         │
│               ▼                                                         │
│  Re-Optimization (CP-SAT with manual overrides locked)                 │
│               │                                                         │
│               ▼                                                         │
│  Updated schedule, costs, KPIs, explanations                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

> **This document represents the complete technical design of the BAOS AI Maritime Decision Intelligence Platform — a production-grade system combining machine learning, constraint optimization, cost modeling, uncertainty quantification, and explainable AI for intelligent berth allocation at scale.**

---

*Document prepared by the BAOS AI Engineering Team — May 2026*
*Chennai Port Authority / BAOS AI*
