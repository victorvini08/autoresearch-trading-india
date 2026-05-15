"""Backfill the macro_regime cache for the full backtest window.

Reads NSE trading days from storage/prices.duckdb (NIFTY index) and runs
classify_macro_regime_batch in chunks of `--chunk-size` days per LLM call.
One LLM call covers many days, which amortizes ~10s of subprocess + agent
startup overhead — for ~1250 days (5y of NSE sessions) this is ~25 calls
instead of 1250.

Cache is durable — Ctrl+C mid-run is safe; a re-run picks up where it left
off because cached cells short-circuit the provider call.

Usage:
    # Default sweep: full window 2020-01-01 → 2024-12-31, Sonnet model
    uv run python scripts/precompute_macro_cache.py

    # Smoke test on a small window
    uv run python scripts/precompute_macro_cache.py --start 2024-03-01 --end 2024-03-08

    # Use a different Claude model + smaller chunks
    uv run python scripts/precompute_macro_cache.py --model claude-opus-4-7 --chunk-size 25
"""
from __future__ import annotations

import argparse
import time
from datetime import date

import duckdb

# TODO Phase 6: data.ingest_general_news is US-specific (Finnhub general
# news feed). The India equivalent is a Pulse-RSS-derived "market-wide
# news" lookup keyed by date; wire it once data.ingest_news.get_general_news_by_date
# lands per design spec §13.2. Until then the per-day news lookup is a
# no-op stub (see _get_general_news_by_date below) and macro_regime
# falls back to numeric-only classification (RBI + FRED India + NSE
# indices + FII/DII), which is still informative.
from data.ingest_prices import DB_PATH as PRICES_DB
from prepare import BACKTEST_END, BACKTEST_START
from llm.classify import classify_macro_regime_batch
from llm.provider import ClaudeCodeProvider, CodexProvider, Provider


def _get_general_news_by_date(d: date, *, lookback_days: int = 3, limit: int = 15) -> list:
    """Stub for Phase 6 wiring (see module docstring TODO).

    Returns empty list so the macro_regime classifier falls back to
    numeric-only inputs. Drop-in replacement for the US repo's
    data.ingest_general_news.get_general_news_by_date.
    """
    return []


def trading_days(start: date, end: date) -> list[date]:
    """Return NSE trading days in [start, end] from prices.duckdb.

    Stale-schema fix (2026-05-15): the store's table is `daily_bars` with a
    `dt` column, and there is NO 'NIFTY' pseudo-ticker. Every traded session
    has rows for many symbols, so DISTINCT dt across daily_bars is the exact
    NSE trading calendar (same source prepare.py / data.universe use).
    """
    con = duckdb.connect(str(PRICES_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT dt FROM daily_bars "
        "WHERE dt BETWEEN ? AND ? ORDER BY dt",
        [start.isoformat(), end.isoformat()],
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _make_provider(provider_name: str, model: str | None) -> Provider:
    if provider_name == "claude":
        return ClaudeCodeProvider(model=model or "claude-sonnet-4-6")
    if provider_name == "codex":
        return CodexProvider(model=model)  # model=None → uses config default
    raise ValueError(
        f"unknown provider {provider_name!r}; expected 'claude' or 'codex'"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    # Defaults bound to prepare's single source of truth so the macro cache
    # spans the FULL window the evaluator/sealed-test/live path will read —
    # not a frozen literal that omits 2025→2026 (audit 2026-05-15). Override
    # with --start/--end for a partial run (idempotent + resumable).
    p.add_argument("--start", type=date.fromisoformat, default=BACKTEST_START)
    p.add_argument("--end", type=date.fromisoformat, default=BACKTEST_END)
    p.add_argument(
        "--provider",
        choices=["claude", "codex"],
        default="claude",
        help="Which LLM CLI to shell out to.",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Model name passed to the provider. Default: Sonnet for claude, "
             "config default (~/.codex/config.toml) for codex.",
    )
    p.add_argument(
        "--chunk-size",
        type=int,
        default=50,
        help="Number of dates per batched LLM call (default 50). Lower this "
             "if you hit context-length errors; raise it for fewer subprocess "
             "round-trips.",
    )
    args = p.parse_args(argv)

    days = trading_days(args.start, args.end)
    if not days:
        print(
            f"no trading days found in [{args.start}, {args.end}] — "
            "is daily_bars in prices.duckdb populated for this range?"
        )
        return 1

    provider = _make_provider(args.provider, args.model)
    n_chunks = (len(days) + args.chunk_size - 1) // args.chunk_size
    print(
        f"precomputing macro_regime: {len(days)} days "
        f"[{days[0]}, {days[-1]}], model={provider.model_id}, "
        f"chunk_size={args.chunk_size} ({n_chunks} chunks)",
        flush=True,
    )

    t0 = time.time()
    processed = 0
    chunk_failures: list[tuple[date, date, str]] = []
    for chunk_idx in range(n_chunks):
        chunk = days[chunk_idx * args.chunk_size:(chunk_idx + 1) * args.chunk_size]
        # Per-date general news lookup. Empty list when no news available
        # (Phase 6 wires the real Pulse-RSS-backed lookup; until then
        # the stub returns empty and the classifier falls back to
        # numeric-only macro inputs).
        news_by_date = {
            d: _get_general_news_by_date(d, lookback_days=3, limit=15)
            for d in chunk
        }
        try:
            classify_macro_regime_batch(
                chunk, provider, recent_news_by_date=news_by_date,
                chunk_size=args.chunk_size,
            )
        except RuntimeError as e:
            chunk_failures.append((chunk[0], chunk[-1], str(e)[:200]))
        processed += len(chunk)
        elapsed = time.time() - t0
        rate = processed / elapsed if elapsed > 0 else 0
        print(
            f"  chunk {chunk_idx + 1}/{n_chunks} done "
            f"({processed}/{len(days)} days, {elapsed:.0f}s, "
            f"{rate:.1f} day/s, {len(chunk_failures)} chunk failures)",
            flush=True,
        )

    elapsed = time.time() - t0
    print(
        f"\ndone. {len(days)} days processed in {elapsed:.0f}s "
        f"({len(chunk_failures)} chunk failures)"
    )
    if chunk_failures:
        print("first 5 chunk failures:")
        for lo, hi, msg in chunk_failures[:5]:
            print(f"  [{lo}..{hi}]: {msg}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
