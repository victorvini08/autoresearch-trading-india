"""MIN_ORDER_INR filter — suppresses tiny mark-drift tick-over trades
without affecting real rebalances. Pins the contract: trades below the
₹1,500 floor are dropped from the *resize* path, but full-liquidation
orders (a name fully exited because it dropped from the strategy) are
NEVER filtered — those must always execute regardless of size.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from brokers.dhan import OrderRequest
from brokers.dhan_mock import DhanMock
from scripts.executors.dhan import DhanExecutor, MIN_ORDER_INR


@pytest.fixture
def prices_db(tmp_path: Path) -> Path:
    p = tmp_path / "prices.duckdb"
    conn = duckdb.connect(str(p))
    try:
        conn.execute(
            "CREATE TABLE daily_bars (ticker VARCHAR, dt DATE, "
            "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, "
            "volume BIGINT, value_inr_crores DOUBLE, "
            "PRIMARY KEY (ticker, dt))"
        )
        for tkr, px in (("CHEAP", 200.0), ("MID", 1500.0), ("PREMIUM", 5000.0)):
            conn.execute(
                "INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?,?)",
                (tkr, date(2026, 5, 25), px, px, px, px, 100_000, 1.0),
            )
    finally:
        conn.close()
    return p


@pytest.fixture
def portfolio_db_empty(tmp_path: Path) -> Path:
    from storage import portfolio_db
    p = tmp_path / "portfolio.duckdb"
    conn = duckdb.connect(str(p))
    try:
        portfolio_db.init_schema(conn)
    finally:
        conn.close()
    return p


def _executor(prices_db, portfolio_db_path, *, broker_cash, broker_positions):
    """Build a DhanExecutor with an injected broker carrying controlled
    cash + positions (bypasses hydration so tests are deterministic)."""
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=broker_cash,
                    slippage_bps=0.0, mode="dhan-paper")
    mock._cash = broker_cash
    for tkr, qty, avg in broker_positions:
        mock._positions[tkr.upper()] = [[qty, avg]]
    e = DhanExecutor(
        mode="dhan-paper", prices_db=prices_db,
        portfolio_db=portfolio_db_path, broker=mock,
    )
    return e


def test_tiny_trade_below_floor_is_suppressed(prices_db, portfolio_db_empty):
    """1-share trim of CHEAP @ ₹200 = ₹200 trade << ₹1,500 floor → SKIP."""
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=49_800.0,                # 100k − 250 × 200.8 ≈ 49.8k
                  broker_positions=[("CHEAP", 251, 200.0)])  # 251 × 200 = ₹50,200
    # equity ≈ 100,000; target 0.50 of CHEAP @ ₹200 = int(50,000/200) = 250.
    # current 251 → delta = -1 → 1-share sell @ ₹200 = ₹200 trade.
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"CHEAP": 0.50},
    )
    assert orders == [], f"tiny ₹200 trade must be suppressed, got: {orders}"


def test_normal_rebalance_above_floor_fires(prices_db, portfolio_db_empty):
    """Multi-share trim that exceeds ₹1,500 → fires normally."""
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=20_000.0,
                  broker_positions=[("CHEAP", 400, 200.0)])  # 400 × 200 = 80k
    # equity ≈ 100k; target 0.50 = ₹50,000 = 250 shares.
    # current 400 → delta = -150 → 150 × 200 = ₹30,000 trade >> ₹1,500.
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"CHEAP": 0.50},
    )
    assert len(orders) == 1
    assert orders[0].transaction_type == "SELL"
    assert orders[0].quantity == 150


def test_full_liquidation_never_filtered(prices_db, portfolio_db_empty):
    """A held name absent from targets → full-exit SELL, regardless of
    size. Even a tiny remaining position must clear to avoid orphans."""
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=99_000.0,
                  broker_positions=[("CHEAP", 5, 200.0)])  # 5 × 200 = ₹1,000 < floor
    # CHEAP NOT in targets -> must fully sell despite ₹1,000 notional.
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"MID": 0.50},
    )
    sells = [o for o in orders if o.transaction_type == "SELL"]
    assert len(sells) == 1
    assert sells[0].ticker == "CHEAP"
    assert sells[0].quantity == 5, "full exit must liquidate the whole position"


def test_min_order_inr_constant_size():
    """₹1,500 keeps DP friction under ~1% (14.75 / 1500 = 0.98%)."""
    assert MIN_ORDER_INR >= 14.75 / 0.01, \
        "MIN_ORDER_INR must keep DP friction ≤ ~1% of trade notional"
