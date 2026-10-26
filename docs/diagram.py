"""The agent architecture diagram as inline SVG (shared by the report and the slides)."""

PINK = "#e75a8d"
PINK_L = "#ffe8f0"
PINK_M = "#f9a8c6"
INK = "#3a2b33"
MUTED = "#7d6f76"
GREEN = "#e3f6ee"
BLUE = "#e8f1ff"
AMBER = "#fff2dc"


def _box(x, y, w, h, title, sub="", fill="white", stroke=PINK_M, title_color=INK, size=14):
    lines = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>',
             f'<text x="{x + w / 2}" y="{y + (h / 2 if not sub else 24)}" text-anchor="middle" dominant-baseline="middle" '
             f'font-size="{size}" font-weight="700" fill="{title_color}">{title}</text>']
    for i, s in enumerate(sub.split("|") if sub else []):
        lines.append(f'<text x="{x + w / 2}" y="{y + 44 + i * 17}" text-anchor="middle" font-size="11.5" fill="{MUTED}">{s}</text>')
    return "\n".join(lines)


def _arrow(x1, y1, x2, y2, label="", dashed=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" stroke-width="1.6" marker-end="url(#ah)"{dash}/>'
    if label:
        s += f'<text x="{(x1 + x2) / 2 + 6}" y="{(y1 + y2) / 2 - 4}" font-size="11" fill="{PINK}" font-weight="700">{label}</text>'
    return s


def architecture_svg() -> str:
    parts = [
        '<svg viewBox="0 0 960 600" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Inter, Arial, sans-serif" role="img" '
        'aria-label="L.I.S.A. agent architecture">',
        f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="{MUTED}"/></marker></defs>',
        _box(30, 20, 180, 62, "K-pop fan", "Korean or English", fill=PINK_L),
        _box(270, 14, 300, 74, "Dash UI", "click planner: artist · type · city|cards with agent buttons · chat"),
        _box(630, 14, 300, 74, "Cards · fansign chart · tracklists", "computed in Python · 0 tokens · $0", fill=GREEN, stroke="#9bd8bd"),
        _arrow(210, 51, 268, 51),
        _arrow(570, 51, 628, 51, "browse"),
        _box(270, 120, 140, 56, "Input guard", "injection / secrets / length", fill=AMBER, stroke="#f0cf8f", size=13),
        _box(430, 120, 140, 56, "Answer cache", "repeat → $0, ~0 s", fill=BLUE, stroke="#a9c4f2", size=13),
        _arrow(420, 88, 340, 118, "ask"),
        _arrow(410, 148, 428, 148),
        _box(300, 205, 360, 70, "Router Manager (gpt-6-luna)", "card button → rule-based route + card id (no LLM call)|free text → JSON route: up to 2 of 4 specialists", fill=PINK_L, stroke=PINK),
        _arrow(500, 176, 480, 203, "miss"),
        _box(30, 320, 210, 120, "🎫 Schedule & Ticketing", "list_events · get_ticketing|get_setlist|dates, presale, sold-out, setlists", size=13),
        _box(260, 320, 210, 120, "✍️ Fansign Analyst", "list_fansigns · predict_fansign_cut|get_fansign_reviews (UNTRUSTED)|cut line → Python model", size=13),
        _box(490, 320, 210, 120, "🚆 Logistics", "list_events · get_logistics|airport → venue, fares,|lockers, show-day tips", size=13),
        _box(720, 320, 210, 120, "🎧 Streaming Coach", "list_releases|build_streaming_playlist|tracklists, official links, fair 스밍", size=13),
        _arrow(380, 275, 135, 318), _arrow(450, 275, 365, 318), _arrow(510, 275, 595, 318), _arrow(580, 275, 825, 318),
        # specialist -> guard arrows first, so the dataset band is drawn over them and its text stays readable
        _arrow(135, 440, 280, 513), _arrow(365, 440, 420, 513), _arrow(595, 440, 540, 513), _arrow(825, 440, 680, 513),
        f'<rect x="30" y="455" width="900" height="34" rx="10" fill="#faf7f8" stroke="{MUTED}" stroke-dasharray="4 4"/>',
        f'<text x="480" y="477" text-anchor="middle" font-size="12" fill="{MUTED}">dataset: events · fansign · releases · venues · setlists · vendors (JSON, sourced + SAMPLE rows)  —  agents cannot browse the web</text>',
        _box(150, 515, 660, 70, "Output guards (code, not prompts)", "official-link allowlist · fansign disclaimer · date grounding check|budget caps ($0.05/session, $2/day) · max 4 model calls per agent", fill=AMBER, stroke="#f0cf8f"),
        "</svg>",
    ]
    return "\n".join(parts)
