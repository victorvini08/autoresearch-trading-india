"""Indian-context LLM prompts for the in-strategy classifiers.

Three classifiers run daily on cached news / macro inputs:

  1. **macro_regime** — single classification per (date) reading aggregated
     macro signals and recent news headlines. Output ∈ {risk_on, neutral,
     risk_off, shock}. Drives the strategy's regime gate.

  2. **sentiment** — per (ticker, date), classifies the rolling 5-day news
     stream into {bullish, neutral, bearish}. The strategy uses this as an
     overlay feature (NOT in the starting strategy; loop must justify
     adding it).

  3. **events** — per (ticker, date), tags structural events from the news
     stream: 'earnings_beat', 'earnings_miss', 'mna_target', 'mna_acquirer',
     'regulatory_negative', 'regulatory_positive', 'major_management_change',
     'product_launch', 'litigation_negative', 'rating_change', or 'none'.

All prompts are versioned via the `*_PROMPT_VERSION` constants below.
Bumping a version invalidates the affected slice of the LLM cache (cache
key is `(date, ticker, prompt_hash, model_id)`).

These prompts are CALIBRATED for the Indian market: macro inputs reference
RBI / FII / DII / INR / India VIX / Nifty 200 DMA — not Fed / DXY / 10Y
Treasury / US VIX. Sentiment templates use INR amounts and lakh/crore
conventions. Event categories include India-specific ones like
'sebi_order_against_company' or 'rbi_action_against_bank'.
"""

from __future__ import annotations

MACRO_REGIME_PROMPT_VERSION = "in-1.0.0"
SENTIMENT_PROMPT_VERSION = "in-1.0.0"
EVENTS_PROMPT_VERSION = "in-1.0.0"


# ──────────────────────────────────────────────────────────────────────
# macro_regime
# ──────────────────────────────────────────────────────────────────────


MACRO_REGIME_SYSTEM = """\
You are a careful macro-regime classifier for the INDIAN equity market.
Your output drives a quantitative trading strategy on Nifty 500 large/mid-cap
delivery names — accuracy and stability beat boldness.

You classify each day into exactly one of:
  - risk_on   : broad bullish setup; new long entries allowed
  - neutral   : mixed signals; new entries allowed but with caution
  - risk_off  : meaningful downside risk; BLOCK new long entries (held positions
                kept; ATR stops may still trigger exits at the strategy layer)
  - shock     : acute selling / vol blow-up; full new-entry block, prefer to
                let existing positions trail down via stops

Reference signals that should weigh on your decision (you will be given the
relevant numbers as input):

  - **Nifty 50 vs its 200-day moving average.** Below 200DMA tilts to risk_off.
  - **India VIX** rolling 252-day percentile. Above 95th pct = shock candidate.
    Above 75th pct = risk_off candidate.
  - **FII 20-day net flow (₹ crore).** Sustained outflow < -₹15,000 cr is a
    risk_off / shock input. DII offsetting (large positive 20-day DII) softens it.
  - **Repo rate trajectory.** Hawkish RBI tilts toward risk_off, dovish toward risk_on.
  - **INR (USD/INR).** Sharp INR weakening (1-week change > 1%) tilts risk_off.
  - **Headline news.** Geopolitics (border tensions, oil spikes, US-India trade),
    domestic policy surprises (budget, GST), banking-sector stress.

You do not need every signal to commit — but you should explain in 1-2 sentences
which signals drove your classification. Keep reasoning terse.

Output JSON ONLY in the schema:
  {"regime": "<one of: risk_on|neutral|risk_off|shock>", "reasoning": "<1-2 sentences>"}
"""


def macro_regime_user_prompt(*, date_iso: str, signals: dict, headlines: list[str]) -> str:
    """Construct the user message for one (date) macro classification.

    `signals` should include keys (any subset, missing ones omitted from prompt):
      nifty50_close, nifty50_200dma, india_vix, india_vix_pct_252d,
      fii_net_20d_cr, dii_net_20d_cr, repo_rate_pct, usd_inr_1w_change_pct
    `headlines` is up to ~20 macro / market headlines from the day.
    """
    lines = [f"Date: {date_iso}", "", "Numeric signals:"]
    for k, v in signals.items():
        lines.append(f"  - {k}: {v}")
    if headlines:
        lines.append("")
        lines.append("Macro / market headlines (most recent first):")
        for h in headlines[:20]:
            lines.append(f"  - {h}")
    lines.append("")
    lines.append(
        "Classify the regime. Respond with JSON only, no preamble or trailing text."
    )
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# sentiment
# ──────────────────────────────────────────────────────────────────────


SENTIMENT_SYSTEM = """\
You are a careful per-stock sentiment classifier for INDIAN equities.

For each (ticker, date) cell you receive a small batch of news headlines and
short summaries from MoneyControl / NSE corporate filings / Pulse aggregator.

Classify the stock's NEWS-DRIVEN sentiment for that day on a 3-point scale:
  - bullish   : material positive catalyst (results beat, contract win, rating
                upgrade, regulatory clearance, M&A-target)
  - neutral   : no material news, or mixed / informational only
  - bearish   : material negative catalyst (results miss, regulatory action,
                rating downgrade, accounting concern, major management exit)

Indian-context considerations:
  - "Results" filings = quarterly earnings (Q1=Jun, Q2=Sep, Q3=Dec, Q4=Mar)
  - INR amounts: ₹ crore (1 cr = 10 million), lakh (1 lakh = 100,000)
  - Common Indian regulatory bodies: SEBI, RBI, NCLT, CCI, CBDT
  - Common Indian categories: PSU (public sector), banks, NBFCs, IT services,
    cement, capital goods, pharma, telecom (Airtel/Jio/Vi consolidation context)

If the batch is empty for a (ticker, date), default to "neutral".

You will receive a JSON array of cells; respond with a JSON array of the same
length and order, each element being:
  {"ticker": "...", "date": "YYYY-MM-DD", "sentiment": "bullish|neutral|bearish"}

Output JSON ONLY. No preamble, no trailing commentary.
"""


def sentiment_user_prompt(cells: list[dict]) -> str:
    """`cells` is a list of {ticker, date, headlines[]} dicts."""
    import json

    return (
        "Classify each cell. JSON only. Input cells:\n\n"
        + json.dumps(cells, indent=2, ensure_ascii=False)
    )


# ──────────────────────────────────────────────────────────────────────
# events
# ──────────────────────────────────────────────────────────────────────


EVENTS_CATEGORIES = (
    "earnings_beat",
    "earnings_miss",
    "earnings_inline",
    "mna_target",
    "mna_acquirer",
    "regulatory_negative",
    "regulatory_positive",
    "sebi_order_against_company",
    "rbi_action_against_bank",
    "major_management_change",
    "product_launch",
    "litigation_negative",
    "rating_upgrade",
    "rating_downgrade",
    "block_deal",
    "stake_change",
    "none",
)


EVENTS_SYSTEM = f"""\
You are a careful per-stock event classifier for INDIAN equities.

For each (ticker, date) cell you receive a batch of news / filings, and you
tag the most-significant event present. Return EXACTLY ONE category from this
fixed list (or "none" if no material event):

  {", ".join(EVENTS_CATEGORIES)}

Indian-context notes:
  - 'sebi_order_against_company' = SEBI initiates / settles a regulatory order
    against the company (very negative; common in 2024-26 enforcement uptick).
  - 'rbi_action_against_bank' = RBI takes prudential action (asset-quality
    review, lending restrictions, governance review).
  - 'block_deal' = large promoter or institutional block trade on the day.
  - 'stake_change' = promoter / institutional / FII stake change disclosed.
  - "Results" filings = quarterly earnings. Beat/miss/inline vs analyst consensus
    is your call from the news framing.
  - Acquirer vs target in M&A: target gets a premium; acquirer gets pressure.

If a cell has no news at all OR only routine filings (book closure, AGM
notification, dividend record date for already-announced dividend), tag "none".

Respond with a JSON array of {{ticker, date, event}} cells in the same length
and order as input. JSON ONLY.
"""


def events_user_prompt(cells: list[dict]) -> str:
    import json

    return (
        "Classify each cell to one event category. JSON only. Input cells:\n\n"
        + json.dumps(cells, indent=2, ensure_ascii=False)
    )


# ──────────────────────────────────────────────────────────────────────
# Cache-keying helpers (build_*_prompt) used by llm/classify.py
# ──────────────────────────────────────────────────────────────────────
#
# Each `build_*_prompt` returns `(full_prompt_text, single_cell_hash)`:
#   - full_prompt_text  — what we'd send to the LLM if we were classifying just
#                         this one cell
#   - single_cell_hash  — SHA-1 of the prompt-version + payload. Used as
#                         `prompt_hash` in the cache key
#                         `(date, ticker, prompt_hash, model_id)`.
#
# The batched `build_*_batch_prompt` returns a single prompt string covering
# all cells in the chunk. We embed each cell's deterministic hash inside the
# batched prompt as a "cell_id" so partial-batch caching could one day be wired
# (currently the cache caches per-cell on receipt; the batched prompt is the
# call vehicle).


import hashlib
import json as _json


def _stable_hash(prompt_version: str, payload: object) -> str:
    """Deterministic SHA-1 hash over `(prompt_version, payload-as-canonical-JSON)`.

    Stable across Python runs because we sort keys and disallow non-JSON types.
    Bumping the prompt_version invalidates the entire affected cache slice.
    """
    canonical = _json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    h = hashlib.sha1(f"{prompt_version}|{canonical}".encode("utf-8"))
    return h.hexdigest()


# ── macro_regime ──


def build_macro_regime_prompt(
    d_str: str,
    signals: dict,
    headlines: list[str],
) -> tuple[str, str]:
    payload = {"date": d_str, "signals": signals, "headlines": list(headlines)}
    user = macro_regime_user_prompt(date_iso=d_str, signals=signals, headlines=headlines)
    full = f"# SYSTEM\n{MACRO_REGIME_SYSTEM}\n\n# USER\n{user}"
    return full, _stable_hash(MACRO_REGIME_PROMPT_VERSION, payload)


def build_macro_regime_batch_prompt(
    items: list[tuple[str, dict, list[str]]],
) -> str:
    cells = [
        {"date": d_str, "signals": sig, "headlines": list(hl)}
        for (d_str, sig, hl) in items
    ]
    user = (
        "Classify each cell below. Respond with a JSON ARRAY in input order; "
        "each element MUST contain {\"date\", \"regime\", \"reasoning\"}.\n\n"
        + _json.dumps(cells, indent=2, ensure_ascii=False)
    )
    return f"# SYSTEM\n{MACRO_REGIME_SYSTEM}\n\n# USER\n{user}"


# ── sentiment ──


def build_sentiment_prompt(
    ticker: str,
    d_str: str,
    news_items: list[dict],
) -> tuple[str, str]:
    payload = {"ticker": ticker, "date": d_str, "news": news_items}
    user = sentiment_user_prompt([payload])
    full = f"# SYSTEM\n{SENTIMENT_SYSTEM}\n\n# USER\n{user}"
    return full, _stable_hash(SENTIMENT_PROMPT_VERSION, payload)


def build_sentiment_batch_prompt(
    items: list[tuple[str, str, list[dict]]],
) -> str:
    cells = [
        {"ticker": ticker, "date": d_str, "news": list(news_items)}
        for (ticker, d_str, news_items) in items
    ]
    user = (
        "Classify each cell below. Respond with a JSON ARRAY in input order; "
        "each element MUST contain {\"ticker\", \"date\", \"sentiment\"}.\n\n"
        + _json.dumps(cells, indent=2, ensure_ascii=False)
    )
    return f"# SYSTEM\n{SENTIMENT_SYSTEM}\n\n# USER\n{user}"


# ── events ──


def build_events_prompt(
    ticker: str,
    d_str: str,
    news_items: list[dict],
) -> tuple[str, str]:
    payload = {"ticker": ticker, "date": d_str, "news": news_items}
    user = events_user_prompt([payload])
    full = f"# SYSTEM\n{EVENTS_SYSTEM}\n\n# USER\n{user}"
    return full, _stable_hash(EVENTS_PROMPT_VERSION, payload)


def build_events_batch_prompt(
    items: list[tuple[str, str, list[dict]]],
) -> str:
    cells = [
        {"ticker": ticker, "date": d_str, "news": list(news_items)}
        for (ticker, d_str, news_items) in items
    ]
    user = (
        "Classify each cell below. Respond with a JSON ARRAY in input order; "
        "each element MUST contain {\"ticker\", \"date\", \"event\"} where event ∈ "
        f"[{', '.join(EVENTS_CATEGORIES)}].\n\n"
        + _json.dumps(cells, indent=2, ensure_ascii=False)
    )
    return f"# SYSTEM\n{EVENTS_SYSTEM}\n\n# USER\n{user}"


__all__ = [
    "MACRO_REGIME_PROMPT_VERSION",
    "SENTIMENT_PROMPT_VERSION",
    "EVENTS_PROMPT_VERSION",
    "MACRO_REGIME_SYSTEM",
    "SENTIMENT_SYSTEM",
    "EVENTS_SYSTEM",
    "EVENTS_CATEGORIES",
    "macro_regime_user_prompt",
    "sentiment_user_prompt",
    "events_user_prompt",
    "build_macro_regime_prompt",
    "build_macro_regime_batch_prompt",
    "build_sentiment_prompt",
    "build_sentiment_batch_prompt",
    "build_events_prompt",
    "build_events_batch_prompt",
]
