"""
Recommendation service — wraps the existing decision_engine for API use.
"""
from __future__ import annotations

import asyncio
from functools import partial
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.app_models import Recommendation, Vessel
from backend.schemas.recommendations import BerthRecommendation, RecommendationResponse
from backend.utils.exceptions import TrainingError

# Add parent project to path so we can import existing engines
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _get_decision_engine():
    """Lazy-load the existing decision engine modules."""
    try:
        from engines.core.decision.recommender import recommend_berth
        from backend.db.repositories.port_store import port_exists
        return recommend_berth, port_exists
    except ImportError:
        return None, None


def _run_decision_engine_recommendation(
    *,
    vessel_name: str,
    vessel_type: str,
    loa_m: float,
    beam_m: float,
    draft_m: float,
    cargo_type: str,
    cargo_tons: float,
    port_code: str,
) -> list[dict] | None:
    """Run the legacy synchronous recommendation stack."""
    recommend_berth, port_exists = _get_decision_engine()
    if not (recommend_berth and port_exists and port_exists(port_code)):
        return None

    # FIX (Phase 5): Use the real recommender function so model integrity errors cannot fall through to samples.
    options = recommend_berth(
        {
            "name": vessel_name,
            "vessel_type": vessel_type,
            "loa": loa_m,
            "beam": beam_m,
            "draft": draft_m,
            "dwt": cargo_tons,
            "cargo_type": cargo_type,
            "cargo_tons": cargo_tons,
        },
        port_code,
        top_k=3,
    )
    return [
        {
            "berth_code": option.berth_code,
            "berth_name": option.berth_name,
            "confidence": option.confidence,
            "technical_score": option.suitability_score,
            "commercial_score": 0.0,
            "reasoning": {
                "headline": option.compact_reason or option.explanation,
                "pros": option.pros,
                "cons": option.cons,
            },
            "expected_turnaround_hours": option.expected_service_hours,
            "expected_wait_hours": option.expected_wait_hours,
            "expected_service_hours": option.expected_service_hours,
        }
        for option in options
    ]


async def generate_recommendation(
    db: AsyncSession,
    vessel_name: str,
    vessel_type: str = "",
    loa_m: float = 0.0,
    beam_m: float = 0.0,
    draft_m: float = 0.0,
    dwt: float = 0.0,
    cargo_type: str = "",
    cargo_tons: float = 0.0,
    port_code: str = "INMAA",
    eta: Optional[str] = None,
) -> RecommendationResponse:
    """
    Generate berth recommendations using existing decision engine.
    Falls back to sample recommendations if engine unavailable.
    """
    recommendations: List[BerthRecommendation] = []
    rec_id = str(uuid.uuid4())

    try:
        loop = asyncio.get_event_loop()
        # FIX (Phase 4): Legacy recommender uses sync DB/model work -> run it off the async event loop.
        # TODO: convert legacy port_store/recommender DB access to AsyncSession.
        results = await loop.run_in_executor(
            None,
            partial(
                _run_decision_engine_recommendation,
                vessel_name=vessel_name,
                vessel_type=vessel_type,
                loa_m=loa_m,
                beam_m=beam_m,
                draft_m=draft_m,
                cargo_type=cargo_type,
                cargo_tons=cargo_tons,
                port_code=port_code,
            ),
        )
    except TrainingError:
        # FIX (Phase 5): Feature-hash/model integrity failures must surface to the API caller.
        raise
    except Exception:
        results = None

    if results:
        for r in results[:3]:
            recommendations.append(BerthRecommendation(
                berth_code=r.get("berth_code", ""),
                berth_name=r.get("berth_name", ""),
                confidence=r.get("confidence", 0.0),
                technical_score=r.get("technical_score", 0.0),
                commercial_score=r.get("commercial_score", 0.0),
                reasoning=r.get("reasoning", {}),
                expected_turnaround_hours=r.get("expected_turnaround_hours"),
                expected_wait_hours=r.get("expected_wait_hours", 0.0),
                expected_service_hours=r.get("expected_service_hours", 0.0),
            ))
    else:
        recommendations = _sample_recommendations(vessel_type)

    # Persist to database
    vessel = Vessel(
        name=vessel_name,
        vessel_type=vessel_type,
        loa_m=loa_m,
        beam_m=beam_m,
        draft_m=draft_m,
        dwt=dwt,
        cargo_type=cargo_type,
        cargo_tons=cargo_tons,
    )
    db.add(vessel)
    await db.flush()

    for rec in recommendations:
        db_rec = Recommendation(
            vessel_id=vessel.id,
            berth_code=rec.berth_code,
            berth_name=rec.berth_name,
            port_code=port_code,
            confidence_score=rec.confidence,
            technical_score=rec.technical_score,
            commercial_score=rec.commercial_score,
            reasoning_json=rec.reasoning,
            vessel_data_json={
                "vessel_name": vessel_name,
                "vessel_type": vessel_type,
                "loa_m": loa_m,
                "beam_m": beam_m,
                "draft_m": draft_m,
                "dwt": dwt,
                "cargo_type": cargo_type,
                "cargo_tons": cargo_tons,
            },
        )
        db.add(db_rec)

    await db.flush()

    return RecommendationResponse(
        recommendation_id=rec_id,
        recommendations=recommendations,
        vessel_name=vessel_name,
        port_code=port_code,
    )


def _sample_recommendations(vessel_type: str = "") -> List[BerthRecommendation]:
    """Fallback sample recommendations when engine is unavailable."""
    return [
        BerthRecommendation(
            berth_code="INMAA-B01",
            berth_name="Berth A1 — Container Terminal",
            confidence=92.5,
            technical_score=95.0,
            commercial_score=88.0,
            reasoning={
                "headline": "Best match based on vessel dimensions and cargo type",
                "factors": [
                    "LOA within berth limits",
                    "Draft within depth clearance",
                    "Cargo type compatible with terminal equipment",
                ],
            },
            expected_turnaround_hours=24.5,
            expected_wait_hours=2.5,
            expected_service_hours=24.0,
        ),
        BerthRecommendation(
            berth_code="INMAA-B03",
            berth_name="Berth B3 — Multi-purpose Terminal",
            confidence=85.2,
            technical_score=88.0,
            commercial_score=80.0,
            reasoning={
                "headline": "Secondary option with good compatibility",
                "factors": [
                    "Adequate dimensions",
                    "Equipment available",
                    "Slightly longer expected turnaround",
                ],
            },
            expected_turnaround_hours=28.0,
            expected_wait_hours=4.2,
            expected_service_hours=28.0,
        ),
        BerthRecommendation(
            berth_code="INMAA-B05",
            berth_name="Berth C1 — General Cargo",
            confidence=72.8,
            technical_score=75.0,
            commercial_score=68.0,
            reasoning={
                "headline": "Alternative berth with available capacity",
                "factors": [
                    "Available within requested window",
                    "Lower utilization rate",
                ],
            },
            expected_turnaround_hours=32.0,
            expected_wait_hours=1.0,
            expected_service_hours=32.0,
        ),
    ]
