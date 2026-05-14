"""Ingest-time LLM batch classifiers.

Each `classify_*_batch` function:
  1. Computes the per-cell single-cell prompt_hash for cache lookup
  2. Skips cells already in cache (zero LLM calls for those)
  3. Chunks remaining cells into groups of `chunk_size`, builds ONE batched
     prompt per chunk, calls the provider once per chunk
  4. Parses the returned JSON array, validates per-row, caches valid rows
     individually (under their original single-cell prompt_hash)

Key invariant: cache rows are keyed by single-cell prompt_hash + model_id, so
existing cache rows from a pre-batching run remain valid. Switching to
batching does not invalidate any cache entries.

Failure semantics:
  - Per-row validation failure → that row is skipped, not cached, no raise.
    Other rows in the same batch are still cached. Re-running picks up the
    skipped row and retries.
  - Whole-batch parse failure (no JSON array extractable) → raise RuntimeError.
  - Zero valid rows in a parsed array → raise RuntimeError. Suspicious LLM
    output that we shouldn't silently swallow.
  - Missing cells (LLM returned fewer rows than requested) → detect, log,
    retry the missing cells in a smaller sub-chunk; if still missing, raise.
    See `docs/learnings-from-us-build.md` §4.1 for the silent-drop bug this
    avoids. Previously these cells were `continue`-skipped, leaving cache
    holes that strategies read as defaults.

Backtests later read from cache only — zero provider calls per iteration.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from typing import Iterable, Iterator, TypeVar

from data.ingest_macro import read_macro
from data.ingest_news import read_news

from .cache import (
    MACRO_TICKER_SENTINEL,
    cache_get,
    cache_put,
    events_ticker_key,
    sentiment_ticker_key,
)
from .prompts import (
    build_events_batch_prompt,
    build_events_prompt,
    build_macro_regime_batch_prompt,
    build_macro_regime_prompt,
    build_sentiment_batch_prompt,
    build_sentiment_prompt,
)
from .provider import Provider

logger = logging.getLogger(__name__)

_MACRO_INDICATORS = ["DGS10", "VIXCLS", "T10Y2Y", "BAMLH0A0HYM2", "USEPUINDXD"]
_ALLOWED_REGIMES = {"risk_on", "risk_off", "neutral", "shock"}

_DEFAULT_CHUNK_SIZE = 50
_MIN_RETRY_CHUNK_SIZE = 5

T = TypeVar("T")


def _chunked(items: list[T], n: int) -> Iterator[list[T]]:
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _fred_snapshot(d: date) -> dict[str, float]:
    """Most recent value of each macro indicator on or before `d`."""
    start = (d - timedelta(days=10)).isoformat()
    end = d.isoformat()
    snap: dict[str, float] = {}
    for series_id in _MACRO_INDICATORS:
        df = read_macro(series_id, start, end)
        if not df.empty:
            snap[series_id] = float(df["value"].iloc[-1])
    return snap


def _extract_json_obj(text: str) -> dict | None:
    """Best-effort JSON object extraction. Returns None if no parse succeeds."""
    candidates = [text.strip()]
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidates.insert(0, fence.group(1))
    obj = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if obj:
        candidates.append(obj.group())
    for c in candidates:
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            continue
    return None


def _extract_json_array(text: str) -> list | None:
    """Best-effort JSON array extraction (for batched LLM responses)."""
    candidates = [text.strip()]
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        candidates.insert(0, fence.group(1))
    arr = re.search(r"\[.*\]", text, re.DOTALL)
    if arr:
        candidates.append(arr.group())
    for c in candidates:
        try:
            parsed = json.loads(c)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


# --- macro_regime ---


def _validate_macro(out: dict) -> bool:
    return (
        isinstance(out, dict)
        and out.get("regime") in _ALLOWED_REGIMES
        and isinstance(out.get("confidence"), (int, float))
        and 0 <= float(out["confidence"]) <= 1
        and isinstance(out.get("reasoning"), str)
    )


def _process_macro_chunk(
    chunk: list[tuple[date, str, dict[str, float], list[str], str]],
    provider: Provider,
    out: dict[date, dict],
) -> list[tuple[date, str, dict[str, float], list[str], str]]:
    """Run one batched LLM call for a macro chunk, write valid cells to `out`
    and the cache, and return the list of cells the LLM did NOT return (or
    returned invalid). Caller decides whether to retry or raise.

    Raises on whole-batch parse failure or zero-valid (those are signal of
    a broken response, not a partial drop).
    """
    items = [(d_str, fred, headlines) for _, d_str, fred, headlines, _ in chunk]
    prompt = build_macro_regime_batch_prompt(items)
    raw = provider.classify(prompt)
    results = _extract_json_array(raw)
    if results is None:
        raise RuntimeError(
            f"macro_regime batch [{items[0][0]}..{items[-1][0]}] "
            f"could not be parsed as a JSON array. Got: {raw[:300]}"
        )
    results_by_date = {
        r.get("date"): r for r in results if isinstance(r, dict)
    }
    valid = 0
    missing: list[tuple[date, str, dict[str, float], list[str], str]] = []
    for d, d_str, fred, headlines, single_hash in chunk:
        entry = results_by_date.get(d_str)
        if entry is None or not _validate_macro(entry):
            missing.append((d, d_str, fred, headlines, single_hash))
            continue
        cache_value = {
            "regime": entry["regime"],
            "confidence": float(entry["confidence"]),
            "reasoning": entry["reasoning"],
        }
        cache_put(
            d_str, MACRO_TICKER_SENTINEL, single_hash,
            provider.model_id, cache_value,
        )
        out[d] = cache_value
        valid += 1
    if valid == 0:
        raise RuntimeError(
            f"macro_regime batch [{items[0][0]}..{items[-1][0]}] "
            f"had 0 valid entries out of {len(chunk)}. Got: {raw[:300]}"
        )
    return missing


def classify_macro_regime_batch(
    dates: list[date],
    provider: Provider,
    recent_news_by_date: dict[date, list[str]] | None = None,
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> dict[date, dict]:
    """Classify each date's macro regime. Cached cells skip the provider call.

    Internally batches the LLM calls by `chunk_size` to amortize subprocess
    startup overhead — for ~1750 days this is ~35 calls instead of ~1750.

    `recent_news_by_date[d]` is the optional list of headlines for the LLM to
    consider on date `d`. Pass None or empty dict for FRED-only classification.
    """
    recent_news_by_date = recent_news_by_date or {}
    out: dict[date, dict] = {}

    # Phase 1: cache lookup, accumulate uncached cells with their single-cell hashes
    pending: list[tuple[date, str, dict[str, float], list[str], str]] = []
    for d in dates:
        d_str = d.isoformat()
        fred_values = _fred_snapshot(d)
        headlines = recent_news_by_date.get(d, [])
        _, single_hash = build_macro_regime_prompt(d_str, fred_values, headlines)
        cached = cache_get(d_str, MACRO_TICKER_SENTINEL, single_hash, provider.model_id)
        if cached is not None:
            out[d] = cached
        else:
            pending.append((d, d_str, fred_values, headlines, single_hash))

    # Phase 2: batch the uncached cells, one LLM call per chunk
    for chunk in _chunked(pending, chunk_size):
        missing = _process_macro_chunk(chunk, provider, out)
        if missing:
            # Silent-drop guard (see docs/learnings-from-us-build.md §4.1):
            # LLM returned fewer/invalid cells than requested. Log explicitly
            # and retry the missing cells in a smaller chunk before giving up.
            missing_keys = [m[1] for m in missing]
            retry_size = max(_MIN_RETRY_CHUNK_SIZE, chunk_size // 4)
            logger.warning(
                "macro_regime batch dropped %d/%d cells (dates=%s); "
                "retrying with chunk_size=%d",
                len(missing), len(chunk), missing_keys, retry_size,
            )
            still_missing: list[
                tuple[date, str, dict[str, float], list[str], str]
            ] = []
            for sub_chunk in _chunked(missing, retry_size):
                still_missing.extend(
                    _process_macro_chunk(sub_chunk, provider, out)
                )
            if still_missing:
                still_keys = [m[1] for m in still_missing]
                logger.error(
                    "macro_regime retry failed: %d cells still missing "
                    "after smaller-chunk retry (dates=%s)",
                    len(still_missing), still_keys,
                )
                raise RuntimeError(
                    f"macro_regime classifier dropped {len(still_missing)} "
                    f"cells even after retry: {still_keys}"
                )

    return out


# --- sentiment ---

_SENTIMENT_DEFAULT = {"score": 0.0, "confidence": 0.0, "is_actionable": False}


def _validate_sentiment(out: dict) -> bool:
    return (
        isinstance(out, dict)
        and isinstance(out.get("score"), (int, float))
        and -1.0 <= float(out["score"]) <= 1.0
        and isinstance(out.get("confidence"), (int, float))
        and 0.0 <= float(out["confidence"]) <= 1.0
        and isinstance(out.get("is_actionable"), bool)
    )


def _news_for(ticker: str, d: date) -> list[dict]:
    df = read_news(ticker, d.isoformat(), d.isoformat())
    return [
        {"headline": row.headline, "summary": row.summary or ""}
        for row in df.itertuples()
    ]


def _process_sentiment_chunk(
    chunk: list[tuple[tuple[str, date], str, str, list[dict], str, str]],
    provider: Provider,
    out: dict[tuple[str, date], dict],
) -> list[tuple[tuple[str, date], str, str, list[dict], str, str]]:
    """Run one batched LLM call for a sentiment chunk. Returns cells the LLM
    did not return (or returned invalid) so the caller can retry."""
    items = [(ticker, d_str, news_items)
             for _, ticker, d_str, news_items, _, _ in chunk]
    prompt = build_sentiment_batch_prompt(items)
    raw = provider.classify(prompt)
    results = _extract_json_array(raw)
    if results is None:
        raise RuntimeError(
            f"sentiment batch ({chunk[0][1]} {chunk[0][2]}..) "
            f"could not be parsed as a JSON array. Got: {raw[:300]}"
        )
    results_by_key = {
        (r.get("ticker"), r.get("date")): r
        for r in results if isinstance(r, dict)
    }
    valid = 0
    missing: list[tuple[tuple[str, date], str, str, list[dict], str, str]] = []
    for key, ticker, d_str, news_items, key_ticker, single_hash in chunk:
        entry = results_by_key.get((ticker, d_str))
        if entry is None or not _validate_sentiment(entry):
            # Silent-drop fix (see docs/learnings-from-us-build.md §4.1):
            # rather than `continue`-skipping this cell and leaving a cache
            # hole, collect it for explicit retry / raise by the caller.
            missing.append(
                (key, ticker, d_str, news_items, key_ticker, single_hash)
            )
            continue
        cache_value = {
            "score": float(entry["score"]),
            "confidence": float(entry["confidence"]),
            "is_actionable": bool(entry["is_actionable"]),
        }
        cache_put(
            d_str, key_ticker, single_hash, provider.model_id, cache_value,
        )
        out[key] = cache_value
        valid += 1
    if valid == 0:
        raise RuntimeError(
            f"sentiment batch ({chunk[0][1]} {chunk[0][2]}..) "
            f"had 0 valid entries out of {len(chunk)}. Got: {raw[:300]}"
        )
    return missing


def classify_sentiment_batch(
    pairs: list[tuple[str, date]],
    provider: Provider,
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> dict[tuple[str, date], dict]:
    """Classify (ticker, date) sentiment. Empty-news cells short-circuit to
    {score: 0, confidence: 0} with NO LLM call. Non-empty cells are batched
    by `chunk_size` to amortize subprocess overhead.
    """
    out: dict[tuple[str, date], dict] = {}

    # Phase 1: short-circuit empty-news, then cache lookup per (ticker, date)
    pending: list[
        tuple[tuple[str, date], str, str, list[dict], str, str]
    ] = []  # (key, ticker, d_str, news_items, key_ticker, single_hash)
    for ticker, d in pairs:
        d_str = d.isoformat()
        news_items = _news_for(ticker, d)
        if not news_items:
            out[(ticker, d)] = _SENTIMENT_DEFAULT.copy()
            continue
        _, single_hash = build_sentiment_prompt(ticker, d_str, news_items)
        key_ticker = sentiment_ticker_key(ticker)
        cached = cache_get(d_str, key_ticker, single_hash, provider.model_id)
        if cached is not None:
            out[(ticker, d)] = cached
        else:
            pending.append(
                ((ticker, d), ticker, d_str, news_items, key_ticker, single_hash)
            )

    # Phase 2: batched LLM calls
    for chunk in _chunked(pending, chunk_size):
        missing = _process_sentiment_chunk(chunk, provider, out)
        if missing:
            # Silent-drop guard (see docs/learnings-from-us-build.md §4.1):
            # Sonnet under load sometimes returns fewer cells than requested.
            # Log the (ticker, date) cells the LLM dropped, then retry them
            # with a smaller chunk. If still missing after retry, raise — do
            # NOT leave silent cache holes for the strategy to read as default
            # sentiment.
            missing_keys = [(m[1], m[2]) for m in missing]
            retry_size = max(_MIN_RETRY_CHUNK_SIZE, chunk_size // 4)
            logger.warning(
                "sentiment batch dropped %d/%d cells (cells=%s); "
                "retrying with chunk_size=%d",
                len(missing), len(chunk), missing_keys, retry_size,
            )
            still_missing: list[
                tuple[tuple[str, date], str, str, list[dict], str, str]
            ] = []
            for sub_chunk in _chunked(missing, retry_size):
                still_missing.extend(
                    _process_sentiment_chunk(sub_chunk, provider, out)
                )
            if still_missing:
                still_keys = [(m[1], m[2]) for m in still_missing]
                logger.error(
                    "sentiment retry failed: %d cells still missing "
                    "after smaller-chunk retry (cells=%s)",
                    len(still_missing), still_keys,
                )
                raise RuntimeError(
                    f"sentiment classifier dropped {len(still_missing)} "
                    f"cells even after retry: {still_keys}"
                )

    return out


# --- events ---

_EVENT_FLAGS = (
    "earnings", "guidance_change", "m_and_a", "regulatory",
    "executive_change", "layoffs", "product_launch",
)
_EVENTS_DEFAULT = {k: {"fired": False, "severity": 0.0} for k in _EVENT_FLAGS}


def _validate_events(out: dict) -> bool:
    """Each event category must be {fired: bool, severity: float in [0,1]}."""
    if not isinstance(out, dict):
        return False
    for k in _EVENT_FLAGS:
        v = out.get(k)
        if not isinstance(v, dict):
            return False
        fired = v.get("fired")
        sev = v.get("severity")
        if not isinstance(fired, bool):
            return False
        if not isinstance(sev, (int, float)) or not (0.0 <= float(sev) <= 1.0):
            return False
        # Internal consistency: not-fired must have severity 0
        if (not fired) and float(sev) != 0.0:
            return False
    return True


def _process_events_chunk(
    chunk: list[tuple[tuple[str, date], str, str, list[dict], str, str]],
    provider: Provider,
    out: dict[tuple[str, date], dict],
) -> list[tuple[tuple[str, date], str, str, list[dict], str, str]]:
    """Run one batched LLM call for an events chunk. Returns cells the LLM
    did not return (or returned invalid) so the caller can retry."""
    items = [(ticker, d_str, news_items)
             for _, ticker, d_str, news_items, _, _ in chunk]
    prompt = build_events_batch_prompt(items)
    raw = provider.classify(prompt)
    results = _extract_json_array(raw)
    if results is None:
        raise RuntimeError(
            f"events batch ({chunk[0][1]} {chunk[0][2]}..) "
            f"could not be parsed as a JSON array. Got: {raw[:300]}"
        )
    results_by_key = {
        (r.get("ticker"), r.get("date")): r
        for r in results if isinstance(r, dict)
    }
    valid = 0
    missing: list[tuple[tuple[str, date], str, str, list[dict], str, str]] = []
    for key, ticker, d_str, news_items, key_ticker, single_hash in chunk:
        entry = results_by_key.get((ticker, d_str))
        if entry is None or not _validate_events(entry):
            missing.append(
                (key, ticker, d_str, news_items, key_ticker, single_hash)
            )
            continue
        cache_value = {
            k: {
                "fired": bool(entry[k]["fired"]),
                "severity": float(entry[k]["severity"]),
            }
            for k in _EVENT_FLAGS
        }
        cache_put(
            d_str, key_ticker, single_hash, provider.model_id, cache_value,
        )
        out[key] = cache_value
        valid += 1
    if valid == 0:
        raise RuntimeError(
            f"events batch ({chunk[0][1]} {chunk[0][2]}..) "
            f"had 0 valid entries out of {len(chunk)}. Got: {raw[:300]}"
        )
    return missing


def classify_events_batch(
    pairs: list[tuple[str, date]],
    provider: Provider,
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> dict[tuple[str, date], dict]:
    """Classify (ticker, date) event flags. Empty-news cells short-circuit
    to all-zero flags with NO LLM call. Non-empty cells are batched.
    """
    out: dict[tuple[str, date], dict] = {}

    pending: list[
        tuple[tuple[str, date], str, str, list[dict], str, str]
    ] = []
    for ticker, d in pairs:
        d_str = d.isoformat()
        news_items = _news_for(ticker, d)
        if not news_items:
            out[(ticker, d)] = _EVENTS_DEFAULT.copy()
            continue
        _, single_hash = build_events_prompt(ticker, d_str, news_items)
        key_ticker = events_ticker_key(ticker)
        cached = cache_get(d_str, key_ticker, single_hash, provider.model_id)
        if cached is not None:
            out[(ticker, d)] = cached
        else:
            pending.append(
                ((ticker, d), ticker, d_str, news_items, key_ticker, single_hash)
            )

    for chunk in _chunked(pending, chunk_size):
        missing = _process_events_chunk(chunk, provider, out)
        if missing:
            # Silent-drop guard (see docs/learnings-from-us-build.md §4.1):
            # same pattern as sentiment — log, retry smaller, raise if still
            # missing. Events cache holes would cause strategies to read the
            # all-zero default and silently miss earnings / regulatory firings.
            missing_keys = [(m[1], m[2]) for m in missing]
            retry_size = max(_MIN_RETRY_CHUNK_SIZE, chunk_size // 4)
            logger.warning(
                "events batch dropped %d/%d cells (cells=%s); "
                "retrying with chunk_size=%d",
                len(missing), len(chunk), missing_keys, retry_size,
            )
            still_missing: list[
                tuple[tuple[str, date], str, str, list[dict], str, str]
            ] = []
            for sub_chunk in _chunked(missing, retry_size):
                still_missing.extend(
                    _process_events_chunk(sub_chunk, provider, out)
                )
            if still_missing:
                still_keys = [(m[1], m[2]) for m in still_missing]
                logger.error(
                    "events retry failed: %d cells still missing "
                    "after smaller-chunk retry (cells=%s)",
                    len(still_missing), still_keys,
                )
                raise RuntimeError(
                    f"events classifier dropped {len(still_missing)} "
                    f"cells even after retry: {still_keys}"
                )

    return out
