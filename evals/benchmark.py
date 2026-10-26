"""Quality + tokenomics benchmark for L.I.S.A.  Run:  python evals/benchmark.py

Three experiments, every number measured from real gpt-6-luna calls:

1. accuracy x caching  - 13 fan questions, run once with provider prompt caching OFF
   (unique prefix on every call) and once ON (stable prefix). Same questions, same grader,
   so any quality loss from the cost cut would show up as a lower score. Both passes skip
   the Portkey response cache, so every call is a real, billed model call.
2. cache layers        - a 30-request "fan day" with realistic repeats, run four ways:
   no caching / + prompt caching / + Portkey gateway cache / + L.I.S.A. answer cache.
3. button routing      - 5 card buttons (rule-based route + the card's id, no router call)
   vs the same questions typed as free text (router LLM call).

Writes evals/results/benchmark.json.
"""

from __future__ import annotations

import json
import random
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lisa import agents, cache  # noqa: E402
from lisa.guardrails import Budget  # noqa: E402

OUT = ROOT / "evals" / "results" / "benchmark.json"

# (question, expected agents, facts that must appear - each inner list is "any of")
CASES = [
    ("When does TXT play in Seoul and is it sold out?", ["schedule"], [["2026-11-13"], ["sold out", "SOLD OUT"]]),
    ("TXT 서울 콘서트 일반예매 언제였어?", ["schedule"], [["2026-10-06"]]),
    ("Where is LISA's Las Vegas residency and what are the dates?", ["schedule"], [["Colosseum"], ["2026-11-13"]]),
    ("What setlist did BTS play on the ARIRANG tour?", ["schedule"], [["Hooligan"], ["Dynamite"]]),
    ("What songs will TXT play on the STEAL THE WIND tour?", ["schedule"], [["not", "no setlist", "아직", "yet"]]),
    ("How many albums do I need for an 80% chance at the TXT Withmuu fansign?", ["fansign"], [["65"]]),
    ("If I buy 100 albums for the BTS Ktown4u video call, what is my chance?", ["fansign"], [["1.2"]]),
    ("Does LISA have any fansign coming up?", ["fansign"], [["no ", "not", "없"]]),
    ("How do I get from Changi Airport to the BTS concert in Singapore?", ["logistics"], [["Stadium"], ["Circle", "Paya Lebar"]]),
    ("인천공항에서 TXT 콘서트장 KSPO DOME 가는 법 알려줘", ["logistics"], [["AREX"], ["Olympic Park", "올림픽공원"]]),
    ("How do I get from Kaohsiung airport to the BTS stadium?", ["logistics"], [["R17", "World Games"]]),
    ("I fly into Incheon for TXT in Seoul - which route should I take and are tickets still available?", ["schedule", "logistics"], [["AREX"], ["sold out", "SOLD OUT", "매진"]]),
    ("What's on BTS's ARIRANG album and which song is the lead single?", ["streaming"], [["SWIM"]]),
    ("TXT 컴백 스밍 리스트 1시간짜리 만들어줘", ["streaming"], [["2026-11-16", "PERFECT STORM"], ["Stick With You"]]),
    ("How much are BTS Singapore tickets and when did the general sale open?", ["schedule"], [["148"], ["2026-06-05"]]),
    ("What's a good recipe for kimchi stew?", [], [["LISA, BTS and TXT"]]),
]

BUTTONS = [
    ("ticketing", {"artist": "txt", "event_id": "txt-seoul-2026"}),
    ("setlist", {"artist": "bts", "event_id": "bts-singapore-2026"}),
    ("fansign", {"artist": "txt", "fansign_id": "txt-fs-withmuu-1205", "albums": 50}),
    ("logistics", {"artist": "bts", "event_id": "bts-bangkok-2026"}),
    ("playlist", {"artist": "txt", "release_id": "txt-perfect-storm", "minutes": 60}),
]


def grade(result: dict, expected_agents: list, facts: list) -> dict:
    text = result["text"]
    hits = [any(f.lower() in text.lower() for f in group) for group in facts]
    routed_ok = sorted(result["agents"]) == sorted(expected_agents)
    return {"routing_ok": routed_ok, "facts_ok": all(hits), "facts_hit": sum(hits), "facts_total": len(hits)}


def slim(r: dict) -> dict:
    keys = ("agents", "cache_hit", "model_calls", "gateway_hits", "tool_calls", "tokens", "cost", "seconds", "guards")
    return {k: r.get(k) for k in keys} | {"text": r["text"]}


def configure(salt: bool = True, per_call_nonce: bool = False, force_refresh: bool = True) -> None:
    """salt: a fresh per-run prefix so this run cannot reuse cache entries from earlier runs."""
    agents.PREFIX_NONCE = f"[run {uuid.uuid4()}]\n" if salt else ""
    agents.PER_CALL_NONCE = per_call_nonce
    agents.FORCE_REFRESH = force_refresh


def run_accuracy(prompt_cache: bool) -> list[dict]:
    rows = []
    configure(per_call_nonce=not prompt_cache, force_refresh=True)
    for q, exp, facts in CASES:
        r = agents.answer(q, {}, use_cache=False, budget=Budget(session_cap=10, daily_cap=50))
        g = grade(r, exp, facts)
        rows.append({"question": q, "expected_agents": exp, **g, **slim(r)})
        print(f"  [{'cache' if prompt_cache else 'nocache'}] routing={g['routing_ok']!s:5} facts={g['facts_hit']}/{g['facts_total']} "
              f"${r['cost']:.5f} in={r['tokens']['input']} cached={r['tokens']['cached_input']} out={r['tokens']['output']} :: {q[:50]}")
    return rows


def run_fan_day(label: str, use_answer_cache: bool, seed: int = 7, **cfg) -> dict:
    """30 requests drawn from the first 12 questions with repeats (popular questions get asked more)."""
    rng = random.Random(seed)
    pool = [c[0] for c in CASES[:12]]
    weights = [6, 3, 4, 3, 2, 5, 2, 1, 3, 6, 2, 4]  # e.g. KSPO route + TXT dates are asked most
    day = rng.choices(pool, weights=weights, k=30)
    cache.clear()
    configure(**cfg)
    total, hits, calls, gw, secs = 0.0, 0, 0, 0, 0.0
    for q in day:
        r = agents.answer(q, {}, use_cache=use_answer_cache, budget=Budget(session_cap=10, daily_cap=50))
        total += r["cost"]
        hits += r["cache_hit"]
        calls += r["model_calls"]
        gw += r.get("gateway_hits", 0)
        secs += r["seconds"]
    print(f"  fan day [{label}]: ${total:.5f}, answer-cache hits {hits}/30, model calls {calls} (gateway hits {gw}), {secs:.0f}s")
    return {"label": label, "answer_cache": use_answer_cache, "requests": 30, "unique_questions": len(set(day)), "cost": round(total, 6),
            "cache_hits": hits, "model_calls": calls, "gateway_hits": gw, "billed_calls": calls - gw, "total_seconds": round(secs, 1)}


def run_buttons() -> list[dict]:
    rows = []
    configure(force_refresh=True)
    for action, sel in BUTTONS:
        btn = agents.answer("", sel, action=action, use_cache=False, budget=Budget(session_cap=10, daily_cap=50))
        typed = agents.answer(btn["message"], {}, use_cache=False, budget=Budget(session_cap=10, daily_cap=50))
        router = [t for t in typed["trace"] if t["kind"] == "model" and t["agent"] == "router"]
        rows.append({"action": action, "button_cost": btn["cost"], "button_calls": btn["model_calls"], "button_seconds": btn["seconds"],
                     "typed_cost": typed["cost"], "typed_calls": typed["model_calls"], "typed_seconds": typed["seconds"],
                     "router_tokens": router[0]["tokens"] if router else None, "router_cost": router[0]["cost"] if router else 0})
        print(f"  button {action}: ${btn['cost']:.5f} ({btn['model_calls']} calls) vs typed ${typed['cost']:.5f} ({typed['model_calls']} calls)")
    return rows


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    tok = {k: round(sum(r["tokens"][k] for r in rows) / n, 1) for k in ("input", "cached_input", "cache_write", "output", "reasoning")}
    return {"questions": n, "routing_accuracy": round(sum(r["routing_ok"] for r in rows) / n, 3),
            "fact_accuracy": round(sum(r["facts_ok"] for r in rows) / n, 3),
            "avg_tokens": tok, "avg_cost": round(sum(r["cost"] for r in rows) / n, 7),
            "avg_seconds": round(sum(r["seconds"] for r in rows) / n, 2),
            "avg_model_calls": round(sum(r["model_calls"] for r in rows) / n, 2)}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("1) accuracy, prompt caching OFF")
    nocache = run_accuracy(prompt_cache=False)
    print("1) accuracy, prompt caching ON")
    withcache = run_accuracy(prompt_cache=True)
    print("2) fan day, four cache layers")
    days = [
        run_fan_day("no caching", False, per_call_nonce=True, force_refresh=True),
        run_fan_day("+ prompt caching", False, force_refresh=True),
        run_fan_day("+ Portkey gateway cache", False, force_refresh=False),
        run_fan_day("+ L.I.S.A. answer cache (production)", True, force_refresh=False),
    ]
    print("3) buttons vs typed")
    buttons = run_buttons()
    result = {
        "model": "gpt-6-luna",
        "run_at": time.strftime("%Y-%m-%d %H:%M"),
        "prompt_cache_off": {"summary": summarize(nocache), "rows": nocache},
        "prompt_cache_on": {"summary": summarize(withcache), "rows": withcache},
        "fan_day": days,
        "buttons_vs_typed": buttons,
        "wall_seconds": round(time.time() - t0, 1),
    }
    configure(salt=False, force_refresh=False)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k]["summary"] for k in ("prompt_cache_off", "prompt_cache_on")}, indent=2))
    print("saved", OUT)


if __name__ == "__main__":
    main()
