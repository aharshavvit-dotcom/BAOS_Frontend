"""
Data Quality Framework
======================
Scores the quality of berth specifications and historical data.
Produces per-field and per-entity quality assessments with
RED/YELLOW/GREEN gates.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_models import (
    BerthSpec, DataSource, QualityGate, ProvenanceField,
)


# ── Field-Level Quality ──────────────────────────────────────────────────────

@dataclass
class FieldQuality:
    """Quality assessment for a single field."""
    field_name: str
    present: bool = False
    valid: bool = False
    source: DataSource = DataSource.ASSUMPTION
    score: float = 0.0         # 0-100
    gate: QualityGate = QualityGate.RED
    notes: str = ""

    @staticmethod
    def compute_gate(score: float) -> QualityGate:
        if score >= 80:
            return QualityGate.GREEN
        elif score >= 60:
            return QualityGate.YELLOW
        return QualityGate.RED


@dataclass
class EntityQuality:
    """Quality assessment for a complete entity (e.g., berth)."""
    entity_id: str
    entity_type: str = ""
    fields: List[FieldQuality] = field(default_factory=list)
    overall_score: float = 0.0
    overall_gate: QualityGate = QualityGate.RED
    critical_gaps: List[str] = field(default_factory=list)

    def compute_overall(self, weights: Optional[Dict[str, float]] = None):
        """Compute weighted overall quality score."""
        if not self.fields:
            self.overall_score = 0.0
            self.overall_gate = QualityGate.RED
            return

        if weights:
            total_weight = 0
            weighted_sum = 0
            for f in self.fields:
                w = weights.get(f.field_name, 1.0)
                weighted_sum += f.score * w
                total_weight += w
            self.overall_score = weighted_sum / total_weight if total_weight > 0 else 0
        else:
            self.overall_score = np.mean([f.score for f in self.fields])

        self.overall_gate = FieldQuality.compute_gate(self.overall_score)

        # Identify critical gaps
        critical_fields = {"max_loa_m", "max_draft_m", "max_depth_m"}
        self.critical_gaps = [
            f.field_name for f in self.fields
            if f.field_name in critical_fields and f.gate == QualityGate.RED
        ]


@dataclass
class QualityReport:
    """Full quality report for a port's data."""
    port_name: str = ""
    entities: List[EntityQuality] = field(default_factory=list)
    overall_score: float = 0.0
    overall_gate: QualityGate = QualityGate.RED
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)

    def compute_summary(self):
        if not self.entities:
            self.summary = "No entities to assess."
            return

        scores = [e.overall_score for e in self.entities]
        self.overall_score = np.mean(scores) if scores else 0
        self.overall_gate = FieldQuality.compute_gate(self.overall_score)

        green = sum(1 for e in self.entities if e.overall_gate == QualityGate.GREEN)
        yellow = sum(1 for e in self.entities if e.overall_gate == QualityGate.YELLOW)
        red = sum(1 for e in self.entities if e.overall_gate == QualityGate.RED)

        self.summary = (
            f"Port: {self.port_name} | "
            f"Score: {self.overall_score:.0f}/100 ({self.overall_gate.value}) | "
            f"Berths: {green} GREEN, {yellow} YELLOW, {red} RED"
        )

        # Generate recommendations
        for e in self.entities:
            if e.critical_gaps:
                self.recommendations.append(
                    f"Berth {e.entity_id}: Missing critical specs — {', '.join(e.critical_gaps)}"
                )


# ── Quality Scoring Functions ────────────────────────────────────────────────

def score_provenance_field(
    field_name: str,
    pf: ProvenanceField,
    expected_range: Optional[Tuple[float, float]] = None,
) -> FieldQuality:
    """Score a single ProvenanceField."""
    fq = FieldQuality(field_name=field_name)

    # Check presence
    if pf.value is None or str(pf.value).strip() == "" or str(pf.value) == "0.0":
        fq.present = False
        fq.score = 0.0
        fq.gate = QualityGate.RED
        fq.notes = "Missing value"
        return fq

    fq.present = True
    fq.source = pf.source

    # Check if "No Restrictions" (valid but unbounded)
    if str(pf.value) == "No Restrictions":
        fq.valid = True
        fq.score = 70.0  # Valid but not a real constraint
        fq.gate = QualityGate.YELLOW
        fq.notes = "No restriction specified (unbounded)"
        return fq

    # Try numeric validation
    if expected_range:
        try:
            val = float(pf.value)
            low, high = expected_range
            if low <= val <= high:
                fq.valid = True
            else:
                fq.valid = False
                fq.notes = f"Out of range [{low}, {high}]: {val}"
        except (ValueError, TypeError):
            fq.valid = False
            fq.notes = f"Non-numeric: {pf.value}"
    else:
        fq.valid = True  # No range to check

    # Score based on source + validity
    base_scores = {
        DataSource.SPEC: 95,
        DataSource.OPERATIONAL: 90,
        DataSource.HISTORICAL: 70,
        DataSource.ASSUMPTION: 30,
        DataSource.USER_INPUT: 80,
    }
    fq.score = base_scores.get(pf.source, 30)

    if not fq.valid:
        fq.score *= 0.5  # Halve score for invalid values

    fq.gate = FieldQuality.compute_gate(fq.score)
    return fq


def score_berth_quality(berth: BerthSpec) -> EntityQuality:
    """Score the data quality of a complete BerthSpec."""
    eq = EntityQuality(entity_id=berth.berth_code, entity_type="berth")

    # Define expected ranges for physical properties
    field_checks = [
        ("max_loa_m", berth.max_loa_m, (10, 500)),
        ("max_draft_m", berth.max_draft_m, (1, 30)),
        ("max_depth_m", berth.max_depth_m, (2, 40)),
        ("max_beam_m", berth.max_beam_m, (5, 100)),
        ("max_dwt", berth.max_dwt, (500, 500000)),
        ("ukc_m", berth.ukc_m, (0, 10)),
    ]

    # Critical field weights
    weights = {
        "max_loa_m": 3.0,
        "max_draft_m": 3.0,
        "max_depth_m": 2.0,
        "max_beam_m": 1.5,
        "max_dwt": 1.0,
        "ukc_m": 1.0,
        "vessel_types": 2.0,
        "cargo_capability": 2.0,
    }

    for fname, pf, expected in field_checks:
        fq = score_provenance_field(fname, pf, expected)
        eq.fields.append(fq)

    # Score vessel type data
    vt_score = 90 if berth.vessel_type_source in (DataSource.SPEC, DataSource.OPERATIONAL) else (
        65 if berth.vessel_type_source == DataSource.HISTORICAL else 30
    )
    eq.fields.append(FieldQuality(
        field_name="vessel_types",
        present=bool(berth.allowed_vessel_types),
        valid=bool(berth.allowed_vessel_types),
        source=berth.vessel_type_source,
        score=vt_score if berth.allowed_vessel_types else 0,
        gate=FieldQuality.compute_gate(vt_score if berth.allowed_vessel_types else 0),
    ))

    # Score cargo capability data
    cargo_present = bool(berth.cargo_categories)
    cargo_score = 90 if cargo_present else 30
    eq.fields.append(FieldQuality(
        field_name="cargo_capability",
        present=cargo_present,
        valid=cargo_present,
        source=DataSource.OPERATIONAL if cargo_present else DataSource.ASSUMPTION,
        score=cargo_score,
        gate=FieldQuality.compute_gate(cargo_score),
    ))

    eq.compute_overall(weights)
    return eq


def score_history_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Score the quality of historical port call data."""
    total = len(df)
    if total == 0:
        return {"total_records": 0, "overall_score": 0, "gate": "red"}

    # Check critical fields
    field_scores = {}
    critical_fields = {
        "loa": (10, 500),
        "adraft": (1, 30),
        "berthcode": None,
        "berth_occupancy_h": (0.1, 1000),
    }

    for col_name, expected_range in critical_fields.items():
        # Check multiple name variants
        actual_col = None
        for c in df.columns:
            if c.lower().strip() == col_name.lower():
                actual_col = c
                break

        if actual_col is None:
            field_scores[col_name] = {"present_pct": 0, "valid_pct": 0, "score": 0}
            continue

        present = df[actual_col].notna().mean() * 100
        valid_pct = present  # Default

        if expected_range and present > 0:
            numeric = pd.to_numeric(df[actual_col], errors="coerce")
            low, high = expected_range
            valid = numeric.between(low, high).mean() * 100
            valid_pct = valid

        score = (present * 0.6 + valid_pct * 0.4)
        field_scores[col_name] = {
            "present_pct": round(present, 1),
            "valid_pct": round(valid_pct, 1),
            "score": round(score, 1),
        }

    overall = np.mean([v["score"] for v in field_scores.values()])
    gate = "green" if overall >= 80 else ("yellow" if overall >= 60 else "red")

    return {
        "total_records": total,
        "field_scores": field_scores,
        "overall_score": round(overall, 1),
        "gate": gate,
    }
