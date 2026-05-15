"""Pure-Python accessors for cached LLM features.

Strategy code calls these to gate decisions:

    from llm.features import macro_regime, sentiment, events, news_volume

    regime = macro_regime(today)            # → 'risk_on' | 'risk_off' | 'neutral' | 'shock' | None
    sent = sentiment("RELIANCE", today)     # → {'score', 'confidence', 'is_actionable'} | None
    evts = events("RELIANCE", today)        # → 7 categories, each {'fired': bool, 'severity': 0..1}
    n = news_volume("RELIANCE", today)      # → int, article count (0 == no news that day)

Point-in-time semantics: each cache cell was classified using only data
available as of `date`. The accessor never sees the future. If a cell has not
yet been classified, the accessor returns None (or the events default of all
zeros) — the strategy treats absence as "no signal" rather than failing.

The accessor uses cache_get_latest, which returns the most recently written
row for (date, ticker, model_id) regardless of prompt_hash. This means a
prompt-version bump invalidates only what gets re-classified — already-stale
rows survive until the next batch run.

`news_volume` reads the raw news table rather than the LLM cache: it answers
"did news exist for this ticker on this date" and lets strategies separate
'no-news' from a sentiment of 0.0 (which is the empty-news short-circuit
default returned by the sentiment classifier).
"""
from __future__ import annotations

import os
from datetime import date

from dotenv import load_dotenv

from data.ingest_news import count_news

from .cache import (
    MACRO_TICKER_SENTINEL,
    cache_get_latest,
    events_ticker_key,
    sentiment_ticker_key,
)

load_dotenv()

# When None, accessors find a cache row regardless of which model wrote it —
# the right default since top-tier models are functionally interchangeable
# for our 4-class regime / [-1,+1] sentiment / 7-flag events tasks. Set
# LLM_FEATURE_MODEL_ID in .env only if you specifically want strict isolation
# (e.g. an ablation study comparing two models' classifications).
DEFAULT_MODEL_ID: str | None = os.getenv("LLM_FEATURE_MODEL_ID") or None

_EVENT_FLAGS = (
    "earnings", "guidance_change", "m_and_a", "regulatory",
    "executive_change", "layoffs", "product_launch",
)
EVENTS_DEFAULT = {k: {"fired": False, "severity": 0.0} for k in _EVENT_FLAGS}


def macro_regime(d: date, model_id: str | None = DEFAULT_MODEL_ID) -> str | None:
    """Return the regime label for date `d`, or None if not yet classified."""
    out = cache_get_latest(d.isoformat(), MACRO_TICKER_SENTINEL, model_id)
    return out.get("regime") if out else None


def sentiment(
    ticker: str, d: date, model_id: str | None = DEFAULT_MODEL_ID
) -> dict | None:
    """Return {'score', 'confidence'} for (ticker, date), or None if no row."""
    return cache_get_latest(d.isoformat(), sentiment_ticker_key(ticker), model_id)


def events(
    ticker: str, d: date, model_id: str | None = DEFAULT_MODEL_ID
) -> dict:
    """Return the 7 event categories for (ticker, date). Each value is a
    dict with shape {'fired': bool, 'severity': float in [0,1]}. Missing →
    all categories not-fired with severity 0.

    Strategy usage:
        evts = events("RELIANCE", today)
        if evts["regulatory"]["fired"] and evts["regulatory"]["severity"] > 0.5:
            tighten_stop()
    """
    out = cache_get_latest(d.isoformat(), events_ticker_key(ticker), model_id)
    return out if out else EVENTS_DEFAULT.copy()


def news_volume(ticker: str, d: date) -> int:
    """Return the news article count for (ticker, date). Zero means no news
    was ingested for that day, which lets strategies distinguish a quiet day
    from a day with balanced positive/negative coverage where sentiment ≈ 0.
    """
    return count_news(ticker, d)
