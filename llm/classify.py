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
import os
import re
from datetime import date, timedelta
from typing import Iterable, Iterator, TypeVar

from pathlib import Path

from data.ingest_macro import read_fii_dii, read_macro_window
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

_ALLOWED_REGIMES = {"risk_on", "risk_off", "neutral", "shock"}

# Indian macro series in storage/macro.duckdb (NOT the US FRED IDs the US
# repo carried — those would silently return an empty snapshot here).
_MACRO_DB = Path("storage/macro.duckdb")
_S_VIX = "index_india_vix"
_S_NIFTY50 = "index_nifty_50"
_S_REPO = "INTDSRINM193N"      # FRED India short-term policy rate proxy
_S_USDINR = "DEXINUS"          # FRED USD/INR daily

_DEFAULT_CHUNK_SIZE = 50


def _skip_model_id(provider: Provider) -> str | None:
    """model_id used for the precompute cache-SKIP lookup.

    Default (None): model-agnostic — a cell already classified by ANY
    provider is reused, so a Codex-filled half-cache is continued by a
    later Claude run instead of being re-computed from scratch. This is
    consistent with llm.features reading the cache model-agnostically by
    default (these coarse outputs — 4-class regime / [-1,1] sentiment /
    7 flags — are treated as model-interchangeable). Writes are still
    tagged with the running provider's real model_id (audit/ablation
    provenance is preserved).

    Set LLM_STRICT_MODEL_CACHE=1 to restore strict per-model skip (each
    provider re-classifies independently) — needed only for a clean
    single-model ablation study. Supersedes the original blanket
    interpretation of hard-constraint #7 per explicit user decision
    2026-05-15.
    """
    if os.getenv("LLM_STRICT_MODEL_CACHE") in ("1", "true", "True"):
        return provider.model_id
    return None
_MIN_RETRY_CHUNK_SIZE = 5

T = TypeVar("T")


def _chunked(items: list[T], n: int) -> Iterator[list[T]]:
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _macro_snapshot(d: date, macro_db: Path = _MACRO_DB) -> dict[str, float]:
    """Indian macro-regime signal snapshot as of `d` (most recent on/before).

    Computes the signals the macro_regime prompt expects:
      india_vix, india_vix_pct_252d, nifty50_close, nifty50_200dma,
      nifty50_pct_vs_200dma, repo_rate_pct, usd_inr, usd_inr_1w_change_pct,
      fii_net_20d_cr, dii_net_20d_cr

    Every signal degrades to "absent" (key omitted) rather than 0.0 when its
    series has no data — the prompt only reasons over keys present, so a
    missing FII history (v2) just means the FII arm is silent, not false.
    A ~430-calendar-day lookback covers the 252d VIX percentile + 200d MA.
    """
    end = d
    start = d - timedelta(days=430)
    snap: dict[str, float] = {}

    vix = read_macro_window(macro_db, _S_VIX, start, end)
    if vix:
        latest = vix[-1][1]
        snap["india_vix"] = round(latest, 2)
        window = [v for _, v in vix][-252:]
        if len(window) >= 30:
            rank = sum(1 for x in window if x <= latest) / len(window)
            snap["india_vix_pct_252d"] = round(rank, 3)

    nifty = read_macro_window(macro_db, _S_NIFTY50, start, end)
    if nifty:
        close = nifty[-1][1]
        snap["nifty50_close"] = round(close, 2)
        last200 = [v for _, v in nifty][-200:]
        if len(last200) >= 50:
            dma = sum(last200) / len(last200)
            snap["nifty50_200dma"] = round(dma, 2)
            snap["nifty50_pct_vs_200dma"] = round((close / dma - 1.0) * 100, 2)

    repo = read_macro_window(macro_db, _S_REPO, start, end)
    if repo:
        snap["repo_rate_pct"] = round(repo[-1][1], 2)

    usdinr = read_macro_window(macro_db, _S_USDINR, start, end)
    if usdinr:
        snap["usd_inr"] = round(usdinr[-1][1], 3)
        # ~1 trading week ago ≈ 5 points back
        if len(usdinr) >= 6:
            wk_ago = usdinr[-6][1]
            if wk_ago:
                snap["usd_inr_1w_change_pct"] = round(
                    (usdinr[-1][1] / wk_ago - 1.0) * 100, 2
                )

    # FII/DII 20-day net — graceful: only emitted if >= 20 trading rows exist
    # (today only ~1 row; full history is the v2 task). The prompt treats
    # absent FII as "no signal", never as zero/negative.
    fii = read_fii_dii(macro_db, start, end)
    if len(fii) >= 20:
        last20 = fii[-20:]
        snap["fii_net_20d_cr"] = round(sum(r[1] for r in last20), 1)
        snap["dii_net_20d_cr"] = round(sum(r[2] for r in last20), 1)

    # GDELT policy/narrative dimension — complementary to the numeric
    # market signals above (it catches systemic-fear / policy-uncertainty
    # regimes the VIX/Nifty/FII series miss). Rows are keyed by the decision
    # date they are valid for, so reading "most recent on/before d" is
    # point-in-time correct. Absent → key omitted (prompt treats as silent).
    for series_id in (
        "gdelt_tone_mean", "gdelt_tone_negfrac",
        "gdelt_epu_policy", "gdelt_centralbank",
        "gdelt_tariff_trade", "gdelt_inflation",
    ):
        pts = read_macro_window(macro_db, series_id, start, end)
        if pts:
            snap[series_id] = round(pts[-1][1], 4)

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
    *,
    strict: bool = True,
) -> list[tuple[date, str, dict[str, float], list[str], str]]:
    """Run one batched LLM call for a macro chunk, write valid cells to `out`
    and the cache, and return the list of cells the LLM did NOT return (or
    returned invalid). Caller decides whether to retry or raise.

    With `strict=True` (default, for the initial call), a zero-valid-batch
    raises RuntimeError — strong signal of a broken LLM response. With
    `strict=False` (used by retry calls), zero-valid is logged and missing
    is returned so the outer driver can continue gracefully.
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
    if valid == 0 and len(chunk) > 0 and strict:
        # All cells in this chunk failed. In the initial call this is
        # strong evidence of a broken LLM response (not a one-row glitch),
        # so we raise. In retry calls, the caller suppresses this by
        # passing `strict=False` and we just return the missing list to
        # be logged at the outer error level.
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
        macro_signals = _macro_snapshot(d)
        headlines = recent_news_by_date.get(d, [])
        _, single_hash = build_macro_regime_prompt(d_str, macro_signals, headlines)
        cached = cache_get(
            d_str, MACRO_TICKER_SENTINEL, single_hash, _skip_model_id(provider)
        )
        if cached is not None:
            out[d] = cached
        else:
            pending.append((d, d_str, macro_signals, headlines, single_hash))

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
                    _process_macro_chunk(sub_chunk, provider, out, strict=False)
                )
            if still_missing:
                still_keys = [m[1] for m in still_missing]
                logger.error(
                    "macro_regime retry failed: %d cells still missing "
                    "after smaller-chunk retry (dates=%s); proceeding "
                    "without these cells — strategy will read None for them",
                    len(still_missing), still_keys,
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
    *,
    strict: bool = True,
) -> list[tuple[tuple[str, date], str, str, list[dict], str, str]]:
    """Run one batched LLM call for a sentiment chunk. Returns cells the LLM
    did not return (or returned invalid) so the caller can retry.

    With `strict=True` (default; initial call) a zero-valid response raises;
    with `strict=False` (retry calls), the missing list is returned so the
    outer driver can continue gracefully.
    """
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
    if valid == 0 and len(chunk) > 0 and strict:
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
        cached = cache_get(d_str, key_ticker, single_hash, _skip_model_id(provider))
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
                    _process_sentiment_chunk(sub_chunk, provider, out, strict=False)
                )
            if still_missing:
                still_keys = [(m[1], m[2]) for m in still_missing]
                logger.error(
                    "sentiment retry failed: %d cells still missing "
                    "after smaller-chunk retry (cells=%s); proceeding "
                    "without these cells — strategy will read None for them",
                    len(still_missing), still_keys,
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
    *,
    strict: bool = True,
) -> list[tuple[tuple[str, date], str, str, list[dict], str, str]]:
    """Run one batched LLM call for an events chunk. Returns cells the LLM
    did not return (or returned invalid) so the caller can retry.

    With `strict=True` (default; initial call), zero-valid raises; with
    `strict=False` (retry calls), missing is returned for the outer
    driver to log and proceed.
    """
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
    if valid == 0 and len(chunk) > 0 and strict:
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
        cached = cache_get(d_str, key_ticker, single_hash, _skip_model_id(provider))
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
                    _process_events_chunk(sub_chunk, provider, out, strict=False)
                )
            if still_missing:
                still_keys = [(m[1], m[2]) for m in still_missing]
                logger.error(
                    "events retry failed: %d cells still missing "
                    "after smaller-chunk retry (cells=%s); proceeding "
                    "without these cells — strategy will read None for them",
                    len(still_missing), still_keys,
                )

    return out
