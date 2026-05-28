"""Daily update orchestrator — pull today's data and classify it.

Run at 09:15 IST as a launchd entry (NSE opens at 09:15; ingest happens
in parallel with the pre-market scan and finishes before the 10:00 IST
execution window). Idempotent: safe to re-run, individual ingest
functions and the LLM cache are upsert / short-circuit on existing data.

Steps:
  1. Extend prices.duckdb with the last few trading days (NSE bhav archive)
  2. Extend macro.duckdb with the last few days of macro (RBI + FRED India + NSE indices + FII/DII)
  3. Pull last 24h of news per ticker (Pulse RSS forward feed)
  4. Refresh earnings calendar (NSE corporate filings, Results category, next 30 days)
  5. Classify today's macro_regime (one LLM call)
  6. Classify today's news per ticker (sentiment + events; empty-news cells
     short-circuit without an LLM call)

Usage:
    uv run python -m scripts.daily_update                           # data only (classify SKIPPED by default)
    uv run python -m scripts.daily_update --date 2026-05-09         # backdated
    uv run python -m scripts.daily_update --no-skip-classify        # also run classifiers
    uv run python -m scripts.daily_update --no-skip-classify --provider codex

Classification is SKIPPED BY DEFAULT (2026-05-18 decision): the committed
momentum-quality strategy consumes only prices/universe/sectors — not
macro_regime/sentiment/events — so daily LLM classify is wasted cost and
adds noise to the paper-validation logs. Re-enable per-run with
--no-skip-classify (then quota ≈ 1 macro + ~200 sentiment/events calls
per market day; only non-empty-news tickers fire the classifier).
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

# Standalone orchestrator: source .env so FRED_API_KEY / DHAN_* are
# present when invoked directly or by the launchd job (matches the same
# pattern in scripts/backfill_5y.py, scripts/bootstrap_ingest.py,
# llm/features.py — nothing else loads .env into the process).
from dotenv import load_dotenv

load_dotenv()

# Phase 3 rewires the data.* package to Indian sources (NSE bhav, Pulse,
# RBI, NSE filings). The function NAMES below — ingest_earnings,
# ingest_macro, ingest_prices, get_live_universe — survive verbatim
# per spec §13.2. The US-specific finnhub helper is replaced; see the
# news step below for the Phase 6 wiring TODO.
from data.ingest_earnings import ingest_earnings
from data.ingest_macro import ingest_macro
from data.ingest_prices import ingest_prices
from data.universe import get_live_universe
from llm.classify import (
    classify_events_batch,
    classify_macro_regime_batch,
    classify_sentiment_batch,
)
from llm.provider import ClaudeCodeProvider, CodexProvider, Provider


def _make_provider(provider_name: str, model: str | None) -> Provider:
    if provider_name == "claude":
        return ClaudeCodeProvider(model=model or "claude-sonnet-4-6")
    if provider_name == "codex":
        return CodexProvider(model=model)
    raise ValueError(
        f"unknown provider {provider_name!r}; expected 'claude' or 'codex'"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    today = date.today()
    p.add_argument(
        "--date", type=date.fromisoformat, default=today,
        help="Run as if today were this date (default: actual today).",
    )
    p.add_argument(
        "--lookback-days", type=int, default=3,
        help="How far back to overlap on price/macro/news ingest (default 3).",
    )
    p.add_argument(
        "--earnings-window-days", type=int, default=30,
        help="How far forward to fetch earnings calendar (default 30).",
    )
    p.add_argument(
        "--provider", choices=["claude", "codex"], default="claude",
    )
    p.add_argument("--model", default=None)
    p.add_argument("--chunk-size", type=int, default=50)
    p.add_argument(
        "--skip-classify",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip the LLM classification steps. DEFAULT: skip — the "
             "committed momentum strategy does not consume "
             "macro_regime/sentiment/events, so daily classify is wasted "
             "cost. Pass --no-skip-classify to run the classifiers.",
    )
    p.add_argument(
        "--skip-fundamentals", action="store_true",
        help="Skip the live fundamentals snapshot step.",
    )
    args = p.parse_args(argv)

    today_d = args.date
    tickers = list(get_live_universe())
    start_d = today_d - timedelta(days=args.lookback_days)
    earnings_end = today_d + timedelta(days=args.earnings_window_days)

    print(f"\n=== daily_update for {today_d} ===")

    # Step 1: prices
    t0 = time.time()
    print(f"[1/6] prices: {len(tickers)} tickers, {start_d}..{today_d}", flush=True)
    n_prices = ingest_prices(tickers, start_d.isoformat(), today_d.isoformat())
    print(f"      → {n_prices} rows ({time.time()-t0:.1f}s)", flush=True)

    # Step 2: macro
    t0 = time.time()
    print(f"[2/6] macro: {start_d}..{today_d}", flush=True)
    n_macro = ingest_macro(start_d.isoformat(), today_d.isoformat())
    print(f"      → {n_macro} rows ({time.time()-t0:.1f}s)", flush=True)

    # Step 3: news (last 24h is fine for daily cadence; lookback absorbs gaps)
    t0 = time.time()
    print(f"[3/6] news: {len(tickers)} tickers, {start_d}..{today_d}", flush=True)
    # TODO Phase 6: wire data.ingest_news.fetch_today(tickers, start, end)
    # against Pulse RSS (forward feed) per design spec §13.2. Until that
    # lands the daily news fetch is a no-op; classifiers downstream
    # short-circuit on empty news cells, so the rest of the pipeline
    # still completes (just with zero news features for today).
    n_news = 0
    print(f"      → {n_news} rows ({time.time()-t0:.1f}s)  [Phase 6: news ingest TODO]", flush=True)

    # Step 4: earnings — same-day news-extraction supplement (real India
    # ingest_earnings signature is (news_db, earnings_db); it has no
    # forward date-range / tickers params). The forward-looking NSE
    # results *calendar* is not implemented for India yet (same
    # documented-gap status as the Phase-6 news ingest above); the
    # point-in-time fundamentals/earnings the system actually uses are
    # refreshed by the NSE results pipeline + Step 4b snapshot_live.
    t0 = time.time()
    print(f"[4/6] earnings: news-extraction supplement "
          f"(forward NSE calendar: TODO India)", flush=True)
    n_earn = ingest_earnings()
    print(f"      → {n_earn} rows ({time.time()-t0:.1f}s)", flush=True)

    # Step 4b: live fundamentals snapshot — PIT-clean by construction
    # (capture date == as_of_date). Non-fatal: the cron must never abort on
    # a fundamentals-source hiccup; the PEAD gate soft-degrades downstream.
    if not args.skip_fundamentals:
        try:
            from pathlib import Path

            from data.ingest_fundamentals import snapshot_live

            n_fund = snapshot_live(
                Path("storage/universe.duckdb"), on_date=today_d,
            )
            print(f"[4b] fundamentals snapshot: {n_fund} new", flush=True)
        except Exception as e:  # noqa: BLE001 — cron must not abort
            print(
                f"[4b] fundamentals snapshot FAILED (non-fatal): {e}",
                flush=True,
            )

    # Step 4c: corporate actions for held/traded tickers — yfinance, free.
    # Non-fatal: a yfinance hiccup just means we don't have fresh CA data
    # this morning; reconciliation will keep using whatever is on disk.
    try:
        from scripts.ingest_corporate_actions import update_corporate_actions

        n_ca = update_corporate_actions(mode="dhan-paper", lookback_days=30)
        print(f"[4c] corporate actions: {n_ca} new", flush=True)
    except Exception as e:  # noqa: BLE001 — cron must not abort
        print(
            f"[4c] corporate actions FAILED (non-fatal): {e}",
            flush=True,
        )

    if args.skip_classify:
        print("\n[skip-classify] not running classifiers.")
        return 0

    provider = _make_provider(args.provider, args.model)
    print(f"\n--- classifier: provider={provider.model_id} ---")

    # Step 5: macro_regime for today
    t0 = time.time()
    print(f"[5/6] macro_regime: {today_d}", flush=True)
    classify_macro_regime_batch([today_d], provider, chunk_size=args.chunk_size)
    print(f"      → done ({time.time()-t0:.1f}s)", flush=True)

    # Step 6: news features (sentiment + events) for today
    pairs = [(t, today_d) for t in tickers]
    t0 = time.time()
    print(f"[6/6] sentiment: {len(pairs)} (ticker, date) cells", flush=True)
    classify_sentiment_batch(pairs, provider, chunk_size=args.chunk_size)
    print(f"      → done ({time.time()-t0:.1f}s)", flush=True)

    t0 = time.time()
    print(f"      events: {len(pairs)} cells", flush=True)
    classify_events_batch(pairs, provider, chunk_size=args.chunk_size)
    print(f"      → done ({time.time()-t0:.1f}s)", flush=True)

    print(f"\n=== daily_update for {today_d} complete ===\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
