# 8. COMPLETE ML PIPELINE

## 8.1 Historical Data Ingestion

### Data Sources

| File | Description | Records |
|---|---|---|
| `PortCall_LogData-Chennai-2025June-Dec.xlsx` | 6 months of historical port calls at Chennai | ~2,000+ records |
| `Berth_configurations.xlsx` | Official berth specifications (physical limits) | All berths |
| `Operational_Capability_of_Berth.xlsx` | Cargo handling capabilities per berth | All berths |

### Ingestion Pipeline (`data_layer/ingest.py` + `spec_ingest.py`)

```
Raw Excel Files
    │
    ├─ spec_ingest.py ──▶ build_port_master()
    │   ├── Parse Berth_configurations.xlsx → BerthSpec objects
    │   ├── Parse Operational_Capability.xlsx → commodity mappings
    │   ├── Cross-reference: merge spec + ops into unified BerthSpec
    │   ├── Quality scoring: GREEN (spec), YELLOW (partial), RED (assumption)
    │   └── Output: PortMaster with Dict[berth_code, BerthSpec]
    │
    ├─ ingest.py ──▶ load_and_clean()
    │   ├── Read port call Excel with openpyxl
    │   ├── Standardize column names (lowercase, strip whitespace)
    │   ├── Parse timestamps: eta, ata, atb, atd (multiple datetime formats)
    │   ├── Handle missing values: forward-fill berth codes, impute drafts
    │   └── Output: cleaned pd.DataFrame
    │
    └─ quality.py ──▶ assess_data_quality()
        ├── Completeness check: % non-null per column
        ├── Consistency check: LOA > 0, draft > 0, valid berth codes
        ├── Freshness check: date range coverage
        └── Output: QualityGate (GREEN/YELLOW/RED) per field
```

### Data Provenance System (`data_models.py`)

Every data value carries its provenance:

```python
class DataSource(str, Enum):
    SPEC = "spec"              # Trust: 1.00 — from official spec sheets
    OPERATIONAL = "operational" # Trust: 0.95 — from operational records
    HISTORICAL = "historical"  # Trust: 0.75 — inferred from port call logs
    ASSUMPTION = "assumption"  # Trust: 0.40 — hardcoded fallback (flagged RED)
    USER_INPUT = "user_input"  # Trust: 0.85 — provided by operator at runtime
```

This enables the confidence engine to penalize decisions based on low-quality data. A berth with `max_loa_m.source = ASSUMPTION` gets a lower confidence score than one with `source = SPEC`.

## 8.2 Feature Engineering (`training_engine/feature_builder.py`)

### Vessel Features

| Feature | Description | Why It Matters |
|---|---|---|
| `loa` | Length Overall (meters) | Primary physical constraint — determines berth eligibility |
| `beam` | Width at widest point | Affects parallel berthing, fender requirements |
| `adraft` / `draft` | Arrival draft (meters) | Must not exceed berth depth minus UKC margin |
| `dwt` | Deadweight tonnage | Proxy for cargo volume; affects service time |
| `vessel_type_enc` | Encoded vessel type | Container, Bulk, Tanker, RoRo have different berth requirements |
| `cargo_type_enc` | Encoded cargo category | Determines equipment needs (cranes, hoses, conveyors) |

### Berth Features

| Feature | Description | Why It Matters |
|---|---|---|
| `berth_max_loa` | Maximum LOA accepted | Hard constraint boundary |
| `berth_depth` | Water depth at berth | Determines draft feasibility |
| `berth_max_draft` | Maximum draft accepted | Combined with UKC for tide analysis |
| `berth_max_beam` | Maximum beam accepted | Physical width constraint |
| `berth_equipment_count` | Number of equipment types | More equipment → more versatile → lower risk |
| `berth_vessel_type_count` | Historically served vessel types | Higher count → more flexible berth |

### Derived Features

| Feature | Derivation | Why It Matters |
|---|---|---|
| `draft_clearance` | `berth_depth - vessel_draft` | Small clearance → tide-sensitive → higher risk |
| `loa_utilization` | `vessel_loa / berth_max_loa` | High utilization → tight fit → longer mooring time |
| `beam_utilization` | `vessel_beam / berth_max_beam` | Affects parallel positioning feasibility |
| `congestion_level` | `total_vessels / num_berths` | Port congestion affects waiting times non-linearly |
| `historical_wait_avg` | Mean wait time at this berth | Indicates berth efficiency and queue depth |
| `historical_service_avg` | Mean service time at this berth | Equipment efficiency proxy |
| `vessel_type_match` | Boolean: vessel type in berth's allowed list | Hard compatibility signal |

## 8.3 ML Models

### Model 1: Service Time Predictor

- **Algorithm:** Gradient Boosting Regressor (GBR) with Quantile Regression
- **Architecture:** Three models — P25 (optimistic), P50 (median), P75 (conservative)
- **Input:** Feature vector (vessel + berth + derived features)
- **Output:** Expected service time in hours + uncertainty bounds
- **Why GBR:** Handles non-linear relationships between vessel size, cargo type, and berth efficiency. Quantile regression provides calibrated uncertainty bounds without distributional assumptions.
- **Hyperparameters:** 100 estimators, max_depth=5, learning_rate=0.1

### Model 2: Delay Predictor

- **Algorithm:** Gradient Boosting Regressor with Quantile Regression
- **Architecture:** Three models — P25/P50/P75
- **Input:** Same feature vector
- **Output:** Expected waiting/delay in hours + uncertainty bounds
- **Why separate from service time:** Delay is driven by port congestion and queue dynamics, not berth characteristics. The feature importance distribution differs significantly.
- **Hyperparameters:** 80 estimators, max_depth=4, learning_rate=0.1

### Model 3: Berth Suitability Classifier

- **Algorithm:** Random Forest Classifier (RFC)
- **Input:** Vessel-only features (berth features deliberately excluded to prevent data leakage)
- **Output:** P(berth_code | vessel_features) for all known berths
- **Why RFC:** Naturally handles multi-class classification with probability outputs. Top-K accuracy tracking ensures useful recommendations even when top-1 is uncertain.
- **Anti-leakage:** `_filter_X()` drops all berth-specific and derived features before prediction
- **Hyperparameters:** 300 estimators, no max_depth limit

### Model 4: Decision Ranker

- **Algorithm:** Weighted score fusion
- **Formula:** `Score = w_suit × suitability_prob - uncertainty_penalty`
- **Design decision:** Wait and service weights are set to zero (`w_wait=0.0, w_service=0.0`) because real-time port occupancy data is unavailable. Historical averages would create misleading rankings. Suitability probability from the classifier is the primary signal.
- **Uncertainty penalty:** 0.05 penalty applied when `uncertainty_ratio > 0.5` to penalize high-variance predictions

### Model 5: XGBoost Ranker (`training_engine/xgboost_ranker.py`)

- **Algorithm:** XGBoost with ranking objective
- **Purpose:** Commercial intelligence — ranks berths by revenue optimization potential
- **Integration:** Feeds into `commercial_engine/commercial_scorer.py`

### Model 6: Pattern Discovery Engine (`training_engine/pattern_discovery.py`)

- **Purpose:** Unsupervised discovery of berth-vessel assignment patterns
- **Output:** Frequent assignment patterns, anomaly detection, trend analysis
- **Integration:** Feeds into weekly refresh pipeline

## 8.4 Training Pipeline

```
Raw Excel Data
    │
    ▼
data_layer/ingest.py → Cleaned DataFrame
    │
    ▼
training_engine/feature_builder.py → Feature Matrix (X) + Labels (y)
    │
    ├── y_service: actual service hours (atd - atb)
    ├── y_delay: actual wait hours (atb - eta)
    └── y_berth: actual berth code assigned
    │
    ▼
training_engine/trainer.py → Orchestration
    │
    ├── Train/test split (80/20, stratified by berth)
    ├── ServiceTimePredictor.train(X, y_service)
    ├── DelayPredictor.train(X, y_delay)
    ├── BerthSuitabilityModel.train(X_vessel_only, y_berth)
    ├── DecisionRanker (no training — weight-based fusion)
    │
    ├── Cross-validation (3-fold) → MAE, R², accuracy metrics
    ├── Feature importance extraction → top-10 features per model
    │
    ▼
Serialization → ports/{port}/models/*.pkl + feature_columns.json
```

## 8.5 ML Limitations (Honest Assessment)

| Limitation | Impact | Mitigation |
|---|---|---|
| **Historical bias** | Models learn from past assignments that may have been suboptimal | Constraint library provides spec-backed overrides |
| **Sparse berth history** | Some berths have <10 historical calls → unreliable predictions | Suitability model falls back to uniform distribution |
| **No real-time congestion** | Models cannot see current port occupancy | Wait/service weights zeroed; shown as informational only |
| **Deterministic training** | Single train/test split, no temporal validation | Cross-validation partially mitigates |
| **No drift detection** | Model staleness not monitored | Weekly refresh pipeline (`learning_engine/weekly_refresh.py`) planned |
| **Quantile coverage** | P25-P75 interval may not achieve 50% coverage on all berths | Coverage metric tracked in model evaluation |

---

# 9. CONSTRAINT OPTIMIZATION ENGINE

## 9.1 Why CP-SAT

The berth allocation problem is a variant of the **Job-Shop Scheduling Problem** (JSSP), which is NP-hard. Simple heuristics (greedy, priority queue) fail because:

1. **Multi-objective trade-offs** — Minimizing wait for vessel A may increase wait for vessel B
2. **Constraint propagation** — Assigning vessel V to berth B at time T constrains all future assignments
3. **Global optimality** — Local decisions (assign next vessel to first available berth) often produce globally suboptimal schedules

**CP-SAT (Constraint Programming — Satisfiability)** from Google OR-Tools was chosen because:

- Native support for **interval variables** and `AddNoOverlap` — natural fit for scheduling
- **Cumulative constraints** for resource pools (tugs, pilots)
- **Reified constraints** (`OnlyEnforceIf`) for conditional logic (vessel-berth assignment activation)
- **Lazy clause generation** — efficient for scheduling with many optional variables
- **Anytime solving** — returns best feasible solution within time limit, with optimality gap

## 9.2 Mathematical Model

### Decision Variables

```
X[v, b] ∈ {0, 1}           — vessel v assigned to berth b
start[v] ∈ [eta_v, H]      — start time (minutes from horizon start)
end[v] = start[v] + service_time[v]   — end time
wait[v] = start[v] - eta[v]           — waiting time (≥ 0)
interval[v, b]              — Optional interval, active iff X[v,b]=1
```

### Hard Constraints

| ID | Constraint | Mathematical Form | Implementation |
|---|---|---|---|
| C1 | LOA fit | `loa_v ≤ max_loa_b` | `model.Add(X[v,b] == 0)` if violated |
| C2 | Draft clearance | `draft_v + UKC ≤ max_draft_b` | Static check + tide adjustment |
| C3 | Beam fit | `beam_v ≤ max_beam_b` | `model.Add(X[v,b] == 0)` if violated |
| C4 | Non-overlap | No two vessels overlap at same berth | `model.AddNoOverlap(intervals_b)` |
| C5 | Berth availability | `start[v] ≥ avail_from_b`, `end[v] ≤ avail_to_b` | `OnlyEnforceIf(X[v,b])` |
| C6 | Tide window | `start[v]` must fall in safe tide window | Enumeration of safe windows with Boolean selectors |
| C7 | 24×7 flag | No night berthing unless `allow_24x7` | Modular arithmetic on `start[v] mod 1440` |
| C8 | Tug availability | ≤ `tug_capacity` concurrent movements | `model.AddCumulative(movement_intervals, demands, capacity)` |
| C9 | Pilot availability | ≤ `pilot_capacity` concurrent movements | Same cumulative constraint |
| C10 | Channel constraint | ≤ `max_channel_movements` simultaneous | Cumulative on inbound + outbound intervals |
| C11 | Customs clearance | Uncustomed vessels cannot berth | `model.Add(X[v,b] == 0)` for all berths |
| C12 | FCFS ordering | `start[v1] ≤ start[v2]` if `eta[v1] < eta[v2]` | Pairwise ordering constraints |
| C13 | GoI override | Government vessels start before all others | Pairwise constraints with government flag |
| C14 | Contract preference | Preferred berth gets bonus in objective | `-w_contract × X[v, preferred_b]` in objective |
| C15 | SLA commitment | Penalty for `wait[v] > sla_limit[v]` | `sla_excess = max(wait - sla_limit, 0)` in objective |
| C16 | Downtime | No vessel during maintenance window | Boolean disjunction: `end ≤ dt_start OR start ≥ dt_end` |
| C17 | Weather | No berthing during adverse weather (all berths) | C16 applied to all berths simultaneously |

### Vessel-Berth Compatibility (Soft)

Instead of hard-blocking all vessel type mismatches, the system uses `compute_compatibility_score()`:
- Score < 30: **Hard block** — truly dangerous combination
- Score 30–60: **Soft penalty** — marginal match, solver adds cost
- Score > 60: **Allowed** — good or excellent match

### Objective Function

```
Minimize:
    Σ_v [ w_waiting × wait[v] ]                           — Total waiting cost
  + Σ_v [ w_sla × max(wait[v] - sla_limit[v], 0) ]       — SLA penalty
  + Σ_v [ w_demurrage × demurrage_rate[v] × wait[v] ]     — Demurrage cost
  + Σ_v [ w_deviation × (1 - X[v, prev_berth[v]]) ]       — Schedule stability
  + Σ_{v,b} [ w_commercial × (100 - compat_score[v,b]) ]  — Revenue loss
  - Σ_v [ w_contract × X[v, preferred_berth[v]] ]          — Contract satisfaction bonus
  + Σ_v [ w_partnership × priority_bonus[v] × wait[v] ]   — VIP waiting penalty
```

**Key trade-offs:**
- Higher `w_waiting` → shorter queues but may violate berth specialization
- Higher `w_sla` → SLA compliance but may increase total cost
- Higher `w_deviation` → more stable schedules but less optimal on disruptions
- Higher `w_commercial` → revenue-optimized but may increase wait times

### Per-Berth + Per-Ship-Type Configuration

The `BerthSchedulerConfig` supports **4-level weight granularity**:

```
Lookup Priority (most specific wins):
    (berth_code, ship_type) → ship_type only → berth only → global
```

This enables scenarios like: "Container ships at berth B1 should have 2× waiting penalty" without affecting other combinations.

## 9.3 Rolling Horizon Scheduling

The `RollingHorizonScheduler` (`optimization_engine/scheduler.py`) implements:

1. **Window-based scheduling** — Only optimizes vessels within a rolling time window
2. **Schedule repair** — Previous assignments can be locked (via `add_manual_overrides()`) while re-optimizing new arrivals
3. **Deviation penalty** — `w_deviation` penalizes changing already-committed assignments
4. **Freeze horizon** — Assignments older than `repair_freeze_hours` are fixed
