"""Rolling-origin backtest of the fansign cut-line model.  Run:  python evals/backtest_fansign.py

For every artist + retailer + format series with at least 3 past cuts, predict each cut from the
cuts before it only (no peeking), then compare with what happened:

* median error  - |predicted median - actual| / actual
* 80% coverage  - share of actual cuts that fell inside the model's 10th-90th percentile band
* baseline      - "same as last time" (what fans do today when they copy the last cut from X)

The data is the SAMPLE history in data/fansign.json, so this checks the method, not real-world
accuracy; rerun it when real community reports arrive. No API calls. Writes evals/results/backtest.json.
"""

from __future__ import annotations

import json
import math
import sys
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lisa import data, fansign_model  # noqa: E402

OUT = ROOT / "evals" / "results" / "backtest.json"
Z80 = 1.2816


def main() -> dict:
    hist = sorted(data.load("fansign")["history"], key=lambda r: (r["artist"], r["retailer_id"], r["format"], r["date"]))
    rows = []
    for key, grp in groupby(hist, key=lambda r: (r["artist"], r["retailer_id"], r["format"])):
        series = list(grp)
        for k in range(2, len(series)):
            train, actual = series[:k], series[k]
            mu, sigma, _ = fansign_model._fit(train, actual["winners"])
            pred = math.exp(mu)
            lo, hi = math.exp(mu - Z80 * sigma), math.exp(mu + Z80 * sigma)
            naive = train[-1]["cut_albums"]
            rows.append({"series": "/".join(key), "date": actual["date"], "actual": actual["cut_albums"],
                         "predicted": round(pred, 1), "band": [round(lo, 1), round(hi, 1)],
                         "model_err_pct": round(abs(pred - actual["cut_albums"]) / actual["cut_albums"] * 100, 1),
                         "naive_err_pct": round(abs(naive - actual["cut_albums"]) / actual["cut_albums"] * 100, 1),
                         "inside_band": lo <= actual["cut_albums"] <= hi,
                         "naive_under": naive < actual["cut_albums"]})
    n = len(rows)
    summary = {
        "predictions": n,
        "model_median_abs_err_pct": round(sorted(r["model_err_pct"] for r in rows)[n // 2], 1),
        "naive_median_abs_err_pct": round(sorted(r["naive_err_pct"] for r in rows)[n // 2], 1),
        "model_mean_abs_err_pct": round(sum(r["model_err_pct"] for r in rows) / n, 1),
        "naive_mean_abs_err_pct": round(sum(r["naive_err_pct"] for r in rows) / n, 1),
        "band_80_coverage_pct": round(100 * sum(r["inside_band"] for r in rows) / n),
        "naive_underbuys_pct": round(100 * sum(r["naive_under"] for r in rows) / n),
        "data": "SAMPLE history (data/fansign.json)",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
