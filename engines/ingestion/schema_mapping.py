"""
Schema Mapping — Column alias resolution for varied Excel formats.
"""
from __future__ import annotations

from typing import Dict, List, Optional


COLUMN_ALIASES: Dict[str, List[str]] = {
    # Port call log columns
    "berth_code": ["berth", "berth code", "berth_code", "berth no", "berth_no", "berthcode"],
    "berth_name": ["berth name", "berth_name", "berthname"],
    "vessel_name": ["vessel", "vessel name", "ship name", "name", "vesselname"],
    "vessel_imo": ["imo", "imo number", "imo_number", "imonumber"],
    "vessel_type": ["vesseltype", "vessel type", "vessel_type", "ship type"],
    "cargo_type": ["cargo type", "cargo_type", "cargotype", "commodity"],
    "loa_m": ["loa", "length overall", "loa_m", "length_overall"],
    "beam_m": ["beam", "beam_m", "breadth", "width"],
    "arrival_draft_m": ["arrival draft", "adraft", "arr draft", "draft", "adraught", "arrival_draft"],
    "departure_draft_m": ["departure draft", "ddraft", "ddraught", "dep draft", "departure_draft"],
    "dwt": ["dwt", "deadweight", "dead weight"],
    "cargo_tons": ["cargo tons", "cargo_tons", "cargo quantity", "cargo_quantity"],
    "eosp_ts": ["eosp", "end of sea passage", "end_of_sea_passage"],
    "pob_ts": ["pob", "pilot on board", "pilot_on_board"],
    "all_fast_ts": ["all fast", "all_fast", "allfast", "all_fast_ts"],
    "last_line_ts": ["last line", "last_line", "lastline", "last_line_ts"],
    "cosp_ts": ["cosp", "commencement of sea passage", "commencement_of_sea_passage"],
    "port_code": ["portcode", "port code", "port_code"],
    "port_name": ["port", "port name", "port_name", "portname"],
    "terminal_code": ["terminalcode", "terminal code", "terminal_code"],
    "terminal_name": ["terminal", "terminal name", "terminal_name", "terminalname"],

    # Berth config columns
    "property_name": ["propertyname", "property name", "property_name"],
    "property_value": ["propertyvalue", "property value", "property_value"],
    "property_uom": ["propertyuom", "property uom", "property_uom"],
    "berth_type": ["berthtype", "berth type", "berth_type"],
    "berthing_side": ["berthingside", "berthing side", "berthing_side"],

    # Operational capability columns
    "operation": ["operation", "op", "operation_type"],
    "commodity_group": ["commoditygroup", "commodity group", "commodity_group"],
    "cargo_category": ["cargocategory", "cargo category", "cargo_category"],
    "terminal_type": ["terminaltype", "terminal type", "terminal_type"],
}


def normalize_columns(columns: List[str]) -> Dict[str, str]:
    """
    Build a mapping from normalized column names to original column names.

    Returns:
        Dict[canonical_name, original_column_name]
    """
    mapping: Dict[str, str] = {}
    normalized = {c: c.strip().lower().replace(" ", "_") for c in columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        alias_set = set(a.lower().replace(" ", "_") for a in aliases)
        for original, norm in normalized.items():
            if norm in alias_set and canonical not in mapping:
                mapping[canonical] = original

    return mapping


def resolve_column(
    columns: List[str],
    canonical_name: str,
) -> Optional[str]:
    """Resolve a canonical column name to its original column name."""
    mapping = normalize_columns(columns)
    return mapping.get(canonical_name)
