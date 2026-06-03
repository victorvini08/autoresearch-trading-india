"""Whole-share rounding hold-band — the expensive-name complement to the
MIN_ORDER_INR floor (test_min_order_size.py).

ROOT CAUSE (reproduced live 2026-06-03): the executor sizes each name with
``target_qty = int(target_fraction * total_equity / px)``. On a non-rebalance
day the strategy carries the book forward, so its target for a held name is
just the projection of what we already own:

    target_fraction = held_qty * px / equity     (forward map)
    target_qty      = target_fraction * equity / px   (inverse — should be held_qty)

In exact arithmetic that round-trip is the identity. In practice the stored
fraction is rounded to 6 dp AND the executor re-derives equity/price from a
slightly different snapshot (signal-time projection vs execution-time
`_load_latest_closes`), so the raw inverse lands a hair below the held integer
— e.g. ``0.99999`` — and ``int()`` floors it to ``held - 1``, manufacturing a
phantom SELL. The MIN_ORDER_INR floor can't catch it for an expensive name:
one TITAN share (~₹4,078) is far above the ₹1,500 floor. Left unfixed it
compounds — TITAN bled 2→1→0 over three consecutive non-rebalance days as each
spurious sell shrank the book and re-truncated the next day.

FIX: a hold-band (the integer analogue of FRACTION_CHANGE_THRESHOLD). If the
*nearest* integer to the raw target equals what we already hold, hold it. This
only ever RETAINS an existing position — it never rounds a new name up, so it
cannot create an unaffordable buy or disturb rebalance-day sizing.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from brokers.dhan_mock import DhanMock
from scripts.executors.dhan import DhanExecutor


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
        # PREMIUM is a clean ₹5,000 share; TITANLIKE mirrors the real incident.
        for tkr, px in (("PREMIUM", 5000.0), ("TITANLIKE", 4078.1)):
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
    """DhanExecutor with an injected broker carrying controlled cash +
    positions (bypasses hydration so tests are deterministic). Mirrors the
    helper in test_min_order_size.py."""
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=broker_cash,
                    slippage_bps=0.0, mode="dhan-paper")
    mock._cash = broker_cash
    for tkr, qty, avg in broker_positions:
        mock._positions[tkr.upper()] = [[qty, avg]]
    return DhanExecutor(
        mode="dhan-paper", prices_db=prices_db,
        portfolio_db=portfolio_db_path, broker=mock,
    )


def test_held_name_target_rounding_to_held_is_not_shed(prices_db, portfolio_db_empty):
    """The bug repro. Held 1 PREMIUM @ ₹5,000; carry-forward target projects
    to raw 0.99999 shares. floor() → 0 → phantom SELL of the whole position.
    With the hold-band: nearest int (1) == held (1) → HOLD, zero orders.
    One share (₹5,000) is far above the ₹1,500 MIN_ORDER floor, so MIN_ORDER
    does NOT save it — only the hold-band does."""
    # total_equity = 95,000 cash + 1 × 5,000 = 100,000
    # target_fraction 0.0499995 → raw = 0.0499995 × 100000 / 5000 = 0.99999
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=95_000.0,
                  broker_positions=[("PREMIUM", 1, 5000.0)])
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"PREMIUM": 0.0499995},
    )
    assert orders == [], f"held position must not be shed by rounding, got: {orders}"


def test_titan_incident_exact_repro(prices_db, portfolio_db_empty):
    """The literal 2026-06-03 incident: TITAN held 1 @ ₹4,078.1, target
    fraction 0.040864, equity ≈ ₹99,796 → raw 0.99999 → int() sold the last
    share. Locks that the fixed engine carries it forward untouched."""
    # cash = 99,796 − 1 × 4,078.1 = 95,717.9  → total_equity ≈ 99,796
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=95_717.9,
                  broker_positions=[("TITANLIKE", 1, 4078.1)])
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"TITANLIKE": 0.040864},
    )
    assert orders == [], f"TITAN-like hold must not be shed, got: {orders}"


def test_titan_incident_full_bleed_prevented(prices_db, portfolio_db_empty):
    """The first domino: the 2026-06-02 state. TITAN held 2 @ ₹4,078.1, target
    fraction 0.080752, equity ≈ ₹99,796 → raw 1.976 → int() = 1 → sold 1
    (2→1), which set up the 06-03 sell that finished the job (1→0). With the
    hold-band the nearest int (2) == held (2) → HOLD, so the bleed never
    starts."""
    # cash = 99,796 − 2 × 4,078.1 = 91,639.8  → total_equity ≈ 99,796
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=91_639.8,
                  broker_positions=[("TITANLIKE", 2, 4078.1)])
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"TITANLIKE": 0.080752},
    )
    assert orders == [], f"held 2 must not be trimmed to 1 by rounding, got: {orders}"


def test_genuine_trim_of_held_premium_still_fires(prices_db, portfolio_db_empty):
    """The hold-band must NOT over-suppress a real rebalance. Held 3 PREMIUM,
    target projects to ~1.2 shares (a genuine 2-share trim). Nearest int (1)
    != held (3) → no snap → SELL 2 fires normally."""
    # total_equity = 85,000 + 3 × 5,000 = 100,000
    # target_fraction 0.06 → raw = 0.06 × 100000 / 5000 = 1.2 → floor 1 → delta −2
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=85_000.0,
                  broker_positions=[("PREMIUM", 3, 5000.0)])
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"PREMIUM": 0.06},
    )
    assert len(orders) == 1
    assert orders[0].transaction_type == "SELL"
    assert orders[0].quantity == 2


def test_new_name_under_one_share_is_not_rounded_up(prices_db, portfolio_db_empty):
    """Cash-safety guard: the hold-band only RETAINS held positions. A name we
    do NOT hold whose target projects to 0.99999 shares must floor to 0 (no
    buy), never round up to a share we may not be able to afford."""
    # total_equity = 100,000; PREMIUM not held; raw 0.99999 → floor 0 → no buy
    e = _executor(prices_db, portfolio_db_empty,
                  broker_cash=100_000.0,
                  broker_positions=[])
    orders, gb, gs = e._build_orders(
        as_of_date=date(2026, 5, 25), targets={"PREMIUM": 0.0499995},
    )
    assert orders == [], f"sub-one-share new name must not be bought, got: {orders}"
