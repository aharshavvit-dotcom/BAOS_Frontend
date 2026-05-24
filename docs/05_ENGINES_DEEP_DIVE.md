# 10. COST ENGINE

## 10.1 Cost Model Architecture (`cost_engine/cost_model.py`)

The cost engine computes per-vessel and aggregate financial metrics for every berth assignment:

### Cost Components

| Component | Formula | Default Rate | Rationale |
|---|---|---|---|
| **Waiting Cost** (Demurrage) | `demurrage_rate × wait_hours` | $500/hr | Vessel idle at anchorage — charterer pays |
| **Fuel Burn** | `fuel_rate × wait_hours` | $150/hr | Auxiliary engines running while waiting |
| **Equipment Rental** | `crane_rate × service_hours` | $200/hr | Shore cranes, hoses, conveyors during operations |
| **SLA Penalty** | `sla_penalty_rate × max(0, wait - sla_limit)` | $1,000/hr | Contractual penalty for exceeding guaranteed wait |
| **Compliance Penalty** | Flat fee for government compliance violations | $5,000 | GoI regulatory breach |

### Revenue Components

| Component | Formula | Default Rate |
|---|---|---|
| **Cargo Revenue** | `cargo_tons × revenue_per_ton` | $2.50/ton |

### Aggregate Metrics

```
Total Cost = Σ(waiting_cost + fuel_burn + equipment + sla_penalty)
Revenue = Σ(cargo_tons × rate)
Net Cost = Total Cost - Revenue
Idle Berth Cost = Σ_berths[(horizon_hours - busy_hours) × idle_rate]
Cost Per Ton = Net Cost / Total Cargo Tons
```

### Cost Configuration Hierarchy

Cost rates are loaded from `ports/{port}/cost_config.json` when available. Fallback to hardcoded defaults is flagged as `ASSUMPTION` quality, ensuring the confidence engine can account for rate uncertainty.

---

# 11. KPI ENGINE

## 11.1 KPI Dashboard (`kpi_engine/kpi_calculator.py`)

### Operational KPIs

| KPI | Formula | Target |
|---|---|---|
| **Avg Waiting Time** | `Σ(wait_minutes) / N_vessels / 60` | < 6 hours |
| **Max Waiting Time** | `max(wait_minutes) / 60` | < 24 hours |
| **SLA Compliance %** | `(1 - sla_violations / N_assigned) × 100` | > 95% |
| **SLA Violations** | Count of `wait > sla_limit` | 0 |

### Utilization KPIs

| KPI | Formula | Target |
|---|---|---|
| **Berth Utilization %** | `Σ(service_hours) / (N_berths × horizon_hours) × 100` | 75–85% |
| **Equipment Utilization %** | Derived from berth busy time | > 70% |
| **Preferred Berth %** | `N_at_preferred / N_assigned × 100` | > 50% |

### Financial KPIs

| KPI | Formula |
|---|---|
| **Total Revenue** | From cost engine summary |
| **Total Cost** | Waiting + fuel + equipment + SLA penalties |
| **Net Cost** | Total cost - revenue |
| **Revenue Per Hour** | `total_revenue / horizon_hours` |
| **Cost Per Vessel** | `total_cost / N_assigned` |

### Throughput KPIs

| KPI | Formula |
|---|---|
| **Throughput** (tons/hour) | `total_cargo_tons / horizon_hours` |
| **Total Cargo Tons** | `Σ(vessel.cargo_tons)` for assigned vessels |

---

# 12. UNCERTAINTY ENGINE

## 12.1 Monte Carlo Simulation (`uncertainty_engine/monte_carlo.py`)

### Perturbation Model

The uncertainty engine runs **N scenarios** (default: 200) with stochastic perturbations:

| Source | Distribution | Parameters | Rationale |
|---|---|---|---|
| **ETA uncertainty** | Gaussian | μ=0, σ=120 min (2hr) | Vessel arrival is inherently uncertain |
| **Weather disruption** | Bernoulli | p=0.05 (5%) | Random weather events block all berths |
| **Equipment failure** | Bernoulli per berth | p=0.02 (2%) | Random equipment breakdowns |
| **Tide forecast error** | Gaussian | μ=0, σ=0.3m | Tidal prediction has inherent error |

### Output Metrics

| Metric | Description |
|---|---|
| **Feasibility Rate** | % of scenarios that produce a feasible schedule |
| **Expected Objective** | Mean objective value across feasible scenarios |
| **Objective P5/P95** | Best-case and worst-case objective values |
| **Value at Risk (VaR)** | Objective value at 95th percentile (worst-case threshold) |
| **Assignment Stability** | % of scenarios where vessel assignments match the most frequent assignment |

### Risk Score Computation

```
risk_score = 1.0 - (0.4 × feasibility_rate + 0.3 × stability + 0.3 × (1 - CV))
```
Where CV is the coefficient of variation of the objective.

- **Low Risk** (< 0.3): Schedule is robust across most perturbations
- **Medium Risk** (0.3–0.6): Some scenarios cause significant changes
- **High Risk** (> 0.6): Schedule is fragile — consider conservative parameters

### Current Limitations

- Scenarios are **independently** sampled — no correlated disruptions
- Weather events are binary (on/off) — no graduated severity
- No real-time data feeds for ETA updates
- Computation cost scales linearly with `n_scenarios × solver_time`

---

# 13. SIMULATION ENGINE

## 13.1 Digital Twin (`simulation_engine/digital_twin.py`)

### Concept

The port digital twin is an **event-driven simulation** that models port operations over time. It processes events (vessel arrivals, departures, weather, breakdowns) in chronological order, maintaining berth occupancy state and queuing vessels when berths are full.

### Event Types

| Event | Trigger | Action |
|---|---|---|
| `arrival` | Vessel ETA | Try to assign to free berth; queue if none available |
| `departure` | `start_time + service_time` | Free berth; try to assign waiting vessels |
| `weather_start` | Scheduled | Block all berths; queue new arrivals |
| `weather_end` | `start + duration` | Resume operations; assign queued vessels |
| `breakdown_start` | Scheduled | Block specific berth |
| `breakdown_end` | `start + duration` | Resume berth; assign queued vessels |

### What-If Simulation

The frontend allows:
1. **Drag-and-drop berth reassignment** — Move a vessel from one berth to another
2. **Conflict propagation** — System detects temporal overlaps and cascading delays
3. **Global re-optimization** — Trigger full CP-SAT re-solve with manual overrides locked
4. **Policy comparison** — Run same vessel set under different optimizer configurations

### Scenario Engine (`scenario_engine/`)

The scenario engine extends the digital twin with:
- **Conflict Detector** (`conflict_detector.py`) — Identifies temporal overlaps, resource conflicts
- **Conflict Resolver** (`conflict_resolver.py`) — Proposes resolution strategies (delay, reassign, swap)
- **Scenario Manager** (`scenario_manager.py`) — Manages multiple named scenarios with comparison

---

# 14. EXPLANATION ENGINE

## 14.1 Architecture

Two explanation systems provide complementary reasoning:

### Agentic Explainer (`explanation_engine/explainer.py`)

Generates high-level, narrative-style explanations:
- **Assignment explanation:** "Vessel V was assigned to Berth B because..."
- **What-if comparison:** "Changing config X improves waiting by Y% but increases SLA violations by Z"
- **Trade-off analysis:** Compares baseline vs. modified schedules across all KPIs

### Structured Explanation Engine (`explanation_engine/structured_explanation.py`)

Generates **deterministic, feature-level** explanations organized into 4 categories:

| Category | Analysis | Example |
|---|---|---|
| **Physical** | LOA margin, UKC clearance, beam fit | "LOA 185m fits within 220m max (margin: 35m, 84% utilized)" |
| **Operational** | Equipment match, cargo compatibility, vessel type | "Berth has crane + hose + gangway — full equipment match" |
| **Performance** | Service time prediction, wait time estimate | "Expected service: 18h (14–22h range), wait: 3.2h" |
| **Commercial** | Terminal type, throughput rate, SLA compliance | "Multipurpose terminal, 450 TPH estimated throughput" |

### Why Explainability Is Critical

1. **Regulatory compliance** — Port authorities require audit trails for berth allocation decisions
2. **Operator trust** — Harbor masters won't use a system they can't understand
3. **Override justification** — When operators override AI recommendations, the system explains the confidence delta
4. **Debugging** — Engineers can trace why a specific assignment was made

---

# 15. CONFIDENCE ENGINE

## 15.1 Calibrated Confidence Model (`decision_engine/confidence.py`)

### Formula

```
Confidence = (α × FeasibilityStability + β × PredictionCertainty
            + γ × HistoricalMatch + δ × CompatibilityScore) × DataQualityMultiplier
```

### Component Weights

| Component | Weight | Description |
|---|---|---|
| α (Feasibility Stability) | 0.25 | 1 - (tight_constraints / total_constraints) |
| β (Prediction Certainty) | 0.20 | f(variance, scenario stability, solver status) |
| γ (Historical Match) | 0.20 | Cosine similarity to historical successful cases |
| δ (Compatibility Score) | 0.35 | Vessel-berth equipment/type matching |

### Data Quality Gate Multiplier

| Gate | Multiplier | Source |
|---|---|---|
| GREEN | 1.00 | Spec-verified data |
| YELLOW | 0.92 | Partially spec-backed |
| RED | 0.80 | Assumption-based — flagged for review |

### Risk Level Thresholds

| Confidence | Risk Level | Interpretation |
|---|---|---|
| ≥ 85% | **Low** | High confidence — proceed with assignment |
| 65–84% | **Medium** | Moderate confidence — review before committing |
| < 65% | **High** | Low confidence — manual validation recommended |

### Confidence Delta Tracking

When operators override assignments, the system computes:
```
delta = new_confidence - original_confidence
```
Reports which factors changed (feasibility, compatibility, tight constraints) and whether risk level shifted.

### Limitations of Heuristic Confidence

- No Bayesian calibration — confidence ≠ probability of success
- Historical match uses cosine similarity — sensitive to feature scaling
- Default values (0.50 for no-data) are conservative but arbitrary
- No feedback loop: confidence is not updated based on assignment outcomes
