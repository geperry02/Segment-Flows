"""Pull TGP Segment Capacity from Kinder Morgan and build the segment-flow workbook.

    python run.py --start 2026-09-01 --end 2026-10-01 --out "September Flows.xlsx"

Raw KM reports are cached in data/raw/ (one file per gas day + cycle), so a re-run
only downloads what is missing. Use --no-fetch to rebuild the workbook from the cache.
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

from segment_flows.config import CYCLES
from segment_flows.report import parse_report
from segment_flows.transform import build
from segment_flows.workbook import write_workbook

RAW_DIR = Path(__file__).parent / "data" / "raw"


def raw_path(day, label):
    return RAW_DIR / f"{day:%Y-%m-%d}_{label}.xlsx"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=date.fromisoformat, required=True, help="first gas day, YYYY-MM-DD")
    p.add_argument("--end", type=date.fromisoformat, required=True, help="last gas day, YYYY-MM-DD")
    p.add_argument("--out", default="September Flows.xlsx", help="workbook to create or update")
    p.add_argument("--no-fetch", action="store_true", help="only use reports already in data/raw")
    p.add_argument("--browser-path", help="Chromium executable (default: Playwright's own)")
    args = p.parse_args()

    dates = [args.start + timedelta(n) for n in range((args.end - args.start).days + 1)]
    todo = [(d, label, km) for d in dates for label, km in CYCLES if not raw_path(d, label).exists()]

    failed = []
    if todo and not args.no_fetch:
        from segment_flows.fetch import KMFetcher
        print(f"Downloading {len(todo)} report(s) from Kinder Morgan...")
        with KMFetcher(browser_path=args.browser_path) as km:
            for n, (d, label, km_cycle) in enumerate(todo, 1):
                print(f"  [{n}/{len(todo)}] {d:%m/%d/%Y} {label}")
                try:
                    km.download_with_retry(d, km_cycle, raw_path(d, label))
                except Exception as exc:  # noqa: BLE001 - keep going, report at the end
                    print(f"    FAILED: {exc}")
                    failed.append((d, label, str(exc)))

    reports = {}
    for d in dates:
        for label, _ in CYCLES:
            if raw_path(d, label).exists():
                reports[(d, label)] = parse_report(raw_path(d, label))

    flows, opcap, design, notes = build(reports, dates)
    write_workbook(args.out, dates, flows, opcap, design, notes)
    print(f"Wrote {args.out}: {len(reports)} reports, {len(notes)} log note(s).")
    for d, label, err in failed:
        print(f"  not downloaded: {d:%m/%d/%Y} {label} ({err})")


if __name__ == "__main__":
    main()
