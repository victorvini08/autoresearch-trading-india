"""Unit tests for scripts.reconciliation.

Uses in-memory duckdb fixtures so tests don't touch the real ledger.
Covers: empty day, clean rebalance, partial fill, T+1 violation, drawdown
threshold crossings.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import duckdb
import pytest

from scripts.reconciliation import (
    DD_HALTED_REVIEW,
    DD_RISK_REDUCED,
    DD_WATCH,
    compute_reconciliation_for_date,
)
from storage import portfolio_db

MODE = "dhan-paper"
INITIAL_DEPOSIT = 100_000.0


@pytest.fixture
def db(tmp_path):
    """Fresh portfolio.duckdb with schema initialized, no data."""
    path = tmp_path / "portfolio.duckdb"
    conn = portfolio_db.connect(path)
    conn.close()
    return path


def _insert_target(conn, *, d, ticker, frac, mode=MODE):
    portfolio_db.upsert_target(
        conn, as_of_date=d, ticker=ticker, target_fraction=frac,
        source="test", mode=mode,
    )


def _insert_order(
    conn, *, d, ticker, side, qty, status="filled", mode=MODE, order_id=None,
):
    order_id = order_id or uuid.uuid4().hex
    conn.execute(
        "INSERT INTO submitted_orders (order_id, submitted_at, as_of_date, "
        "ticker, side, order_type, quantity, limit_price, status, mode) "
        "VALUES (?, ?, ?, ?, ?, 'MARKET', ?, NULL, ?, ?)",
        [order_id, datetime.combine(d, datetime.min.time()), d, ticker,
         side, qty, status, mode],
    )
    return order_id


def _insert_fill(
    conn, *, order_id, d, ticker, side, qty, price, slippage_bps=5.0, mode=MODE,
):
    conn.execute(
        "INSERT INTO actual_fills (fill_id, order_id, filled_at, ticker, side, "
        "quantity, fill_price, commission, slippage_bps, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?)",
        [uuid.uuid4().hex, order_id, datetime.combine(d, datetime.min.time()),
         ticker, side, qty, price, slippage_bps, mode],
    )


def _insert_cash(
    conn, *, d, kind, amount, mode=MODE, entry_id=None, notes=None,
):
    """Write a cash_ledger row dated at d (entry_at = midnight on d)."""
    conn.execute(
        "INSERT INTO cash_ledger (entry_id, entry_at, as_of_date, kind, "
        "amount_usd, notes, mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [entry_id or uuid.uuid4().hex,
         datetime.combine(d, datetime.min.time()),
         d, kind, amount, notes, mode],
    )


def _insert_snapshot(conn, *, d, ticker, qty, mark_price, mode=MODE):
    conn.execute(
        "INSERT INTO broker_positions (snapshot_date, ticker, quantity, "
        "avg_entry_price, mark_price, mark_value, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, ticker, qty, mark_price, mark_price, qty * mark_price, mode],
    )


# === Q1 / Q2 / Q4 happy path on an empty day ===============================

def test_empty_day_all_ok(db):
    """A day with no orders / no fills / no positions returns OK across the
    board, with appropriate 'no activity' messages."""
    out = compute_reconciliation_for_date(date(2026, 5, 28), MODE, db)
    for q in (
        "held_what_intended",
        "execution_matched_assumptions",
        "construction_drag",
        "t1_cash_math",
        "drawdown_threshold",
    ):
        assert out[q]["status"] == "ok", f"{q} should be ok on empty day"


# === Q1: partial fill is flagged ===========================================

def test_partial_fill_is_flagged(db):
    d = date(2026, 5, 26)
    with portfolio_db.connect(db) as c:
        oid = _insert_order(
            c, d=d, ticker="ONGC", side="buy", qty=100, status="filled",
        )
        _insert_fill(
            c, order_id=oid, d=d, ticker="ONGC", side="buy", qty=80,
            price=280.0,
        )
    out = compute_reconciliation_for_date(d, MODE, db)
    q1 = out["held_what_intended"]
    assert q1["status"] == "flag"
    assert q1["mismatches"][0]["ticker"] == "ONGC"
    assert q1["mismatches"][0]["requested"] == 100
    assert q1["mismatches"][0]["filled"] == 80


# === Q2: high slippage is flagged ==========================================

def test_high_slippage_flagged(db):
    d = date(2026, 5, 26)
    with portfolio_db.connect(db) as c:
        oid = _insert_order(c, d=d, ticker="ONGC", side="buy", qty=10)
        _insert_fill(
            c, order_id=oid, d=d, ticker="ONGC", side="buy", qty=10,
            price=280.0, slippage_bps=250.0,  # above MAX threshold of 200
        )
    out = compute_reconciliation_for_date(d, MODE, db)
    assert out["execution_matched_assumptions"]["status"] == "flag"


# === Q4: T+1 violation is flagged =========================================

def test_t1_cash_math_violation(db):
    """If today's buys exceed pre-day cash + non-sell inflows, flag T+1."""
    d = date(2026, 5, 26)
    yesterday = d - timedelta(days=1)
    with portfolio_db.connect(db) as c:
        # Drain to ₹0 pre-day cash with a withdrawal-style entry
        _insert_cash(
            c, d=yesterday, kind="commission", amount=-INITIAL_DEPOSIT,
        )
        # Today: ₹50,000 of buys with no pre-day cash and no deposits.
        _insert_cash(
            c, d=d, kind="buy", amount=-50_000.0,
            notes="ONGC buy 100 @ 500",
        )
    out = compute_reconciliation_for_date(d, MODE, db)
    q4 = out["t1_cash_math"]
    assert q4["status"] == "flag"
    assert q4["todays_buys"] == 50_000.0
    assert q4["available_for_buys"] < 1.0


def test_t1_cash_math_ok_when_funded_by_pre_day_cash(db):
    d = date(2026, 5, 26)
    with portfolio_db.connect(db) as c:
        _insert_cash(c, d=d, kind="buy", amount=-50_000.0)
    out = compute_reconciliation_for_date(d, MODE, db)
    # initial deposit ₹1L > ₹50k buy → OK
    assert out["t1_cash_math"]["status"] == "ok"


# === Q5: drawdown threshold crossings =====================================

@pytest.mark.parametrize(
    "dd_frac, expected_status, expected_substr",
    [
        (0.04, "ok", "NORMAL"),
        (0.09, "warn", "WATCH"),
        (0.13, "flag", "RISK_REDUCED"),
        (0.18, "flag", "HALTED_REVIEW"),
    ],
)
def test_drawdown_thresholds(db, dd_frac, expected_status, expected_substr):
    """For a synthetic peak-then-drop equity curve, the right state fires."""
    d_peak = date(2026, 5, 20)
    d_today = date(2026, 5, 28)
    peak_equity = 200_000.0
    today_equity = peak_equity * (1 - dd_frac)
    # We need: peak_equity to be the historical max from broker_positions+cash.
    # Easiest: seed initial_deposit then write two snapshots — peak day with a
    # ₹100k position (₹1L cash + ₹1L position = ₹200k peak), today with a
    # position that values at (today_equity - INITIAL_DEPOSIT).
    with portfolio_db.connect(db) as c:
        _insert_snapshot(
            c, d=d_peak, ticker="PEAK", qty=1000,
            mark_price=(peak_equity - INITIAL_DEPOSIT) / 1000,
        )
        _insert_snapshot(
            c, d=d_today, ticker="PEAK", qty=1000,
            mark_price=(today_equity - INITIAL_DEPOSIT) / 1000,
        )
    out = compute_reconciliation_for_date(d_today, MODE, db)
    q5 = out["drawdown_threshold"]
    assert q5["status"] == expected_status, (
        f"Expected {expected_status} at DD={dd_frac}, got {q5['status']}: {q5}"
    )
    assert expected_substr in q5["detail"]


# === Q3: construction drag ================================================

def test_construction_drag_zero_when_targets_match_positions(db):
    """Targets exactly match position values → 0 bps drag."""
    d = date(2026, 5, 26)
    with portfolio_db.connect(db) as c:
        # ₹1L cash (initial) + position worth ₹10k → equity ₹1.1L → 10k/110k = 9.09%
        _insert_snapshot(c, d=d, ticker="ONGC", qty=100, mark_price=100.0)
        _insert_target(c, d=d, ticker="ONGC", frac=10_000 / 110_000)
    out = compute_reconciliation_for_date(d, MODE, db)
    q3 = out["construction_drag"]
    assert q3["status"] == "ok"
    assert abs(q3["total_drag_bps"]) < 5  # within rounding tolerance


def test_construction_drag_large_drag_flagged(db):
    """Targets sum 30%, positions sum 5% → large unfilled drag."""
    d = date(2026, 5, 26)
    with portfolio_db.connect(db) as c:
        _insert_snapshot(c, d=d, ticker="ONGC", qty=5_000, mark_price=1.0)
        # Want 30% of equity (~₹31.5k) in ONGC, actually hold ₹5k
        _insert_target(c, d=d, ticker="ONGC", frac=0.30)
    out = compute_reconciliation_for_date(d, MODE, db)
    q3 = out["construction_drag"]
    assert q3["status"] == "flag"
    assert q3["total_drag_bps"] > 500  # threshold


# === Q1: status bucketing (Step 1.d granularity) ==========================

def test_q1_bucketizes_mixed_statuses(db):
    """3 traded + 1 partial + 1 rejected + 1 pending, mixed casing.
    The bucket histogram must collapse legacy lowercase 'filled' and
    new uppercase 'TRADED' into the same `traded` bucket."""
    d = date(2026, 5, 26)
    with portfolio_db.connect(db) as c:
        # 3 fully traded — one legacy lowercase, two new uppercase
        o1 = _insert_order(c, d=d, ticker="AAA", side="buy", qty=10, status="filled")
        _insert_fill(c, order_id=o1, d=d, ticker="AAA", side="buy", qty=10, price=100.0)
        o2 = _insert_order(c, d=d, ticker="BBB", side="buy", qty=10, status="TRADED")
        _insert_fill(c, order_id=o2, d=d, ticker="BBB", side="buy", qty=10, price=100.0)
        o3 = _insert_order(c, d=d, ticker="CCC", side="buy", qty=10, status="TRADED")
        _insert_fill(c, order_id=o3, d=d, ticker="CCC", side="buy", qty=10, price=100.0)
        # 1 partial
        o4 = _insert_order(c, d=d, ticker="DDD", side="buy", qty=10, status="PART_TRADED")
        _insert_fill(c, order_id=o4, d=d, ticker="DDD", side="buy", qty=4, price=100.0)
        # 1 rejected (zero fills)
        _insert_order(c, d=d, ticker="EEE", side="buy", qty=10, status="REJECTED")
        # 1 pending (zero fills, broker still in transit at EOD)
        _insert_order(c, d=d, ticker="FFF", side="buy", qty=10, status="TRANSIT")
    out = compute_reconciliation_for_date(d, MODE, db)
    q1 = out["held_what_intended"]
    assert q1["status"] == "flag"  # partials + rejects + pending all show as mismatches
    b = q1["buckets"]
    assert b["traded"] == 3, b
    assert b["partial"] == 1, b
    assert b["rejected"] == 1, b
    assert b["pending"] == 1, b  # TRANSIT routes to pending
    # Detail summarises non-zero buckets
    assert "3 traded" in q1["detail"]
    assert "1 partial" in q1["detail"]
    assert "1 rejected" in q1["detail"]
    assert "1 pending" in q1["detail"]


def test_q1_all_traded_clean(db):
    """All orders fully filled — no mismatch, single 'traded' bucket."""
    d = date(2026, 5, 26)
    with portfolio_db.connect(db) as c:
        for tk in ("AAA", "BBB"):
            oid = _insert_order(c, d=d, ticker=tk, side="buy", qty=10, status="TRADED")
            _insert_fill(c, order_id=oid, d=d, ticker=tk, side="buy", qty=10, price=100.0)
    out = compute_reconciliation_for_date(d, MODE, db)
    q1 = out["held_what_intended"]
    assert q1["status"] == "ok"
    assert q1["buckets"]["traded"] == 2
    assert q1["buckets"]["partial"] == 0
    assert "2 traded" in q1["detail"]
    assert "all filled as intended" in q1["detail"]


# === Module-level constants exposed ========================================

def test_thresholds_match_spec():
    assert DD_WATCH == 0.08
    assert DD_RISK_REDUCED == 0.12
    assert DD_HALTED_REVIEW == 0.16
