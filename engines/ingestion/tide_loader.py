"""
Tide Loader — loads real or synthetic tide data.

FIX (Phase 5.2): Centralizes tide data loading with a warning when
synthetic data is used (the default until real hydrographic feeds are available).

Real tide data format:
    See docs/tide_data_format.md for the expected CSV schema.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import numpy as np

from backend.config.settings import settings

logger = logging.getLogger(__name__)

_SYNTHETIC_WARNING_LOGGED = False


def load_tides(
    start_date: datetime,
    days: int = 7,
    tide_data_path: Optional[str] = None,
) -> List:
    """
    Load tide windows.

    If USE_REAL_TIDE_DATA is True and a valid TIDE_DATA_PATH is configured,
    loads from CSV. Otherwise, generates synthetic semi-diurnal tides and
    logs a warning (once per process).
    """
    global _SYNTHETIC_WARNING_LOGGED

    path = tide_data_path or settings.TIDE_DATA_PATH

    if settings.USE_REAL_TIDE_DATA and path:
        real_path = Path(path)
        if real_path.exists():
            return _load_real_tides(real_path, start_date, days)
        else:
            logger.error(
                "USE_REAL_TIDE_DATA=True but file not found: %s. "
                "Falling back to synthetic tides.", path
            )

    # Synthetic fallback
    if not _SYNTHETIC_WARNING_LOGGED:
        logger.warning(
            "Using SYNTHETIC tide data. Under-keel clearance calculations "
            "are approximate. Set USE_REAL_TIDE_DATA=True and provide "
            "TIDE_DATA_PATH to use real hydrographic data."
        )
        _SYNTHETIC_WARNING_LOGGED = True

    return _generate_synthetic_tides(start_date, days)


def _generate_synthetic_tides(start_date: datetime, days: int = 7) -> List:
    """Generate synthetic semi-diurnal tide windows."""
    from backend.db.models.domain import TideWindow

    tides = []
    for d in range(days * 4):  # ~4 tidal events per day
        offset_hours = d * 6.21  # semi-diurnal ~12.42h period
        t_start = start_date + timedelta(hours=offset_hours)
        is_high = (d % 2 == 0)
        height = (
            4.5 + 1.2 * np.sin(d * np.pi / 2) if is_high
            else 1.8 + 0.5 * np.sin(d * np.pi / 2)
        )
        tides.append(TideWindow(
            start=t_start,
            end=t_start + timedelta(hours=3.0),
            height_m=round(float(height), 2),
            is_high_tide=is_high,
        ))
    return tides


def _load_real_tides(
    path: Path,
    start_date: datetime,
    days: int,
) -> List:
    """
    Load real tide data from CSV.

    Expected columns: datetime_utc, height_m, is_high_tide
    See docs/tide_data_format.md for details.
    """
    import pandas as pd
    from backend.db.models.domain import TideWindow

    try:
        df = pd.read_csv(path, parse_dates=["datetime_utc"])
        end_date = start_date + timedelta(days=days)
        mask = (df["datetime_utc"] >= start_date) & (df["datetime_utc"] <= end_date)
        df = df.loc[mask].sort_values("datetime_utc").reset_index(drop=True)

        if df.empty:
            logger.warning(
                "Real tide data file has no entries for %s to %s. "
                "Falling back to synthetic.", start_date, end_date
            )
            return _generate_synthetic_tides(start_date, days)

        tides = []
        for _, row in df.iterrows():
            t_start = row["datetime_utc"].to_pydatetime()
            tides.append(TideWindow(
                start=t_start,
                end=t_start + timedelta(hours=3.0),
                height_m=round(float(row["height_m"]), 2),
                is_high_tide=bool(row.get("is_high_tide", row["height_m"] > 3.0)),
            ))

        logger.info("Loaded %d real tide entries from %s", len(tides), path)
        return tides

    except Exception as e:
        logger.error("Failed to parse tide CSV %s: %s. Falling back to synthetic.", path, e)
        return _generate_synthetic_tides(start_date, days)
