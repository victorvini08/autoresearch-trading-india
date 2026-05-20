"""Unit tests for `brokers.dhan_mock`. The mock backs v1 paper-only operation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from brokers.dhan import OrderRequest
from brokers.dhan_mock import DhanMock


@pytest.fixture
def prices_db(tmp_path: Path) -> Path:
    """Create a tiny prices.duckdb with two tickers."""
    p = tmp_path / "prices.duckdb"
    conn = duckdb.connect(str(p))
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
        rows = [
            ("RELIANCE", date(2026, 5, 12), 1200.0, 1210.0, 1190.0, 1200.0, 1000000, 12.0),
            ("RELIANCE", date(2026, 5, 13), 1200.0, 1215.0, 1195.0, 1205.0, 1100000, 13.0),
            ("INFY",     date(2026, 5, 12), 1500.0, 1510.0, 1490.0, 1500.0, 800000, 12.0),
            ("INFY",     date(2026, 5, 13), 1500.0, 1525.0, 1500.0, 1520.0, 900000, 13.7),
        ]
        for r in rows:
            conn.execute(
                "INSERT INTO daily_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)", r
            )
    finally:
        conn.close()
    return p


def test_initial_cash(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0)
    assert m.get_cash()["availableBalance"] == 50_000.0
    assert m.get_positions() == []


def test_buy_consumes_cash_and_creates_position(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    resp = m.place_order(OrderRequest("BUY", "RELIANCE", 10, "MARKET"))
    assert resp.status == "TRADED"
    # At slippage 0: cash decreases by 10 × 1205.0 = ₹12,050
    cash = m.get_cash()["availableBalance"]
    assert cash == pytest.approx(50_000.0 - 12_050.0, abs=0.01)
    positions = m.get_positions()
    assert len(positions) == 1
    assert positions[0].ticker == "RELIANCE"
    assert positions[0].quantity == 10


def test_buy_with_slippage(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=10.0)
    resp = m.place_order(OrderRequest("BUY", "RELIANCE", 10, "MARKET"))
    assert resp.status == "TRADED"
    # 10 bps slippage on ₹1205 = ₹1.205 → fill at 1206.205
    cash = m.get_cash()["availableBalance"]
    expected = 50_000.0 - 10 * 1205.0 * (1 + 10 / 10_000.0)
    assert cash == pytest.approx(expected, abs=0.05)


def test_insufficient_cash_rejects(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=1_000.0, slippage_bps=0.0)
    resp = m.place_order(OrderRequest("BUY", "RELIANCE", 10, "MARKET"))
    assert resp.status == "REJECTED"
    assert m.get_cash()["availableBalance"] == 1_000.0
    assert m.get_positions() == []


def test_sell_requires_holding(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0)
    resp = m.place_order(OrderRequest("SELL", "RELIANCE", 5, "MARKET"))
    assert resp.status == "REJECTED"


def test_buy_then_sell_round_trip(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    m.place_order(OrderRequest("BUY", "RELIANCE", 10, "MARKET"))
    m.place_order(OrderRequest("SELL", "RELIANCE", 10, "MARKET"))
    # FIFO close → positions empty; cash back at ₹50,000 (zero slippage)
    assert m.get_positions() == []
    assert m.get_cash()["availableBalance"] == pytest.approx(50_000.0, abs=0.5)


def test_get_fills_tracks_trades(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    m.place_order(OrderRequest("BUY", "RELIANCE", 5, "MARKET"))
    m.place_order(OrderRequest("BUY", "INFY", 3, "MARKET"))
    fills = m.get_fills()
    assert len(fills) == 2
    tickers = {f.ticker for f in fills}
    assert tickers == {"RELIANCE", "INFY"}
    assert all(f.commission == 0.0 for f in fills)   # Dhan delivery brokerage = ₹0


def test_partial_sell_partial_lot_remainder(prices_db: Path) -> None:
    m = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    m.place_order(OrderRequest("BUY", "RELIANCE", 10, "MARKET"))
    m.place_order(OrderRequest("SELL", "RELIANCE", 4, "MARKET"))
    pos = m.get_positions()
    assert len(pos) == 1
    assert pos[0].quantity == 6


def test_no_prices_db_rejects(tmp_path: Path) -> None:
    m = DhanMock(prices_db=tmp_path / "does_not_exist.duckdb", initial_cash_inr=50_000.0)
    resp = m.place_order(OrderRequest("BUY", "RELIANCE", 5, "MARKET"))
    assert resp.status == "REJECTED"


# ── Cross-invocation state contract (regressions for the 2026-05-20 paper bug) ──
# Launchd starts a fresh process daily. The old mock (counter from 1;
# empty positions; cash reset to initial) (a) collided on the persisted
# submitted_orders PK on day 2, and (b) would have double-bought
# yesterday's book even if (a) were fixed.


def test_order_ids_unique_across_instances(prices_db: Path) -> None:
    m1 = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    m2 = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    r1 = m1.place_order(OrderRequest("BUY", "RELIANCE", 1, "MARKET"))
    r2 = m2.place_order(OrderRequest("BUY", "RELIANCE", 1, "MARKET"))
    assert r1.status == "TRADED" and r2.status == "TRADED"
    assert r1.order_id != r2.order_id


def _make_portfolio_db(tmp_path: Path) -> Path:
    from storage import portfolio_db
    p = tmp_path / "portfolio.duckdb"
    conn = duckdb.connect(str(p))
    try:
        portfolio_db.init_schema(conn)
    finally:
        conn.close()
    return p


def test_cash_hydrates_from_ledger(tmp_path: Path, prices_db: Path) -> None:
    from datetime import datetime
    from storage import portfolio_db
    p = _make_portfolio_db(tmp_path)
    conn = duckdb.connect(str(p))
    try:
        portfolio_db.insert_cash_entry(
            conn, entry_id="e1",
            entry_at=datetime(2026, 5, 19, 10, 0),
            as_of_date=date(2026, 5, 19),
            kind="buy", amount_usd=-12_050.0, notes="t", mode="dhan-paper",
        )
    finally:
        conn.close()
    m = DhanMock(prices_db=prices_db, portfolio_db=p,
                 initial_cash_inr=50_000.0, mode="dhan-paper")
    assert m.get_cash()["availableBalance"] == pytest.approx(
        50_000.0 - 12_050.0, abs=0.01)


# ── Phase B contract: paper MARKET fills priced at today's NSE open ──
# via the injected fetcher (yfinance in live operation), with graceful
# fallback to bhav close when the fetcher returns None / fails.


def test_phase_b_uses_injected_fetcher_for_today(prices_db: Path) -> None:
    from datetime import date as _date
    today = datetime.now().astimezone().date() if False else None
    # We don't know "today" in the test environment vs the mock's IST clock,
    # so call the price-resolution helper directly with as_of_date == today.
    fetcher_called: list = []
    def fixed(t):
        fetcher_called.append(t)
        return 1234.56  # NOT 1205 (bhav close); has to come from the fetcher
    m = DhanMock(
        prices_db=prices_db, initial_cash_inr=50_000.0,
        slippage_bps=0.0, fill_price_fetcher=fixed,
    )
    from zoneinfo import ZoneInfo
    from datetime import datetime as _dt
    today_ist = _dt.now(ZoneInfo("Asia/Kolkata")).date()
    px = m._fill_reference_price("RELIANCE", today_ist)
    assert px == 1234.56, "today's fill must come from the injected fetcher"
    assert fetcher_called == ["RELIANCE"]


def test_phase_b_falls_back_to_bhav_when_fetcher_returns_none(prices_db: Path) -> None:
    from zoneinfo import ZoneInfo
    from datetime import datetime as _dt
    m = DhanMock(
        prices_db=prices_db, initial_cash_inr=50_000.0,
        slippage_bps=0.0,
        fill_price_fetcher=lambda t: None,  # yfinance glitch / stale day
    )
    today_ist = _dt.now(ZoneInfo("Asia/Kolkata")).date()
    px = m._fill_reference_price("RELIANCE", today_ist)
    assert px == 1205.0, "fetcher=None must fall back to the bhav close"


def test_phase_b_falls_back_to_bhav_when_fetcher_raises(prices_db: Path) -> None:
    from zoneinfo import ZoneInfo
    from datetime import datetime as _dt
    def boom(t):
        raise RuntimeError("Yahoo 503")
    m = DhanMock(
        prices_db=prices_db, initial_cash_inr=50_000.0,
        slippage_bps=0.0, fill_price_fetcher=boom,
    )
    today_ist = _dt.now(ZoneInfo("Asia/Kolkata")).date()
    px = m._fill_reference_price("RELIANCE", today_ist)
    assert px == 1205.0, "fetcher exception must fall back to the bhav close"


def test_phase_b_uses_bhav_for_backfill_dates(prices_db: Path) -> None:
    # Backfill / replay: as_of_date is in the past. yfinance "today" is not
    # the trade date, so use the authoritative bhav archive regardless of
    # whether a fetcher is injected.
    m = DhanMock(
        prices_db=prices_db, initial_cash_inr=50_000.0,
        slippage_bps=0.0,
        fill_price_fetcher=lambda t: 9999.0,  # would be wrong for backfill
    )
    px = m._fill_reference_price("RELIANCE", date(2026, 5, 13))
    assert px == 1205.0, "backfill must use bhav close, not the fetcher"


def test_positions_hydrate_from_open_lots(tmp_path: Path, prices_db: Path) -> None:
    from storage import portfolio_db
    p = _make_portfolio_db(tmp_path)
    conn = duckdb.connect(str(p))
    try:
        portfolio_db.open_lot(
            conn, lot_id="L1", ticker="RELIANCE", buy_fill_id="F1",
            buy_date=date(2026, 5, 19), buy_price=1200.0, qty=10,
            mode="dhan-paper",
        )
    finally:
        conn.close()
    m = DhanMock(prices_db=prices_db, portfolio_db=p,
                 initial_cash_inr=50_000.0, mode="dhan-paper")
    pos = m.get_positions()
    assert len(pos) == 1
    assert pos[0].ticker == "RELIANCE"
    assert pos[0].quantity == 10
    resp = m.place_order(OrderRequest("SELL", "RELIANCE", 4, "MARKET"))
    assert resp.status == "TRADED"
    assert m.get_positions()[0].quantity == 6
