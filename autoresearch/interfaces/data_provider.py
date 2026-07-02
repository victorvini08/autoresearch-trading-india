"""DataProvider extension point — supply prices + a point-in-time universe.

Implement this to feed the backtest/evaluator from your own market's data
instead of the NSE bhav archive. The reference implementation ingests the free
NSE bhav archive into ``storage/prices.duckdb`` and derives a survivorship-free
universe from price history.

Table-schema contract
---------------------
The library reads adjusted daily bars in this shape (DuckDB table
``daily_bars`` in the reference impl):

    daily_bars(
        ticker  TEXT,
        dt      DATE,
        open    DOUBLE,
        high    DOUBLE,
        low     DOUBLE,
        close   DOUBLE,     -- split/bonus-adjusted
        volume  DOUBLE
    )

A point-in-time universe MUST be derivable from bar history alone — never a
"current membership" list, which would inject survivorship bias. The reference
builds it as the top-N names by trailing average daily traded value as of each
date.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date


class DataProvider(ABC):
    """Prices + point-in-time universe. Reference: NSE bhav archive."""

    @abstractmethod
    def read_prices(self, tickers: list[str], start: date, end: date):
        """Return adjusted daily bars for ``tickers`` in [start, end].

        Shape follows the ``daily_bars`` contract documented in this module.
        """

    @abstractmethod
    def pit_universe(self, as_of: date, size: int) -> list[str]:
        """Return the point-in-time tradeable universe (top ``size`` by liquidity)."""
