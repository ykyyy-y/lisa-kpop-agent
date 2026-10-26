"""The fansign cut-line predictor (팬싸컷 예측) - plain statistics, no LLM.

A fansign "cut" is the smallest number of albums a winner bought. Fans post the cut on X
after every event. We model the next cut as log-normal:

* take past cuts for the same artist + retailer + format (fall back to artist + format
  when a retailer has fewer than 3 reports),
* rescale each past cut to the new event's number of winners (fewer winners -> higher
  cut, elasticity 0.5),
* fit a linear trend on log(cut) over time and project one event ahead,
* use the residual spread (at least 0.12) as the uncertainty.

From that we get the albums needed for a 50/80/90% chance and the win chance for any
album count. Keeping this in code (not in the model) means the numbers are reproducible
and cost zero tokens.
"""

from __future__ import annotations

import math

from . import data

WINNER_ELASTICITY = 0.5
MIN_SIGMA = 0.12
Z = {50: 0.0, 80: 0.8416, 90: 1.2816}


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def history_rows(artist: str, retailer: str, fmt: str) -> list[dict]:
    """Dataset reports + accepted community reports for one artist / retailer / format."""
    from . import community
    rows = data.load("fansign")["history"] + community.accepted(artist)
    return sorted([r for r in rows if r["artist"] == artist and r["retailer_id"] == retailer and r["format"] == fmt],
                  key=lambda r: r["date"])


def _history(artist: str, retailer: str, fmt: str) -> tuple[list[dict], str]:
    same = history_rows(artist, retailer, fmt)
    n_comm = sum(1 for r in same if r.get("source") == "community")
    tag = f" incl. {n_comm} community" if n_comm else ""
    if len(same) >= 3:
        return same, f"{len(same)} past {fmt} reports at this retailer{tag}"
    from . import community
    rows = data.load("fansign")["history"] + community.accepted(artist)
    pooled = sorted([r for r in rows if r["artist"] == artist and r["format"] == fmt], key=lambda r: r["date"])
    return pooled, f"{len(pooled)} past {fmt} reports for this artist (all retailers)"


def _fit(hist: list[dict], winners: int) -> tuple[float, float, float]:
    """(mu, sigma, slope) of log(cut) one event past the last report, rescaled to `winners`."""
    logs = [math.log(r["cut_albums"] * (r["winners"] / winners) ** WINNER_ELASTICITY) for r in hist]
    n = len(logs)
    xs = list(range(n))
    x_bar, y_bar = sum(xs) / n, sum(logs) / n
    sxx = sum((x - x_bar) ** 2 for x in xs)
    slope = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, logs)) / sxx if sxx else 0.0
    fitted = [y_bar + slope * (x - x_bar) for x in xs]
    resid = [y - f for y, f in zip(logs, fitted)]
    sigma = max(math.sqrt(sum(r * r for r in resid) / max(n - 2, 1)), MIN_SIGMA)
    return y_bar + slope * (n - x_bar), sigma, slope


def outlier_z(base: list[dict], winners: int, cut: int) -> float | None:
    """How unusual a new report is versus existing ones (None if fewer than 3 to compare with)."""
    if len(base) < 3:
        return None
    mu, sigma, _ = _fit(base, winners)
    return abs(math.log(cut) - mu) / sigma


def predict(fansign_id: str, albums: int | None = None) -> dict:
    fs = data.fansign(fansign_id)
    if not fs:
        return {"error": f"Unknown fansign id '{fansign_id}'."}
    hist, basis = _history(fs["artist"], fs["retailer_id"], fs["format"])
    if len(hist) < 2:
        return {"error": "Not enough past cut reports to predict this fansign.", "reports": len(hist)}
    mu, sigma, slope = _fit(hist, fs["winners"])

    price = fs["album_price_krw"]
    levels = {}
    for pct, z in Z.items():
        k = math.ceil(math.exp(mu + z * sigma))
        levels[f"p{pct}"] = {"albums": k, "cost_krw": k * price}

    out = {
        "fansign_id": fansign_id,
        "title": fs["title"],
        "retailer": data.vendor_name(fs["retailer_id"]),
        "format": fs["format"],
        "winners": fs["winners"],
        "album_price_krw": price,
        "predicted_median_cut": levels["p50"]["albums"],
        "albums_for_chance": levels,
        "trend_per_event_pct": round((math.exp(slope) - 1) * 100, 1),
        "past_cuts": [{"date": r["date"], "winners": r["winners"], "cut": r["cut_albums"],
                       "source": r.get("source", "dataset")} for r in hist],
        "basis": basis,
        "method": "log-normal on winner-adjusted past cuts with a linear time trend",
        "data_status": fs.get("data_status", "sample"),
    }
    if albums:
        p = _phi((math.log(albums) - mu) / sigma)
        out["your_albums"] = {"albums": albums, "win_chance_pct": round(p * 100, 1), "cost_krw": albums * price}
    return out


def curve(fansign_id: str, points: int = 40) -> list[tuple[int, float]]:
    """(albums, win chance %) pairs for the UI chart."""
    base = predict(fansign_id)
    if "error" in base:
        return []
    top = base["albums_for_chance"]["p90"]["albums"] * 1.4
    step = max(int(top / points), 1)
    return [(k, predict(fansign_id, k)["your_albums"]["win_chance_pct"]) for k in range(step, int(top) + step, step)]
