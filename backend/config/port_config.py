"""
Configuration Layer for Berth Optimization.
Generates default port configs from historical data,
and handles save/load of configuration packages.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from backend.config.settings import settings
from backend.db.models.domain import (
    Berth, PortConfig, TideWindow, WeatherWindow, ChannelWindow,
    ResourceSlot, ContractRule, GoIOverrideRule, LeverConfig,
    DowntimeWindow
)

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
_INFERRED_BERTH_LIMIT_WARNING = (
    "Berth specs unavailable for one or more berths; using conservative inferred limits "
    "from historical vessel dimensions."
)


def _load_port_master_for_config(
    port_name: str = "chennai",
    berth_config_path: Optional[str] = None,
    operational_capability_path: Optional[str] = None,
    history_df: Optional[pd.DataFrame] = None,
):
    """
    Load PortMaster from DB if available.
    Falls back to Excel files if DB is not reachable or empty.
    """
    # ── Try Database first ──────────────────────────────────
    try:
        from backend.db.session import get_sync_db
        from backend.db.models.baos_models import BaosPort, BaosBerth
        from backend.db.models.data_models import PortMaster, BerthSpec, ProvenanceField, QualityGate
        
        session = get_sync_db()
        try:
            from backend.db.repositories.port_store import _get_port_code
            port_code = _get_port_code(session, port_name)
            port = session.query(BaosPort).filter(BaosPort.port_code == port_code).first()
            if port:
                berths = session.query(BaosBerth).filter(BaosBerth.port_id == port.port_id).all()
                if berths:
                    berth_specs = {}
                    for b in berths:
                        vessel_types = sorted(set(c.vessel_type for c in b.capabilities if c.vessel_type))
                        cargo_types = sorted(set(c.cargo_type for c in b.capabilities if c.cargo_type))
                        
                        spec = BerthSpec(
                            berth_code=b.berth_code,
                            berth_name=b.berth_name or b.berth_code,
                            terminal_name=b.terminal_name or "",
                            port_code=port_code,
                            port_name=port.port_name,
                        )
                        spec.max_loa_m = ProvenanceField.from_spec(b.max_loa_m or 400.0)
                        spec.max_beam_m = ProvenanceField.from_spec(b.max_beam_m or 60.0)
                        spec.max_draft_m = ProvenanceField.from_spec(b.max_draft_m or 15.0)
                        spec.max_depth_m = ProvenanceField.from_spec(b.depth_m or 16.0)
                        spec.allowed_vessel_types = vessel_types
                        spec.supported_commodities = cargo_types
                        spec.equipment_types = ["crane", "hose", "gangway"]
                        try:
                            spec.data_quality = QualityGate(b.data_quality_level.lower() if b.data_quality_level else "spec")
                        except Exception:
                            spec.data_quality = QualityGate.GREEN
                        berth_specs[b.berth_code] = spec
                        
                    port_master = PortMaster(
                        port_code=port_code,
                        port_name=port.port_name,
                        berths=berth_specs,
                        spec_loaded=True,
                        operational_loaded=True,
                        history_loaded=True
                    )
                    logger.info(f"Loaded PortMaster from DB: {len(port_master.berths)} berths")
                    return port_master
        finally:
            session.close()
    except Exception as db_err:
        logger.warning(f"Failed to load PortMaster from DB: {db_err}. Falling back to Excel files.")

    # ── Fallback to Excel files ─────────────────────────────
    try:
        from engines.ingestion.spec_ingest import build_port_master

        sample_data = _ROOT / "sample_data"

        # Use provided paths or auto-discover from sample_data/
        bcfg = berth_config_path or str(sample_data / "Berth_configurations.xlsx")
        ocap = operational_capability_path or str(sample_data / "Operational_Capability_of_Berth.xlsx")

        if not Path(bcfg).exists():
            logger.info("No berth config spec found — using history-derived limits")
            return None

        port_master = build_port_master(
            port_name=port_name,
            berth_config_path=bcfg,
            operational_capability_path=ocap if Path(ocap).exists() else None,
            history_df=history_df,
        )
        logger.info(
            f"Loaded PortMaster: {len(port_master.berths)} berths, "
            f"spec={port_master.spec_loaded}, ops={port_master.operational_loaded}"
        )
        return port_master
    except Exception as e:
        logger.warning(f"Failed to load PortMaster from Excel: {e}")
        return None


# ── Generate default configs from historical data ───────────────────────────

def build_berths_from_history(df: pd.DataFrame, port_master=None) -> List[Berth]:
    """
    Build berth master from historical port-call log.
    
    When port_master (PortMaster) is provided, physical limits come from
    the spec sheet instead of historical inference (eliminating the 10% buffer
    behavior-cloning pattern).
    """
    for col in ["berthcode", "berth", "terminalcode", "terminal", "portcode", "port"]:
        if col not in df.columns:
            df[col] = "UNKNOWN"

    berths = []
    grouped = df.groupby(
        ["portcode", "port", "terminalcode", "terminal", "berthcode", "berth"],
        dropna=False
    )

    for keys, part in grouped:
        portcode, port, terminalcode, terminal, berthcode, berth_name = keys
        bc_str = str(int(berthcode)) if pd.notna(berthcode) else str(berthcode)

        # Check if we have spec-derived data for this berth
        spec = port_master.get_berth(bc_str) if port_master else None

        if spec:
            # Use spec-derived limits (authoritative)
            # FIX (Phase 5): Missing spec fields must not inflate berth limits from historical assignments.
            max_loa = spec.get_max_loa() if spec.get_max_loa() > 0 else 400.0
            max_draft = spec.get_max_draft() if spec.get_max_draft() > 0 else 15.0
            depth = spec.get_depth() if spec.get_depth() > 0 else max_draft * 1.1
            max_beam = spec.get_max_beam() if spec.get_max_beam() > 0 else 60.0
            vessel_types = spec.allowed_vessel_types if spec.allowed_vessel_types else sorted(set(
                x.strip() for x in part.get("vesseltype", pd.Series([], dtype=str)).dropna().astype(str).tolist()
                if x.strip()
            ))
            equipment = spec.equipment_types if spec.equipment_types else ["crane", "hose", "gangway"]
            cargo_types = sorted(spec.supported_commodities) if spec.supported_commodities else []
        else:
            # FIX (Phase 5): History-derived limits are conservative and flagged because specs are absent.
            logger.warning("%s berth_code=%s", _INFERRED_BERTH_LIMIT_WARNING, bc_str)
            hist_max_loa = pd.to_numeric(part.get("loa"), errors="coerce").max()
            hist_max_draft = pd.to_numeric(part.get("adraft"), errors="coerce").max()
            hist_max_beam = pd.to_numeric(part.get("beam"), errors="coerce").max() if "beam" in part.columns else None
            factor = settings.berth_limit_inference_factor
            
            max_loa = float(hist_max_loa * factor) if pd.notna(hist_max_loa) else 400.0
            max_draft = float(hist_max_draft * factor) if pd.notna(hist_max_draft) else 15.0
            depth = float(hist_max_draft * factor) if pd.notna(hist_max_draft) else 16.0
            max_beam = float(hist_max_beam * factor) if pd.notna(hist_max_beam) and hist_max_beam > 0 else 60.0
            vessel_types = sorted(set(
                x.strip() for x in part.get("vesseltype", pd.Series([], dtype=str)).dropna().astype(str).tolist()
                if x.strip()
            ))
            equipment = ["crane", "hose", "gangway"]
            cargo_types = []

        berths.append(Berth(
            berth_code=bc_str,
            berth_name=str(berth_name) if pd.notna(berth_name) else bc_str,
            terminal_code=str(terminalcode) if pd.notna(terminalcode) else "UNK",
            terminal_name=str(terminal) if pd.notna(terminal) else str(terminalcode),
            port_code=str(portcode) if pd.notna(portcode) else "UNK",
            port_name=str(port) if pd.notna(port) else str(portcode),
            max_loa_m=max_loa,
            max_beam_m=max_beam,
            max_draft_m=max_draft,
            depth_m=depth,
            allowed_vessel_types=vessel_types,
            equipment_types=equipment,
            allowed_cargo_types=cargo_types,
        ))

    return sorted(berths, key=lambda b: (b.port_code, b.terminal_code, b.berth_code))


def generate_sample_tides(start_date: datetime, days: int = 7) -> List[TideWindow]:
    """Generate synthetic semi-diurnal tide windows."""
    tides = []
    for d in range(days * 4):  # ~4 tidal events per day
        offset_hours = d * 6.21  # semi-diurnal ~12.42h period
        t_start = start_date + timedelta(hours=offset_hours)
        is_high = (d % 2 == 0)
        height = 4.5 + 1.2 * np.sin(d * np.pi / 2) if is_high else 1.8 + 0.5 * np.sin(d * np.pi / 2)
        tides.append(TideWindow(
            start=t_start,
            end=t_start + timedelta(hours=3.0),
            height_m=round(float(height), 2),
            is_high_tide=is_high
        ))
    return tides


def generate_sample_resources(start_date: datetime, days: int = 7) -> List[ResourceSlot]:
    """Generate sample pilot/tug availability slots."""
    slots = []
    for d in range(days):
        day_start = start_date + timedelta(days=d)
        # 3 pilots available 06:00-22:00, 1 pilot overnight
        slots.append(ResourceSlot(
            resource_type="pilot", resource_id="pilot_day",
            available_from=day_start.replace(hour=6, minute=0),
            available_to=day_start.replace(hour=22, minute=0),
            capacity=3
        ))
        slots.append(ResourceSlot(
            resource_type="pilot", resource_id="pilot_night",
            available_from=day_start.replace(hour=22, minute=0),
            available_to=(day_start + timedelta(days=1)).replace(hour=6, minute=0),
            capacity=1
        ))
        # 4 tugs day, 2 night
        slots.append(ResourceSlot(
            resource_type="tug", resource_id="tug_day",
            available_from=day_start.replace(hour=6, minute=0),
            available_to=day_start.replace(hour=22, minute=0),
            capacity=4
        ))
        slots.append(ResourceSlot(
            resource_type="tug", resource_id="tug_night",
            available_from=day_start.replace(hour=22, minute=0),
            available_to=(day_start + timedelta(days=1)).replace(hour=6, minute=0),
            capacity=2
        ))
    return slots


def build_port_config_from_history(
    df: pd.DataFrame,
    planning_start: datetime,
    port_master=None,
) -> PortConfig:
    """
    Build a full port configuration from historical data.
    
    When port_master is None, auto-discovers spec sheets from sample_data/.
    Pass port_master explicitly to skip auto-discovery.
    """
    port_code = "INMAA"
    port_name = "Chennai"

    if "portcode" in df.columns and df["portcode"].notna().any():
        port_code = str(df["portcode"].mode().iloc[0])
    if "port" in df.columns and df["port"].notna().any():
        port_name = str(df["port"].mode().iloc[0])

    # Auto-load PortMaster from spec sheets if not provided
    if port_master is None:
        port_master = _load_port_master_for_config(
            port_name=port_name.lower().replace(" ", "_"),
            history_df=df,
        )

    berths = build_berths_from_history(df, port_master=port_master)
    tides = generate_sample_tides(planning_start, days=7)
    resources = generate_sample_resources(planning_start, days=7)

    return PortConfig(
        port_code=port_code,
        port_name=port_name,
        berths=berths,
        tide_windows=tides,
        resource_slots=resources,
        contract_rules=[
            ContractRule(
                contract_id="DEFAULT_CONTAINER",
                vessel_type="Container Ship",
                priority_boost=-10,
                sla_max_wait_hours=12.0,
                penalty_per_hour_delay=500.0,
            ),
            ContractRule(
                contract_id="DEFAULT_TANKER",
                vessel_type="Crude Oil Tanker",
                priority_boost=-5,
                sla_max_wait_hours=24.0,
                penalty_per_hour_delay=800.0,
            ),
        ],
        goi_override=GoIOverrideRule(enabled=False),
        levers=LeverConfig(),
    )


# ── Serialization helpers ───────────────────────────────────────────────────

def _serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.strftime("%H:%M")
    raise TypeError(f"Object of type {type(obj)} is not serializable")


def save_port_config(config: PortConfig, path: str):
    """Save port config to JSON."""
    import dataclasses
    data = dataclasses.asdict(config)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=_serialize_datetime)


def berths_to_dataframe(berths: List[Berth]) -> pd.DataFrame:
    """Convert berth list to a DataFrame for editing/display."""
    rows = []
    for b in berths:
        rows.append({
            "port_code": b.port_code,
            "port": b.port_name,
            "terminal_code": b.terminal_code,
            "terminal": b.terminal_name,
            "berth_code": b.berth_code,
            "berth": b.berth_name,
            "max_loa_m": b.max_loa_m,
            "max_beam_m": b.max_beam_m,
            "max_draft_m": b.max_draft_m,
            "depth_m": b.depth_m,
            "allowed_vessel_types": ", ".join(b.allowed_vessel_types),
            "equipment_types": ", ".join(b.equipment_types),
            "allow_24x7": b.allow_24x7,
            "work_start": b.work_start.strftime("%H:%M"),
            "work_end": b.work_end.strftime("%H:%M"),
            "shore_storage_capacity_tons": b.shore_storage_capacity_tons,
        })
    return pd.DataFrame(rows)


def dataframe_to_berths(df: pd.DataFrame) -> List[Berth]:
    """Convert DataFrame back to berth list."""
    berths = []
    for _, row in df.iterrows():
        allowed = []
        if pd.notna(row.get("allowed_vessel_types")):
            allowed = [x.strip() for x in str(row["allowed_vessel_types"]).split(",") if x.strip()]
        equip = []
        if pd.notna(row.get("equipment_types")):
            equip = [x.strip() for x in str(row["equipment_types"]).split(",") if x.strip()]

        ws = time(0, 0)
        we = time(23, 59)
        try:
            h, m = str(row.get("work_start", "00:00")).split(":")
            ws = time(int(h), int(m))
        except Exception:
            pass
        try:
            h, m = str(row.get("work_end", "23:59")).split(":")
            we = time(int(h), int(m))
        except Exception:
            pass

        berths.append(Berth(
            berth_code=str(row.get("berth_code", "")),
            berth_name=str(row.get("berth", row.get("berth_code", ""))),
            terminal_code=str(row.get("terminal_code", "")),
            terminal_name=str(row.get("terminal", row.get("terminal_code", ""))),
            port_code=str(row.get("port_code", "")),
            port_name=str(row.get("port", row.get("port_code", ""))),
            max_loa_m=float(row.get("max_loa_m", 400)),
            max_beam_m=float(row.get("max_beam_m", 60)),
            max_draft_m=float(row.get("max_draft_m", 15)),
            depth_m=float(row.get("depth_m", 16)),
            allowed_vessel_types=allowed,
            equipment_types=equip,
            allow_24x7=bool(row.get("allow_24x7", True)),
            work_start=ws,
            work_end=we,
            shore_storage_capacity_tons=float(row.get("shore_storage_capacity_tons", 50000)),
        ))
    return berths
