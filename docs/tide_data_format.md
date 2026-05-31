# Tide Data Format

The BAOS tide loader (`engines/ingestion/tide_loader.py`) can ingest real hydrographic data from a CSV file.

## Configuration

Set these in `backend/.env`:

```
USE_REAL_TIDE_DATA=True
TIDE_DATA_PATH=/path/to/tide_data.csv
```

## CSV Schema

| Column | Type | Required | Description |
|---|---|---|---|
| `datetime_utc` | ISO 8601 datetime | ✅ | Tide event timestamp in UTC |
| `height_m` | float | ✅ | Tide height in metres above chart datum |
| `is_high_tide` | boolean | ❌ | True for high tide, False for low. If omitted, inferred from `height_m > 3.0` |

## Example

```csv
datetime_utc,height_m,is_high_tide
2026-06-01T00:15:00,4.82,True
2026-06-01T06:21:00,1.23,False
2026-06-01T12:37:00,4.91,True
2026-06-01T18:44:00,1.15,False
```

## Notes

- The loader filters entries to the requested planning window (start_date to start_date + days).
- If the file is missing, empty for the date range, or unparseable, the system falls back to synthetic semi-diurnal tides and logs a warning.
- The synthetic tide generator uses a ~12.42h period with height range 1.3–5.7m, matching typical Indian Ocean semi-diurnal patterns.
- Under-keel clearance is controlled by `BERTH_DEPTH_BUFFER` in settings (default: 1.5m).
