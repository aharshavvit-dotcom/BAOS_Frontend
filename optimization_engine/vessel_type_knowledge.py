"""
Vessel Type Knowledge Base — Dynamic Capability Assessment.

Replaces hardcoded vessel-type whitelists with intelligent compatibility
scoring based on vessel requirements vs berth capabilities.

Instead of: "vessel type not allowed" → hard rejection
Now:        "X% compatible" → scored feasibility with explanation
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# ── Vessel Type Equipment Requirements ─────────────────────────────────────
# For each vessel type, define:
#   - required_equipment: MUST have (score heavily penalized if missing)
#   - preferred_equipment: NICE to have (score boosted if present)
#   - hazmat_required: Safety-critical flag (only hard-block if True and missing)
#   - typical_cargo_types: Common cargo for this vessel type
#   - base_compatibility: Baseline compatibility with generic berths (0-100)

VESSEL_TYPE_REQUIREMENTS: Dict[str, dict] = {
    "Bulk dry": {
        "required_equipment": ["crane", "conveyor"],
        "preferred_equipment": ["gangway", "hose"],
        "hazmat_required": False,
        "typical_cargo_types": [
            "Coal", "Iron Ore", "Grain", "Cement", "Fertilizer",
            "Bauxite", "Sugar", "Limestone", "Bulk Dry",
        ],
        "base_compatibility": 80,
        "description": "Needs bulk handling equipment (cranes, conveyors)",
    },
    "General cargo": {
        "required_equipment": ["crane"],
        "preferred_equipment": ["gangway", "conveyor"],
        "hazmat_required": False,
        "typical_cargo_types": [
            "General Cargo", "Steel", "Timber", "Machinery",
            "Project Cargo", "Break Bulk",
        ],
        "base_compatibility": 85,
        "description": "Flexible, needs basic crane capability",
    },
    "Container": {
        "required_equipment": ["crane"],
        "preferred_equipment": ["gangway"],
        "hazmat_required": False,
        "typical_cargo_types": [
            "Containers", "Container", "Reefer", "Mixed Container",
        ],
        "base_compatibility": 75,
        "description": "Needs gantry/container cranes, fast turnaround",
    },
    "Tanker": {
        "required_equipment": ["hose"],
        "preferred_equipment": ["gangway"],
        "hazmat_required": True,
        "typical_cargo_types": [
            "Crude Oil", "Petroleum", "Diesel", "Fuel Oil",
            "Gasoline", "Chemicals", "Liquid Bulk",
        ],
        "base_compatibility": 60,
        "description": "Needs liquid handling, hazmat safety systems",
    },
    "Chemical tanker": {
        "required_equipment": ["hose"],
        "preferred_equipment": ["gangway"],
        "hazmat_required": True,
        "typical_cargo_types": [
            "Chemicals", "Acids", "Caustic Soda", "Methanol",
            "Chemical Bulk",
        ],
        "base_compatibility": 55,
        "description": "Needs chemical-grade hoses, hazmat containment",
    },
    "RoRo": {
        "required_equipment": ["ramp"],
        "preferred_equipment": ["gangway"],
        "hazmat_required": False,
        "typical_cargo_types": [
            "Vehicles", "Cars", "Trucks", "Heavy Equipment",
            "Rolling Stock", "RoRo Cargo",
        ],
        "base_compatibility": 65,
        "description": "Needs vehicle ramps, deck-level access",
    },
    "LPG tanker": {
        "required_equipment": ["hose"],
        "preferred_equipment": ["gangway"],
        "hazmat_required": True,
        "typical_cargo_types": [
            "LPG", "Propane", "Butane", "Liquid Gas",
        ],
        "base_compatibility": 50,
        "description": "Needs gas-rated hoses, explosion-proof systems",
    },
    "LNG tanker": {
        "required_equipment": ["hose"],
        "preferred_equipment": ["gangway"],
        "hazmat_required": True,
        "typical_cargo_types": [
            "LNG", "Natural Gas", "Liquefied Gas",
        ],
        "base_compatibility": 50,
        "description": "Needs cryogenic hoses, LNG-specific safety",
    },
    "Multipurpose": {
        "required_equipment": [],
        "preferred_equipment": ["crane", "gangway", "conveyor"],
        "hazmat_required": False,
        "typical_cargo_types": [
            "Mixed", "General", "Project Cargo", "Multipurpose",
        ],
        "base_compatibility": 80,
        "description": "Flexible vessel, moderate equipment needs",
    },
    "Passenger": {
        "required_equipment": ["gangway"],
        "preferred_equipment": [],
        "hazmat_required": False,
        "typical_cargo_types": ["Passengers", "Cruise"],
        "base_compatibility": 70,
        "description": "Needs passenger gangways, terminal facilities",
    },
    "Crude oil tanker": {
        "required_equipment": ["hose"],
        "preferred_equipment": ["gangway"],
        "hazmat_required": True,
        "typical_cargo_types": ["Crude Oil", "Petroleum"],
        "base_compatibility": 55,
        "description": "Needs oil-grade hoses, SPM/SBM or jetty",
    },
    "BULK CARRIER": {
        "required_equipment": ["crane", "conveyor"],
        "preferred_equipment": ["gangway", "hose"],
        "hazmat_required": False,
        "typical_cargo_types": [
            "Coal", "Iron Ore", "Grain", "Cement", "Fertilizer",
            "Bauxite", "Sugar", "Limestone", "Bulk Dry",
        ],
        "base_compatibility": 80,
        "description": "Needs bulk handling equipment",
    },
}

# Aliases: map common alternative names to canonical types
VESSEL_TYPE_ALIASES: Dict[str, str] = {
    "bulk carrier": "Bulk dry",
    "bulker": "Bulk dry",
    "dry bulk": "Bulk dry",
    "general": "General cargo",
    "cargo": "General cargo",
    "container ship": "Container",
    "containership": "Container",
    "oil tanker": "Tanker",
    "product tanker": "Tanker",
    "chemical": "Chemical tanker",
    "ro-ro": "RoRo",
    "roro carrier": "RoRo",
    "vehicle carrier": "RoRo",
    "car carrier": "RoRo",
    "lpg": "LPG tanker",
    "lng": "LNG tanker",
    "gas carrier": "LPG tanker",
    "multi-purpose": "Multipurpose",
    "mpp": "Multipurpose",
    "cruise": "Passenger",
    "passenger ship": "Passenger",
    "crude tanker": "Crude oil tanker",
    "crude carrier": "Crude oil tanker",
}


def _normalize_vessel_type(vessel_type: str) -> str:
    """Normalize vessel type to a canonical name."""
    if not vessel_type:
        return ""
    # Check exact match first (case-insensitive key match)
    for key, reqs in VESSEL_TYPE_REQUIREMENTS.items():
        if key.lower() == vessel_type.lower():
            return key
    # Check aliases
    vt_lower = vessel_type.lower().strip()
    if vt_lower in VESSEL_TYPE_ALIASES:
        return VESSEL_TYPE_ALIASES[vt_lower]
    # Partial match
    for alias, canonical in VESSEL_TYPE_ALIASES.items():
        if alias in vt_lower or vt_lower in alias:
            return canonical
    return vessel_type  # Return original if no match


def get_vessel_requirements(vessel_type: str) -> dict:
    """Get requirements for a vessel type, with fallback for unknown types."""
    normalized = _normalize_vessel_type(vessel_type)
    if normalized in VESSEL_TYPE_REQUIREMENTS:
        return VESSEL_TYPE_REQUIREMENTS[normalized]
    # Unknown vessel type: return moderate defaults
    return {
        "required_equipment": [],
        "preferred_equipment": ["crane", "gangway"],
        "hazmat_required": False,
        "typical_cargo_types": [],
        "base_compatibility": 65,
        "description": f"Unknown vessel type '{vessel_type}' — using moderate defaults",
    }


def compute_compatibility_score(
    vessel_type: str,
    cargo_type: str,
    berth_equipment: List[str],
    berth_allowed_types: List[str],
) -> Tuple[float, str, List[str]]:
    """
    Compute dynamic compatibility score for a vessel-berth combination.

    Returns:
        (score: 0-100, summary: str, factors: List[str])

    Score ranges:
        90-100: Perfect match (equipment ideal, vessel type historically handled)
        75-89:  Excellent match (equipment adequate, good compatibility)
        60-74:  Good match (workable, minor gaps)
        45-59:  Acceptable match (feasible but suboptimal)
        30-44:  Marginal match (risky, many gaps)
        <30:    Poor match (should avoid, safety concern)
    """
    reqs = get_vessel_requirements(vessel_type)
    factors = []
    score = reqs["base_compatibility"]

    # Normalize equipment lists for comparison
    berth_equip_lower = {e.lower().strip() for e in berth_equipment}

    # ── Factor 1: Historical vessel type match (0-20 points) ──
    if berth_allowed_types:
        normalized_vt = _normalize_vessel_type(vessel_type)
        type_match = False
        for allowed in berth_allowed_types:
            if (allowed.lower() == vessel_type.lower() or
                _normalize_vessel_type(allowed) == normalized_vt):
                type_match = True
                break
        if type_match:
            score += 15
            factors.append("Vessel type historically handled at this berth (+15)")
        else:
            # Not historically handled, but not necessarily incompatible
            score -= 5
            factors.append("Vessel type not previously seen at this berth (-5)")
    else:
        # No type restrictions = open berth
        score += 5
        factors.append("Berth has no vessel type restrictions (+5)")

    # ── Factor 2: Required equipment availability (0-25 points) ──
    required = reqs["required_equipment"]
    if required:
        met = sum(1 for eq in required if eq.lower() in berth_equip_lower)
        total = len(required)
        if total > 0:
            ratio = met / total
            equip_bonus = int(ratio * 25)
            score += equip_bonus - 10  # Penalize missing required equipment
            if ratio == 1.0:
                factors.append(f"All required equipment available ({', '.join(required)}) (+15)")
            elif ratio > 0:
                missing = [eq for eq in required if eq.lower() not in berth_equip_lower]
                factors.append(
                    f"{met}/{total} required equipment available, missing: {', '.join(missing)} ({equip_bonus - 10:+d})"
                )
            else:
                factors.append(
                    f"No required equipment available (needs: {', '.join(required)}) (-10)"
                )
    else:
        score += 5
        factors.append("Vessel type has no specific equipment requirements (+5)")

    # ── Factor 3: Preferred equipment (0-10 bonus) ──
    preferred = reqs["preferred_equipment"]
    if preferred:
        pref_met = sum(1 for eq in preferred if eq.lower() in berth_equip_lower)
        if pref_met > 0:
            bonus = min(pref_met * 4, 10)
            score += bonus
            factors.append(f"{pref_met}/{len(preferred)} preferred equipment available (+{bonus})")

    # ── Factor 4: Cargo type alignment (0-10 points) ──
    if cargo_type and reqs["typical_cargo_types"]:
        cargo_lower = cargo_type.lower().strip()
        cargo_match = any(
            cargo_lower == tc.lower() or cargo_lower in tc.lower() or tc.lower() in cargo_lower
            for tc in reqs["typical_cargo_types"]
        )
        if cargo_match:
            score += 5
            factors.append(f"Cargo type '{cargo_type}' aligns with vessel type (+5)")
        else:
            score -= 3
            factors.append(f"Cargo type '{cargo_type}' unusual for this vessel type (-3)")

    # ── Factor 5: Hazmat safety check (critical) ──
    if reqs["hazmat_required"]:
        has_hazmat_equip = any(
            kw in " ".join(berth_equip_lower)
            for kw in ["hose", "hazmat", "chemical", "oil", "gas", "liquid"]
        )
        if has_hazmat_equip:
            score += 5
            factors.append("Hazmat-capable equipment detected (+5)")
        else:
            score -= 30
            factors.append("⚠️ HAZMAT REQUIRED but no liquid handling equipment detected (-30)")

    # ── Clamp score to 0-100 ──
    score = max(0, min(100, score))

    # ── Generate summary ──
    if score >= 90:
        summary = f"Excellent compatibility ({score}%) — ideal match for {vessel_type}"
    elif score >= 75:
        summary = f"Good compatibility ({score}%) — well-suited for {vessel_type}"
    elif score >= 60:
        summary = f"Acceptable compatibility ({score}%) — workable for {vessel_type}"
    elif score >= 45:
        summary = f"Marginal compatibility ({score}%) — feasible but suboptimal for {vessel_type}"
    elif score >= 30:
        summary = f"Poor compatibility ({score}%) — significant gaps for {vessel_type}"
    else:
        summary = f"Incompatible ({score}%) — safety concern for {vessel_type}"

    return score, summary, factors
