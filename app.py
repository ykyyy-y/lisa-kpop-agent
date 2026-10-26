"""L.I.S.A. - Live Idol Schedule & Analytics. Run:  python app.py  -> http://127.0.0.1:8050"""

from __future__ import annotations

import os
from datetime import date
from urllib.parse import quote

import plotly.graph_objects as go
from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update

from lisa import agents, calendar_export, community, data, fansign_model
from lisa.config import SESSION_BUDGET_USD, key_status
from lisa.guardrails import DISCLAIMER_EN, DISCLAIMER_KO

# The mascot is drawn in code (SVG), not generated: a pink bunny with a light stick.
MASCOT_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
<ellipse cx='22' cy='14' rx='6' ry='13' fill='#f9a8c6'/><ellipse cx='42' cy='14' rx='6' ry='13' fill='#f9a8c6'/>
<ellipse cx='22' cy='15' rx='3' ry='9' fill='#ffe8f0'/><ellipse cx='42' cy='15' rx='3' ry='9' fill='#ffe8f0'/>
<circle cx='32' cy='38' r='20' fill='#ffd0e0'/><circle cx='25' cy='36' r='3' fill='#3a2b33'/><circle cx='39' cy='36' r='3' fill='#3a2b33'/>
<circle cx='26' cy='35' r='1' fill='white'/><circle cx='40' cy='35' r='1' fill='white'/>
<ellipse cx='20' cy='43' rx='3.5' ry='2' fill='#f48fb1' opacity='.7'/><ellipse cx='44' cy='43' rx='3.5' ry='2' fill='#f48fb1' opacity='.7'/>
<path d='M28 44 Q32 48 36 44' stroke='#3a2b33' stroke-width='2' fill='none' stroke-linecap='round'/>
<rect x='50' y='30' width='4' height='16' rx='2' fill='#7d6f76'/><circle cx='52' cy='28' r='5' fill='#e75a8d'/><circle cx='52' cy='28' r='2.4' fill='white' opacity='.8'/>
</svg>"""
MASCOT = "data:image/svg+xml;utf8," + quote(MASCOT_SVG)

CATEGORIES = [("concert", "🎤 Concert"), ("fansign", "✍️ Fansign"), ("streaming", "🎧 Streaming")]
SUGGESTIONS = [
    "BTS 싱가포르 콘서트 예매 일정이랑 가격 알려줘",
    "팬싸컷 120장 사면 BTS 케이타운포유 영상통화 당첨 확률 얼마야?",
    "I land at Changi for BTS in Singapore - how do I get to the stadium?",
    "TXT 컴백 스밍 리스트 1시간짜리 만들어줘",
]
ACTION_LABELS = {
    "ticketing": "🎫 Ticket strategy", "setlist": "🎵 Setlist", "logistics": "🚆 Airport → venue",
    "fansign": "✍️ My win chance", "reviews": "💬 What winners said", "playlist": "🎧 Build streaming playlist",
}

app = Dash(__name__, title="L.I.S.A. · Live Idol Schedule & Analytics", suppress_callback_exceptions=True)
server = app.server


def pill_radio(id_, options, value):
    return dcc.RadioItems(id=id_, options=[{"label": l, "value": v} for v, l in options], value=value,
                          className="pills pill-radio", inline=True)


planner = html.Div(className="card", children=[
    html.H2("Plan with clicks — no typing needed"),
    html.Div("1 · Artist", className="step"),
    pill_radio("artist", [(a["id"], a["name"]) for a in data.artists()], "bts"),
    html.Div("2 · Event type", className="step"),
    pill_radio("category", CATEGORIES, "concert"),
    html.Div(id="city-controls", children=[
        html.Div("3 · City", className="step"),
        dcc.Dropdown(id="city", placeholder="All cities", clearable=True),
    ]),
    html.Div(id="fansign-controls", style={"display": "none"}, children=[
        html.Div("3 · Albums you plan to buy", className="step"),
        dcc.Slider(id="albums", min=5, max=200, step=5, value=50,
                   marks={v: str(v) for v in (5, 50, 100, 150, 200)}, tooltip={"placement": "bottom"}),
        html.Details(className="report-box", children=[
            html.Summary("📝 Won or lost a past fansign? Report the cut (improves the model)"),
            html.Div(className="report-grid", children=[
                dcc.Dropdown(id="rep-retailer", options=[{"label": n, "value": v} for v, n in
                             (("withmuu", "Withmuu"), ("makestar", "Makestar"), ("ktown4u", "Ktown4u"))],
                             value="withmuu", clearable=False),
                dcc.Dropdown(id="rep-format", options=[{"label": "🖊️ offline", "value": "offline"},
                                                       {"label": "🎥 video call", "value": "video_call"}],
                             value="offline", clearable=False),
                dcc.Input(id="rep-date", type="text", placeholder="date YYYY-MM-DD", debounce=True),
                dcc.Input(id="rep-winners", type="number", placeholder="winners", min=1, max=500),
                dcc.Input(id="rep-cut", type="number", placeholder="cut (albums)", min=1, max=1000),
                html.Button("Submit report", id="rep-submit", className="btn small primary"),
            ]),
            html.Div(id="rep-status", className="hint"),
        ]),
    ]),
    html.Div(id="streaming-controls", style={"display": "none"}, children=[
        html.Div("3 · Playlist length", className="step"),
        pill_radio("minutes", [(30, "30 min"), (60, "1 hour"), (120, "2 hours")], 60),
    ]),
    html.Div(id="events", className="events"),
    html.Div("Cards, links and the fansign chart are computed locally for $0. Each card's buttons send a "
             "ready-made question about that card to the right agent, without a router call.", className="hint"),
])

chat = html.Div(className="card chat", children=[
    html.Div(className="chat-head", children=[
        html.Img(src=MASCOT, className="avatar", alt="L.I.S.A. mascot"),
        html.Div([html.Div("Ask L.I.S.A.", className="title"),
                  html.Div("Router → Schedule & Ticketing · Fansign Analyst · Logistics · Streaming Coach  ·  Korean or English", className="sub")]),
    ]),
    html.Div(id="messages", className="messages"),
    html.Div(className="composer", children=[
        dcc.Textarea(id="chat-input", placeholder="e.g. BTS 방콕 콘서트 가려면 수완나품 공항에서 어떻게 가? (Enter to send, Shift+Enter for a new line)",
                     title="Message to L.I.S.A.", maxLength=1500, rows=2),
        html.Button("Send", id="send-btn", className="btn primary send", **{"aria-label": "Send message"}),
    ]),
])

usage_tab = html.Div(className="page", style={"gridTemplateColumns": "1fr"}, children=[
    html.Div(className="card", children=[html.H2("Usage, cost and safety for this session"), html.Div(id="usage-panel")]),
    html.Div(className="card", children=[html.H2("About the data"), html.Div(id="data-panel")]),
])

app.layout = html.Div([
    dcc.Store(id="history", storage_type="session", data=[]),
    dcc.Store(id="pending", data=None),
    dcc.Store(id="community-version", data=0),
    dcc.Store(id="reports-made", storage_type="session", data=0),
    dcc.Download(id="ics-download"),
    html.Div(className="topbar", children=[
        html.Div(className="brand", children=[
            html.Img(src=MASCOT, style={"width": "46px"}, alt=""),
            html.Div([html.H1("L.I.S.A."), html.P("Live Idol Schedule & Analytics — concerts, fansigns & streaming in one place")]),
        ]),
        html.Div(id="meter", className="meter"),
    ]),
    html.Div(className="tabs-wrap", children=[
        dcc.Tabs(id="tabs", value="plan", children=[
            dcc.Tab(label="Plan & Ask", value="plan"),
            dcc.Tab(label="Usage & Safety", value="usage"),
        ], colors={"border": "#ffd0e0", "primary": "#e75a8d", "background": "#fff6f9"}),
    ]),
    html.Div(className="howto", children=[
        html.Span("How it works", className="howto-title"),
        html.Span([html.B("1"), " Pick an artist and a category"]),
        html.Span([html.B("2"), " Read the free cards — dates, official links, win-chance chart, tracklists"]),
        html.Span([html.B("3"), " Tap a card button (🎫 🚆 ✍️ 🎧 📅) or ask in Korean / English"]),
    ]),
    html.Div(id="plan-view", className="page", children=[planner, chat]),
    html.Div(id="usage-view", style={"display": "none"}, children=usage_tab),
    html.Div(className="footer-note", children=[
        "Concert, ticketing and album rows: public reporting with sources on every card (checked 2026-10-25). Rows marked ",
        html.Span("SAMPLE", className="badge sample"),
        "are illustrative prototype data. Always confirm on the official notice. Model: gpt-6-luna via Portkey.",
    ]),
])


# ---------------------------------------------------------------- planner ----

@app.callback(Output("plan-view", "style"), Output("usage-view", "style"), Input("tabs", "value"))
def switch_tab(tab):
    return ({}, {"display": "none"}) if tab == "plan" else ({"display": "none"}, {})


@app.callback(Output("city", "options"), Output("city", "value"), Output("city-controls", "style"),
              Output("fansign-controls", "style"), Output("streaming-controls", "style"),
              Input("artist", "value"), Input("category", "value"))
def update_controls(artist, category):
    hide, show = {"display": "none"}, {}
    cities = data.cities(artist, category) if category == "concert" else []
    return ([{"label": c, "value": c} for c in cities], None,
            show if category == "concert" else hide,
            show if category == "fansign" else hide,
            show if category == "streaming" else hide)


def _date_chips(dates):
    today = date.today().isoformat()
    return html.Div(className="chips", children=[html.Span(d, className="chip past" if d < today else "chip") for d in dates])


def _status_badge(row):
    if row.get("data_status") == "sample":
        return html.Span("SAMPLE", className="badge sample")
    return html.Span("SOURCED", className="badge ok")


def _actions(ref: str, actions: list[str]):
    """The agent buttons for one card - only the ones that make sense for it."""
    return html.Div(className="card-actions", children=[
        html.Button(ACTION_LABELS[a], id={"type": "card-act", "action": a, "ref": ref}, n_clicks=0, className="btn small")
        for a in actions] + [html.Button("📅 Add to calendar", id={"type": "cal", "ref": ref}, n_clicks=0,
                                         className="btn small ghost", title="Download an .ics file for your phone calendar")])


def event_card(e):
    v = data.venue(e["venue_id"]) or {}
    t = e["ticketing"]
    links = [html.A(f"Official: {data.vendor_name(t['vendor_id'])}", href=t["url"], target="_blank", className="linkbtn")]
    links += [html.A(f"Source {i + 1}", href=s, target="_blank", className="linkbtn ghost") for i, s in enumerate(e["sources"][:2])]
    setlist = data.setlist_for(e["artist"])
    actions = ["ticketing"] + (["setlist"] if setlist else []) + ["logistics"]
    note = None if setlist else html.Div("🎵 Setlist: not published yet - this tour has not started.", className="hint")
    return html.Div(className="event", children=[
        html.H3([_status_badge(e), e["title"]]),
        html.Div(f"📍 {v.get('name', '')} · {e['city']}", className="venue"),
        _date_chips(e["dates"]),
        html.Div(e["date_note"], className="hint") if e["date_note"] else None,
        html.Div([html.B("Tickets: "), t["status"]], className="status"),
        html.Div([html.B("General sale: "), t["general_open"]], className="status"),
        html.Div(links),
        note,
        _actions(e["id"], actions),
    ])


def fansign_card(f, albums):
    pred = fansign_model.predict(f["id"], albums)
    if "error" in pred:
        return html.Div(className="event", children=[html.H3(f["title"]), html.Div(pred["error"], className="hint")])
    lv = pred["albums_for_chance"]
    curve = fansign_model.curve(f["id"])
    fig = go.Figure(go.Scatter(x=[c[0] for c in curve], y=[c[1] for c in curve], mode="lines",
                               line={"color": "#e75a8d", "width": 3}, fill="tozeroy", fillcolor="rgba(231,90,141,.12)",
                               hovertemplate="%{x} albums → %{y:.0f}% chance<extra></extra>"))
    fig.add_vline(x=albums, line_dash="dot", line_color="#3a2b33",
                  annotation_text=f"you: {albums}", annotation_position="top left")
    fig.update_layout(height=170, margin={"l": 36, "r": 10, "t": 10, "b": 30}, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font={"size": 11, "color": "#7d6f76"},
                      xaxis={"title": "albums bought", "gridcolor": "#ffe8f0"},
                      yaxis={"title": "win chance %", "range": [0, 100], "gridcolor": "#ffe8f0"})
    mine = pred["your_albums"]
    fmt = "🎥 video call" if f["format"] == "video_call" else "🖊️ offline"
    return html.Div(className="event", children=[
        html.H3([_status_badge(f), f["title"]]),
        html.Div(f"🗓️ {f['event_date']} · {fmt} · {f['city']} · {f['winners']} winners · ₩{f['album_price_krw']:,}/album", className="venue"),
        html.Div(f"Entry window: {f['apply_window']}", className="hint"),
        html.Div(className="fs-row", children=[
            html.Div(className="stat", children=[html.Div(f"{mine['win_chance_pct']:.0f}%", className="num"),
                                                 html.Div(f"your chance with {albums}", className="lbl")]),
            html.Div(className="stat", children=[html.Div(str(lv["p50"]["albums"]), className="num"), html.Div("albums for 50%", className="lbl")]),
            html.Div(className="stat", children=[html.Div(str(lv["p80"]["albums"]), className="num"), html.Div("albums for 80%", className="lbl")]),
        ]),
        html.Div(f"Your plan costs ₩{mine['cost_krw']:,}. An 80% chance costs ₩{lv['p80']['cost_krw']:,}. "
                 f"Cut trend: {pred['trend_per_event_pct']:+.1f}% per event ({pred['basis']}).", className="status"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"height": "170px"}),
        html.A(f"Official: {pred['retailer']}", href=f["url"], target="_blank", className="linkbtn"),
        html.Div(f"⚠️ {DISCLAIMER_EN} / {DISCLAIMER_KO}", className="disclaimer"),
        _actions(f["id"], ["fansign", "reviews"]),
    ])


def release_card(r):
    upcoming = r["status"] == "upcoming"
    days = (date.fromisoformat(r["release_date"]) - date.today()).days
    badge = html.Span(f"D-{days}" if upcoming and days >= 0 else "RELEASED", className="badge sample" if upcoming else "badge ok")
    focus = (r["title_tracks"] or [r["title"]])[0]
    links = data.streaming_links(r["artist"], focus if r["tracks"] else r["title"])
    tracks = (html.Details(className="tracklist", children=[
        html.Summary(f"Tracklist ({len(r['tracks'])} songs)"),
        html.Ol([html.Li([t, html.Span(" ★ title", className="title-mark") if any(t.startswith(x) for x in r["title_tracks"]) else None])
                 for t in r["tracks"]]),
    ]) if r["tracks"] else None)
    return html.Div(className="event", children=[
        html.H3([badge, f"{r['title']}"]),
        html.Div(f"💿 {r['type']} · release {r['release_date']}", className="venue"),
        html.Div(className="chips", children=[html.Span(f"★ {t}", className="chip") for t in r["title_tracks"]]) if r["title_tracks"] else None,
        tracks,
        html.Div(r["note"], className="hint"),
        html.Div([html.A(f"▶ {name}", href=url, target="_blank", className="linkbtn ghost") for name, url in links.items()]),
        html.Div([html.A(f"Source {i + 1}", href=s, target="_blank", className="srclink") for i, s in enumerate(r["sources"][:2])]),
        _actions(r["id"], ["playlist"]),
    ])


@app.callback(Output("events", "children"), Input("artist", "value"), Input("category", "value"),
              Input("city", "value"), Input("albums", "value"), Input("community-version", "data"))
def show_events(artist, category, city, albums, _version):
    name = data.artist_name(artist)
    if category == "fansign":
        rows = data.fansigns(artist)
        if not rows:
            return html.Div(f"No upcoming album fansign for {name} in the dataset - try Concert or Streaming.", className="empty")
        return [fansign_card(f, albums or 50) for f in rows]
    if category == "streaming":
        rows = data.releases(artist)
        return [release_card(r) for r in rows] or html.Div(f"No release for {name} in the dataset.", className="empty")
    rows = data.events(artist, "concert", city)
    if not rows:
        return html.Div(f"No concert for {name} in the dataset yet.", className="empty")
    return [event_card(e) for e in rows]


# ------------------------------------------------------------------- chat ----

def bubble_user(text):
    return html.Div(className="msg user", children=[html.Div(text, className="bubble")])


def _trace_items(r):
    items = []
    for t in r.get("trace", []):
        k = t["kind"]
        if k == "router":
            d = t["decision"]
            items.append(html.Li(["Router (", t["mode"], ") → ", html.B(", ".join(d.get("agents") or ["none"])), f" — {d.get('reason', '')}"]))
        elif k == "model":
            u = t["tokens"]
            gw = " · gateway cache replay" if t.get("gateway_cache") else ""
            items.append(html.Li(f"{t['agent']}: gpt-6-luna call · in {u['input']:,} (cached {u['cached_input']:,}) · "
                                 f"out {u['output']:,} · ${t['cost']:.5f} · {t['seconds']}s{gw}"))
        elif k == "tool":
            items.append(html.Li([f"{t['agent']} → tool ", html.Code(t["name"]), " ", html.Code(str(t["args"]))]))
        elif k == "guard":
            items.append(html.Li(["🛡️ guard ", html.B(t["name"]), f": {t['detail']}"]))
        elif k == "cache":
            items.append(html.Li("⚡ " + t["detail"]))
        else:
            items.append(html.Li(f"⚠️ {t.get('detail', '')}"))
    return items


def bubble_bot(r):
    meta = [html.Span(f"{agents.SPECIALISTS[a]['icon']} {agents.SPECIALISTS[a]['label']}", className="badge agent") for a in r.get("agents", [])]
    if r.get("cache_hit"):
        meta.append(html.Span("⚡ cached · $0", className="badge cache"))
    else:
        tok = r.get("tokens", {})
        meta.append(html.Span(f"{r.get('model_calls', 0)} model calls · {r.get('tool_calls', 0)} tools · "
                              f"{tok.get('input', 0) + tok.get('output', 0):,} tokens · ${r.get('cost', 0):.5f} · {r.get('seconds', 0)}s"))
    if r.get("gateway_hits"):
        meta.append(html.Span(f"↺ gateway cache ×{r['gateway_hits']} ($0)", className="badge cache",
                              title="Portkey replayed an identical earlier model response; not billed"))
    meta += [html.Span(f"🛡️ {g['name']}", className="badge guard", title=g["detail"]) for g in r.get("guards", [])]
    return html.Div(className="msg bot", children=[
        html.Img(src=MASCOT, className="avatar", alt="L.I.S.A."),
        html.Div(className="bubble", children=[
            dcc.Markdown(r["text"], link_target="_blank"),
            html.Div(meta, className="meta"),
            html.Details(className="trace", children=[html.Summary("Show agent trace"), html.Ol(_trace_items(r))]),
        ]),
    ])


def render(history, thinking=False):
    if not history and not thinking:
        return html.Div(className="welcome", children=[
            html.Img(src=MASCOT, style={"width": "84px"}),
            html.H3("Hi! I'm L.I.S.A. 💗"),
            html.Div("Pick an artist on the left and use the buttons on a card, or ask me anything about LISA, BTS or TXT concerts, fansigns and streaming."),
            html.Div(className="suggest", children=[html.Button(s, id={"type": "suggest", "i": i}, n_clicks=0) for i, s in enumerate(SUGGESTIONS)]),
        ])
    out = []
    for m in history:
        out.append(bubble_user(m["user"]) if m["role"] == "user" else bubble_bot(m["result"]))
    if thinking:
        out.append(html.Div(className="msg bot", children=[
            html.Img(src=MASCOT, className="avatar", alt=""),
            html.Div(className="bubble", children=[html.Div(className="typing", children=[html.Span(), html.Span(), html.Span()]),
                                                  html.Span("  routing to the right agent…", className="hint")]),
        ]))
    return out


@app.callback(Output("messages", "children"), Input("history", "data"), Input("pending", "data"))
def show_messages(history, pending):
    return render(history or [], thinking=bool(pending))


@app.callback(
    Output("pending", "data"), Output("history", "data", allow_duplicate=True), Output("chat-input", "value"),
    Input("send-btn", "n_clicks"), Input({"type": "card-act", "action": ALL, "ref": ALL}, "n_clicks"),
    Input({"type": "suggest", "i": ALL}, "n_clicks"),
    State("chat-input", "value"), State("history", "data"), State("artist", "value"),
    State("albums", "value"), State("minutes", "value"),
    prevent_initial_call=True,
)
def queue_message(_send, _cards, _suggest, text, history, artist, albums, minutes):
    trig = ctx.triggered_id
    # cards and suggestion chips are re-created on every selection change with n_clicks=0 - ignore those
    if not ctx.triggered or ctx.triggered[0]["value"] in (None, 0):
        return no_update, no_update, no_update
    history = history or []
    action, sel = None, {}
    if isinstance(trig, dict) and trig.get("type") == "suggest":
        text = SUGGESTIONS[trig["i"]]
    elif isinstance(trig, dict) and trig.get("type") == "card-act":
        action, ref = trig["action"], trig["ref"]
        sel = {"artist": artist}
        if data.event(ref):
            sel["event_id"] = ref
            title = data.event(ref)["title"]
        elif data.fansign(ref):
            sel.update(fansign_id=ref, albums=albums)
            title = data.fansign(ref)["title"] + (f" · {albums} albums" if action == "fansign" else "")
        else:
            sel.update(release_id=ref, minutes=minutes)
            title = f"{data.release(ref)['title']} · {minutes} min"
        text = f"{ACTION_LABELS[action]} · {title}"
    elif not (text or "").strip():
        return no_update, no_update, no_update
    text = text.strip()
    history = history + [{"role": "user", "user": text}]
    return {"text": text, "action": action, "sel": sel}, history, ""


@app.callback(Output("history", "data"), Output("pending", "data", allow_duplicate=True),
              Input("pending", "data"), State("history", "data"), prevent_initial_call=True)
def run_agents(pending, history):
    if not pending:
        return no_update, no_update
    spent = sum(m["result"].get("cost", 0) for m in (history or []) if m["role"] == "bot")
    message = "" if pending["action"] else pending["text"]
    result = agents.answer(message, pending["sel"], pending["action"], session_spent=spent)
    keep = {k: result.get(k) for k in ("text", "agents", "cache_hit", "tokens", "cost", "seconds", "model_calls", "gateway_hits",
                                       "tool_calls", "guards", "trace", "message")}
    return (history or []) + [{"role": "bot", "result": keep}], None


@app.callback(Output("send-btn", "disabled"), Input("pending", "data"))
def lock_send(pending):
    return bool(pending)


# ------------------------------------------------------------ usage meter ----

@app.callback(Output("meter", "children"), Output("usage-panel", "children"), Input("history", "data"))
def usage(history):
    bots = [m["result"] for m in (history or []) if m["role"] == "bot"]
    cost = sum(r.get("cost", 0) for r in bots)
    tokens = sum(r.get("tokens", {}).get("input", 0) + r.get("tokens", {}).get("output", 0) for r in bots)
    hits = sum(1 for r in bots if r.get("cache_hit"))
    guards = [g for r in bots for g in r.get("guards", [])]
    meter = [
        html.Span(["Answers ", html.B(len(bots))], className="pill"),
        html.Span(["Tokens ", html.B(f"{tokens:,}")], className="pill"),
        html.Span(["Cost ", html.B(f"${cost:.4f}"), f" / ${SESSION_BUDGET_USD:.2f} cap"], className="pill"),
        html.Span(["Cache hits ", html.B(hits)], className="pill"),
        html.Span(["🛡️ Guards ", html.B(len(guards))], className="pill"),
    ]

    def kpi(num, lbl):
        return html.Div(className="stat", children=[html.Div(num, className="num"), html.Div(lbl, className="lbl")])

    rows = [html.Tr([html.Td(r.get("message", "")[:70]), html.Td(", ".join(r.get("agents") or []) or "—"),
                     html.Td("⚡ cache" if r.get("cache_hit") else f"{r.get('model_calls', 0)} / {r.get('tool_calls', 0)}"),
                     html.Td(f"{r.get('tokens', {}).get('input', 0):,} / {r.get('tokens', {}).get('cached_input', 0):,} / {r.get('tokens', {}).get('output', 0):,}"),
                     html.Td(f"${r.get('cost', 0):.5f}"), html.Td("; ".join(g["name"] for g in r.get("guards", [])) or "—")]) for r in bots]
    panel = [
        html.Div(className="kpis", children=[kpi(str(len(bots)), "answers"), kpi(f"${cost:.4f}", f"spent of ${SESSION_BUDGET_USD:.2f} session cap"),
                                             kpi(str(hits), "answers served from cache ($0)"), kpi(str(len(guards)), "guardrail events")]),
        html.Table(className="usage-table", children=[
            html.Thead(html.Tr([html.Th("Question"), html.Th("Agents"), html.Th("Model calls / tools"),
                                html.Th("Input / cached / output tokens"), html.Th("Cost"), html.Th("Guards")])),
            html.Tbody(rows or [html.Tr([html.Td("No answers yet.", colSpan=6)])]),
        ]),
        html.P(key_status().split(" from ")[0] + ". Limits: 4 model calls per agent, 1,200 output tokens per call, "
               f"${SESSION_BUDGET_USD:.2f} per session, daily app cap in runtime/daily_spend.json.", className="hint"),
    ]
    return meter, panel


# ------------------------------------------------------- calendar + reports ----

@app.callback(Output("ics-download", "data"), Input({"type": "cal", "ref": ALL}, "n_clicks"), prevent_initial_call=True)
def download_ics(_clicks):
    if not ctx.triggered or ctx.triggered[0]["value"] in (None, 0):
        return no_update
    built = calendar_export.build(ctx.triggered_id["ref"])
    return dict(content=built[1], filename=built[0]) if built else no_update


@app.callback(Output("rep-status", "children"), Output("community-version", "data"), Output("reports-made", "data"),
              Input("rep-submit", "n_clicks"),
              State("artist", "value"), State("rep-retailer", "value"), State("rep-format", "value"),
              State("rep-date", "value"), State("rep-winners", "value"), State("rep-cut", "value"),
              State("community-version", "data"), State("reports-made", "data"), prevent_initial_call=True)
def report_cut(_n, artist, retailer, fmt, when, winners, cut, version, made):
    if (made or 0) >= community.MAX_REPORTS_PER_SESSION:
        return "🛡️ Limit reached: 3 reports per session.", no_update, no_update
    res = community.submit(artist, retailer, fmt, when, winners, cut)
    icon = {"accepted": "✅", "quarantined": "🛡️", "rejected": "⚠️"}[res["status"]]
    bump = (version or 0) + 1 if res["status"] == "accepted" else no_update
    return f"{icon} {res['reason']}", bump, (made or 0) + (res["status"] != "rejected")


@app.callback(Output("data-panel", "children"), Input("tabs", "value"), Input("community-version", "data"))
def data_panel(_tab, _v):
    ev = data.load("events")["events"]
    rel = data.releases()
    fs = data.fansigns()
    hist = data.load("fansign")["history"]
    c = community.counts()
    rows = [
        ("🎤 Concerts", f"{len(ev)} tours/cities · {sum(len(e['dates']) for e in ev)} show dates", "Sourced (Soompi, NOL, Ticketmaster SG, ThaiTicketMajor, tixCraft reporting)", "2026-10-25"),
        ("🎫 Ticketing", f"{sum(1 for e in ev if 'Not in our dataset' not in e['ticketing']['general_open'])}/{len(ev)} with sale times · "
                        f"{sum(1 for e in ev if e['ticketing']['price_note'][:1].isdigit() or e['ticketing']['price_note'][:3] in ('SGD', 'THB', 'NT$'))} with price tiers", "Sourced", "2026-10-25"),
        ("🎵 Setlists", f"{len(data.load('setlists')['setlists'])} published · {len(data.load('setlists')['no_setlist_yet'])} tours not started", "Official Charts", "2026-10-25"),
        ("🚆 Venues", f"{len(data.load('venues')['venues'])} venues · {sum(len(v['routes']) for v in data.load('venues')['venues'])} routes", "Standard transit routes; times approximate", "2026-10"),
        ("💿 Albums", f"{len(rel)} releases · {sum(len(r['tracks']) for r in rel)} tracks", "Sourced (label / press)", "2026-10-25"),
        ("✍️ Fansigns", f"{len(fs)} upcoming · {len(hist)} past cut reports", "SAMPLE (illustrative)", "—"),
        ("📝 Community reports", f"{c['accepted']} accepted · {c['quarantined']} quarantined", "Fans, via the report form", "live"),
    ]
    return html.Table(className="usage-table", children=[
        html.Thead(html.Tr([html.Th(h) for h in ("Category", "Coverage", "Source", "Checked")])),
        html.Tbody([html.Tr([html.Td(x) for x in r]) for r in rows]),
    ])


if __name__ == "__main__":
    # debug off + no reloader: one edit never spawns a second server.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8050")), debug=False, use_reloader=False)
