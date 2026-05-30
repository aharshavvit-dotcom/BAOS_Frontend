"""
Conflict Detector — Identifies schedule conflicts for scenario analysis.

Checks for:
  - Berth overlap between vessels
  - Resource availability (tug, pilot) violations
  - Depth / draft violations
  - Downtime window conflicts
  - Channel movement conflicts
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engines.simulation.optimization.constraint_model import (
    VesselInput, BerthInput, AssignmentResult, ResourceInput,
    DowntimeWindowInput, SchedulerConfig,
)
from engines.simulation.optimization.vessel_type_knowledge import compute_compatibility_score


def detect_conflicts(
    vessel_id: str,
    berth_code: str,
    start_min: int,
    end_min: int,
    vessels: Dict[str, VesselInput],
    berths: Dict[str, BerthInput],
    existing_assignments: List[AssignmentResult],
    resources: Optional[List[ResourceInput]] = None,
    downtimes: Optional[List[DowntimeWindowInput]] = None,
    config: Optional[SchedulerConfig] = None,
) -> List[str]:
    """
    Detect all conflicts for a proposed vessel placement.

    Returns a list of human-readable conflict descriptions.
    Empty list = no conflicts.
    """
    cfg = config or SchedulerConfig()
    conflicts: List[str] = []

    vessel = vessels.get(vessel_id)
    berth = berths.get(berth_code)

    if not vessel:
        conflicts.append(f"Unknown vessel: {vessel_id}")
        return conflicts
    if not berth:
        conflicts.append(f"Unknown berth: {berth_code}")
        return conflicts

    # ── 1. Physical feasibility ──────────────────────────────────────────
    if vessel.loa_m > 0 and berth.max_loa_m < vessel.loa_m:
        conflicts.append(
            f"LOA violation: Vessel {vessel.loa_m:.0f}m exceeds berth max {berth.max_loa_m:.0f}m"
        )

    ukc = cfg.ukc_margin_m
    if vessel.draft_m > 0 and berth.max_draft_m < (vessel.draft_m + ukc):
        excess = (vessel.draft_m + ukc) - berth.max_draft_m
        conflicts.append(
            f"Draft violation: Draft {vessel.draft_m:.1f}m + UKC {ukc:.1f}m "
            f"exceeds berth max draft {berth.max_draft_m:.1f}m by {excess:.1f}m"
        )

    if vessel.beam_m > 0 and berth.max_beam_m < vessel.beam_m:
        conflicts.append(
            f"Beam violation: Vessel beam {vessel.beam_m:.1f}m exceeds berth max {berth.max_beam_m:.1f}m"
        )

    # Dynamic compatibility scoring instead of hard vessel type rejection
    if vessel.vessel_type:
        compat_score, summary, _ = compute_compatibility_score(
            vessel.vessel_type, vessel.cargo_type,
            berth.equipment_types, berth.allowed_vessel_types,
        )
        if compat_score < 30:
            conflicts.append(
                f"Vessel type incompatible: {summary}"
            )
        elif compat_score < 60:
            conflicts.append(
                f"⚠️ Low compatibility ({compat_score}%): {summary}"
            )

    # ── 2. Berth overlap ────────────────────────────────────────────────
    for a in existing_assignments:
        if a.vessel_id == vessel_id:
            continue  # Skip self
        if a.berth_code != berth_code:
            continue
        # Check time overlap
        if start_min < a.end_minutes and end_min > a.start_minutes:
            v_other = vessels.get(a.vessel_id)
            other_name = v_other.name if v_other and v_other.name else a.vessel_id
            conflicts.append(
                f"Overlap with {other_name} "
                f"({a.start_minutes // 60:.0f}h–{a.end_minutes // 60:.0f}h)"
            )

    # ── 3. Downtime conflict ────────────────────────────────────────────
    if downtimes:
        for dt in downtimes:
            if dt.berth_code != berth_code:
                continue
            if start_min < dt.end_min and end_min > dt.start_min:
                reason = dt.reason or "Planned maintenance"
                conflicts.append(
                    f"Downtime conflict: {reason} "
                    f"({dt.start_min // 60:.0f}h–{dt.end_min // 60:.0f}h)"
                )

    # ── 4. Resource conflicts ───────────────────────────────────────────
    if resources:
        movement_dur = cfg.movement_duration_minutes
        move_start = start_min
        move_end = start_min + movement_dur

        for res in resources:
            if res.resource_type == "tug" and not vessel.needs_tug:
                continue
            if res.resource_type == "pilot" and not vessel.needs_pilot:
                continue

            # Count concurrent resource usage at vessel's movement time
            concurrent = 0
            for a in existing_assignments:
                if a.vessel_id == vessel_id:
                    continue
                v_other = vessels.get(a.vessel_id)
                if not v_other:
                    continue
                if res.resource_type == "tug" and not v_other.needs_tug:
                    continue
                if res.resource_type == "pilot" and not v_other.needs_pilot:
                    continue

                # Check overlap with other vessel's movement window
                other_move_end = a.start_minutes + movement_dur
                if move_start < other_move_end and move_end > a.start_minutes:
                    concurrent += 1

            if concurrent >= res.capacity:
                conflicts.append(
                    f"{res.resource_type.title()} availability exceeded: "
                    f"{concurrent + 1} needed, {res.capacity} available "
                    f"at {start_min // 60:.0f}h"
                )

    # ── 5. Channel movement conflict ────────────────────────────────────
    max_ch = cfg.max_channel_movements
    if max_ch > 0:
        movement_dur = cfg.movement_duration_minutes
        move_start = start_min
        move_end = start_min + movement_dur

        concurrent_movements = 0
        for a in existing_assignments:
            if a.vessel_id == vessel_id:
                continue
            # Inbound movement
            other_in_end = a.start_minutes + movement_dur
            if move_start < other_in_end and move_end > a.start_minutes:
                concurrent_movements += 1
            # Outbound movement
            other_out_end = a.end_minutes + movement_dur
            if move_start < other_out_end and move_end > a.end_minutes:
                concurrent_movements += 1

        if concurrent_movements >= max_ch:
            conflicts.append(
                f"Channel congestion: {concurrent_movements + 1} movements "
                f"at {start_min // 60:.0f}h, max {max_ch} allowed"
            )

    # ── 6. Berth availability window ────────────────────────────────────
    if start_min < berth.available_from_min or end_min > berth.available_to_min:
        conflicts.append(
            f"Outside berth availability: "
            f"need [{start_min // 60:.0f}h–{end_min // 60:.0f}h], "
            f"available [{berth.available_from_min // 60:.0f}h–{berth.available_to_min // 60:.0f}h]"
        )

    return conflicts
