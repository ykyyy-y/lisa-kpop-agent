"""What a general chatbot gets right without L.I.S.A.  Run:  python evals/baseline_chatbot.py

Same model (gpt-6-luna), same 16 benchmark questions, same strict grader - but no L.I.S.A. data,
tools or guardrails, just "You are a helpful assistant". This isolates what the agent design adds.
(It is not the ChatGPT product, which can also search the web; the report says so.)

Writes evals/results/baseline_chatbot.json.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evals"))

from benchmark import CASES  # noqa: E402

from lisa import data  # noqa: E402
from lisa.config import MODEL, client, cost_usd, usage_dict  # noqa: E402

OUT = ROOT / "evals" / "results" / "baseline_chatbot.json"
URL = re.compile(r"https?://([^/\s)\]]+)")


def unofficial(text: str) -> list[str]:
    allowed = data.allowed_domains()
    return [h for h in URL.findall(text) if not any(h.lower().removeprefix("www.") == d or h.lower().endswith("." + d) for d in allowed)]


def main() -> None:
    rows = []
    for q, _exp, facts in CASES:
        t0 = time.time()
        raw = client().responses.with_raw_response.create(
            model=MODEL, instructions=f"You are a helpful assistant. Today is {date.today().isoformat()}.",
            input=q, max_output_tokens=1200, reasoning={"effort": "low"},
            extra_headers={"x-portkey-cache-force-refresh": "true"})
        r = raw.parse()
        text = r.output_text or ""
        hits = [any(f.lower() in text.lower() for f in g) for g in facts]
        rows.append({"question": q, "facts_ok": all(hits), "facts_hit": sum(hits), "facts_total": len(hits),
                     "unofficial_links": unofficial(text), "cost": cost_usd(usage_dict(r.usage)),
                     "seconds": round(time.time() - t0, 2), "text": text})
        print(f"facts={sum(hits)}/{len(hits)} links={len(unofficial(text))} :: {q[:60]}")
    n = len(rows)
    summary = {"questions": n, "fact_accuracy": round(sum(r["facts_ok"] for r in rows) / n, 3),
               "answers_with_unofficial_links": sum(1 for r in rows if r["unofficial_links"]),
               "avg_cost": round(sum(r["cost"] for r in rows) / n, 7), "model": MODEL, "run_at": time.strftime("%Y-%m-%d %H:%M")}
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
