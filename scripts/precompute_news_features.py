"""Backfill the sentiment + events caches for the universe over a window.

For each (ticker, date) cell:
  - empty-news cells short-circuit inside the classifier (no LLM call)
  - non-empty cells are batched at `--chunk-size` per LLM call

Runs sentiment first, then events. Both classifiers internally chunk by the
size we pass in, but we ALSO chunk at the script level so progress prints
land regularly and a chunk failure doesn't kill the whole night.

Cache is durable; re-run is safe (cache hits short-circuit the LLM).

Usage:
    # Default: full universe, last 5 years (Pulse + MoneyControl + NSE + RBI
    # + SEBI horizon — see design spec §13.2 ingest_news_historical).
    uv run python scripts/precompute_news_features.py

    # Custom window + Codex
    uv run python scripts/precompute_news_features.py \\
        --start 2024-01-01 --end 2024-12-31 --provider codex

    # Subset of tickers
    uv run python scripts/precompute_news_features.py \\
        --tickers RELIANCE,HDFCBANK,INFY --start 2024-06-01 --end 2024-12-31
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import duckdb

from data.ingest_prices import DB_PATH as PRICES_DB
from data.universe import get_live_universe
from llm.classify import classify_events_batch, classify_sentiment_batch
from llm.provider import ClaudeCodeProvider, CodexProvider, Provider


def trading_days(start: date, end: date) -> list[date]:
    """NSE trading days in [start, end] from prices.duckdb (NIFTY index)."""
    con = duckdb.connect(str(PRICES_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT date FROM prices WHERE ticker = 'NIFTY' "
        "AND date BETWEEN ? AND ? ORDER BY date",
        [start.isoformat(), end.isoformat()],
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _make_provider(provider_name: str, model: str | None) -> Provider:
    if provider_name == "claude":
        return ClaudeCodeProvider(model=model or "claude-sonnet-4-6")
    if provider_name == "codex":
        return CodexProvider(model=model)
    raise ValueError(
        f"unknown provider {provider_name!r}; expected 'claude' or 'codex'"
    )


def _run_classifier(
    name: str,
    classifier,
    pairs: list[tuple[str, date]],
    provider: Provider,
    chunk_size: int,
) -> int:
    """Run classifier in script-level chunks for progress/isolation. Returns
    the number of chunk failures."""
    n_chunks = (len(pairs) + chunk_size - 1) // chunk_size
    print(
        f"\n=== {name}: {len(pairs)} cells, {n_chunks} chunks "
        f"(chunk_size={chunk_size}) ===",
        flush=True,
    )
    t0 = time.time()
    failures: list[tuple[str, str]] = []
    processed = 0
    for chunk_idx in range(n_chunks):
        chunk = pairs[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size]
        try:
            classifier(chunk, provider, chunk_size=chunk_size)
        except RuntimeError as e:
            label = f"{chunk[0][0]} {chunk[0][1]}..{chunk[-1][0]} {chunk[-1][1]}"
            failures.append((label, str(e)[:200]))
        processed += len(chunk)
        elapsed = time.time() - t0
        rate = processed / elapsed if elapsed > 0 else 0
        print(
            f"  {name} chunk {chunk_idx + 1}/{n_chunks} done "
            f"({processed}/{len(pairs)} cells, {elapsed:.0f}s, "
            f"{rate:.1f} cell/s, {len(failures)} chunk failures)",
            flush=True,
        )
    if failures:
        print(f"\n{name} chunk failures (first 5):")
        for label, msg in failures[:5]:
            print(f"  [{label}]: {msg}")
    return len(failures)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    today = date.today()
    p.add_argument(
        "--start", type=date.fromisoformat,
        default=today - timedelta(days=5 * 365),
        help="Inclusive start date (default: 5 years ago — Indian news horizon).",
    )
    p.add_argument(
        "--end", type=date.fromisoformat, default=today,
        help="Inclusive end date (default: today).",
    )
    p.add_argument(
        "--tickers", default=None,
        help="Comma-separated ticker subset (default: full TRADABLE_UNIVERSE).",
    )
    p.add_argument(
        "--provider", choices=["claude", "codex"], default="claude",
    )
    p.add_argument(
        "--model", default=None,
        help="Model override. Default: Sonnet for claude, codex config default.",
    )
    p.add_argument(
        "--chunk-size", type=int, default=50,
        help="(ticker, date) cells per batched LLM call (default 50).",
    )
    p.add_argument(
        "--skip-sentiment", action="store_true",
        help="Run only the events classifier.",
    )
    p.add_argument(
        "--skip-events", action="store_true",
        help="Run only the sentiment classifier.",
    )
    args = p.parse_args(argv)

    days = trading_days(args.start, args.end)
    if not days:
        print(
            f"no trading days found in [{args.start}, {args.end}] — "
            "is prices.duckdb populated for NIFTY?"
        )
        return 1

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = list(get_live_universe())

    pairs = [(t, d) for t in tickers for d in days]
    provider = _make_provider(args.provider, args.model)
    print(
        f"news features: {len(tickers)} tickers x {len(days)} days = "
        f"{len(pairs)} cells, model={provider.model_id}, "
        f"chunk_size={args.chunk_size}",
        flush=True,
    )
    print(
        "(empty-news cells short-circuit inside the classifier — most cells "
        "won't actually hit the LLM.)",
        flush=True,
    )

    total_failures = 0
    if not args.skip_sentiment:
        total_failures += _run_classifier(
            "sentiment", classify_sentiment_batch, pairs, provider, args.chunk_size,
        )
    if not args.skip_events:
        total_failures += _run_classifier(
            "events", classify_events_batch, pairs, provider, args.chunk_size,
        )

    print(f"\nall done. {total_failures} total chunk failures.")
    return 0 if total_failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
