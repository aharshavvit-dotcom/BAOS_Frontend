"""
Port Data Store — Layer 1
CRUD operations for port configurations, history, and models.
Now database-backed, with legacy file-based fallbacks.
"""
from __future__ import annotations
import json, os, sys, logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Add parent dir so we can import existing modules
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PORTS_DIR = _ROOT / "ports"


def _port_dir(port_name: str) -> Path:
    return PORTS_DIR / port_name.lower().replace(" ", "_")


def _get_port_code(session, port_name: str) -> str:
    """Helper to resolve a port name/code string to a canonical port code."""
    from backend.db.models.baos_models import BaosPort
    # Try looking up by port_code
    port = session.query(BaosPort).filter(BaosPort.port_code.ilike(port_name)).first()
    if port:
        return port.port_code
    # Try looking up by port_name
    port = session.query(BaosPort).filter(BaosPort.port_name.ilike(f"%{port_name}%")).first()
    if port:
        return port.port_code
    # Defaults
    if port_name.lower() == "chennai":
        return "INMAA"
    return port_name.upper()


def list_ports() -> List[str]:
    """Return list of available port names."""
    try:
        from backend.db.session import get_sync_db
        from backend.db.models.baos_models import BaosPort
        session = get_sync_db()
        try:
            ports = session.query(BaosPort).filter(BaosPort.is_active == True).all()
            if ports:
                return sorted([p.port_code for p in ports])
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Failed to list ports from DB: {e}")

    # Fallback to file system
    if not PORTS_DIR.exists():
        return []
    return sorted([
        d.name for d in PORTS_DIR.iterdir()
        if d.is_dir() and (d / "port_config.json").exists()
    ])


def port_exists(port_name: str) -> bool:
    try:
        from backend.db.session import get_sync_db
        from backend.db.models.baos_models import BaosPort
        session = get_sync_db()
        try:
            port_code = _get_port_code(session, port_name)
            port = session.query(BaosPort).filter(BaosPort.port_code == port_code).first()
            if port:
                return True
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Failed to check port existence in DB: {e}")

    # Fallback to file system
    d = _port_dir(port_name)
    return d.exists() and (d / "port_config.json").exists()


def load_port_config(port_name: str) -> dict:
    """Load port configuration from database with legacy file-based fallback."""
    try:
        from backend.db.session import get_sync_db
        from backend.db.models.baos_models import BaosPort, BaosBerth, BaosPortCall, BaosAssumptionConfig
        
        session = get_sync_db()
        try:
            port_code = _get_port_code(session, port_name)
            port = session.query(BaosPort).filter(BaosPort.port_code == port_code).first()
            if not port:
                raise ValueError(f"Port {port_code} not found in DB")
                
            berths = session.query(BaosBerth).filter(BaosBerth.port_id == port.port_id, BaosBerth.is_active == True).all()
            
            berth_list = []
            for b in berths:
                vessel_types = sorted(set(c.vessel_type for c in b.capabilities if c.vessel_type))
                cargo_types = sorted(set(c.cargo_type for c in b.capabilities if c.cargo_type))
                
                berth_list.append({
                    "berth_code": b.berth_code,
                    "berth_name": b.berth_name or b.berth_code,
                    "terminal_name": b.terminal_name or "",
                    "terminal_code": b.terminal_name or "",
                    "port_code": port_code,
                    "port_name": port.port_name,
                    "max_loa_m": b.max_loa_m or 400.0,
                    "max_beam_m": b.max_beam_m or 60.0,
                    "max_draft_m": b.max_draft_m or 15.0,
                    "depth_m": b.depth_m or 16.0,
                    "allowed_vessel_types": vessel_types,
                    "allowed_cargo_types": cargo_types,
                    "allow_24x7": True,
                    "equipment": ["crane", "hose", "gangway"],
                    "data_quality_level": b.data_quality_level or "SPEC",
                })
                
            # Service time stats
            from sqlalchemy import func
            stats_q = session.query(
                BaosPortCall.berth_code_raw,
                BaosPortCall.vessel_type,
                func.count(BaosPortCall.port_call_id).label("cnt"),
                func.avg(BaosPortCall.berth_occupancy_hours).label("avg_hrs")
            ).filter(
                BaosPortCall.port_id == port.port_id,
                BaosPortCall.is_valid_for_training == True,
                BaosPortCall.berth_occupancy_hours > 0
            ).group_by(
                BaosPortCall.berth_code_raw,
                BaosPortCall.vessel_type
            ).all()
            
            service_time_stats = []
            for row in stats_q:
                service_time_stats.append({
                    "port_code": port_code,
                    "berth_code": row.berth_code_raw,
                    "vessel_type": row.vessel_type,
                    "count": row.cnt,
                    "service_hours_median": round(float(row.avg_hrs), 2) if row.avg_hrs else 12.0,
                    "service_hours_mean": round(float(row.avg_hrs), 2) if row.avg_hrs else 12.0,
                })
                
            # Assumptions
            assumptions = session.query(BaosAssumptionConfig).filter(
                BaosAssumptionConfig.port_id == port.port_id,
                BaosAssumptionConfig.is_active == True
            ).all()
            assumptions_dict = {a.assumption_key: a.assumption_value for a in assumptions}
            
            return {
                "port_name": port.port_name,
                "port_code": port.port_code,
                "planning_start": "2026-02-24T00:00:00",
                "num_berths": len(berth_list),
                "berths": berth_list,
                "service_time_stats": service_time_stats,
                "assumptions": assumptions_dict
            }
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Failed to load port config from DB, falling back to JSON file: {e}")

    # Fallback to file system
    path = _port_dir(port_name) / "port_config.json"
    if not path.exists():
        raise FileNotFoundError(f"Port config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_port_config(port_name: str, config: dict):
    """Save port configuration JSON (write-through to file system for provenance)."""
    d = _port_dir(port_name)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "port_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)


def load_history(port_name: str) -> pd.DataFrame:
    """Load enriched historical data from DB with legacy CSV fallback."""
    try:
        from backend.db.session import get_sync_db
        from backend.db.models.baos_models import BaosPort, BaosPortCall
        
        session = get_sync_db()
        try:
            port_code = _get_port_code(session, port_name)
            port = session.query(BaosPort).filter(BaosPort.port_code == port_code).first()
            if not port:
                raise ValueError(f"Port {port_code} not found in DB")
                
            port_calls = session.query(BaosPortCall).filter(
                BaosPortCall.port_id == port.port_id,
                BaosPortCall.is_valid_for_training == True
            ).all()
            
            rows = []
            for pc in port_calls:
                rows.append({
                    "port_call_id": str(pc.port_call_id),
                    "portcode": port_code,
                    "port": port.port_name,
                    "berthcode": pc.berth_code_raw,
                    "berth": pc.berth_code_raw,
                    "vesseltype": pc.vessel_type,
                    "name": pc.vessel_name,
                    "imo": pc.vessel_imo,
                    "cargo_type": pc.cargo_type,
                    "loa": pc.loa_m,
                    "beam": pc.beam_m,
                    "adraft": pc.arrival_draft_m,
                    "ddraught": pc.departure_draft_m,
                    "dwt": pc.dwt,
                    "cargo_tons": pc.cargo_tons,
                    "eosp": pc.eosp_ts.isoformat() if pc.eosp_ts else None,
                    "pob": pc.pob_ts.isoformat() if pc.pob_ts else None,
                    "all_fast": pc.all_fast_ts.isoformat() if pc.all_fast_ts else None,
                    "last_line": pc.last_line_ts.isoformat() if pc.last_line_ts else None,
                    "cosp": pc.cosp_ts.isoformat() if pc.cosp_ts else None,
                    "pilot_wait_h": pc.pilot_wait_hours,
                    "pilot_to_berth_h": pc.pilot_to_berth_hours,
                    "berth_occupancy_h": pc.berth_occupancy_hours,
                    "unberth_outbound_h": pc.unberth_outbound_hours,
                    "total_port_stay_h": pc.total_port_stay_hours,
                })
            if rows:
                return pd.DataFrame(rows)
            else:
                raise ValueError("No historical port calls found in DB")
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Failed to load history from DB, falling back to CSV file: {e}")

    # Fallback to file system
    path = _port_dir(port_name) / "history.csv"
    if not path.exists():
        raise FileNotFoundError(f"History not found: {path}")
    return pd.read_csv(path)


def save_history(port_name: str, df: pd.DataFrame):
    """Save enriched historical data as CSV."""
    d = _port_dir(port_name)
    d.mkdir(parents=True, exist_ok=True)
    df.to_csv(d / "history.csv", index=False)


def get_port_dir(port_name: str) -> Path:
    """Get or create port directory."""
    d = _port_dir(port_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_models_dir(port_name: str) -> Path:
    """Get or create models directory for a port."""
    d = _port_dir(port_name) / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_trained(port_name: str) -> bool:
    """Check if ML models exist for this port (DB-backed or local files)."""
    try:
        from backend.db.session import get_sync_db
        from backend.db.models.baos_models import BaosPort, BaosMLModelRegistry
        session = get_sync_db()
        try:
            port_code = _get_port_code(session, port_name)
            port = session.query(BaosPort).filter(BaosPort.port_code == port_code).first()
            if port:
                active_model = session.query(BaosMLModelRegistry).filter(
                    BaosMLModelRegistry.port_id == port.port_id,
                    BaosMLModelRegistry.is_active == True
                ).first()
                if active_model:
                    return True
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Failed to check trained model in DB: {e}")

    # Fallback
    d = _port_dir(port_name) / "models"
    if not d.exists():
        return False
    return (d / "berth_suitability.pkl").exists()


def get_model_info(port_name: str) -> Optional[dict]:
    """Load model training metadata if available."""
    try:
        from backend.db.session import get_sync_db
        from backend.db.models.baos_models import BaosPort, BaosMLModelRegistry
        session = get_sync_db()
        try:
            port_code = _get_port_code(session, port_name)
            port = session.query(BaosPort).filter(BaosPort.port_code == port_code).first()
            if port:
                active_model = session.query(BaosMLModelRegistry).filter(
                    BaosMLModelRegistry.port_id == port.port_id,
                    BaosMLModelRegistry.is_active == True
                ).first()
                if active_model:
                    return {
                        "model_id": str(active_model.model_id),
                        "model_name": active_model.model_name,
                        "model_version": active_model.model_version,
                        "metrics": active_model.metrics,
                        "training_rows": active_model.training_rows,
                        "created_at": active_model.created_at.isoformat() if active_model.created_at else None
                    }
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Failed to load model info from DB: {e}")

    # Fallback
    path = _port_dir(port_name) / "models" / "metadata.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
