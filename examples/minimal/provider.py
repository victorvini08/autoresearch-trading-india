"""A minimal DataProvider backed by the deterministic synthetic generator.

Demonstrates the DataProvider contract (read_prices + pit_universe) with zero
real market data. A build-your-own-market user would implement the same two
methods against their own source, returning the documented table shapes.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from autoresearch.data.synthetic import generate
from autoresearch.interfaces import DataProvider


class SyntheticDataProvider(DataProvider):
    def __init__(self, n_tickers=40, start=date(2019, 1, 1),
                 end=date(2022, 12, 31), seed=42):
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
