"""
Data Ingestion — Layer 1
Takes raw port-call Excel data + spec sheets, enriches them,
builds canonical PortMaster, and saves everything.

Data Source Priority:
  1. Berth_configurations.xlsx (spec) -> Physical specs
  2. Operational_Capability_of_Berth.xlsx -> Cargo/operation capability
  3. Port call logs -> Historical enrichment + service time stats
"""
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, time

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.db.repositories.port_store import save_port_config, save_history, get_port_dir
from engines.ingestion.spec_ingest import build_port_master, save_port_master_config
from engines.learning.data_prep import prepare_portcall_log, default_service_time_model

logger = logging.getLogger(__name__)


def ingest_port_data(
    port_name: str,
    df_raw: pd.DataFrame,
    berth_config_path: str | Path | None = None,
    operational_capability_path: str | Path | None = None,
) -> dict:
    """
    Full ingestion pipeline:
    1. Enrich raw data (timestamps, KPIs, port_call_id)
    2. Build PortMaster from spec + operational + historical data
    3. Save history.csv + port_config.json
    Returns summary dict.
    """
    # Enrich historical data
    df_enriched = prepare_portcall_log(df_raw)

    # Service time model stats
    svc_model = default_service_time_model(df_enriched)

    # Save history
    save_history(port_name, df_enriched)

    # Build PortMaster from all sources
    port_master = build_port_master(
        port_name=port_name,
        port_code=str(df_enriched.get("portcode", pd.Series([3779])).iloc[0]),
        berth_config_path=berth_config_path,
        operational_capability_path=operational_capability_path,
        history_df=df_enriched,
    )

    # Generate backward-compatible port_config.json + new fields
    port_dir = get_port_dir(port_name)
    config_path = port_dir / "port_config.json"
    
    # Build config dict with backward compatibility
    config_dict = {
        "port_name": port_name,
        "port_code": port_master.port_code,
        "planning_start": datetime.combine(datetime.today().date(), time(0, 0)).isoformat(),
        "num_berths": len(port_master.berths),
        "data_quality": port_master.data_quality.value,
        "quality_score": round(port_master.quality_score, 1),
        "spec_loaded": port_master.spec_loaded,
        "operational_loaded": port_master.operational_loaded,
        "berths": [
            b.to_legacy_dict() for b in sorted(
                port_master.berths.values(),
                key=lambda x: x.berth_code,
            )
        ],
        "service_time_stats": svc_model.to_dict(orient="records") if svc_model is not None else [],
    }
    save_port_config(port_name, config_dict)

    # Save service time model
    if svc_model is not None:
        svc_model.to_csv(port_dir / "service_time_model.csv", index=False)

    # Save ingestion log
    ingestion_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "port_name": port_name,
        "records_ingested": len(df_enriched),
        "berths_discovered": len(port_master.berths),
        "spec_file": str(berth_config_path) if berth_config_path else None,
        "operational_file": str(operational_capability_path) if operational_capability_path else None,
        "quality_summary": port_master.summary(),
    }
    with open(port_dir / "ingestion_log.json", "w", encoding="utf-8") as f:
        json.dump(ingestion_log, f, indent=2, default=str)

    return {
        "port_name": port_name,
        "records_ingested": len(df_enriched),
        "berths_discovered": len(port_master.berths),
        "service_time_entries": len(svc_model) if svc_model is not None else 0,
        "data_quality": port_master.data_quality.value,
        "quality_score": round(port_master.quality_score, 1),
    }


def ingest_from_excel(
    port_name: str,
    excel_path: str,
    berth_config_path: str | None = None,
    operational_capability_path: str | None = None,
) -> dict:
    """Convenience: ingest from Excel file path with optional spec files."""
    df_raw = pd.read_excel(excel_path)
    return ingest_port_data(
        port_name, df_raw,
        berth_config_path=berth_config_path,
        operational_capability_path=operational_capability_path,
    )
