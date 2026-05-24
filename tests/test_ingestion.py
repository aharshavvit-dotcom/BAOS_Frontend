"""
Tests for Data Ingestion Layer.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "backend"))
sys.path.insert(0, str(_ROOT))

from data_ingestion.transformers import safe_float, safe_datetime, compute_derived_durations
from data_ingestion.schema_mapping import normalize_columns, resolve_column
from data_ingestion.validators import validate_port_call_row


def test_safe_float():
    assert safe_float(12.3) == 12.3
    assert safe_float("12.3") == 12.3
    assert safe_float("no restrictions") is None
    assert safe_float("nan") is None
    assert safe_float(None) is None
    assert safe_float("abc", default=999.0) == 999.0


def test_safe_datetime():
    dt = datetime(2026, 5, 24, 12, 0, 0)
    assert safe_datetime(dt) == dt
    assert safe_datetime("2026-05-24T12:00:00") == dt
    assert safe_datetime("invalid") is None
    assert safe_datetime(None) is None


def test_compute_derived_durations():
    base = datetime(2026, 5, 24, 12, 0, 0)
    row = {
        "eosp_ts": base,
        "pob_ts": base + timedelta(hours=2),
        "all_fast_ts": base + timedelta(hours=3),
        "last_line_ts": base + timedelta(hours=10),
        "cosp_ts": base + timedelta(hours=12),
    }
    durations = compute_derived_durations(row)
    assert durations["pilot_wait_hours"] == 2.0
    assert durations["pilot_to_berth_hours"] == 1.0
    assert durations["berth_occupancy_hours"] == 7.0
    assert durations["unberth_outbound_hours"] == 2.0
    assert durations["total_port_stay_hours"] == 12.0


def test_column_alias_mapping():
    cols = ["Berth Code", "Vessel Name", "IMO", "LOA", "Draft"]
    mapping = normalize_columns(cols)
    assert mapping["berth_code"] == "Berth Code"
    assert mapping["vessel_name"] == "Vessel Name"
    assert mapping["vessel_imo"] == "IMO"
    assert mapping["loa_m"] == "LOA"
    assert mapping["arrival_draft_m"] == "Draft"


def test_validate_port_call_row():
    # Valid row
    valid_row = {
        "loa_m": 200,
        "beam_m": 32,
        "arrival_draft_m": 12,
        "eosp_ts": datetime(2026, 5, 24, 12, 0),
        "pob_ts": datetime(2026, 5, 24, 13, 0),
        "all_fast_ts": datetime(2026, 5, 24, 14, 0),
        "last_line_ts": datetime(2026, 5, 24, 20, 0),
        "cosp_ts": datetime(2026, 5, 24, 22, 0),
        "pilot_wait_hours": 1.0,
        "pilot_to_berth_hours": 1.0,
        "berth_occupancy_hours": 6.0,
        "unberth_outbound_hours": 2.0,
        "total_port_stay_hours": 10.0,
    }
    res = validate_port_call_row(valid_row)
    assert res.is_valid_for_training is True
    assert res.status == "VALID"

    # Outlier row
    outlier_row = valid_row.copy()
    outlier_row["berth_occupancy_hours"] = 800.0  # Exceeds max 720h limit
    res = validate_port_call_row(outlier_row)
    assert res.is_valid_for_training is False
    assert res.status == "OUTLIER"

    # Invalid timestamp sequence row
    invalid_seq_row = valid_row.copy()
    invalid_seq_row["all_fast_ts"] = datetime(2026, 5, 24, 10, 0)  # ALL_FAST < POB
    res = validate_port_call_row(invalid_seq_row)
    assert res.is_valid_for_training is False
    assert res.status == "INVALID"


ALL_TESTS = [
    ("safe_float", test_safe_float),
    ("safe_datetime", test_safe_datetime),
    ("compute_derived_durations", test_compute_derived_durations),
    ("column_alias_mapping", test_column_alias_mapping),
    ("validate_port_call_row", test_validate_port_call_row),
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in ALL_TESTS:
        try:
            fn()
            passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {name} -- {e}")
            import traceback
            traceback.print_exc()

    print(f"\nIngestion Tests: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    sys.exit(1 if failed > 0 else 0)
