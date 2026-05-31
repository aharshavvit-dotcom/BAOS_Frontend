"""
Data Preparation Utilities for Berth Optimization
- Reads the Chennai port-call log Excel (908 rows, 45 cols)
- Creates derived KPIs from EOSP/POB/ALL FAST/LAST LINE/COSP
- Generates a data dictionary (null%, distinct count, examples)
"""

from __future__ import annotations
import hashlib
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

from backend.config.settings import settings


TS_COLS = ["EOSP", "POB", "ALL FAST", "LAST LINE", "COSP"]


def _snake(s: str) -> str:
    s = s.strip().lower().replace(" ", "_")
    s = s.replace("__", "_")
    return s


def make_port_call_id(row: pd.Series) -> str:
    key = "|".join([
        str(row.get("portcode", "")),
        str(row.get("terminalcode", "")),
        str(row.get("berthcode", "")),
        str(row.get("imo", "")),
        str(row.get("eosp", "")),
        str(row.get("cosp", "")),
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def prepare_portcall_log(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    # Standardize columns
    df.columns = [_snake(c) for c in df.columns]

    # Normalize common vessel dimension fields
    if 'adraught' in df.columns and 'adraft' not in df.columns:
        df = df.rename(columns={'adraught': 'adraft'})

    # Parse timestamps
    for c in [c.lower().replace(" ", "_") for c in TS_COLS]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Derived KPIs (hours)
    def dur_hours(a, b):
        return (b - a).dt.total_seconds() / 3600.0

    if "eosp" in df.columns and "pob" in df.columns:
        df["pilot_wait_h"] = dur_hours(df["eosp"], df["pob"])
    if "pob" in df.columns and "all_fast" in df.columns:
        df["pilot_to_berth_h"] = dur_hours(df["pob"], df["all_fast"])
    if "all_fast" in df.columns and "last_line" in df.columns:
        df["berth_occupancy_h"] = dur_hours(df["all_fast"], df["last_line"])
    if "last_line" in df.columns and "cosp" in df.columns:
        df["unberth_outbound_h"] = dur_hours(df["last_line"], df["cosp"])
    if "eosp" in df.columns and "cosp" in df.columns:
        df["total_port_stay_h"] = dur_hours(df["eosp"], df["cosp"])

    # Port call id
    df["port_call_id"] = df.apply(make_port_call_id, axis=1)

    # Sanity flags
    for c in ["pilot_wait_h", "pilot_to_berth_h", "berth_occupancy_h", "unberth_outbound_h", "total_port_stay_h"]:
        if c in df.columns:
            df[c + "_neg_flag"] = df[c] < 0

    return df


def data_dictionary(df: pd.DataFrame, max_examples: int = 3) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        s = df[c]
        null_pct = float(s.isna().mean() * 100.0)
        distinct = int(s.nunique(dropna=True))
        dtype = str(s.dtype)

        examples = []
        for v in s.dropna().head(max_examples).tolist():
            examples.append(str(v))
        rows.append({
            "column": c,
            "dtype": dtype,
            "null_%": round(null_pct, 2),
            "distinct": distinct,
            "examples": " | ".join(examples)
        })
    return pd.DataFrame(rows).sort_values(["null_%", "column"], ascending=[True, True]).reset_index(drop=True)


def default_berth_master(df_enriched: pd.DataFrame) -> pd.DataFrame:
    """
    Builds a practical starting config from history:
    - Each berth seen in logs becomes a row.
    - max_loa/max_draft are conservatively inferred from observed max (editable in UI).
    - allowed vessel types are derived from observed types (editable).
    """
    df = df_enriched.copy()
    for col in ["berthcode", "berth", "terminalcode", "terminal", "portcode", "port"]:
        if col not in df.columns:
            df[col] = None

    g = df.groupby(["portcode", "port", "terminalcode", "terminal", "berthcode", "berth"], dropna=False)

    out = []
    for keys, part in g:
        portcode, port, terminalcode, terminal, berthcode, berth = keys
        max_loa_obs = pd.to_numeric(part.get("loa"), errors="coerce").max()
        max_draft_obs = pd.to_numeric(part.get("adraft"), errors="coerce").max()
        vessel_types = sorted(set([x for x in part.get("vesseltype", pd.Series([], dtype=str)).dropna().astype(str).tolist() if x.strip()]))

        out.append({
            "port_code": portcode,
            "port": port,
            "terminal_code": terminalcode,
            "terminal": terminal,
            "berth_code": berthcode,
            "berth": berth,
            # FIX (Phase 5): Do not inflate inferred berth limits above observed history.
            "max_loa_m": float(max_loa_obs * settings.berth_limit_inference_factor) if pd.notna(max_loa_obs) else None,
            "max_draft_m": float(max_draft_obs * settings.berth_limit_inference_factor) if pd.notna(max_draft_obs) else None,
            "allowed_vessel_types": ", ".join(vessel_types) if vessel_types else None,
            "allow_24x7": True,
            "work_start": "00:00",
            "work_end": "23:59",
        })

    return pd.DataFrame(out).sort_values(["port_code", "terminal_code", "berth_code"]).reset_index(drop=True)


def default_service_time_model(df_enriched: pd.DataFrame) -> pd.DataFrame:
    """
    Learns typical berth occupancy time from history.
    Returns medians by (terminal, berth, vesseltype).
    """
    df = df_enriched.copy()
    df["berth_occupancy_h"] = pd.to_numeric(df.get("berth_occupancy_h"), errors="coerce")
    df = df[df["berth_occupancy_h"].notna() & (df["berth_occupancy_h"] > 0)]

    grp = df.groupby(["portcode", "terminalcode", "berthcode", "vesseltype"], dropna=False)["berth_occupancy_h"]
    out = grp.agg(["count", "median", "mean", "p25", "p75"] if False else ["count", "median", "mean"])
    out = out.reset_index()
    out = out.rename(columns={
        "portcode": "port_code",
        "terminalcode": "terminal_code",
        "berthcode": "berth_code",
        "vesseltype": "vessel_type",
        "median": "service_hours_median",
        "mean": "service_hours_mean",
    })
    return out.sort_values(["port_code", "terminal_code", "berth_code", "vessel_type"]).reset_index(drop=True)
