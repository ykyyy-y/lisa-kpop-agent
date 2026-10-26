"""Loads the JSON dataset once and offers small lookup helpers used by the UI and tools."""

from __future__ import annotations

import json
from functools import lru_cache

from .config import DATA_DIR


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


def artists() -> list[dict]:
    return load("events")["artists"]


def artist_name(artist_id: str) -> str:
    return next((a["name"] for a in artists() if a["id"] == artist_id), artist_id)


def events(artist: str | None = None, category: str | None = None, city: str | None = None) -> list[dict]:
    rows = load("events")["events"]
    if artist:
        rows = [e for e in rows if e["artist"] == artist.lower()]
    if category:
        rows = [e for e in rows if e["category"] == category.lower()]
    if city:
        rows = [e for e in rows if e["city"].lower() == city.lower()]
    return rows


def event(event_id: str) -> dict | None:
    return next((e for e in load("events")["events"] if e["id"] == event_id), None)


def venue(venue_id: str) -> dict | None:
    return next((v for v in load("venues")["venues"] if v["id"] == venue_id), None)


def fansigns(artist: str | None = None) -> list[dict]:
    rows = load("fansign")["upcoming"]
    return [f for f in rows if not artist or f["artist"] == artist.lower()]


def fansign(fansign_id: str) -> dict | None:
    return next((f for f in load("fansign")["upcoming"] if f["id"] == fansign_id), None)


def vendors() -> list[dict]:
    return load("vendors")["vendors"]


def vendor_name(vendor_id: str) -> str:
    return next((v["name"] for v in vendors() if v["id"] == vendor_id), vendor_id)


def allowed_domains() -> set[str]:
    data = load("vendors")
    domains = {d for v in data["vendors"] for d in v["domains"]}
    return domains | set(data["info_domains"])


def cities(artist: str | None = None, category: str | None = None) -> list[str]:
    if category == "streaming":
        return []
    found = [] if category == "fansign" else [e["city"] for e in events(artist, category)]
    if category in (None, "fansign"):
        found += [f["city"] for f in fansigns(artist)]
    return sorted(set(found))


def releases(artist: str | None = None) -> list[dict]:
    rows = load("releases")["releases"]
    return [r for r in rows if not artist or r["artist"] == artist.lower()]


def release(release_id: str) -> dict | None:
    return next((r for r in load("releases")["releases"] if r["id"] == release_id), None)


def setlist_for(artist: str) -> dict | None:
    return next((s for s in load("setlists")["setlists"] if s["artist"] == artist), None)


def streaming_links(artist: str, query: str) -> dict:
    """Official-platform search links (always valid, always the official domain)."""
    from urllib.parse import quote, quote_plus
    q = f"{artist_name(artist)} {query}"
    return {
        "YouTube": "https://www.youtube.com/results?search_query=" + quote_plus(q + " official"),
        "Spotify": "https://open.spotify.com/search/" + quote(q),
        "Melon": "https://www.melon.com/search/total/index.htm?q=" + quote_plus(q),
        "Apple Music": "https://music.apple.com/us/search?term=" + quote_plus(q),
    }
