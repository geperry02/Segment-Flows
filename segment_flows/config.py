"""Static configuration: cycles to pull and the segment columns we report on."""

KM_URL = "https://pipeline2.kindermorgan.com/Capacity/OpAvailSegment.aspx?code=TGP"

# (label used in our workbook, label in KM's Cycle dropdown / report header)
CYCLES = [
    ("Timely", "TIMELY"),
    ("Eve", "EVENING"),
    ("ID1", "INTRADAY 1"),
    ("ID2", "INTRADAY 2"),
    ("ID3", "INTRADAY 3"),
    ("8AM", "08 AM"),
]
CYCLE_LABELS = [label for label, _ in CYCLES]
KM_CYCLE = dict(CYCLES)
HISTORY_CYCLE = "8AM"  # cycle whose month-to-date flows break an all-zero day

# Columns of the Flows / Op Cap sheets, left to right: (zone, segment, location name).
# A column is identified by segment + location name together (segment 534 appears twice).
SEGMENTS = [
    ("04", 394, "STA 319 EAST"),
    ("04", 319, "STA 319"),
    ("04", 318, "MLV 318"),
    ("04", 317, "STA 317"),
    ("04", 316, "MLV 316"),
    ("04", 315, "STA 315"),
    ("04", 314, "MLV 314 EAST"),
    ("04", 313, "MLV 314 WEST"),
    ("04", 307, "STA 307"),
    ("04", 300, "STA 219 EAST"),
    ("04", 217, "MLV 217"),
    ("04", 216, "MLV 216"),
    ("04", 214, "STA 214"),
    ("04", 212, "MLV 212"),
    ("04", 209, "STA 209"),
    ("04", 204, "STA 204"),
    ("04", 200, "STA 200"),
    ("02", 110, "STA 110 NORTH"),
    ("02", 187, "STA 110 SOUTH"),
    ("01", 860, "STA 860 NORTH"),
    ("01", 548, "STA 860 SOUTH 500 LINE"),
    ("01", 542, "MLV 548"),
    ("01", 539, "STA 542"),
    ("01", 534, "MLV 539"),
    ("01", 534, "STA 534"),
    ("01", 530, "STA 534 SOUTH OF POOL"),
    ("L", 527, "STA 527"),
    ("L", 524, "MLV 524"),
    ("L", 516, "STA 523 MUSKRAT LINE"),
]


def loc_key(segment, name):
    """Normalized (segment, location name) key used to match report rows to columns."""
    return int(segment), " ".join(str(name).split()).upper()
