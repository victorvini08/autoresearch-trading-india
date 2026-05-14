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
