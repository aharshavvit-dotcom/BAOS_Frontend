# BAOS AI — Maritime Berth Optimization & Decision Intelligence Platform

## Technical Design Document

> **Version:** 2.0.0 | **Last Updated:** May 2026 | **Classification:** Enterprise Technical Documentation

---

# 1. PROJECT OVERVIEW

## 1.1 Problem Statement

Maritime berth allocation is a combinatorial optimization problem of NP-hard complexity. At any major port, dozens of vessels compete for a finite number of berths, each with physical constraints (LOA, draft, beam), temporal constraints (tides, working hours), resource constraints (tugs, pilots), and commercial obligations (SLA contracts, demurrage penalties). Manual planning by harbor masters — typically done via spreadsheets and radio coordination — leads to:

- **Suboptimal berth utilization** (often 40–60% vs. achievable 75–85%)
- **Excessive vessel waiting times** averaging 18–36 hours at congested ports
- **Demurrage costs** of $500–$2,000/hour per idle vessel
- **SLA violations** triggering contractual penalties of $1,000+/hour
- **Revenue leakage** from mismatched vessel-berth assignments

## 1.2 What BAOS AI Solves

BAOS AI is a **full-stack AI + Constraint Optimization platform** that replaces manual berth planning with an automated, explainable, cost-aware decision intelligence system. It combines:

1. **Machine Learning** — Predicts service times, delays, and berth suitability from historical port call data
2. **Constraint Programming (CP-SAT)** — Solves the multi-vessel scheduling problem optimally under 15+ hard/soft constraints
3. **Cost Modeling** — Evaluates demurrage, fuel burn, SLA penalties, and revenue per assignment
4. **Explainable AI** — Generates human-readable, multi-factor reasoning for every decision
5. **Uncertainty Quantification** — Monte Carlo simulation and quantile regression for risk scoring

## 1.3 Scheduling Paradigms Compared

| Approach | Description | Limitations |
|---|---|---|
| **Manual Planning** | Harbor master assigns berths via experience and radio | No optimization, high error rate, no cost visibility |
| **Rule-Based** | FCFS or priority queues with static rules | Cannot handle multi-objective trade-offs, no learning |
| **Optimization-Driven** | CP-SAT solver with hard/soft constraints | Deterministic — no uncertainty modeling |
| **AI-Assisted (BAOS AI)** | ML predictions + CP-SAT optimization + uncertainty + explainability | Full decision intelligence with confidence scoring |

BAOS AI implements the fourth paradigm — **AI-Assisted Scheduling** — where ML models inform the optimizer, uncertainty engines quantify risk, and explanation engines make every decision auditable.

## 1.4 Business Impact

| Metric | Before BAOS AI | With BAOS AI |
|---|---|---|
| Berth Utilization | 40–60% | 75–85% |
| Avg Vessel Wait | 18–36 hours | 4–12 hours |
| SLA Compliance | ~70% | 90–98% |
| Demurrage Costs | Untracked | Minimized by solver |
| Decision Transparency | None | Full audit trail |
| What-If Analysis | Manual estimation | Real-time simulation |

---

# 2. SYSTEM OBJECTIVES

## 2.1 Functional Objectives

| # | Objective | Implementation |
|---|---|---|
| F1 | Single vessel berth recommendation | `decision_engine/recommender.py` — ML-powered top-K ranking |
| F2 | Multi-vessel optimization | `optimization_engine/constraint_model.py` — CP-SAT solver |
| F3 | Feasibility validation | `optimization_engine/feasibility_checker.py` + `constraint_library.py` |
| F4 | Cost-aware scheduling | `cost_engine/cost_model.py` — demurrage, fuel, SLA, revenue |
| F5 | KPI generation | `kpi_engine/kpi_calculator.py` — utilization, throughput, compliance |
| F6 | Interactive simulation | `simulation_engine/digital_twin.py` — event-driven port simulation |
| F7 | What-if analysis | `explanation_engine/explainer.py` — scenario comparison |
| F8 | AI explanation generation | `explanation_engine/structured_explanation.py` — 4-category reasoning |
| F9 | Confidence scoring | `decision_engine/confidence.py` — 4-factor calibrated model |
| F10 | Historical analytics | `training_engine/pattern_discovery.py` + `learning_engine/` |
| F11 | Commercial intelligence | `commercial_engine/` — revenue optimization, partnership tiers |

## 2.2 Non-Functional Objectives

| # | Objective | Approach |
|---|---|---|
| NF1 | **Scalability** | Modular engine architecture — each engine is an independent package |
| NF2 | **Extensibility** | Plugin-style engines with `__init__.py` exports; new engines added without modifying core |
| NF3 | **Explainability** | Every recommendation includes structured multi-paragraph reasoning |
| NF4 | **Real-time Responsiveness** | CP-SAT solves in <30s; WebSocket push for live updates |
| NF5 | **Reliability** | Demo mode fallback when backend is unavailable |
| NF6 | **Maintainability** | TypeScript frontend, Pydantic schemas, SQLAlchemy ORM |
| NF7 | **Production Readiness** | JWT auth, CORS, PostgreSQL, Docker-ready |
| NF8 | **Fault Tolerance** | Client-side simulation fallback, graceful engine degradation |
| NF9 | **UI Usability** | Interactive Gantt timelines, drag-drop, rich tooltips |

---

# 3. EVOLUTION OF THE PLATFORM

## 3.1 Phase 1 — Initial Prototype

**Stack:** Python + Streamlit + HTML/CSS/JS

**Why rapid prototyping was chosen:**
- Streamlit allowed building an interactive ML dashboard in days, not weeks
- Direct Python integration meant ML models, optimization, and UI shared the same process
- Excel-based data ingestion was natural for port operations teams

**Advantages realized:**
- Fast iteration on ML pipeline (feature engineering → training → inference in one session)
- Interactive lever configuration (sliders for optimization weights)
- Immediate visual feedback (Plotly charts, berth timelines)

**Limitations encountered:**
- **No component reuse** — Streamlit reruns the entire script on every interaction
- **No state management** — Sidebar state resets on navigation; no undo/redo
- **No concurrent users** — Single-threaded Streamlit server
- **No authentication** — No user roles, no audit trail
- **No database** — All data in memory or JSON files
- **No real-time updates** — Polling-only architecture
- **Limited UI flexibility** — Cannot build complex dashboards (feasibility matrices, drag-drop timelines)

## 3.2 Phase 2 — Production Migration

### Frontend Migration: React.js + Next.js + TypeScript

| Decision | Rationale |
|---|---|
| **Next.js 16** | Server-side rendering, file-based routing, API routes, optimized builds |
| **TypeScript** | Type safety across 50+ component interfaces; catches schema mismatches at compile time |
| **Tailwind CSS** | Utility-first styling; consistent design tokens across all pages |
| **Zustand** | Lightweight state management (vs. Redux overhead); shared optimizer/simulation state |
| **Recharts** | React-native charting; integrates with component lifecycle |
| **Axios** | HTTP client with interceptors for JWT token refresh |
| **Socket.IO** | Real-time WebSocket for live schedule updates |
| **Framer Motion** | Smooth animations for page transitions and component mounting |

### Backend Migration: FastAPI + PostgreSQL

| Decision | Rationale |
|---|---|
| **FastAPI** | Async-native, auto-generated OpenAPI docs, Pydantic validation, 3–10x faster than Flask |
| **SQLAlchemy (async)** | Mature ORM with async support; `asyncpg` driver for PostgreSQL |
| **PostgreSQL** | ACID compliance, JSON column support, UUID primary keys, production-grade |
| **JWT Authentication** | Stateless auth with access + refresh tokens; bcrypt password hashing |
| **Pydantic v2** | Request/response validation with TypeDict-style models |

### Engineering Trade-offs

1. **Dual API Layer:** The legacy `api/endpoints.py` (FastAPI) coexists with the new `backend/routes/` layer. Legacy endpoints are mounted into the production app for backward compatibility, avoiding a big-bang migration.

2. **Demo Mode Fallback:** The frontend works fully without the backend — uses client-side simulation for optimizer/recommendations and demo auth. This allows instant demos without infrastructure setup, at the cost of maintaining parallel logic.

3. **Engine Independence:** Each Python engine (`cost_engine/`, `decision_engine/`, etc.) is a standalone package with its own `__init__.py`. This enables future microservice decomposition but means engines must use `sys.path` manipulation for cross-engine imports.
