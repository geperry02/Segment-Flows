# Segment Flows

Pulls Kinder Morgan **TGP Segment Capacity** reports and organizes them for the
segments we run transport through.

## What it produces

A workbook (default `September Flows.xlsx`) with:

| Sheet | Contents |
|---|---|
| **Flows** | Total Scheduled Quantity per segment location, by gas day and cycle |
| **Op Cap** | Operating Capacity per segment location, by gas day and cycle |
| **Design Cap** | Design Capacity per segment location, by gas day (TD1 row and TD2 row) |
| **Log** | Anything that needed a judgment call or was missing |

Cycles: Timely, Eve (KM "EVENING"), ID1, ID2, ID3, 8AM (KM "08 AM").
Columns (zone / segment / location) are listed in `segment_flows/config.py`.

### Sign convention

Forward haul (TD1) is **positive**, backhaul (TD2) is **negative**. Each location gets
one value per cycle instead of a TD1 row and a TD2 row:

1. Only one direction posted → use it (TD1 always +, TD2 always −).
2. Scheduled flow in one direction → that direction's scheduled quantity and
   operating capacity, with its sign. (KM nets flows, so both directions should
   never be scheduled at once; if it happens the larger wins and it is logged.)
3. Zero flow in the cycle → the most common flowing direction across that day's cycles.
4. Whole day zero (or a tie) → the most common direction of the 8AM-cycle flows
   from the start of the run up to that day (ties → most recent 8AM flow).
5. No history at all → TD1 (+), logged.

Design Capacity is taken per day for both directions (TD1 +, TD2 −); a change within
the day is logged.

## Running it

```
pip install -r requirements.txt
playwright install chromium
python run.py --start 2026-09-01 --end 2026-10-01 --out "September Flows.xlsx"
```

- Raw KM exports are cached in `data/raw/` (`YYYY-MM-DD_<cycle>.xlsx`); re-runs only
  download what is missing. `--no-fetch` rebuilds the workbook from the cache.
- Running again with an existing workbook updates it in place: matching date/cycle
  rows are overwritten, new dates are appended, other sheets are left alone.
- Every download is checked against the gas day and cycle in the report header.

## Tests

```
python -m unittest -v
```

Includes a check that the 9/1/2026 Timely output matches the team template exactly.
