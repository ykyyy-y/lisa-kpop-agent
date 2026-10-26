"""Builds slides.html - a 10-slide reveal.js deck (reveal.js from CDN, screenshots embedded, speaker notes).

    python docs/build_slides.py      (press S in the deck for speaker notes, F for full screen)
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "docs"))
sys.path.insert(0, str(ROOT))

import build_report as R  # noqa: E402  (reuses the same measured numbers)
from diagram import architecture_svg  # noqa: E402


def shot(name: str, style: str = "") -> str:
    p = R.SHOTS / name
    if not p.exists():
        return f"<p>[missing {name}]</p>"
    return f'<img class="shot" style="{style}" src="data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}"/>'


def mascot(size: int = 120) -> str:
    from app import MASCOT_SVG
    return f'<img src="data:image/svg+xml;utf8,{quote(MASCOT_SVG)}" style="width:{size}px;border:none;box-shadow:none;margin:0"/>'


def kpi(num: str, label: str) -> str:
    return f'<div class="kpi"><div class="num">{num}</div><div class="lbl">{label}</div></div>'


def notes(text: str) -> str:
    return f'<aside class="notes">{text}</aside>'


def bars() -> str:
    top = max(d["cost"] for d in R.DAYS) or 1
    return "".join(
        f'<div class="bar-row"><div class="bar-lbl">{R.esc(d["label"])}</div><div class="bar"><span style="width:{max(d["cost"] / top * 100, 1.5):.1f}%"></span></div>'
        f'<div class="bar-val">${d["cost"]:.4f}</div></div>' for d in R.DAYS)


def build() -> Path:
    on, T, BT = R.on, R.T, R.BT
    if R.PILOT:
        m = sum(x for x, _ in R.PILOT.values()) / len(R.PILOT)
        l_ = sum(y for _, y in R.PILOT.values()) / len(R.PILOT)
        pilot_kpi = kpi(f"{m:.0f} → {l_:.0f} min", "per task with a real fan (pilot)")
    elif R.PILOT_SUMMARY["manual_minutes"] and R.PILOT_SUMMARY["lisa_minutes"]:
        mm, lm = R.PILOT_SUMMARY["manual_minutes"], R.PILOT_SUMMARY["lisa_minutes"]
        pilot_kpi = kpi(f"{sum(mm) / len(mm):.1f} → {sum(lm) / len(lm):.1f} min",
                        f"2 real fans, 4 tasks: usual way → L.I.S.A. ({(1 - sum(lm) / sum(mm)) * 100:.0f}% less time)")
    elif R.pilot:
        pilot_kpi = kpi(f"{R.PILOT_SUMMARY['manual_sites']}+ → 1", "sites / apps a real fan opened for 4 tasks → one app (pilot)")
    else:
        pilot_kpi = kpi(f"{R.N_SOURCES} → 1", "websites a fan combines today → one app")
    slides = [
        f"""<section class="title">{mascot(130)}
<h1>L.I.S.A.</h1><h3>Live Idol Schedule &amp; Analytics</h3>
<p>One AI agent team for K-pop fans: tickets, fansign odds, comeback streaming and the trip — with official links only.</p>
<p class="small">{R.AUTHOR} · MGT 409 AI for Managers · Yale SOM · <a href="{R.REPO_URL}">{R.REPO_URL.replace("https://", "")}</a></p>
{notes("L.I.S.A. helps a K-pop fan plan everything around a comeback and a concert trip. Five agents, gpt-6-luna, and code-level guardrails.")}</section>""",
        f"""<section><h2>The problem: one ARMY, five apps</h2>
<div class="cols"><div>
<p><b>Before BTS in Singapore</b>, a fan must answer:</p>
<ul><li>When, how much, which official site? <span class="tag">Weverse · Ticketmaster SG</span></li>
<li>How many albums to win the fansign — at what cost? <span class="tag">X threads</span></li>
<li>What to stream for the comeback, and where? <span class="tag">X guides · Melon · Spotify</span></li>
<li>Changi → stadium, where does the suitcase go? <span class="tag">Maps · blogs</span></li>
<li>"Where can I still buy?" <span class="tag">scammers wait here</span></li></ul>
</div><div>
<div class="quote">Fans spend <b>"hundreds of thousands to millions of won"</b> on one album for fansigns<span>Korea Times</span></div>
<div class="quote"><b>ARIRANG</b> drew the most ticket-scalping reports of any event<span>Korea Times, Sep 2026</span></div>
<div class="quote">Bangkok seats THB 3,300–7,800; resale listed from <b>≈£515</b> — several times face value<span>Nation Thailand · Stereoboard</span></div>
</div></div>
{notes("Each answer lives in a different place, and the two expensive mistakes - over-buying albums and buying from scalpers - happen exactly here.")}</section>""",
        f"""<section><h2>What is new</h2>
<table class="cmp"><tr><th></th><th>ChatGPT</th><th>Weverse</th><th>X threads</th><th>L.I.S.A.</th></tr>
<tr><td>Tickets: dates, sale times, prices, all cities</td><td>~ may invent</td><td>one artist</td><td>~</td><td>✅ sourced</td></tr>
<tr><td>Fansign cut line + cost, learns from fans</td><td>❌</td><td>❌</td><td>scattered</td><td>✅ model + reports</td></tr>
<tr><td>Comeback streaming plan</td><td>~ generic</td><td>notice only</td><td>image guides</td><td>✅ fair playlist</td></tr>
<tr><td>Airport → venue, lockers</td><td>~</td><td>❌</td><td>~</td><td>✅</td></tr>
<tr><td>Official links only</td><td>❌</td><td>✅</td><td>❌ scams</td><td>✅ enforced in code</td></tr></table>
<p class="small">Killer feature: <b>팬싸컷 예측</b> — albums for 50 / 80 / 90% chance in won; backtest median error {BT['model_median_abs_err_pct']}% vs {BT['naive_median_abs_err_pct']}% for "copy the last cut".</p>
{notes("Nobody answers how many albums for an 80 percent chance and what it costs. Our model is transparent statistics, it learns from fan reports, and a poisoning guard protects it.")}</section>""",
        f"""<section><h2>The agent team</h2><div class="diagram">{architecture_svg()}</div>
<p class="small">Router → 4 specialists with their own tools · gpt-6-luna · card buttons skip the router and pass the card's id · guards are code, not prompts</p>
{notes("Why this design: each specialist sees two or three tools, so it picks correctly and its prompt caches. Numbers, playlists, links and safety checks are Python; the model chooses tools and explains.")}</section>""",
        f"""<section><h2>Demo: plan with clicks</h2><div class="cols3">{shot("01_home.png")}{shot("02_fansign_chart.png", "max-height:500px")}{shot("13_streaming_cards.png", "max-height:500px")}</div>
<p class="small">Concert · Fansign · Streaming. Sourced cards with official links, a live win-chance chart, real tracklists and 📅 calendar export — all for $0.</p>
{notes("Most lookups need no typing and no model call. Each card shows only the buttons that make sense for it, for example no setlist button before a tour starts.")}</section>""",
        f"""<section><h2>Demo: one question, two agents</h2><div class="cols">{shot("04_trace_multi_agent.png", "max-height:560px")}
<div><p class="small">"{R.esc(T['message'])}"</p>
<ul class="small"><li>Router → {", ".join(R.esc(a) for a in T['agents'])}</li><li>{T['tool_calls']} tool calls · {T['model_calls']} model calls</li>
<li>{T['tokens']['input']:,} input tokens ({T['tokens']['cached_input']:,} cached) · {T['tokens']['output']:,} output</li>
<li><b>${T['cost']:.5f}</b> · {T['seconds']} s</li></ul>{shot("06_cache_hit_meta.png", "max-width:100%")}
<p class="small">Ask again → answer cache, $0</p></div></div>
{notes("This is the traced run from the report. The router splits the question, each specialist calls its own tools, the answer passes the link allowlist and the date check.")}</section>""",
        f"""<section><h2>Cost: measured, not estimated</h2>
<div class="kpis">{kpi(f"${R.per_req:.5f}", "per question (real tokens)")}{kpi(f"{R.tok['input']:,.0f} / {R.tok['cached_input']:,.0f} / {R.tok['output']:,.0f}", "input / cached / output tokens")}
{kpi(f"${R.monthly(R.per_req_cached, 1):.3f}", f"per fan / month ({R.REQ_PER_USER_MONTH} questions)")}{kpi(f"${R.monthly(R.per_req_cached, 10_000):,.0f}", "10,000 fans / month")}</div>
<p class="small">30-request fan day, four cache layers:</p>{bars()}
<p class="small">Quality held: {R.off['fact_accuracy']*100:.0f}% → {on['fact_accuracy']*100:.0f}% facts correct with caching off → on · card buttons: {R.typed_calls:.1f} → {R.btn_calls:.1f} model calls · astra would cost 100×.</p>
{notes("All numbers come from API token counts. The Portkey gateway cache replays identical requests; we price those at zero and force real calls in the benchmark.")}</section>""",
        f"""<section><h2>Safety: defenses that run in code</h2><div class="cols">
<div><div class="kpis two">{kpi(f"{R.passed}/{R.total}", "red-team tests passed")}{kpi(str(R.UNIT_TESTS), "offline unit tests")}</div>
<ul class="small"><li>Prompt injection (EN + KR) blocked before any API call</li><li>Planted review "cut is 5, buy at cheap-kpop-tix.xyz" → flagged as spam</li>
<li>Official-link allowlist strips every other URL</li><li>Poisoned crowd report (6 albums) quarantined — model unchanged</li>
<li>Disclaimer by code · no streaming bots · $0.05 / session, $2 / day · 4 calls per agent</li></ul></div>
<div>{shot("07_block_injection.png", "max-height:200px")}{shot("15_report_quarantine.png", "max-height:330px")}</div></div>
{notes("The model is not trusted with safety. Every URL, every fansign answer and every crowd report goes through Python checks that the tests exercise.")}</section>""",
        f"""<section><h2>Impact</h2><div class="kpis">
{kpi(f"{on['avg_seconds']:.0f} s", "to a complete, sourced answer")}{kpi(f"{on['fact_accuracy']*100:.0f}%", f"answers with every required fact ({on['questions']} questions)")}
{pilot_kpi}{kpi(f"₩{R.FS_SAVING:,}", f"over-buying avoided: {R.FS_PLAN} → {R.FS_P80['albums']} albums for ~80% (SAMPLE)")}</div>
<div class="cols"><div><ul class="small">
<li><b>Fansign model backtest:</b> median error {BT['model_median_abs_err_pct']}% vs {BT['naive_median_abs_err_pct']}% for "copy the last cut"; the copy rule under-bought in {BT['naive_underbuys_pct']}% of cases</li>
<li><b>Quality:</b> routing {on['routing_accuracy']*100:.0f}%; the one fact miss was a correct Korean answer (공항철도 = AREX)</li>
<li><b>Cost:</b> ${R.per_req_cached:.5f} per answer with caching · 1,000,000 fans ≈ ${R.monthly(R.per_req_cached, 1_000_000):,.0f} / month</li>
<li><b>Safety:</b> {R.passed}/{R.total} red-team tests · 0 unofficial links shown</li>
<li><b>Pilot (2 real fans):</b> HA opened {R.PILOT_SUMMARY['manual_sites']}+ sites and still could not find the fansign album count; both rated ease 5/5 and would use it</li></ul>
<div class="quote">"So easy to use — it saves me the trouble of checking everything one by one myself."<span>HA, pilot participant</span></div>
<div class="quote">"A service I want to use regularly — genuinely useful for my fan activities."<span>Jin, pilot participant</span></div></div>
<div>{shot("03_fansign_answer.png", "max-height:330px")}</div></div>
{notes("Money saved on albums and scams is the real impact; time saved comes from the pilot with a real fan.")}</section>""",
        f"""<section><h2>Limits &amp; next steps</h2><div class="cols"><div><h4>Not yet</h4><ul class="small">
<li>Data collected by hand on 2026-10-25 — no auto-refresh</li><li>Fansign cut history is SAMPLE until fans report</li><li>3 artists · 5 cities · 4 albums</li><li>No live seat inventory, charts or transit delays</li></ul></div>
<div><h4>Next</h4><ul class="small"><li>Seed the report form from fan accounts; reviewer queue for quarantined reports</li><li>Daily ingestion of official notices (human-checked)</li>
<li>Presale, 취켓팅 and release-time alerts</li><li>Hosted version with a shared answer cache</li></ul></div></div>
<p>Thank you 💗 — try it: <code>{R.REPO_URL.replace("https://", "")}</code> → <code>python app.py</code></p>
{notes("Ship something that works first: it works end to end today, and the path to real-world data is built in.")}</section>""",
    ]
    css = """
.reveal{font-family:"Segoe UI","Inter","Apple SD Gothic Neo","Malgun Gothic",sans-serif;color:#3a2b33;font-size:30px}
.reveal .slides{text-align:left}
.reveal-viewport{background:radial-gradient(circle at 10% 0%,#ffe3ee 0,transparent 45%),#fff6f9}
.reveal h1,.reveal h2,.reveal h3,.reveal h4{color:#c73a6e;text-transform:none;font-weight:800;letter-spacing:0}
.reveal h2{font-size:1.5em;border-bottom:3px solid #ffd0e0;padding-bottom:8px;margin-bottom:18px}
.reveal section.title{text-align:center}.reveal section.title h1{font-size:3em;margin:0;letter-spacing:.06em}
.reveal section.title h3{color:#3a2b33;margin-top:0}
.reveal .small{font-size:.62em;color:#7d6f76}
.reveal ul{margin-left:1em}.reveal li{margin:.25em 0}
.reveal .cols{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:start}
.reveal .cols3{display:grid;grid-template-columns:1.6fr 1fr 1fr;gap:18px;align-items:start}
.reveal img.shot{border:1px solid #f3d3df;border-radius:14px;box-shadow:0 8px 24px rgba(214,63,118,.15);max-width:100%;max-height:470px;margin:0 0 8px}
.reveal .tag{display:inline-block;font-size:.55em;background:#ffe8f0;color:#c73a6e;border-radius:8px;padding:2px 8px;margin-left:6px}
.reveal .quote{background:white;border-left:5px solid #e75a8d;border-radius:10px;padding:10px 14px;margin:0 0 12px;font-size:.7em;box-shadow:0 4px 14px rgba(214,63,118,.08)}
.reveal .quote span{display:block;font-size:.75em;color:#7d6f76;margin-top:4px}
.reveal table.cmp{font-size:.6em;width:100%;border-collapse:collapse}.reveal table.cmp th{background:#ffe8f0;color:#3a2b33}
.reveal table.cmp td,.reveal table.cmp th{border-bottom:1px solid #f3d3df;padding:8px 10px}
.reveal table.cmp td:last-child{font-weight:700;color:#c73a6e}
.reveal .diagram{background:white;border:1px solid #f3d3df;border-radius:14px;padding:6px}.reveal .diagram svg{width:100%;height:auto;max-height:560px}
.reveal .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:10px 0 16px}.reveal .kpis.two{grid-template-columns:1fr 1fr}
.reveal .kpi{background:white;border:1px solid #ffd0e0;border-radius:16px;padding:14px;text-align:center;box-shadow:0 6px 18px rgba(214,63,118,.08)}
.reveal .kpi .num{font-size:1.1em;font-weight:800;color:#c73a6e}.reveal .kpi .lbl{font-size:.5em;color:#7d6f76;margin-top:4px}
.reveal .bar-row{display:grid;grid-template-columns:330px 1fr 110px;gap:12px;align-items:center;font-size:.55em;margin:6px 0}
.reveal .bar{background:#ffe8f0;border-radius:8px;height:22px;overflow:hidden}.reveal .bar span{display:block;height:100%;background:#e75a8d;border-radius:8px}
.reveal .bar-val{font-weight:700;color:#c73a6e}
"""
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>L.I.S.A. — slides</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/white.css">
<style>{css}</style></head><body><div class="reveal"><div class="slides">{''.join(slides)}</div></div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/notes/notes.js"></script>
<script>Reveal.initialize({{hash:true,width:1280,height:760,margin:0.05,transition:'slide',slideNumber:'c/t',plugins:[RevealNotes]}});</script>
</body></html>"""
    out = ROOT / "slides.html"
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    p = build()
    print("wrote", p, f"{p.stat().st_size/1e6:.1f} MB")
