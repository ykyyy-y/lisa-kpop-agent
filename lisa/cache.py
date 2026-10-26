"""Answer cache: fans ask the same questions over and over ("how do I get to KSPO Dome
from Incheon?"). A repeat question with the same selections is answered from disk for
$0 and ~0 s. Entries expire after CACHE_TTL_SECONDS so ticketing status stays fresh.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time

from .config import CACHE_TTL_SECONDS, RUNTIME_DIR

CACHE_FILE = RUNTIME_DIR / "answer_cache.json"
_lock = threading.Lock()


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s가-힣]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def key(message: str, selections: dict) -> str:
    sel = {k: selections.get(k) for k in sorted(selections)}
    raw = normalize(message) + "|" + json.dumps(sel, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _read() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get(k: str) -> dict | None:
    with _lock:
        entry = _read().get(k)
    if entry and time.time() - entry["saved_at"] < CACHE_TTL_SECONDS:
        return entry["result"]
    return None


def put(k: str, result: dict) -> None:
    with _lock:
        store = _read()
        store[k] = {"saved_at": time.time(), "result": result}
        CACHE_FILE.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")


def clear() -> None:
    with _lock:
        CACHE_FILE.unlink(missing_ok=True)
