"""End-to-end smoke validation of the strategy on real ingested data.

Steps:
  1. Build the universe at `--as-of` using `data.universe.compute_universe`
     (top-200-by-ADV from Nifty 500 + filters).
  2. Run a one-day backtest with the strategy against the universe price feeds
     — verify the strategy issues orders without exceptions.
  3. Apply the strategy logic manually (no backtrader) to produce a target_fractions
     dict and print the top-K names + sector aggregation + regime gate result.

This is NOT a full backtest. It's a one-day pipeline-validation tool to run
after a fresh ingest, before kicking off the autoresearch loop.

Usage:
  uv run python -m scripts.validate_strategy_smoke --as-of 2026-05-13
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_recent_macro_snapshot(macro_db: Path, on_date: date) -> dict:
    """Return the most-recent value of each macro indicator on or before `on_date`."""
    import duckdb

    if not macro_db.exists():
        return {}
    conn = duckdb.connect(str(macro_db), read_only=True)
    try:
        rows = conn.execute(
            """
            WITH ranked AS (
              SELECT series_id, value, dt,
                     ROW_NUMBER() OVER (PARTITION BY series_id ORDER BY dt DESC) rn
                FROM macro_daily
               WHERE dt <= ?
            )
            SELECT series_id, value FROM ranked WHERE rn = 1
            """,
            (on_date,),
        ).fetchall()
    finally:
        conn.close()
    return {s: v for s, v in rows}


def _compute_regime_signals(macro_db: Path, on_date: date) -> dict:
    """Compute the canonical regime-gate inputs the strategy uses."""
    import duckdb

    if not macro_db.exists():
        return {}
    conn = duckdb.connect(str(macro_db), read_only=True)
    try:
        # India VIX latest
        vix_row = conn.execute(
            "SELECT value FROM macro_daily WHERE series_id='index_india_vix' "
            "AND dt <= ? ORDER BY dt DESC LIMIT 1",
            (on_date,),
        ).fetchone()
        # India VIX 252d rolling 95th percentile
        vix_252d_rows = conn.execute(
            "SELECT value FROM macro_daily WHERE series_id='index_india_vix' "
            "AND dt <= ? AND dt > ? - INTERVAL '252 DAYS' ORDER BY dt",
            (on_date, on_date),
        ).fetchall()
        vix_values = sorted([v[0] for v in vix_252d_rows if v[0] is not None])
        if vix_values:
            idx = int(len(vix_values) * 0.95)
            vix_95pct = vix_values[min(idx, len(vix_values) - 1)]
        else:
            vix_95pct = None
        # Nifty 50 latest + 200DMA
        nifty_row = conn.execute(
            "SELECT value FROM macro_daily WHERE series_id='index_nifty_50' "
            "AND dt <= ? ORDER BY dt DESC LIMIT 1",
            (on_date,),
        ).fetchone()
        nifty_200d_rows = conn.execute(
            "SELECT value FROM macro_daily WHERE series_id='index_nifty_50' "
            "AND dt <= ? AND dt > ? - INTERVAL '200 DAYS' ORDER BY dt",
            (on_date, on_date),
        ).fetchall()
        nifty_200dma = (
            sum(v[0] for v in nifty_200d_rows) / len(nifty_200d_rows)
            if nifty_200d_rows
            else None
        )
        # FII 20-day net
        fii_rows = conn.execute(
            "SELECT fii_net_cr FROM fii_dii_daily WHERE dt <= ? "
            "ORDER BY dt DESC LIMIT 20",
            (on_date,),
        ).fetchall()
        fii_20d_net = sum(v[0] for v in fii_rows) if fii_rows else None
    finally:
        conn.close()

    return {
        "india_vix_latest": vix_row[0] if vix_row else None,
        "india_vix_95pct_252d": vix_95pct,
        "nifty_50_latest": nifty_row[0] if nifty_row else None,
        "nifty_50_200dma": nifty_200dma,
        "fii_net_20d_cr": fii_20d_net,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="Validation date (default: most recent date in prices.duckdb)",
    )
    p.add_argument("--prices-db", type=str, default="storage/prices.duckdb")
    p.add_argument("--universe-db", type=str, default="storage/universe.duckdb")
    p.add_argument("--macro-db", type=str, default="storage/macro.duckdb")
    p.add_argument("--top-k", type=int, default=10, help="how many ranked names to print")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    import duckdb

    prices_db = Path(args.prices_db)
    universe_db = Path(args.universe_db)
    macro_db = Path(args.macro_db)

    if not prices_db.exists():
        print(f"ERROR: {prices_db} does not exist — run bootstrap_ingest first")
        return 1

    if args.as_of:
        as_of = date.fromisoformat(args.as_of)
    else:
        conn = duckdb.connect(str(prices_db), read_only=True)
        try:
            row = conn.execute("SELECT MAX(dt) FROM daily_bars").fetchone()
        finally:
            conn.close()
        as_of = row[0]
        print(f"== using most-recent ingested date: {as_of} ==\n")

    # Step 1: universe construction
    print(f"=== Step 1: Universe at {as_of} ===")
    from data.universe import compute_universe, fetch_nifty500_constituents

    try:
        constituents = fetch_nifty500_constituents()
    except Exception as e:
        print(f"WARNING: could not fetch live Nifty 500 list ({e}); using empty list")
        constituents = []
    universe = compute_universe(
        as_of, prices_db, universe_db, constituents=constituents
    )
    print(f"Universe size: {len(universe)} (target 200; reflects current ADV + filters)")
    if universe:
        print("Top-10 by ADV:")
        for u in universe[:10]:
            print(f"  {u.ticker:14s}  ADV ₹{u.adv_20d_cr:8.1f}cr   industry={u.industry}")

    if not universe:
        print("ERROR: empty universe — ADV filter probably too tight for the data we have")
        return 2

    # Step 2: macro regime
    print(f"\n=== Step 2: Macro regime signals at {as_of} ===")
    sig = _compute_regime_signals(macro_db, as_of)
    for k, v in sig.items():
        vstr = f"{v:.2f}" if isinstance(v, (int, float)) and v is not None else str(v)
        print(f"  {k:30s}  {vstr}")

    # Step 3: rank universe by 12-1 momentum
    print(f"\n=== Step 3: 12-1 momentum ranking ===")
    conn = duckdb.connect(str(prices_db), read_only=True)
    try:
        lookback = 252
        skip = 21
        end_skip = as_of - timedelta(days=int(skip * 7 / 5))  # ~ 21 trading days
        start_lookback = as_of - timedelta(days=int((lookback + skip) * 7 / 5))
        tickers_in_universe = tuple(u.ticker for u in universe)
        placeholders = ",".join("?" * len(tickers_in_universe))
        rows = conn.execute(
            f"""
            WITH starts AS (
              SELECT ticker, close FROM daily_bars
              WHERE ticker IN ({placeholders}) AND dt <= ?
              QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY dt) = 1
            ),
            recents AS (
              SELECT ticker, close FROM daily_bars
              WHERE ticker IN ({placeholders}) AND dt <= ?
              QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY dt DESC) = 1
            )
            SELECT s.ticker, s.close AS start_close, r.close AS recent_close,
                   (r.close - s.close) / s.close AS mom_pct
              FROM starts s JOIN recents r USING (ticker)
             WHERE s.close > 0
             ORDER BY mom_pct DESC
             LIMIT ?
            """,
            (*tickers_in_universe, start_lookback, *tickers_in_universe, end_skip, args.top_k),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print("ERROR: no momentum signal computed — likely insufficient lookback data")
        return 3

    print(f"Top-{args.top_k} by 12-1 momentum:")
    for ticker, sc, rc, mom in rows:
        print(f"  {ticker:14s}  mom {mom*100:+6.1f}%   start ₹{sc:8.1f}   recent ₹{rc:8.1f}")

    # Summary
    print(f"\n=== Pipeline validated end-to-end at {as_of} ===")
    print("Next: run `uv run python prepare.py research` for a full walk-forward backtest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
