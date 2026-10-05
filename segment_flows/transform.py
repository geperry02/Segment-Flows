"""Collapse TD1/TD2 rows into one signed value per location.

Sign convention: forward haul (TD1) is positive, backhaul (TD2) is negative.
Operating capacity takes the sign and value of the direction gas is flowing.

Direction for a location in a cycle:
  1. Only one direction posted -> that direction.
  2. Scheduled flow in one direction -> that direction.
     (Flow in both directions should not happen; the larger wins and it is logged.)
  3. Zero flow -> most common flowing direction across that day's cycles.
  4. Whole day zero (or a tie) -> most common direction of the 8AM-cycle flows
     from the start of the run up to that day; ties go to the most recent 8AM flow.
  5. No history at all -> TD1, logged.
"""

from collections import Counter, defaultdict

from .config import CYCLE_LABELS, HISTORY_CYCLE, SEGMENTS, loc_key

SIGN = {"TD1": 1, "TD2": -1}


def flow_direction(dirs):
    """Return (direction or None, reason) for one location in one cycle."""
    td1, td2 = dirs.get("TD1"), dirs.get("TD2")
    if td1 and not td2:
        return "TD1", "only"
    if td2 and not td1:
        return "TD2", "only"
    if td1.scheduled and td2.scheduled:
        return ("TD1" if td1.scheduled >= td2.scheduled else "TD2"), "both"
    if td1.scheduled:
        return "TD1", "flow"
    if td2.scheduled:
        return "TD2", "flow"
    return None, "zero"


def _majority(directions):
    counts = Counter(directions).most_common()
    if not counts or (len(counts) > 1 and counts[0][1] == counts[1][1]):
        return None
    return counts[0][0]


def build(reports, dates):
    """reports: {(date, cycle label): Report}. Returns (flows, opcap, design, notes).

    flows/opcap: {(date, cycle label): {key: int}}
    design:      {date: {key: (td1 design, td2 design)}}  (None where not posted)
    notes:       [(date, cycle label, segment, location, message)]
    """
    keys = [loc_key(seg, name) for _, seg, name in SEGMENTS]
    flows, opcap, design, notes = defaultdict(dict), defaultdict(dict), {}, []
    history = defaultdict(list)  # key -> 8AM flowing directions, chronological

    for day in dates:
        day_reports = {c: reports[(day, c)] for c in CYCLE_LABELS if (day, c) in reports}
        for c in CYCLE_LABELS:
            if c not in day_reports:
                notes.append((day, c, "", "", "Cycle not available from KM; left blank"))

        design[day] = {}
        for key in keys:
            seg, name = key
            per_cycle = {}
            for c, rep in day_reports.items():
                dirs = rep.locations.get(key)
                if not dirs:
                    notes.append((day, c, seg, name, "Location not in KM report; left blank"))
                    continue
                direction, reason = flow_direction(dirs)
                if reason == "both":
                    notes.append((day, c, seg, name,
                                  f"Scheduled in both directions (TD1 {dirs['TD1'].scheduled:,}, "
                                  f"TD2 {dirs['TD2'].scheduled:,}); used {direction}"))
                per_cycle[c] = (dirs, direction, reason)

            day_flowing = [d for _, d, r in per_cycle.values() if r in ("flow", "both")]
            for c, (dirs, direction, reason) in per_cycle.items():
                if direction is None:
                    direction = _majority(day_flowing)
                if direction is None:
                    direction = _majority(history[key])
                    if direction is None and history[key]:
                        direction = history[key][-1]
                    if direction is None:
                        direction = "TD1"
                        notes.append((day, c, seg, name,
                                      "Zero flow with no 8AM history; defaulted to TD1 (+)"))
                row = dirs[direction]
                flows[(day, c)][key] = SIGN[direction] * row.scheduled
                opcap[(day, c)][key] = SIGN[direction] * row.operating

            if HISTORY_CYCLE in per_cycle and per_cycle[HISTORY_CYCLE][2] in ("flow", "both"):
                history[key].append(per_cycle[HISTORY_CYCLE][1])

            # Design capacity by day: first available cycle; flag if it changes within the day.
            seen = {}
            for c, (dirs, _, _) in per_cycle.items():
                value = tuple(dirs[d].design if d in dirs else None for d in ("TD1", "TD2"))
                seen.setdefault(value, c)
            if seen:
                design[day][key] = next(iter(seen))
                if len(seen) > 1:
                    notes.append((day, "", seg, name,
                                  f"Design capacity changed during the day: {seen}; used first"))
    return flows, opcap, design, notes
