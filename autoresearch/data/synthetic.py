"""Deterministic synthetic market data — lets a fresh clone run the backtest
and the evaluator with no real ingestion.

Generates a self-consistent pair of DuckDB stores matching the schema the
library reads:

  prices.duckdb   → daily_bars(ticker, dt, open, high, low, close, volume,
                               value_inr_crores, prev_close)
  universe.duckdb → universe_snapshot(as_of_date, ticker, isin, company,
                               industry, free_float_mcap_cr, adv_20d_cr,
                               rank_by_adv)

The paths are geometric-Brownian-motion price walks with a fixed seed, so the
output is reproducible (no wall-clock / RNG entropy leaks). This is a smoke
fixture for wiring/plumbing — NOT a realistic market and NOT for alpha claims.

Usage:
    uv run python -m autoresearch.data.synthetic            # default fixture
    uv run python -m autoresearch.data.synthetic --tickers 80 --start 2017-01-01
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from autoresearch.config import DEFAULT_CONFIG
from autoresearch.interfaces import DataProvider

_INDUSTRIES = [
    "FINANCE", "IT", "PHARMA", "AUTO", "FMCG", "METALS", "ENERGY", "INFRA",
]


def _business_days(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d += timedelta(days=1)
    return days


def generate(
    prices_db: Path,
    universe_db: Path,
    *,
    n_tickers: int = 60,
    start: date = date(2017, 1, 1),
    end: date = date(2024, 12, 31),
    seed: int = 42,
) -> None:
    """Write a reproducible synthetic prices + universe pair."""
    rng = np.random.default_rng(seed)
    days = _business_days(start, end)
    n_days = len(days)
    tickers = [f"SYN{i:03d}" for i in range(n_tickers)]

    price_rows: list[tuple] = []
    snap_rows: list[tuple] = []

    # Monthly universe snapshot dates (first business day each month present).
    snapshot_dates = sorted({d for d in days if d.day <= 3})

    for ti, tkr in enumerate(tickers):
        # Per-ticker drift/vol so the cross-section has dispersion to rank on.
        mu = rng.normal(0.08, 0.05) / 252.0
        sigma = rng.uniform(0.15, 0.45) / np.sqrt(252.0)
        p0 = float(rng.uniform(50, 1500))
        shocks = rng.normal(mu, sigma, n_days)
        closes = p0 * np.exp(np.cumsum(shocks))
        industry = _INDUSTRIES[ti % len(_INDUSTRIES)]
        prev = np.nan
        for di, d in enumerate(days):
            c = float(closes[di])
            o = c * float(1 + rng.normal(0, 0.004))
            hi = max(o, c) * float(1 + abs(rng.normal(0, 0.004)))
            lo = min(o, c) * float(1 - abs(rng.normal(0, 0.004)))
            vol = int(rng.uniform(50_000, 5_000_000))
            value_cr = c * vol / 1e7
            price_rows.append((tkr, d, o, hi, lo, c, vol, value_cr, prev))
            prev = c

    # Build universe snapshots: rank tickers by trailing avg traded value.
    # Simple proxy: use each ticker's mean value_inr_crores over all bars.
    by_ticker: dict[str, list[float]] = {t: [] for t in tickers}
    for (tkr, _d, _o, _h, _l, _c, _v, value_cr, _p) in price_rows:
        by_ticker[tkr].append(value_cr)
    mean_adv = {t: float(np.mean(v)) for t, v in by_ticker.items()}
    for as_of in snapshot_dates:
        ranked = sorted(tickers, key=lambda t: mean_adv[t], reverse=True)
        for rank, tkr in enumerate(ranked, start=1):
            snap_rows.append((
                as_of, tkr, f"INSYN{tkr[3:]}01011", f"{tkr} Ltd",
                _INDUSTRIES[tickers.index(tkr) % len(_INDUSTRIES)],
                mean_adv[tkr] * 100.0,  # synthetic free-float mcap (cr)
                mean_adv[tkr],          # adv_20d_cr
                rank,
            ))

    prices_db.parent.mkdir(parents=True, exist_ok=True)
    universe_db.parent.mkdir(parents=True, exist_ok=True)

    pc = duckdb.connect(str(prices_db))
    pc.execute("DROP TABLE IF EXISTS daily_bars")
    pc.execute(
        """CREATE TABLE daily_bars (
             ticker VARCHAR, dt DATE, open DOUBLE, high DOUBLE, low DOUBLE,
             close DOUBLE, volume BIGINT, value_inr_crores DOUBLE, prev_close DOUBLE
           )"""
    )
    pc.executemany(
        "INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?,?,?)", price_rows
    )
    pc.close()

    uc = duckdb.connect(str(universe_db))
    uc.execute("DROP TABLE IF EXISTS universe_snapshot")
    uc.execute(
        """CREATE TABLE universe_snapshot (
             as_of_date DATE, ticker VARCHAR, isin VARCHAR, company VARCHAR,
             industry VARCHAR, free_float_mcap_cr DOUBLE, adv_20d_cr DOUBLE,
             rank_by_adv INTEGER
           )"""
    )
    uc.executemany(
        "INSERT INTO universe_snapshot VALUES (?,?,?,?,?,?,?,?)", snap_rows
    )
    uc.close()

    print(
        f"wrote {len(price_rows):,} bars ({n_tickers} tickers, {n_days} days) "
        f"-> {prices_db}\n"
        f"wrote {len(snap_rows):,} universe rows ({len(snapshot_dates)} snapshots) "
        f"-> {universe_db}"
    )


class SyntheticDataProvider(DataProvider):
    """A ready-made DataProvider backed by the deterministic synthetic generator.

    Lets you run the engine/evaluator with zero real data — ideal for a first
    run or a scaffolded project. Swap it for your own DataProvider (implementing
    ``read_prices`` + ``pit_universe``) to trade a real market.
    """

    def __init__(self, n_tickers: int = 40, start: date = date(2019, 1, 1),
                 end: date = date(2022, 12, 31), seed: int = 42):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        self._prices = tmp / "prices.duckdb"
        self._universe = tmp / "universe.duckdb"
        generate(self._prices, self._universe, n_tickers=n_tickers,
                 start=start, end=end, seed=seed)

    def read_prices(self, tickers, start, end):
        """Return {ticker: OHLCV DataFrame indexed by date} — ready for the engine."""
        con = duckdb.connect(str(self._prices), read_only=True)
        out = {}
        for t in tickers:
            df = con.execute(
                "SELECT dt, open, high, low, close, volume FROM daily_bars "
                "WHERE ticker = ? AND dt BETWEEN ? AND ? ORDER BY dt",
                [t, start, end],
            ).fetchdf()
            if not df.empty:
                df["dt"] = pd.to_datetime(df["dt"])
                out[t] = df.set_index("dt")
        con.close()
        return out

    def pit_universe(self, as_of, size):
        """Top `size` tickers by liquidity as of the latest snapshot <= as_of."""
        con = duckdb.connect(str(self._universe), read_only=True)
        latest = con.execute(
            "SELECT MAX(as_of_date) FROM universe_snapshot WHERE as_of_date <= ?",
            [as_of],
        ).fetchone()[0]
        rows = con.execute(
            "SELECT ticker FROM universe_snapshot WHERE as_of_date = ? "
            "ORDER BY rank_by_adv ASC LIMIT ?",
            [latest, size],
        ).fetchall()
        con.close()
        return [t for (t,) in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic prices + universe.")
    ap.add_argument("--out-prices", type=Path, default=DEFAULT_CONFIG.db("prices.duckdb"))
    ap.add_argument("--out-universe", type=Path, default=DEFAULT_CONFIG.db("universe.duckdb"))
    ap.add_argument("--tickers", type=int, default=60)
    ap.add_argument("--start", type=date.fromisoformat, default=date(2017, 1, 1))
    ap.add_argument("--end", type=date.fromisoformat, default=date(2024, 12, 31))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    generate(
        args.out_prices, args.out_universe,
        n_tickers=args.tickers, start=args.start, end=args.end, seed=args.seed,
    )


if __name__ == "__main__":
    main()
