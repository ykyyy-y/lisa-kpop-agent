"""Runs one multi-agent request and saves its full trace (for the report's traced run).

    python evals/trace_example.py   -> evals/results/trace_example.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lisa import agents  # noqa: E402
from lisa.guardrails import Budget  # noqa: E402

QUESTION = "I fly into Changi for BTS in Singapore - how do I get to the stadium, and how much were tickets?"

if __name__ == "__main__":
    agents.FORCE_REFRESH = True  # a real, billed run - not a gateway cache replay
    r = agents.answer(QUESTION, {}, use_cache=False, budget=Budget(session_cap=10, daily_cap=50))
    out = ROOT / "evals" / "results" / "trace_example.json"
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(r["text"])
    print(r["agents"], r["model_calls"], r["tool_calls"], r["tokens"], r["cost"], r["seconds"])
