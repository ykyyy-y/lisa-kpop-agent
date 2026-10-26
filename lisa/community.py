"""Crowdsourced fansign cut reports ("I won with 62 albums at Withmuu on 2026-08-29").

Fans already post these on X; L.I.S.A. lets them file the same fact in a structured form so the
cut-line model learns from real reports. Because anyone can submit, every report passes a
data-poisoning guard before the model may use it:

1. range check      - 1-1,000 albums, 1-500 winners, a past date not before 2020;
2. duplicate check  - one report per artist + retailer + format + date;
3. outlier check    - a report more than 3 standard deviations from what the existing reports
                      predict (log scale, winner-adjusted) is QUARANTINED: stored, shown to no one,
                      and ignored by the model until a human reviews it;
4. rate limit       - the UI accepts at most 3 reports per browser session.
"""

from __future__ import annotations

import json
import threading
from datetime import date

from .config import RUNTIME_DIR

COMMUNITY_FILE = RUNTIME_DIR / "community_reports.json"
MAX_REPORTS_PER_SESSION = 3
OUTLIER_Z = 3.0
_lock = threading.Lock()


def _read() -> list[dict]:
    try:
        return json.loads(COMMUNITY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def accepted(artist: str | None = None) -> list[dict]:
    rows = [r for r in _read() if r["status"] == "accepted"]
    return [r for r in rows if not artist or r["artist"] == artist]


def counts() -> dict:
    rows = _read()
    return {s: sum(1 for r in rows if r["status"] == s) for s in ("accepted", "quarantined")}


def submit(artist: str, retailer_id: str, fmt: str, when: str, winners: int, cut: int) -> dict:
    """Validate and store one report. Returns {"status": accepted|quarantined|rejected, "reason": ...}."""
    from . import fansign_model  # local import: the model reads accepted reports from here

    try:
        winners, cut = int(winners), int(cut)
        day = date.fromisoformat(str(when))
    except (TypeError, ValueError):
        return {"status": "rejected", "reason": "Please give a date (YYYY-MM-DD), the number of winners and the cut as whole numbers."}
    if not (1 <= cut <= 1000):
        return {"status": "rejected", "reason": "The cut must be between 1 and 1,000 albums."}
    if not (1 <= winners <= 500):
        return {"status": "rejected", "reason": "Winners must be between 1 and 500."}
    if not (date(2020, 1, 1) <= day <= date.today()):
        return {"status": "rejected", "reason": "The fansign date must be in the past (2020 or later)."}

    base = fansign_model.history_rows(artist, retailer_id, fmt)
    if any(r["date"] == day.isoformat() for r in base):
        return {"status": "rejected", "reason": "A cut for this retailer, format and date is already on record."}

    row = {"artist": artist, "retailer_id": retailer_id, "format": fmt, "date": day.isoformat(),
           "winners": winners, "cut_albums": cut, "source": "community"}
    z = fansign_model.outlier_z(base, winners, cut)
    if z is not None and z > OUTLIER_Z:
        row.update(status="quarantined", z=round(z, 1))
        result = {"status": "quarantined", "z": round(z, 1),
                  "reason": f"This cut is {z:.1f} standard deviations away from {len(base)} earlier reports, so it is held "
                            "for review and not used by the model."}
    else:
        row.update(status="accepted", z=None if z is None else round(z, 1))
        result = {"status": "accepted", "reason": "Thanks! The model now includes your report."}
    with _lock:
        rows = _read()
        rows.append(row)
        COMMUNITY_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return result

