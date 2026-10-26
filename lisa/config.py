"""One place for the model, the API client, the price card and the safety limits.

The key is read from ``.env`` in the repo folder first, then one level above it (where
the teaching staff keep a shared ``.env``). Its value is never printed or logged.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("LISA_DATA_DIR", ROOT / "data"))
RUNTIME_DIR = ROOT / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True)

ENV_CANDIDATES = (ROOT / ".env", ROOT.parent / ".env")
ENV_FILE = next((p for p in ENV_CANDIDATES if p.exists()), None)
if ENV_FILE:
    load_dotenv(ENV_FILE)

PORTKEY_GATEWAY_URL = "https://api.portkey.ai/v1"

#: The only model the course key may call.
MODEL = "gpt-6-luna"

#: USD per 1M tokens for gpt-6-luna (OpenAI standard tier, MGT 409 Lecture 11).
PRICES = {"input": 0.10, "cached_input": 0.01, "cache_write": 0.125, "output": 0.50}

# Safety limits ---------------------------------------------------------------
MAX_TOOL_ROUNDS = 4            # model calls per specialist before we stop the loop
MAX_OUTPUT_TOKENS = 1200       # per specialist call (reasoning tokens included)
ROUTER_MAX_OUTPUT_TOKENS = 300
MAX_INPUT_CHARS = 1500         # longer messages are refused before any API call
SESSION_BUDGET_USD = float(os.getenv("LISA_SESSION_BUDGET_USD", "0.05"))
DAILY_BUDGET_USD = float(os.getenv("LISA_DAILY_BUDGET_USD", "2.00"))
CACHE_TTL_SECONDS = 6 * 3600


def key_status() -> str:
    """A human-readable note about where the key came from (never the key itself)."""
    if not os.getenv("PORTKEY_API_KEY"):
        looked = ", ".join(str(p) for p in ENV_CANDIDATES)
        return f"PORTKEY_API_KEY not found. Looked in: {looked}"
    return f"PORTKEY_API_KEY loaded from {ENV_FILE}" if ENV_FILE else "PORTKEY_API_KEY loaded from environment"


@lru_cache(maxsize=1)
def client() -> OpenAI:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(key_status() + ". Copy .env.example to .env and add your key.")
    return OpenAI(api_key=api_key, base_url=PORTKEY_GATEWAY_URL, timeout=60, max_retries=1)


def usage_dict(usage) -> dict:
    """Flatten a Responses API usage object into the four numbers we price."""
    details = getattr(usage, "input_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) or 0
    written = getattr(details, "cache_write_tokens", 0) or 0
    out_details = getattr(usage, "output_tokens_details", None)
    return {
        "input": usage.input_tokens,
        "cached_input": cached,
        "cache_write": written,
        "output": usage.output_tokens,
        "reasoning": getattr(out_details, "reasoning_tokens", 0) or 0,
    }


def cost_usd(u: dict) -> float:
    """Price one call. ``input`` includes the cached and cache-written tokens."""
    uncached = max(u["input"] - u["cached_input"] - u["cache_write"], 0)
    total = (
        uncached * PRICES["input"]
        + u["cached_input"] * PRICES["cached_input"]
        + u["cache_write"] * PRICES["cache_write"]
        + u["output"] * PRICES["output"]
    ) / 1_000_000
    return round(total, 8)
