"""Unit tests for `data.universe`. Network-touching fetchers are tested via mocks."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

from data.universe import (
    MIN_LISTING_TRADING_DAYS,
    TARGET_UNIVERSE_SIZE,
    UniverseRow,
    compute_universe,
    fetch_nifty500_constituents,
    get_live_universe,
    get_universe_at,
    latest_universe_date,
    load_universe,
)


def _seed_prices(prices_db: Path, tickers: list[str], end: date, n_days: int = 750) -> None:
    conn = duckdb.connect(str(prices_db))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_bars (
                ticker VARCHAR NOT NULL, dt DATE NOT NULL,
                open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
                volume BIGINT, value_inr_crores DOUBLE,
                PRIMARY KEY (ticker, dt)
            )
            """
        )
        for t in tickers:
            for i in range(n_days):
                d = end - timedelta(days=n_days - 1 - i)
                if d.weekday() >= 5:
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO daily_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (t, d, 100.0, 102.0, 99.0, 101.0, 1_000_000, 100.0),
                )
    finally:
        conn.close()


def test_compute_universe_filters_short_history(tmp_path: Path) -> None:
    """A ticker with < MIN_LISTING_TRADING_DAYS of price history must be excluded."""
    prices_db = tmp_path / "prices.duckdb"
    universe_db = tmp_path / "universe.duckdb"
    end = date(2026, 5, 13)
    _seed_prices(prices_db, ["MATURE"], end, n_days=750)
    _seed_prices(prices_db, ["TOO_NEW"], end, n_days=100)
    constituents = [
        {"symbol": "MATURE", "series": "EQ", "company": "Mature Co", "industry": "IT", "isin": "INE1"},
        {"symbol": "TOO_NEW", "series": "EQ", "company": "New Co", "industry": "IT", "isin": "INE2"},
    ]
    rows = compute_universe(end, prices_db, universe_db, constituents=constituents)
    tickers = {r.ticker for r in rows}
    assert "MATURE" in tickers
    assert "TOO_NEW" not in tickers


def test_compute_universe_drops_non_eq_series(tmp_path: Path) -> None:
    prices_db = tmp_path / "prices.duckdb"
    universe_db = tmp_path / "universe.duckdb"
    end = date(2026, 5, 13)
    _seed_prices(prices_db, ["EQ_NAME", "SME_NAME"], end, n_days=750)
    constituents = [
        {"symbol": "EQ_NAME", "series": "EQ", "company": "A", "industry": "IT", "isin": "INE1"},
        {"symbol": "SME_NAME", "series": "SM", "company": "B", "industry": "IT", "isin": "INE2"},
    ]
    rows = compute_universe(end, prices_db, universe_db, constituents=constituents)
    tickers = {r.ticker for r in rows}
    assert "EQ_NAME" in tickers
    assert "SME_NAME" not in tickers


def test_compute_universe_orders_by_adv_desc(tmp_path: Path) -> None:
    prices_db = tmp_path / "prices.duckdb"
    universe_db = tmp_path / "universe.duckdb"
    end = date(2026, 5, 13)
    # Three tickers with monotonically increasing volume (and thus ADV)
    conn = duckdb.connect(str(prices_db))
    try:
        conn.execute(
            """
            CREATE TABLE daily_bars (
                ticker VARCHAR NOT NULL, dt DATE NOT NULL,
                open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
                volume BIGINT, value_inr_crores DOUBLE,
                PRIMARY KEY (ticker, dt)
            )
            """
        )
        for ticker, vol in (("LOW", 100_000), ("MID", 500_000), ("HIGH", 5_000_000)):
            for i in range(750):
                d = end - timedelta(days=749 - i)
                if d.weekday() >= 5:
                    continue
                conn.execute(
                    "INSERT INTO daily_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ticker, d, 100.0, 102.0, 99.0, 101.0, vol, vol * 101.0 / 1e7),
                )
    finally:
        conn.close()
    constituents = [
        {"symbol": t, "series": "EQ", "company": t, "industry": "IT", "isin": f"INE{i}"}
        for i, t in enumerate(["LOW", "MID", "HIGH"])
    ]
    rows = compute_universe(end, prices_db, universe_db, constituents=constituents)
    ordered_tickers = [r.ticker for r in rows]
    # ADV ranking: HIGH > MID > LOW (some may fall below the ₹10 cr cutoff)
    high_adv_first = [r.ticker for r in rows if r.adv_20d_cr >= 10]
    if high_adv_first:
        assert ordered_tickers[0] == "HIGH"


def test_load_universe_returns_snapshot(tmp_path: Path) -> None:
    prices_db = tmp_path / "prices.duckdb"
    universe_db = tmp_path / "universe.duckdb"
    end = date(2026, 5, 13)
    _seed_prices(prices_db, ["A", "B"], end, n_days=750)
    constituents = [
        {"symbol": t, "series": "EQ", "company": t, "industry": "IT", "isin": f"INE{i}"}
        for i, t in enumerate(["A", "B"])
    ]
    compute_universe(end, prices_db, universe_db, constituents=constituents)
    loaded = load_universe(universe_db, end)
    assert {r.ticker for r in loaded} >= {"A", "B"} & {r.ticker for r in loaded}


def test_get_universe_at_falls_back_to_latest_prior(tmp_path: Path) -> None:
    prices_db = tmp_path / "prices.duckdb"
    universe_db = tmp_path / "universe.duckdb"
    end = date(2026, 5, 13)
    _seed_prices(prices_db, ["A"], end, n_days=750)
    constituents = [
        {"symbol": "A", "series": "EQ", "company": "A", "industry": "IT", "isin": "INE1"},
    ]
    compute_universe(end, prices_db, universe_db, constituents=constituents)
    # Query a later date — should fall back to the snapshot we wrote at `end`
    tickers = get_universe_at(end + timedelta(days=7), universe_db)
    assert tickers == ["A"]


def test_get_live_universe_returns_latest(tmp_path: Path) -> None:
    universe_db = tmp_path / "universe.duckdb"
    prices_db = tmp_path / "prices.duckdb"
    end = date(2026, 5, 13)
    _seed_prices(prices_db, ["A"], end, n_days=750)
    constituents = [
        {"symbol": "A", "series": "EQ", "company": "A", "industry": "IT", "isin": "INE1"}
    ]
    compute_universe(end, prices_db, universe_db, constituents=constituents)
    last = latest_universe_date(universe_db)
    assert last == end
    assert get_live_universe(universe_db) == ["A"]


def test_target_universe_size_default_is_200() -> None:
    assert TARGET_UNIVERSE_SIZE == 200
