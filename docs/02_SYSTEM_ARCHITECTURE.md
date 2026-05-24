# 4. HIGH-LEVEL SYSTEM ARCHITECTURE

## 4.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER (Next.js 16)                  │
│  Landing │ Login │ Dashboard │ Optimizer │ Recommend │ Commercial│
├─────────────────────────────────────────────────────────────────┤
│                     API LAYER (FastAPI)                          │
│  REST Endpoints │ WebSocket (Socket.IO) │ JWT Auth │ CORS       │
├─────────────────────────────────────────────────────────────────┤
│                   DECISION LAYER                                │
│  Recommender │ Confidence Calculator │ ML Enrichment            │
├──────────────┬──────────────┬───────────────────────────────────┤
│ OPTIMIZATION │   COST       │        ML LAYER                   │
│ CP-SAT Model │ Demurrage    │ Service Time Predictor            │
│ Constraints  │ SLA Penalty  │ Delay Predictor                   │
│ Scheduler    │ Revenue      │ Suitability Classifier            │
│ Feasibility  │ Fuel Burn    │ XGBoost Ranker                    │
├──────────────┴──────────────┴───────────────────────────────────┤
│                  SIMULATION LAYER                               │
│  Digital Twin │ Scenario Engine │ Conflict Detection/Resolution │
├─────────────────────────────────────────────────────────────────┤
│                  EXPLANATION LAYER                              │
│  Structured Explanation │ Agentic Explainer │ Trade-off Analysis│
├─────────────────────────────────────────────────────────────────┤
│              UNCERTAINTY + CONFIDENCE LAYER                     │
│  Monte Carlo Engine │ Quantile Regression │ Risk Scoring        │
├─────────────────────────────────────────────────────────────────┤
│                  DATABASE LAYER                                 │
│  PostgreSQL │ SQLAlchemy ORM │ Commercial Repository            │
├─────────────────────────────────────────────────────────────────┤
│                  DATA LAYER                                     │
│  Spec Ingest │ Port Store │ Quality Gates │ Data Provenance     │
└─────────────────────────────────────────────────────────────────┘
```

## 4.2 Component Responsibility Matrix

| Layer | Components | Responsibility |
|---|---|---|
| **Frontend** | `frontend-next/` | React components, Zustand state, Recharts visualization, WebSocket |
| **API** | `backend/routes/`, `api/endpoints.py` | REST endpoints, JWT auth, request validation, CORS |
| **Decision** | `decision_engine/` | Single-vessel recommendation pipeline, confidence scoring |
| **Optimization** | `optimization_engine/` | CP-SAT model, constraint library, feasibility checker, scheduler |
| **Cost** | `cost_engine/` | Demurrage, fuel, SLA penalty, revenue, net cost computation |
| **ML** | `training_engine/` | Model training, feature engineering, pattern discovery |
| **Simulation** | `simulation_engine/`, `scenario_engine/` | Digital twin, what-if scenarios, conflict detection |
| **Explanation** | `explanation_engine/` | Structured reasoning, agentic explanations, comparison insights |
| **Uncertainty** | `uncertainty_engine/` | Monte Carlo simulation, VaR, risk scoring |
| **Database** | `backend/database/`, `db/` | SQLAlchemy models, migrations, seed data, commercial repository |
| **Data** | `data_layer/` | Excel ingestion, spec sheet parsing, quality scoring |
| **Commercial** | `commercial_engine/` | Revenue optimization, partnership tiers, dynamic pricing |
| **Learning** | `learning_engine/` | Assignment tracking, weekly model refresh |
| **RL** | `rl_engine/` | Reinforcement learning weight agent (stub) |

## 4.3 Request Lifecycle — Single Vessel Recommendation

```
User enters vessel parameters (LOA, beam, draft, cargo, type)
    │
    ▼
Frontend (React) ──POST /api/v1/recommend/{port}──▶ FastAPI Router
    │
    ▼
Recommender Pipeline (decision_engine/recommender.py)
    │
    ├─1─▶ Load PortConfig (port_store) + Trained Models (pkl files)
    │
    ├─2─▶ Feasibility Filtering
    │     ├── ConstraintLibrary.check_feasibility() for each berth
    │     ├── Hard constraint checks: LOA ≤ max_loa, draft ≤ max_draft, beam ≤ max_beam
    │     ├── Vessel type compatibility scoring (compute_compatibility_score)
    │     └── Returns: eligible_berths{} + rejection_reasons{}
    │
    ├─3─▶ ML Inference (for each eligible berth)
    │     ├── build_inference_features(vessel, berth, port_config, congestion)
    │     ├── ServiceTimePredictor.predict_with_uncertainty() → P25/P50/P75
    │     ├── DelayPredictor.predict_with_uncertainty() → P25/P50/P75
    │     └── BerthSuitabilityModel.predict_top_k() → probabilities
    │
    ├─4─▶ DecisionRanker.rank() → sorted BerthOption list
    │     └── Score = w_suit × suitability - uncertainty_penalty
    │
    ├─5─▶ ConfidenceCalculator.compute() → calibrated confidence %
    │     └── α·FeasibilityStability + β·PredictionCertainty + γ·HistoricalMatch + δ·Compatibility
    │
    ├─6─▶ StructuredExplanationEngine.explain() → multi-category reasoning
    │     └── Physical + Operational + Performance + Commercial analysis
    │
    └─7─▶ Response: List[BerthOption] with confidence, pros/cons, explanations
```

## 4.4 Request Lifecycle — Multi-Vessel Optimization

```
User configures N vessels + optimization levers (weights, constraints)
    │
    ▼
Frontend (React) ──POST──▶ /api/v1/optimize
    │
    ▼
RollingHorizonScheduler.optimize()
    │
    ├─1─▶ BerthConstraintModel(vessels, berths, config)
    │     ├── Creates decision variables: X[v,b], start[v], end[v], interval[v,b]
    │     └── Each vessel assigned to exactly one berth (AddExactlyOne)
    │
    ├─2─▶ model.add_physical_constraints()     → C1-C3 (LOA, draft, beam)
    ├─3─▶ model.add_temporal_constraints()     → C4-C7 (non-overlap, availability, night)
    ├─4─▶ model.add_tide_constraints(tides)    → C6 (safe tide windows)
    ├─5─▶ model.add_resource_constraints(res)  → C8-C10 (tug, pilot, channel)
    ├─6─▶ model.add_policy_constraints()       → C11-C15 (customs, FCFS, GoI, SLA)
    ├─7─▶ model.add_downtime_constraints()     → C16 (berth maintenance)
    ├─8─▶ model.add_weather_constraints()      → C17 (adverse weather)
    │
    ├─9─▶ model._build_objective()
    │     └── Minimize: w_wait·Σwait + w_sla·Σsla_excess + w_dem·Σdemurrage
    │                   - w_contract·Σpreferred_berth_bonus
    │                   + w_deviation·Σschedule_instability
    │                   + w_commercial·Σrevenue_loss
    │
    ├─10─▶ solver.Solve() → OPTIMAL or FEASIBLE
    │
    ├─11─▶ CostEngine.compute_schedule_cost() → per-vessel cost breakdown
    ├─12─▶ AgenticExplainer.explain_assignment() → AI reasoning per assignment
    └─13─▶ Response: assignments, KPIs, costs, explanations
```

## 4.5 Data Flow Architecture

```
                    ┌──────────────┐
                    │  Excel Data  │  (Berth_configurations.xlsx,
                    │  Spec Sheets │   Operational_Capability.xlsx,
                    └──────┬───────┘   PortCall_LogData.xlsx)
                           │
                    ┌──────▼───────┐
                    │  data_layer/ │  spec_ingest.py → PortMaster
                    │  ingest.py   │  quality.py → QualityGate scoring
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │   training_engine/      │
              │  feature_builder.py     │  Build training features
              │  ml_models.py           │  Train GBR, RFC models
              │  trainer.py             │  Orchestrate pipeline
              └────────────┬────────────┘
                           │ (serialized .pkl models)
              ┌────────────▼────────────┐
              │   ports/{port}/models/  │  Persisted model artifacts
              │   service_time.pkl      │  + port_config.json
              │   delay_predictor.pkl   │  + feature_columns.json
              │   berth_suitability.pkl │
              └────────────┬────────────┘
                           │ (loaded at inference)
              ┌────────────▼────────────┐
              │   decision_engine/      │  Real-time recommendations
              │   recommender.py        │  using trained models
              │   confidence.py         │  + constraint library
              └─────────────────────────┘
```

---

# 5. FRONTEND ARCHITECTURE (React + Next.js)

## 5.1 Why React + Next.js Were Chosen

| Requirement | Streamlit Limitation | Next.js Solution |
|---|---|---|
| Component reuse | Script reruns on every interaction | React component lifecycle |
| State management | No persistent state across pages | Zustand stores |
| Real-time updates | Polling only | WebSocket (Socket.IO) |
| Complex UI | Limited to Streamlit widgets | Custom components (Gantt, matrices) |
| Type safety | Python duck typing | TypeScript interfaces |
| Performance | Full page rerender | Virtual DOM diffing |
| Authentication | No built-in auth | JWT middleware |
| Deployment | Streamlit Cloud only | Vercel, Nginx, Docker |

## 5.2 Frontend Directory Structure

```
frontend-next/src/
├── app/                          # Next.js App Router
│   ├── page.tsx                  # Landing page — animated hero + feature cards
│   ├── login/page.tsx            # JWT login with demo mode fallback
│   ├── signup/page.tsx           # User registration
│   ├── globals.css               # Design system — CSS custom properties
│   └── dashboard/
│       ├── layout.tsx            # Sidebar + Topbar layout (persistent nav)
│       ├── page.tsx              # Dashboard overview — KPI cards + charts
│       ├── optimizer/
│       │   ├── page.tsx          # Multi-vessel CP-SAT optimizer
│       │   └── types.ts          # Optimizer types + client-side feasibility
│       ├── recommend/page.tsx    # AI recommendation engine
│       └── commercial/page.tsx   # Commercial intelligence dashboard
├── store/                        # Zustand state management
│   └── (auth store, optimizer store, simulation store)
├── hooks/                        # Custom React hooks
│   └── (useWebSocket, useAuth, useOptimizer)
├── lib/                          # API client configuration
│   └── (axios instance, socket client, auth helpers)
└── types/                        # TypeScript interfaces
    └── (vessel, berth, assignment, KPI types)
```

## 5.3 State Management (Zustand)

Zustand was chosen over Redux for its minimal boilerplate and React hook integration. Key stores:

- **Auth Store** — JWT tokens, user profile, login/logout, demo mode detection
- **Optimizer Store** — Vessel configurations, lever values, solver results, assignments, feasibility matrix
- **Simulation Store** — Drag-drop reassignment state, undo/redo stack, conflict propagation

State synchronization pattern:
```
User action → Zustand store update → Component re-render
                    │
                    └── WebSocket emit (if real-time sync needed)
                           │
                    Server processes → WebSocket broadcast → All clients update
```

## 5.4 UI Modules

### Optimizer Dashboard
The most complex UI module. Implements:
- **Vessel Configuration Panel** — Dynamic form for N vessels with LOA/beam/draft/cargo/type/ETA
- **Global Optimization Levers** — 10+ sliders (waiting cost weight, SLA penalty, demurrage, throughput, UKC margin)
- **Per-Ship-Type Levers** — 2-step workflow: select vessel type → select berths → apply custom weights
- **Interactive Berth Timeline** — Hoverable Gantt chart showing wait periods (hatched) and service periods
- **Feasibility Matrix** — Color-coded grid with rich tooltips (LOA/draft/beam clearances, UKC analysis, equipment compatibility, cargo handling match, turnaround projections)
- **Schedule Assignments Table** — With "Change Berth" dropdown for manual overrides
- **Cost Breakdown Table** — Per-vessel cost with "Change Berth" option
- **AI Explanations** — Multi-paragraph decision analysis per assignment
- **Undo/Redo** — Revert all manual overrides to solver-optimal solution

### Recommendation Page
- Vessel detail entry form → top-3 ranked berth recommendations
- Interactive berth allocation timeline with wait + service visualization
- Rich pros/cons with equipment types, throughput rates, dollar amounts
- Expandable "DECISION ANALYSIS" blocks per recommendation

### Dashboard Overview
- Real-time KPI cards: vessel count, revenue, cost, utilization, SLA compliance
- Recharts: monthly comparison bars, utilization trend lines, vessel type distribution pie, cost breakdown

### Commercial Intelligence
- Revenue analytics per berth and vessel type
- Partnership tier management (VIP/Premium/Standard)
- Pattern discovery insights from historical data
