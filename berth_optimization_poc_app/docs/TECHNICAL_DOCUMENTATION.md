# ⚓ BAOS AI — Maritime Berth Optimization & Decision Intelligence Platform

## Enterprise Technical Design Document

> **Version:** 2.0.0 | **Status:** Production | **Last Updated:** May 2026
> **Classification:** Enterprise Technical Documentation | **Pages:** ~20 equivalent

---

## 📑 Document Index

This technical design document is organized into six comprehensive sections:

| # | Document | Sections Covered | Pages |
|---|---|---|---|
| 1 | [Overview & Objectives](01_OVERVIEW_AND_OBJECTIVES.md) | Project Overview, System Objectives, Platform Evolution | ~4 |
| 2 | [System Architecture](02_SYSTEM_ARCHITECTURE.md) | High-Level Architecture, Data Flow, Frontend Architecture | ~4 |
| 3 | [Backend & Database](03_BACKEND_AND_DATABASE.md) | FastAPI Backend, PostgreSQL Schema, ORM Layer | ~3 |
| 4 | [ML & Optimization](04_ML_AND_OPTIMIZATION.md) | ML Pipeline, CP-SAT Constraint Model, Mathematical Formulation | ~5 |
| 5 | [Engine Deep Dives](05_ENGINES_DEEP_DIVE.md) | Cost, KPI, Uncertainty, Simulation, Explanation, Confidence | ~4 |
| 6 | [Deployment & Roadmap](06_DEPLOYMENT_AND_ROADMAP.md) | Deployment, Limitations, Future Roadmap, Tech Stack, E2E Flow | ~4 |
| 7 | [**Frontend Deep Dive**](07_FRONTEND_DEEP_DIVE.md) | Next.js, React, TypeScript types, Zustand stores, hooks, design system, every page component | ~6 |
| 8 | [**FastAPI Deep Dive**](08_FASTAPI_DEEP_DIVE.md) | Routes, services, auth flow, JWT, WebSocket, ORM models, config, error handling | ~6 |

---

## 🏗 Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                 FRONTEND — Next.js 16 + TypeScript              │
│     Landing │ Dashboard │ Optimizer │ Recommend │ Commercial    │
├─────────────────────────────────────────────────────────────────┤
│                 API — FastAPI + JWT + WebSocket                  │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│ Decision │ Optim.   │ Cost     │ ML       │ Explanation         │
│ Engine   │ Engine   │ Engine   │ Engine   │ Engine              │
│          │ (CP-SAT) │          │ (sklearn)│                     │
├──────────┴──────────┴──────────┴──────────┴─────────────────────┤
│ Simulation │ Uncertainty │ Confidence │ Commercial │ Learning   │
├─────────────────────────────────────────────────────────────────┤
│              PostgreSQL + SQLAlchemy + Data Layer               │
└─────────────────────────────────────────────────────────────────┘
```

## 🔑 Key Engineering Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Solver | Google OR-Tools CP-SAT | Native interval variables, cumulative constraints, anytime solving |
| ML Framework | scikit-learn + XGBoost | Quantile regression for uncertainty; lightweight inference |
| Frontend | Next.js 16 + TypeScript | SSR, type safety, component architecture |
| Backend | FastAPI (ASGI) | Async, auto-docs, Pydantic validation, 3-10x faster than Flask |
| Database | PostgreSQL 14+ | ACID, JSON columns, UUID PKs, production-grade |
| State | Zustand | Minimal boilerplate, hook-based, shared optimizer state |
| Real-time | Socket.IO | Auto-reconnect, fallback to polling |
| Confidence | 4-factor weighted model | Feasibility + Prediction + Historical + Compatibility |

## 📊 System Capabilities Summary

| Capability | Status | Engine |
|---|---|---|
| Single vessel recommendation | ✅ Production | `decision_engine/recommender.py` |
| Multi-vessel CP-SAT optimization | ✅ Production | `optimization_engine/constraint_model.py` |
| 17 hard/soft constraints | ✅ Production | C1-C17 in constraint model |
| Per-berth + per-ship-type weights | ✅ Production | `BerthSchedulerConfig` 4-level lookup |
| Quantile regression (P25/P50/P75) | ✅ Production | `training_engine/ml_models.py` |
| Cost breakdown (demurrage, SLA, fuel) | ✅ Production | `cost_engine/cost_model.py` |
| Structured explanations (4-category) | ✅ Production | `explanation_engine/structured_explanation.py` |
| Calibrated confidence scoring | ✅ Production | `decision_engine/confidence.py` |
| Data provenance tracking | ✅ Production | `data_models.py` — SPEC/HISTORICAL/ASSUMPTION |
| Interactive Gantt timeline | ✅ Production | Frontend optimizer page |
| Feasibility matrix with tooltips | ✅ Production | Frontend optimizer page |
| What-if scenario comparison | ✅ Production | `explanation_engine/explainer.py` |
| Monte Carlo uncertainty | ✅ Production | `uncertainty_engine/monte_carlo.py` |
| Digital twin simulation | ✅ Production | `simulation_engine/digital_twin.py` |
| Commercial intelligence | ✅ Production | `commercial_engine/` |
| Partnership tier management | ✅ Production | `commercial_engine/partnership_manager.py` |
| JWT authentication | ✅ Production | `backend/auth/` |
| Demo mode fallback | ✅ Production | Frontend client-side simulation |
| Reinforcement learning | 🔧 Stub | `rl_engine/weight_agent.py` |
| Real-time AIS tracking | 📋 Planned | Future roadmap |
| Multi-port optimization | 📋 Planned | Future roadmap |

---

*For detailed technical content, navigate to the individual documents listed in the Document Index above.*

*BAOS AI Engineering Team — Chennai Port Authority — May 2026*
