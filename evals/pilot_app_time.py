"""Measures how long L.I.S.A. itself takes to answer the four pilot tasks (docs/PILOT_TEST.md).

    python evals/pilot_app_time.py   -> evals/results/pilot_app_time.json

This is the app's response time for the same questions the pilot participant answered by hand -
real, billed model calls (Portkey response cache bypassed). It is NOT a participant's time: reading
and clicking are not included, and the report labels it that way.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lisa import agents  # noqa: E402
from lisa.guardrails import Budget  # noqa: E402

TASKS = {
    "A": "BTS plays Singapore in December. What are the dates, when did tickets go on sale, what is the price range, and what is the official ticket site?",
    "B": "BTS has a video-call fansign at Ktown4u. How many albums would I need for a good chance, and what would it cost?",
    "C": "I land at Changi Airport. How do I get to the BTS stadium, and where can I leave a suitcase?",
    "D": "TXT's next album comes out soon. When is it, and what should a one-hour streaming playlist look like?",
}

if __name__ == "__main__":
    agents.FORCE_REFRESH = True
    rows = []
    for task, q in TASKS.items():
        r = agents.answer(q, {}, use_cache=False, budget=Budget(session_cap=10, daily_cap=50))
        rows.append({"task": task, "question": q, "agents": r["agents"], "seconds": r["seconds"], "model_calls": r["model_calls"],
                     "cost": r["cost"], "answer": r["text"]})
        print(f"{task}: {r['seconds']} s, {r['agents']}, ${r['cost']:.5f}")
    out = {"total_seconds": round(sum(r["seconds"] for r in rows), 1), "total_cost": round(sum(r["cost"] for r in rows), 6), "rows": rows}
    (ROOT / "evals" / "results" / "pilot_app_time.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("total", out["total_seconds"], "s", out["total_cost"])
