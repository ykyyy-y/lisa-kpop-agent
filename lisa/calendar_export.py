"""'Add to calendar' (.ics) for any card: concert dates + sale times, fansign entry window, album release.

Missed presales and entry windows are the most common fan failure, so every card can drop its dates
into the fan's phone calendar. Pure Python, no API call.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from . import data


def _day(d: str) -> str:
    return d.replace("-", "")


def _event(uid: str, start: str, summary: str, description: str, end: str | None = None) -> list[str]:
    end_day = (date.fromisoformat(end or start) + timedelta(days=1)).isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    clean = description.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
    return ["BEGIN:VEVENT", f"UID:{uid}@lisa", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{_day(start)}",
            f"DTEND;VALUE=DATE:{_day(end_day)}", f"SUMMARY:{summary}", f"DESCRIPTION:{clean}", "END:VEVENT"]


def build(ref: str) -> tuple[str, str] | None:
    """(filename, ics text) for an event, fansign or release id."""
    lines: list[str] = []
    if e := data.event(ref):
        v = data.venue(e["venue_id"]) or {}
        t = e["ticketing"]
        info = f"{v.get('name', '')}\nTickets: {t['status']}\nOfficial: {t['url']}"
        for i, d in enumerate(e["dates"]):
            lines += _event(f"{ref}-{i}", d, f"🎤 {e['title']}", info)
        name = f"{ref}.ics"
    elif f := data.fansign(ref):
        start = f["apply_window"][:10]
        end = f["apply_window"].split(" to ")[-1][:10]
        lines += _event(f"{ref}-apply", start, f"✍️ Fansign entry opens: {f['title']}",
                        f"Entry window {f['apply_window']}\nOfficial: {f['url']}", end)
        lines += _event(f"{ref}-day", f["event_date"], f"✍️ {f['title']}", f"{f['city']} · {f['winners']} winners")
        name = f"{ref}.ics"
    elif r := data.release(ref):
        links = data.streaming_links(r["artist"], r["title"])
        lines += _event(f"{ref}-release", r["release_date"], f"🎧 {data.artist_name(r['artist'])} '{r['title']}' release",
                        "Stream: " + " | ".join(f"{k} {v}" for k, v in links.items()))
        name = f"{ref}.ics"
    else:
        return None
    body = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//L.I.S.A.//Live Idol Schedule & Analytics//EN", *lines, "END:VCALENDAR"]
    return name, "\r\n".join(body) + "\r\n"
