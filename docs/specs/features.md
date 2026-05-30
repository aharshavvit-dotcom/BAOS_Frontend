# BAOS — Implemented Features

> Last updated: 2026-05-24

## Feature Matrix

### ✅ Fully Implemented

| # | Feature | Frontend | Backend | Notes |
|---|---------|----------|---------|-------|
| 1 | Multi-vessel CP-SAT optimization | ✅ Optimizer page | ✅ `POST /api/v1/optimize` | 15 hard/soft constraints, OR-Tools CP-SAT solver |
| 2 | Per-vessel berth recommendation | ✅ Recommend page | ✅ `POST /api/recommendations/get-recommendation` | AI-powered with parameter-level breakdown |
| 3 | Feasibility matrix | ✅ API client ready | ✅ `POST /api/v1/feasibility` | Hard/soft violation check per vessel×berth pair |
| 4 | Cost engine | ✅ Cost display | ✅ `cost_engine/cost_model.py` | Waiting, fuel, equipment, SLA penalty, revenue |
| 5 | AI explanations | ✅ Explanation cards | ✅ `explanation_engine/explainer.py` | Per-assignment agentic reasoning |
| 6 | Structured explanations | ✅ Parameter breakdown | ✅ `explanation_engine/structured_explanation.py` | Physical Fit, Operational, Performance, Commercial |
| 7 | What-if scenarios | ✅ API client ready | ✅ `POST /api/v1/what-if` | Baseline vs modified config comparison |
| 8 | Commercial Intelligence | ✅ Commercial page | ✅ `commercial_engine/` | Revenue scoring, partnership tiers, dynamic pricing |
| 9 | ML service time prediction | — | ✅ `decision_engine/ml_enrichment.py` | XGBoost with quantile uncertainty |
| 10 | ML berth suitability | — | ✅ `training_engine/ml_models.py` | 35.6 MB trained model for Chennai |
| 11 | Model training pipeline | — | ✅ `training_engine/trainer.py` | Feature builder, XGBoost, metadata persistence |
| 12 | Pattern discovery | — | ✅ `training_engine/pattern_discovery.py` | Historical pattern analysis |
| 13 | Dynamic port config | ✅ Port store | ✅ `GET /api/v1/ports/{code}/config` | Real berth specs from port_config.json |
| 14 | Port status/model info | ✅ PortSelector | ✅ `GET /api/v1/ports/{code}/status` | Training status, data quality badge |
| 15 | Manual override → re-optimize | ✅ Optimizer store | ✅ `POST /api/v1/scenarios/apply-override` | Backend re-runs solver with locked constraints |
| 16 | Ranked alternatives | ✅ API client ready | ✅ `POST /api/v1/optimizer/ranked-alternatives` | Solver-ranked berth options per vessel |
| 17 | Scenario impact deltas | ✅ ScenarioImpactBanner | ✅ Override response includes deltas | Wait Δ, cost Δ, objective Δ |
| 18 | Solver status banner | ✅ SolverStatusBanner | ✅ Status in response | OPTIMAL/FEASIBLE/INFEASIBLE/TIMEOUT |
| 19 | Demo mode flag | ✅ `NEXT_PUBLIC_DEMO_MODE` | — | Controls mock fallback behavior |
| 20 | Centralized API client | ✅ `lib/api/client.ts` | — | JWT interceptor, refresh, error extraction |
| 21 | Assumption-based placeholders | ✅ `assumptionDefaults.ts` | — | Every placeholder labeled with source, confidence |
| 22 | Source quality badges | ✅ StatusBadge component | — | SPEC/HISTORICAL/ML/ASSUMPTION/DEMO |
| 23 | Reusable component library | ✅ 7+ components | — | KpiCard, SectionHeader, StatusBadge, etc. |
| 24 | Dashboard KPIs & charts | ✅ Dashboard page | ✅ `GET /api/dashboard/kpis` | Animated counters, Recharts |
| 25 | Authentication | ✅ Login/signup | ✅ JWT + refresh tokens | PostgreSQL user store |
| 26 | Confidence scoring | — | ✅ `decision_engine/confidence.py` | 18K lines, multi-factor |
| 27 | Conflict detection | — | ✅ `scenario_engine/conflict_detector.py` | Berth overlap, resource, tide conflicts |
| 28 | Conflict resolution | — | ✅ `scenario_engine/conflict_resolver.py` | Auto-resolve with strategies |
| 29 | Data quality assessment | — | ✅ `data_layer/quality.py` | Completeness, recency scoring |
| 30 | Vessel type compatibility | — | ✅ `optimization_engine/vessel_type_knowledge.py` | Dynamic scoring (not hard boolean) |

### 🔨 Infrastructure

| Component | Status | Location |
|-----------|--------|----------|
| Next.js App Router | ✅ | `frontend-next/` |
| Zustand stores (3) | ✅ | `store/portStore.ts`, `store/optimizerStore.ts`, `store/dashboardStore.ts` |
| API client layer (6 services) | ✅ | `lib/api/*.ts` |
| FastAPI (2 apps) | ✅ | `api/endpoints.py`, `backend/main.py` |
| CORS middleware | ✅ | Both apps |
| specs/ documentation | ✅ | `specs/architecture.md`, `specs/features.md` |

### 📊 Data Assets

| Asset | Port | Size | Notes |
|-------|------|------|-------|
| Port config | Chennai | 28.9 KB | 23 berths, 4 terminals, service time stats |
| Historical data | Chennai | CSV | 607+ port-call records |
| Berth suitability model | Chennai | 35.6 MB | Trained XGBoost |
| Service time model | Chennai | 670 KB | Trained XGBoost with quantile |
| Delay predictor | Chennai | 293 KB | Trained XGBoost |
| Feature columns | Chennai | 521 B | Alignment artifact |

---

## Decision-Making Approach

### Source of Truth
- **Backend is the source of truth** for all scheduling and recommendation decisions
- No local mock-generated schedules in production (`NEXT_PUBLIC_DEMO_MODE=false`)
- Demo data is only used when explicitly enabled

### Wording Policy
- Use **safe, non-guaranteed wording**: "Estimated", "Historical average", "Assumption-based"
- Never use "guaranteed", "will", or "autonomous" in system outputs
- Every number shown to users must indicate its source quality

### Cost Participation
- All configurable cost placeholders participate in the decision objective
- Each has a `confidenceMultiplier` that scales its weight
- Values labeled `ASSUMPTION` have reduced confidence influence

---

## API Contract Summary

### Optimizer — Frontend→Backend

| Frontend Field | Backend Field | Conversion |
|---------------|---------------|------------|
| `eta_hours` | `eta_minutes` | × 60 |
| `service_hours` | `service_time_minutes` | × 60 |
| `sla_max_wait_hours` | `sla_max_wait_minutes` | × 60 |
| `loa_m` | `loa_m` | Direct |
| `beam_m` | `beam_m` | Direct |
| `draft_m` | `draft_m` | Direct |

### Recommendation — Frontend→Backend

| Frontend Form | Backend Schema |
|--------------|---------------|
| `vessel_name` | `vessel_name` |
| `loa` → `loa_m` | `loa_m` |
| `beam` → `beam_m` | `beam_m` |
| `draft` → `draft_m` | `draft_m` |
| `eta_date + eta_time` | `eta` (ISO datetime) |
| — | `port_code` (required) |

### Response Reading

| Response | Field Path |
|----------|-----------|
| Optimization result | `data.assignments`, `data.status`, `data.kpis` |
| Recommendation | `data.recommendations` (not `data.options`) |
| Feasibility | `data.matrix[vessel_id][berth_code]` |
| Scenario impact | `data.scenario_impact` |
