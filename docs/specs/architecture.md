# BAOS Architecture Specification

## System Overview

The **Berth Allocation Optimization System (BAOS)** is a decision intelligence platform for maritime port operations. It combines constraint programming (CP-SAT), machine learning, and commercial intelligence to optimize vessel-to-berth assignments.

> **Important**: All data-driven outputs in this system are labeled with their source quality (SPEC, HISTORICAL, ML_PREDICTED, ASSUMPTION). Values labeled ASSUMPTION are estimates — not guarantees — and require real operational data before production deployment.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BAOS Decision Intelligence                      │
├────────────────────────────────────────┬────────────────────────────┤
│         Next.js Frontend               │     FastAPI Backend        │
│                                        │                            │
│  ┌──────────────┐  ┌──────────────┐   │  ┌──────────────────────┐  │
│  │  Dashboard    │  │  Optimizer   │   │  │  Legacy API (v1)     │  │
│  │  (KPIs/Charts)│  │  (CP-SAT)   │   │  │  POST /optimize      │  │
│  └──────────────┘  └──────┬───────┘   │  │  POST /feasibility   │  │
│  ┌──────────────┐         │           │  │  POST /what-if        │  │
│  │  Recommend   │  ┌──────▼───────┐   │  │  GET  /ports          │  │
│  │  (Per-Vessel) │  │  Scenario   │   │  │  POST /scenarios/     │  │
│  └──────────────┘  │  Manager     │   │  │      apply-override   │  │
│  ┌──────────────┐  └──────────────┘   │  └──────────────────────┘  │
│  │  Commercial  │                     │  ┌──────────────────────┐  │
│  │  Intelligence│                     │  │  Backend App         │  │
│  └──────────────┘                     │  │  (Auth, Dashboard)   │  │
│  ┌──────────────┐                     │  │  JWT + PostgreSQL    │  │
│  │  Analytics   │                     │  └──────────────────────┘  │
│  └──────────────┘                     │                            │
├────────────────────────────────────────┼────────────────────────────┤
│              Zustand Stores            │        Engine Layer        │
│  ┌────────┐ ┌──────────┐ ┌─────────┐  │                            │
│  │ Port   │ │ Optimizer│ │Dashboard│  │  ┌────────────────┐        │
│  │ Store  │ │ Store    │ │ Store   │  │  │ Optimization   │        │
│  └───┬────┘ └────┬─────┘ └────┬────┘  │  │ Engine (CP-SAT)│        │
│      │           │            │       │  │ 15 constraints │        │
│      └───────────┼────────────┘       │  └────────────────┘        │
│                  │                    │  ┌────────────────┐        │
│      ┌───────────▼────────────┐       │  │ Cost Engine    │        │
│      │  API Client Layer      │       │  └────────────────┘        │
│      │  lib/api/*.ts          │───────│  ┌────────────────┐        │
│      │  • optimizer.ts        │  HTTP │  │ ML Enrichment  │        │
│      │  • recommendations.ts  │◄─────►│  │ Service Time   │        │
│      │  • ports.ts            │       │  │ Predictor      │        │
│      │  • feasibility.ts      │       │  └────────────────┘        │
│      │  • scenarios.ts        │       │  ┌────────────────┐        │
│      └────────────────────────┘       │  │ Explanation    │        │
│                                       │  │ Engine         │        │
│                                       │  └────────────────┘        │
│                                       │  ┌────────────────┐        │
│                                       │  │ Scenario       │        │
│                                       │  │ Manager        │        │
│                                       │  └────────────────┘        │
│                                       │  ┌────────────────┐        │
│                                       │  │ Decision       │        │
│                                       │  │ Engine         │        │
│                                       │  │ (Confidence +  │        │
│                                       │  │  ML Enrichment)│        │
│                                       │  └────────────────┘        │
├───────────────────────────────────────┼────────────────────────────┤
│               Data Layer              │                            │
│  ┌────────────────────────────────────┴──────────────────────────┐ │
│  │  ports/{port_name}/                                           │ │
│  │    ├── port_config.json  (berth specs, vessel types)          │ │
│  │    ├── history.csv       (historical port-call data)          │ │
│  │    └── models/           (trained ML models)                  │ │
│  │         ├── berth_suitability.pkl                             │ │
│  │         ├── service_time.pkl                                  │ │
│  │         ├── delay_predictor.pkl                               │ │
│  │         └── metadata.json                                     │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture

### Two FastAPI Applications

| App | Entry Point | Port | Auth Required | Purpose |
|-----|------------|------|---------------|---------|
| Legacy API | `api/endpoints.py` | 8000 | No | CP-SAT optimization, feasibility, ports, KPIs |
| Backend App | `backend/main.py` | 8001 | JWT | Auth, dashboard, recommendations |

The Backend App mounts the Legacy API routes, so both coexist.

### API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/v1/ports` | No | List available ports with training status |
| `GET` | `/api/v1/ports/{code}/status` | No | Port model info, data quality, berth count |
| `GET` | `/api/v1/ports/{code}/config` | No | Full port config with berth inventory |
| `POST` | `/api/v1/optimize` | No | Run multi-vessel CP-SAT optimization |
| `POST` | `/api/v1/feasibility` | No | Feasibility matrix (vessel × berth) |
| `POST` | `/api/v1/what-if` | No | What-if scenario comparison |
| `POST` | `/api/v1/scenarios/apply-override` | No | Apply manual override → re-optimize |
| `POST` | `/api/v1/optimizer/ranked-alternatives` | No | Solver-ranked berth alternatives per vessel |
| `GET` | `/api/v1/schedule/{port}` | No | Last computed schedule |
| `GET` | `/api/v1/kpis/{port}` | No | KPI dashboard for last schedule |
| `POST` | `/api/v1/commercial/score` | No | Commercial scoring |
| `GET` | `/api/v1/partnerships` | No | Partnership list |
| `POST` | `/api/recommendations/get-recommendation` | JWT | Per-vessel berth recommendation |
| `GET` | `/api/dashboard/kpis` | JWT | Dashboard KPIs |
| `GET` | `/api/dashboard/charts` | JWT | Dashboard chart data |

### Engine Layer

| Engine | File | Purpose |
|--------|------|---------|
| **Optimization** | `optimization_engine/constraint_model.py` | CP-SAT formulation with 15 constraint types |
| **Scheduler** | `optimization_engine/scheduler.py` | Rolling horizon scheduler wrapper |
| **Feasibility** | `optimization_engine/feasibility_checker.py` | Hard/soft constraint checking |
| **Cost** | `cost_engine/cost_model.py` | Waiting, fuel, equipment, SLA cost computation |
| **ML Enrichment** | `decision_engine/ml_enrichment.py` | Predict per-vessel service time from trained models |
| **Confidence** | `decision_engine/confidence.py` | Calibrated confidence scoring |
| **Recommender** | `decision_engine/recommender.py` | Single-vessel berth recommendation engine |
| **Scenario** | `scenario_engine/scenario_manager.py` | What-if / override scenario management |
| **Explanation** | `explanation_engine/explainer.py` | Agentic AI explanations |
| **Training** | `training_engine/ml_models.py` | XGBoost model training (service time, suitability) |
| **Commercial** | `commercial_engine/commercial_scorer.py` | Revenue, partnership, dynamic pricing |

---

## Frontend Architecture

### Technology Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.2.1 | React framework with App Router |
| React | 19.2.4 | UI library |
| Zustand | 5.0.12 | State management |
| Recharts | 3.8.1 | Charts and visualizations |
| Axios | 1.14.0 | HTTP client |
| Framer Motion | 12.38.0 | Animations |

### Store Architecture

| Store | File | Manages |
|-------|------|---------|
| `usePortStore` | `store/portStore.ts` | Port selection, berth inventory, model status |
| `useOptimizerStore` | `store/optimizerStore.ts` | Vessels, levers, results, overrides |
| `useDashboardStore` | `store/dashboardStore.ts` | KPIs, charts, recommendations |
| `useAuthStore` | `store/authStore.ts` | JWT tokens, user session |

### API Client Architecture

All API calls go through `lib/api/client.ts` which provides:
- JWT token attachment via request interceptor
- 401 refresh token flow
- Demo mode awareness (`NEXT_PUBLIC_DEMO_MODE`)
- Standardized error extraction

Domain-specific API services:
- `lib/api/ports.ts` — Port config and status
- `lib/api/optimizer.ts` — CP-SAT optimization with unit conversion
- `lib/api/recommendations.ts` — Per-vessel recommendations
- `lib/api/feasibility.ts` — Feasibility matrix
- `lib/api/scenarios.ts` — Manual overrides and what-if

### Component Library

| Category | Components |
|----------|-----------|
| Common | `KpiCard`, `StatusBadge`, `SectionHeader`, `LoadingState`, `ErrorState`, `EmptyState`, `ScenarioImpactBanner` |
| Optimizer | `SolverStatusBanner` |
| Port | `PortSelector` |

---

## Data Model

### Port Configuration

Each port is stored as a directory under `ports/{port_name}/`:

```
ports/chennai/
  ├── port_config.json   # Berth specs, vessel types, service time stats
  ├── history.csv        # Historical port-call data (607 rows for Chennai)
  └── models/
       ├── berth_suitability.pkl  (35.6 MB — XGBoost classifier)
       ├── service_time.pkl       (670 KB — XGBoost regressor)
       ├── delay_predictor.pkl    (293 KB — delay prediction)
       ├── decision_ranker.pkl    (61 B — placeholder)
       ├── feature_columns.json   (feature alignment)
       └── metadata.json          (training metrics, date range)
```

### Chennai Port — 23 Berths across 4 Terminals

| Terminal | Berths | Vessel Types |
|----------|--------|-------------|
| Jawahar Terminal | JD1–JD6 | Bulk Dry, Chemical, Container, General Cargo, Oil |
| CITPL Terminal | SCB1–SCB3 | Container, General Cargo |
| CCTL Terminal | CTB1–CTB4 | Container, General Cargo |
| Oil Terminal | BD1–BD3 | Chemical, Oil |
| Ambedkar Terminal | 1 South, 2 South, 1–4 West, C | Bulk Dry, Chemical, General Cargo, RoRo, Other |

### CP-SAT Constraint Model (15 Constraints)

| # | Constraint | Type | Description |
|---|-----------|------|-------------|
| C1 | LOA Fit | Hard | vessel.loa ≤ berth.max_loa |
| C2 | Draft Clearance | Hard | vessel.draft + UKC ≤ berth.depth |
| C3 | Beam Fit | Hard | vessel.beam ≤ berth.max_beam |
| C4 | Non-overlap | Hard | One vessel per berth at any time |
| C5 | Berth Availability | Hard | Assignment within berth windows |
| C6 | Tide Window | Hard | Berthing during safe tide periods |
| C7 | Night Restriction | Hard | No night ops unless berth allows 24×7 |
| C8 | Tug Availability | Hard | Cumulative tug constraint |
| C9 | Pilot Availability | Hard | Cumulative pilot constraint |
| C10 | Channel Capacity | Hard | Max simultaneous movements |
| C11 | Customs Clearance | Hard | Vessel must be cleared |
| C12 | FCFS Ordering | Soft | ETA order respected |
| C13 | GoI Override | Hard | Government priority vessels first |
| C14 | Contract Preference | Soft | Preferred berth bonus |
| C15 | SLA Commitment | Soft | Penalty for exceeding SLA wait |

---

## Assumption-Based Placeholders

All cost and decision factors that lack real operational data are clearly labeled:

| Parameter | Value | Unit | Source | Used in Objective |
|-----------|-------|------|--------|-------------------|
| Demurrage Rate | 500 | USD/hour | ASSUMPTION | Yes |
| Fuel Wait Rate | 150 | USD/hour | ASSUMPTION | Yes |
| SLA Penalty | 1,000 | USD/hour | ASSUMPTION | Yes |
| Revenue per Ton | 2.50 | USD/ton | ASSUMPTION | Yes |
| UKC Safety Margin | 0.5 | meters | ASSUMPTION | Yes |
| Pilot Capacity | 2 | pilots | ASSUMPTION | Yes |
| Tug Capacity | 3 | tugs | ASSUMPTION | Yes |

> See `frontend-next/src/lib/constants/assumptionDefaults.ts` for the full list with descriptions and confidence multipliers.

---

## Environment Configuration

```env
# Backend API endpoint
NEXT_PUBLIC_API_URL=http://localhost:8000

# Demo mode: when true, shows demo data if backend unavailable
# When false, shows proper error states
NEXT_PUBLIC_DEMO_MODE=false

# WebSocket real-time updates
NEXT_PUBLIC_ENABLE_WEBSOCKET=false
```
