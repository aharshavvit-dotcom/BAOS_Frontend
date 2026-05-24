"""
Port Data Store — Layer 1
CRUD operations for port configurations, history, and models.
Each port is stored as a folder: /ports/{port_name}/
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

# Add parent dir so we can import existing modules
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PORTS_DIR = _ROOT / "ports"


def _port_dir(port_name: str) -> Path:
    return PORTS_DIR / port_name.lower().replace(" ", "_")


def list_ports() -> List[str]:
    """Return list of available port names."""
    if not PORTS_DIR.exists():
        return []
    return sorted([
        d.name for d in PORTS_DIR.iterdir()
        if d.is_dir() and (d / "port_config.json").exists()
    ])


def port_exists(port_name: str) -> bool:
    d = _port_dir(port_name)
    return d.exists() and (d / "port_config.json").exists()


def load_port_config(port_name: str) -> dict:
    """Load port configuration JSON."""
    path = _port_dir(port_name) / "port_config.json"
    if not path.exists():
        raise FileNotFoundError(f"Port config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_port_config(port_name: str, config: dict):
    """Save port configuration JSON."""
    d = _port_dir(port_name)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "port_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)


def load_history(port_name: str) -> pd.DataFrame:
    """Load enriched historical data."""
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
    """Check if ML models exist for this port."""
    d = _port_dir(port_name) / "models"
    if not d.exists():
        return False
    return (d / "berth_suitability.pkl").exists()


def get_model_info(port_name: str) -> Optional[dict]:
    """Load model training metadata if available."""
    path = _port_dir(port_name) / "models" / "metadata.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
