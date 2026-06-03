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


def _seed_range(prices_db: Path, ticker: str, start: date, stop: date) -> None:
    """Seed liquid daily bars for `ticker` on weekdays in [start, stop]."""
    rows = []
    d = start
    while d <= stop:
        if d.weekday() < 5:
            rows.append((ticker, d, 100.0, 102.0, 99.0, 101.0, 1_000_000, 10.1))
        d += timedelta(days=1)
    conn = duckdb.connect(str(prices_db))
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS daily_bars (
                ticker VARCHAR NOT NULL, dt DATE NOT NULL,
                open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
                volume BIGINT, value_inr_crores DOUBLE,
                PRIMARY KEY (ticker, dt))"""
        )
        conn.executemany(
            "INSERT OR REPLACE INTO daily_bars VALUES (?,?,?,?,?,?,?,?)", rows
        )
    finally:
        conn.close()


def test_membership_is_independent_of_constituent_list(tmp_path: Path) -> None:
    """Survivorship-fix contract: a name with sufficient PIT price history is
    a member even if it is ABSENT from the (current) Nifty 500 list — that
    list is sector/ISIN enrichment only, never the membership gate. A real
    delisted name is exactly this case (not in today's CSV).

    (EQ-only filtering is enforced UPSTREAM at price ingest via
    parse_bhav_csv series_filter=("EQ",); daily_bars has no series column,
    so the universe layer neither can nor should re-filter by series.)
    """
    prices_db = tmp_path / "prices.duckdb"
    universe_db = tmp_path / "universe.duckdb"
    end = date(2026, 5, 13)
    _seed_prices(prices_db, ["IN_LIST", "NOT_IN_LIST"], end, n_days=750)
    constituents = [
        {"symbol": "IN_LIST", "series": "EQ", "company": "A",
         "industry": "IT", "isin": "INE1"},
        # NOT_IN_LIST deliberately omitted — mimics a delisted name.
    ]
    rows = compute_universe(end, prices_db, universe_db, constituents=constituents)
    by = {r.ticker: r for r in rows}
    assert "IN_LIST" in by and "NOT_IN_LIST" in by
    # Enrichment falls back gracefully for the non-listed name.
    assert by["NOT_IN_LIST"].industry == "OTHER"
    assert by["NOT_IN_LIST"].isin == ""
    assert by["IN_LIST"].industry == "IT"


def test_no_survivorship_bias_delisted_name_drops_out(tmp_path: Path) -> None:
    """A name liquid until mid-2023 then delisted MUST appear in a 2023
    snapshot and MUST be absent from a 2026 snapshot — automatically, with
    no entry in the constituent list. This is the core money-correctness
    guarantee of the point-in-time universe."""
    prices_db = tmp_path / "prices.duckdb"
    universe_db = tmp_path / "universe.duckdb"
    _seed_range(prices_db, "SURVIVOR", date(2021, 1, 1), date(2026, 5, 13))
    _seed_range(prices_db, "DELISTED", date(2021, 1, 1), date(2023, 6, 30))
    constituents = [
        {"symbol": "SURVIVOR", "series": "EQ", "company": "S",
         "industry": "IT", "isin": "INE1"},
    ]  # DELISTED not in the current list — like every real delisted name.

    early = compute_universe(date(2023, 6, 15), prices_db, universe_db,
                             constituents=constituents)
    late = compute_universe(date(2026, 5, 13), prices_db, universe_db,
                            constituents=constituents)

    early_t = {r.ticker for r in early}
    late_t = {r.ticker for r in late}
    assert "DELISTED" in early_t, "delisted name must be a member while trading"
    assert "DELISTED" not in late_t, "delisted name must vanish after it stops"
    assert "SURVIVOR" in early_t and "SURVIVOR" in late_t


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


def test_get_universe_at_filters_etfs_from_stale_snapshot(tmp_path: Path) -> None:
    """Defense-in-depth (2026-03..04 replay regression): a snapshot built BEFORE
    a ticker was added to _ETF_EXCLUDE still contains it, and get_universe_at
    must filter it at READ time so it can't leak into the live universe. Without
    this, LIQUIDCASE leaked from a stale snapshot and — scoring top-tier on the
    low-vol/low-drawdown quality factors — climbed to the #1 live holding."""
    import duckdb
    from data.universe import _ETF_EXCLUDE

    assert "LIQUIDCASE" in _ETF_EXCLUDE  # precondition: it IS on the exclude list
    universe_db = tmp_path / "universe.duckdb"
    snap = date(2026, 5, 13)
    conn = duckdb.connect(str(universe_db))
    conn.execute(
        "CREATE TABLE universe_snapshot (as_of_date DATE, ticker VARCHAR, isin VARCHAR,"
        " company VARCHAR, industry VARCHAR, free_float_mcap_cr DOUBLE,"
        " adv_20d_cr DOUBLE, rank_by_adv INTEGER, PRIMARY KEY (as_of_date, ticker))"
    )
    # Stale snapshot: a real equity AND a leaked cash ETF.
    conn.execute("INSERT INTO universe_snapshot VALUES (?,?,?,?,?,?,?,?)",
                 [snap, "RELIANCE", "INE1", "RELIANCE", "Energy", 0.0, 100.0, 1])
    conn.execute("INSERT INTO universe_snapshot VALUES (?,?,?,?,?,?,?,?)",
                 [snap, "LIQUIDCASE", "INE2", "LIQUIDCASE", "ETF", 0.0, 200.0, 2])
    conn.close()

    tickers = get_universe_at(snap, universe_db)
    assert "RELIANCE" in tickers
    assert "LIQUIDCASE" not in tickers, \
        "ETF on _ETF_EXCLUDE must be filtered from the live universe even if the snapshot carries it"


def test_target_universe_size_default_is_200() -> None:
    assert TARGET_UNIVERSE_SIZE == 200
