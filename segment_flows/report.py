"""Parse a KM Segment Capacity Excel export (OpAvailExportedData.xlsx)."""

from dataclasses import dataclass
from datetime import datetime

import openpyxl

from .config import loc_key


@dataclass
class Row:
    design: int
    operating: int
    scheduled: int


@dataclass
class Report:
    gas_day: datetime
    cycle: str  # KM cycle label, e.g. "TIMELY"
    posted: str
    # {(segment, location name): {"TD1": Row, "TD2": Row}}
    locations: dict


def _num(value):
    if value is None or str(value).strip() == "":
        return 0
    return int(str(value).replace(",", "").strip())


def parse_report(path):
    ws = openpyxl.load_workbook(path, read_only=True).active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]

    header = rows[0]
    info = dict(zip(header, rows[1]))
    gas_day = datetime.strptime(str(info["Eff Gas Day/Eff Time"]).split()[0], "%m/%d/%Y")
    cycle = str(info["CycleDesc"]).strip()

    start = next(i for i, r in enumerate(rows) if r and r[0] == "Loc (Segment)")
    cols = {name: i for i, name in enumerate(rows[start]) if name}
    locations = {}
    for r in rows[start + 1:]:
        if r[0] is None or str(r[0]).startswith("Row Count"):
            break  # end of the table; footnotes follow
        key = loc_key(r[cols["Loc (Segment)"]], r[cols["Loc Name (Segment)"]])
        direction = str(r[cols["Flow Ind"]]).strip()
        dirs = locations.setdefault(key, {})
        if direction in dirs:
            raise ValueError(f"{path}: duplicate {direction} row for {key}")
        dirs[direction] = Row(
            design=_num(r[cols["Design Capacity"]]),
            operating=_num(r[cols["Operating Capacity"]]),
            scheduled=_num(r[cols["Total Scheduled Quantity"]]),
        )
    return Report(gas_day, cycle, str(info.get("Post Date/Post Time", "")), locations)
