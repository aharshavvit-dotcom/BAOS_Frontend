"""
Constraint Library — Single Source of Truth for All Constraints
================================================================
Replaces hardcoded constraint checks scattered across:
  - feasibility_checker.py (inline LOA/draft checks)
  - vessel_type_knowledge.py (hardcoded compatibility scores)
  - constraint_model.py (magic thresholds 30/60)

All constraints are typed, source-tracked, and checked against
specifications rather than historical data.

Constraint Tiers:
  Tier 1 (HARD): Physical limits from spec sheets — cannot be violated
  Tier 2 (SOFT_HIGH): Operational compatibility — strong penalty
  Tier 3 (SOFT_LOW): Contextual/preference — weak penalty
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.db.models.data_models import (
    BerthSpec, ConstraintCategory, ConstraintCheckResult, ConstraintDefinition,
    ConstraintSeverity, DataSource, FeasibilityResult, ProvenanceField,
    QualityGate, PortMaster,
)


class ConstraintLibrary:
    """
    Builds and evaluates constraints from berth specifications.
    
    Usage:
        lib = ConstraintLibrary(port_master)
        result = lib.check_feasibility(vessel_dict, berth_code)
        all_results = lib.check_all_berths(vessel_dict)
    """

    def __init__(self, port_master: PortMaster):
        self.port = port_master
        self._constraints_cache: Dict[str, List[ConstraintDefinition]] = {}
        self._build_constraints()

    def _build_constraints(self):
        """Build constraint definitions for all berths from specs."""
        for bc, berth in self.port.berths.items():
            constraints = []

            # ── Tier 1: Physical / Hard ─────────────────────────────────
            # LOA constraint
            if berth.get_max_loa() > 0:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_loa",
                    name="Max LOA",
                    category=ConstraintCategory.PHYSICAL,
                    severity=ConstraintSeverity.HARD,
                    description=f"Vessel LOA must not exceed {berth.get_max_loa():.0f}m",
                    source=berth.max_loa_m.source,
                    data_quality=berth.max_loa_m.quality,
                    field_name="loa",
                    operator="lte",
                    limit_value=berth.get_max_loa(),
                ))

            # Min LOA constraint (some berths require minimum vessel length)
            if berth.get_min_loa() > 0:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_min_loa",
                    name="Min LOA",
                    category=ConstraintCategory.PHYSICAL,
                    severity=ConstraintSeverity.HARD,
                    description=f"Vessel LOA must be at least {berth.get_min_loa():.0f}m for this berth",
                    source=berth.min_loa_m.source,
                    data_quality=berth.min_loa_m.quality,
                    field_name="loa",
                    operator="gte",
                    limit_value=berth.get_min_loa(),
                ))

            # Draft constraint (with UKC consideration)
            if berth.get_max_draft() > 0:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_draft",
                    name="Max Draft",
                    category=ConstraintCategory.PHYSICAL,
                    severity=ConstraintSeverity.HARD,
                    description=f"Vessel draft must not exceed {berth.get_max_draft():.1f}m",
                    source=berth.max_draft_m.source,
                    data_quality=berth.max_draft_m.quality,
                    field_name="draft",
                    operator="lte",
                    limit_value=berth.get_max_draft(),
                ))

            # Depth / UKC constraint
            if berth.get_depth() > 0:
                effective_depth = berth.get_depth() - berth.get_ukc()
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_depth_ukc",
                    name="Effective Depth (incl. UKC)",
                    category=ConstraintCategory.PHYSICAL,
                    severity=ConstraintSeverity.HARD,
                    description=f"Vessel draft must fit within depth {berth.get_depth():.1f}m minus UKC {berth.get_ukc():.1f}m = {effective_depth:.1f}m",
                    source=berth.max_depth_m.source,
                    data_quality=berth.max_depth_m.quality,
                    field_name="draft",
                    operator="lte",
                    limit_value=effective_depth,
                ))

            # Beam constraint
            if berth.get_max_beam() > 0:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_beam",
                    name="Max Beam",
                    category=ConstraintCategory.PHYSICAL,
                    severity=ConstraintSeverity.HARD,
                    description=f"Vessel beam must not exceed {berth.get_max_beam():.1f}m",
                    source=berth.max_beam_m.source,
                    data_quality=berth.max_beam_m.quality,
                    field_name="beam",
                    operator="lte",
                    limit_value=berth.get_max_beam(),
                ))

            # DWT constraint
            max_dwt = 0
            try:
                max_dwt = float(berth.max_dwt.value) if berth.max_dwt.value and str(berth.max_dwt.value) != "No Restrictions" else 0
            except (ValueError, TypeError):
                pass
            if max_dwt > 0:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_dwt",
                    name="Max DWT",
                    category=ConstraintCategory.PHYSICAL,
                    severity=ConstraintSeverity.HARD,
                    source=berth.max_dwt.source,
                    data_quality=berth.max_dwt.quality,
                    field_name="dwt",
                    operator="lte",
                    limit_value=max_dwt,
                ))

            # Channel draft constraint
            try:
                ch_draft = float(berth.channel_max_draft_m.value) if berth.channel_max_draft_m.value else 0
            except (ValueError, TypeError):
                ch_draft = 0
            if ch_draft > 0:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_channel_draft",
                    name="Channel Max Draft",
                    category=ConstraintCategory.PHYSICAL,
                    severity=ConstraintSeverity.HARD,
                    source=berth.channel_max_draft_m.source,
                    data_quality=berth.channel_max_draft_m.quality,
                    field_name="draft",
                    operator="lte",
                    limit_value=ch_draft,
                ))

            # ── Tier 2: Operational / Soft-High ─────────────────────────
            # Cargo category compatibility
            if berth.cargo_categories:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_cargo_cat",
                    name="Cargo Category",
                    category=ConstraintCategory.OPERATIONAL,
                    severity=ConstraintSeverity.SOFT_HIGH,
                    description=f"Berth handles: {sorted(berth.cargo_categories)}",
                    source=DataSource.OPERATIONAL,
                    data_quality=QualityGate.GREEN,
                    field_name="cargo_category",
                    operator="in",
                    limit_value=berth.cargo_categories,
                    penalty_cost=5000,
                ))

            # Vessel type compatibility
            if berth.allowed_vessel_types:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_vessel_type",
                    name="Vessel Type",
                    category=ConstraintCategory.OPERATIONAL,
                    severity=ConstraintSeverity.SOFT_HIGH,
                    description=f"Berth accepts: {berth.allowed_vessel_types}",
                    source=berth.vessel_type_source,
                    data_quality=(QualityGate.GREEN if berth.vessel_type_source in
                                  (DataSource.SPEC, DataSource.OPERATIONAL) else QualityGate.YELLOW),
                    field_name="vessel_type",
                    operator="in",
                    limit_value=berth.allowed_vessel_types,
                    penalty_cost=3000,
                ))

            # Tidal restriction
            if berth.tidal_restricted:
                constraints.append(ConstraintDefinition(
                    id=f"{bc}_tidal",
                    name="Tidal Restricted",
                    category=ConstraintCategory.CONTEXTUAL,
                    severity=ConstraintSeverity.INFO,
                    description="Berth is tidal restricted — arrival/departure timing may be constrained",
                    source=DataSource.SPEC,
                    data_quality=QualityGate.GREEN,
                    field_name="tidal_restricted",
                    operator="eq",
                    limit_value=True,
                ))

            self._constraints_cache[bc] = constraints

    def get_constraints(self, berth_code: str) -> List[ConstraintDefinition]:
        """Get all constraints for a berth."""
        return self._constraints_cache.get(str(berth_code), [])

    def check_feasibility(
        self,
        vessel: dict,
        berth_code: str,
    ) -> FeasibilityResult:
        """
        Check all constraints for a vessel-berth pair.
        
        Args:
            vessel: Dict with keys: loa, draft, beam, dwt, vessel_type, cargo_category
            berth_code: Target berth
            
        Returns:
            FeasibilityResult with detailed per-constraint outcomes
        """
        constraints = self.get_constraints(str(berth_code))
        result = FeasibilityResult(
            vessel_id=vessel.get("vessel_id", "unknown"),
            berth_code=str(berth_code),
        )

        if not constraints:
            result.explanation = f"No constraints found for berth {berth_code}"
            result.data_quality = QualityGate.RED
            return result

        # Map vessel fields to constraint field names
        field_map = {
            "loa": vessel.get("loa", vessel.get("loa_m", 0)),
            "draft": vessel.get("draft", vessel.get("draft_m", vessel.get("adraft", 0))),
            "beam": vessel.get("beam", vessel.get("beam_m", vessel.get("breadthExtreme",
                     vessel.get("breadth_extreme", 0)))),
            "dwt": vessel.get("dwt", 0),
            "vessel_type": vessel.get("vessel_type", ""),
            "cargo_category": vessel.get("cargo_category", vessel.get("cargo_type", "")),
            "tidal_restricted": True,
        }

        for constraint in constraints:
            actual_value = field_map.get(constraint.field_name)
            if actual_value is None or (isinstance(actual_value, (int, float)) and actual_value == 0):
                # Missing vessel data — skip but note
                result.add_result(ConstraintCheckResult(
                    constraint_id=constraint.id,
                    passed=True,
                    reason=f"{constraint.name}: Skipped (no vessel data for '{constraint.field_name}')",
                    data_quality=QualityGate.RED,
                ))
                continue

            check_result = constraint.check(actual_value)
            result.add_result(check_result)

        # Overall quality = worst quality among checks
        qualities = [r.data_quality for r in result.constraint_results]
        if QualityGate.RED in qualities:
            result.data_quality = QualityGate.RED
        elif QualityGate.YELLOW in qualities:
            result.data_quality = QualityGate.YELLOW
        else:
            result.data_quality = QualityGate.GREEN

        result.build_explanation()
        return result

    def check_all_berths(self, vessel: dict) -> Dict[str, FeasibilityResult]:
        """Check feasibility against all berths."""
        results = {}
        for bc in self.port.berths:
            results[bc] = self.check_feasibility(vessel, bc)
        return results

    def get_feasible_berths(self, vessel: dict) -> List[str]:
        """Return list of berth codes where vessel is feasible."""
        all_results = self.check_all_berths(vessel)
        return [bc for bc, r in all_results.items() if r.feasible]

    def compute_suitability_score(
        self,
        vessel: dict,
        berth_code: str,
    ) -> float:
        """
        Compute a data-driven suitability score (0-100) for vessel-berth pair.
        
        Replaces hardcoded compatibility scores in vessel_type_knowledge.py.
        Score based on:
          - Constraint pass rate (40%)
          - Physical margin (30%) — how much room to spare
          - Operational match (30%) — cargo/vessel type fit
        """
        result = self.check_feasibility(vessel, berth_code)
        berth = self.port.get_berth(str(berth_code))

        if not result.feasible:
            return 0.0  # Hard violation = 0

        if not berth:
            return 0.0

        # 1. Constraint pass rate (40%)
        pass_score = result.pass_rate * 100 * 0.4

        # 2. Physical margins (30%)
        # If the vessel fits, it should score functionally 100 for physical alignment.
        margin_scores = []
        loa = float(vessel.get("loa", vessel.get("loa_m", 0)))
        draft = float(vessel.get("draft", vessel.get("draft_m", vessel.get("adraft", 0))))

        max_loa = berth.get_max_loa()
        if max_loa > 0 and loa > 0:
            margin_scores.append(100.0 if loa <= max_loa else 0.0)

        max_draft = berth.get_max_draft()
        if max_draft > 0 and draft > 0:
            margin_scores.append(100.0 if draft <= max_draft else 0.0)

        margin_score = (np.mean(margin_scores) if margin_scores else 100) * 0.3

        margin_score = (np.mean(margin_scores) if margin_scores else 100) * 0.3

        # 3. Operational match (30%)
        # Unify with heuristic compatibility engine (which handles equipment, cargo, etc.)
        from engines.simulation.optimization.vessel_type_knowledge import compute_compatibility_score
        
        vtype = vessel.get("vessel_type", "")
        cargo_cat = vessel.get("cargo_category", "")
        
        op_score, _, _ = compute_compatibility_score(
            vessel_type=vtype,
            cargo_type=cargo_cat,
            berth_equipment=berth.equipment_types if berth.equipment_types else [],
            berth_allowed_types=berth.allowed_vessel_types if berth.allowed_vessel_types else []
        )
                
        op_score_weighted = op_score * 0.3

        total = pass_score + margin_score + op_score_weighted
        
        # If there is a massive operational mismatch, slash the total score heavily.
        if op_score < 50:
            total *= 0.1
            
        return round(min(max(total, 0.0), 100.0), 1)

    def summary(self) -> dict:
        """Summary of the constraint library."""
        total_constraints = sum(len(v) for v in self._constraints_cache.values())
        hard = sum(
            1 for cs in self._constraints_cache.values()
            for c in cs if c.severity == ConstraintSeverity.HARD
        )
        soft = total_constraints - hard
        spec_sourced = sum(
            1 for cs in self._constraints_cache.values()
            for c in cs if c.source in (DataSource.SPEC, DataSource.OPERATIONAL)
        )

        return {
            "total_berths": len(self._constraints_cache),
            "total_constraints": total_constraints,
            "hard_constraints": hard,
            "soft_constraints": soft,
            "spec_sourced": spec_sourced,
            "spec_coverage_pct": round(spec_sourced / total_constraints * 100, 1) if total_constraints else 0,
        }
