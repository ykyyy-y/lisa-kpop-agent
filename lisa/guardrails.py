"""Code-level defenses. None of these rely on the model behaving well.

1. ``screen_input``     - refuses prompt-injection / secret-fishing messages before any API call.
2. ``filter_links``     - deletes every URL whose domain is not on the official allowlist.
3. ``enforce_disclaimer`` - fansign predictions always carry the "no guarantee" warning.
4. ``check_dates``      - flags any YYYY-MM-DD date the answer states that no tool returned.
5. ``Budget``           - per-session and per-day spending caps, checked before every call.
"""

from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import urlparse

from . import data
from .config import DAILY_BUDGET_USD, MAX_INPUT_CHARS, RUNTIME_DIR, SESSION_BUDGET_USD

DISCLAIMER_KO = "본 예측은 과거 데이터 기반이며 당첨을 보장하지 않습니다."
DISCLAIMER_EN = "This prediction is based on past data and does not guarantee a win."
DISCLAIMER = f"⚠️ {DISCLAIMER_EN} / {DISCLAIMER_KO}"

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (your|all|the) (instructions|rules|guidelines)",
    r"(reveal|print|show|repeat|leak).{0,30}(system prompt|instructions|hidden prompt|developer message)",
    r"(api[ _-]?key|portkey|\.env\b|secret key|(your|system|admin|developer) password)",
    r"you are now (?!going)",
    r"\b(jailbreak|DAN mode|developer mode)\b",
    r"(이전|위의|앞의).{0,6}(지시|명령|규칙).{0,6}(무시|잊어)",
    r"(시스템|system).{0,4}(프롬프트|prompt).{0,10}(보여|알려|출력)",
]

URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s)\]>\"'*]+"  # full links
    r"|\b(?:[a-z0-9-]+\.)+(?:com|net|org|co|kr|io|me|tv|ly|gg|app|xyz|top|shop|click|link|live|site|online|store|ru|cn|tk)"
    r"\b(?:/[^\s)\]>\"']*)?",  # bare domains such as stubhub.com/x
    re.I,
)
DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def screen_input(text: str) -> tuple[bool, str]:
    """Return (blocked, reason)."""
    if len(text) > MAX_INPUT_CHARS:
        return True, f"Message is longer than {MAX_INPUT_CHARS} characters."
    for pat in INJECTION_PATTERNS:
        if re.search(pat, text, re.I):
            return True, "Message looks like a prompt-injection or secret-extraction attempt."
    return False, ""


def _domain_ok(url: str, allowed: set[str]) -> bool:
    host = urlparse(url if "://" in url else "https://" + url).netloc.lower().split(":")[0]
    host = host.removeprefix("www.")
    return any(host == d or host.endswith("." + d) for d in allowed)


def filter_links(text: str) -> tuple[str, list[str]]:
    """Remove non-allowlisted links. Returns (clean_text, removed_urls)."""
    allowed = data.allowed_domains()
    removed: list[str] = []

    def repl(m: re.Match) -> str:
        url = m.group(0).rstrip(".,;:!?")
        tail = m.group(0)[len(url):]
        if _domain_ok(url, allowed):
            return m.group(0)
        removed.append(url)
        return "[link removed: not an official vendor]" + tail

    return URL_RE.sub(repl, text), removed


def enforce_disclaimer(text: str) -> tuple[str, bool]:
    """Append the disclaimer if the model left it out. Returns (text, was_added)."""
    if DISCLAIMER_KO in text and DISCLAIMER_EN in text:
        return text, False
    return text.rstrip() + "\n\n" + DISCLAIMER, True


def check_dates(text: str, tool_outputs: list[str]) -> list[str]:
    """Dates in the answer that appear in no tool output (today's date is allowed)."""
    blob = " ".join(tool_outputs) + " " + date.today().isoformat()
    return sorted({d for d in DATE_RE.findall(text) if d not in blob})


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """Spending caps. Session spend lives in the Dash store; daily spend in a file."""

    DAILY_FILE = RUNTIME_DIR / "daily_spend.json"

    def __init__(self, session_spent: float = 0.0, session_cap: float = SESSION_BUDGET_USD,
                 daily_cap: float = DAILY_BUDGET_USD):
        self.session_spent = session_spent
        self.session_cap = session_cap
        self.daily_cap = daily_cap

    def _daily(self) -> dict:
        try:
            d = json.loads(self.DAILY_FILE.read_text())
        except Exception:
            d = {}
        return d if d.get("date") == date.today().isoformat() else {"date": date.today().isoformat(), "usd": 0.0}

    def check(self) -> None:
        if self.session_spent >= self.session_cap:
            raise BudgetExceeded(f"Session budget of ${self.session_cap:.2f} reached (spent ${self.session_spent:.4f}).")
        if self._daily()["usd"] >= self.daily_cap:
            raise BudgetExceeded(f"Daily app budget of ${self.daily_cap:.2f} reached.")

    def add(self, usd: float) -> None:
        self.session_spent += usd
        d = self._daily()
        d["usd"] = round(d["usd"] + usd, 8)
        self.DAILY_FILE.write_text(json.dumps(d))
