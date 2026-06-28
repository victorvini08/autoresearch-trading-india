"""Unit tests for data.live_health (the dashboard's process-fidelity panel).

In-memory duckdb fixtures, never the real ledger. Uses a custom mode so the
₹50k 'dhan-paper' initial-deposit anchor doesn't dominate the toy cash numbers
(get_cash_balance falls back to 0.0 for an unknown mode).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

import pytest

from data.live_health import _dd_protection_pp, compute_live_health
from storage import portfolio_db


def test_dd_protection_sign():
    """Positive = we fell LESS than Nifty (the edge); negative = we fell more."""
    # strat dipped −0.53%, Nifty −1.42% → we protected by +0.89pp
    assert _dd_protection_pp(-0.53, -1.42) == pytest.approx(0.89)
    # strat dipped −5%, Nifty only −2% → we fell 3pp MORE → negative
    assert _dd_protection_pp(-5.0, -2.0) == pytest.approx(-3.0)
    # missing benchmark → NaN, not a bogus number
    assert _dd_protection_pp(-1.0, float("nan")) != _dd_protection_pp(-1.0, float("nan"))

MODE = "test-health"
D1 = date(2026, 6, 15)
D2 = date(2026, 6, 19)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "portfolio.duckdb"
    portfolio_db.connect(path).close()
    return path


def _target(conn, *, d, ticker, frac, source):
    portfolio_db.upsert_target(
        conn, as_of_date=d, ticker=ticker, target_fraction=frac,
        source=source, mode=MODE,
    )


def _snapshot(conn, *, d, ticker, qty, mark):
    conn.execute(
        "INSERT INTO broker_positions (snapshot_date, ticker, quantity, "
        "avg_entry_price, mark_price, mark_value, mode) VALUES (?,?,?,?,?,?,?)",
        [d, ticker, qty, mark, mark, qty * mark, MODE],
    )


def _cash(conn, *, d, amount):
    conn.execute(
        "INSERT INTO cash_ledger (entry_id, entry_at, as_of_date, kind, "
        "amount_usd, notes, mode) VALUES (?,?,?,?,?,?,?)",
        [uuid.uuid4().hex, datetime.combine(d, datetime.min.time()), d,
         "deposit", amount, None, MODE],
    )


def _fill(conn, *, d, ticker, qty, price, slippage_bps=5.0):
    oid = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO submitted_orders (order_id, submitted_at, as_of_date, "
        "ticker, side, order_type, quantity, limit_price, status, mode) "
        "VALUES (?,?,?,?,?,'MARKET',?,NULL,'filled',?)",
        [oid, datetime.combine(d, datetime.min.time()), d, ticker, "buy", qty, MODE],
    )
    conn.execute(
        "INSERT INTO actual_fills (fill_id, order_id, filled_at, ticker, side, "
        "quantity, fill_price, commission, slippage_bps, mode) "
        "VALUES (?,?,?,?,?,?,?,0.0,?,?)",
        [uuid.uuid4().hex, oid, datetime.combine(d, datetime.min.time()),
         ticker, "buy", qty, price, slippage_bps, MODE],
    )


def _faithful_book(path):
    """A book that exactly matches its intent: AAA/BBB at 10% each, LIQUIDCASE
    floor at 50%, ₹300 residual cash → total ₹1000."""
    conn = portfolio_db.connect(path)
    _target(conn, d=D2, ticker="AAA", frac=0.10, source="strategy")
    _target(conn, d=D2, ticker="BBB", frac=0.10, source="strategy")
    _target(conn, d=D2, ticker="LIQUIDCASE", frac=0.50, source="cash_floor")
    _cash(conn, d=D1, amount=300.0)
    for d in (D1, D2):
        _snapshot(conn, d=d, ticker="AAA", qty=10, mark=10.0)
        _snapshot(conn, d=d, ticker="BBB", qty=10, mark=10.0)
        _snapshot(conn, d=d, ticker="LIQUIDCASE", qty=5, mark=100.0)
    _fill(conn, d=D1, ticker="AAA", qty=10, price=10.0)
    conn.close()


def test_empty_bucket_returns_none(db):
    assert compute_live_health(mode=MODE, db_path=db) is None


def test_faithful_book_is_green(db):
    _faithful_book(db)
    h = compute_live_health(mode=MODE, db_path=db)
    assert h is not None
    assert h["verdict"]["status"] == "GREEN"

    by_key = {f["key"]: f for f in h["fidelity"]}
    assert by_key["selection"]["status"] == "ok"
    assert by_key["deployment"]["status"] == "ok"
    assert by_key["floor"]["status"] == "ok"
    # window spans both snapshots
    assert h["window"]["n_snapshots"] == 2
    # behaviour panel present and flat (~0% over the toy window)
    assert "strategy_return_pct" in h["behavior"]
    # checklist + pending layers exist
    assert h["capital_checklist"]
    assert len(h["pending"]) == 2


def test_dropped_name_zero_target_is_not_a_mismatch(db):
    """A name the strategy dropped (target 0.0) and that we correctly no longer
    hold must read as a MATCH, not a false 'intended-not-held' flag. This is the
    every-rebalance regression: the strategy writes an explicit 0.0 to drive the
    sell, and that name is intended-FLAT."""
    conn = portfolio_db.connect(db)
    _target(conn, d=D2, ticker="AAA", frac=0.10, source="strategy")
    _target(conn, d=D2, ticker="BBB", frac=0.10, source="strategy")
    _target(conn, d=D2, ticker="ZZZ", frac=0.0, source="strategy")   # dropped
    _target(conn, d=D2, ticker="LIQUIDCASE", frac=0.50, source="cash_floor")
    _cash(conn, d=D1, amount=300.0)
    for d in (D1, D2):
        _snapshot(conn, d=d, ticker="AAA", qty=10, mark=10.0)
        _snapshot(conn, d=d, ticker="BBB", qty=10, mark=10.0)
        _snapshot(conn, d=d, ticker="LIQUIDCASE", qty=5, mark=100.0)
    conn.close()

    h = compute_live_health(mode=MODE, db_path=db)
    by_key = {f["key"]: f for f in h["fidelity"]}
    assert by_key["selection"]["status"] == "ok"
    assert "ZZZ" not in by_key["selection"]["detail"]


def test_selection_mismatch_flags_red(db):
    """Held names diverge from intent (BBB missing, CCC unexpected) → RED."""
    conn = portfolio_db.connect(db)
    _target(conn, d=D2, ticker="AAA", frac=0.10, source="strategy")
    _target(conn, d=D2, ticker="BBB", frac=0.10, source="strategy")
    _target(conn, d=D2, ticker="LIQUIDCASE", frac=0.50, source="cash_floor")
    _cash(conn, d=D1, amount=300.0)
    _snapshot(conn, d=D1, ticker="AAA", qty=10, mark=10.0)
    _snapshot(conn, d=D1, ticker="CCC", qty=10, mark=10.0)   # not intended
    _snapshot(conn, d=D1, ticker="LIQUIDCASE", qty=5, mark=100.0)
    conn.close()

    h = compute_live_health(mode=MODE, db_path=db)
    by_key = {f["key"]: f for f in h["fidelity"]}
    assert by_key["selection"]["status"] == "flag"
    assert h["verdict"]["status"] == "RED"


def test_floor_drift_warns(db):
    """Floor far from its target but selection fine → not GREEN, floor flagged."""
    conn = portfolio_db.connect(db)
    _target(conn, d=D1, ticker="AAA", frac=0.10, source="strategy")
    _target(conn, d=D1, ticker="LIQUIDCASE", frac=0.50, source="cash_floor")
    _cash(conn, d=D1, amount=800.0)                      # too much idle cash
    _snapshot(conn, d=D1, ticker="AAA", qty=10, mark=10.0)
    _snapshot(conn, d=D1, ticker="LIQUIDCASE", qty=1, mark=100.0)  # only 100 in floor
    conn.close()

    h = compute_live_health(mode=MODE, db_path=db)
    by_key = {f["key"]: f for f in h["fidelity"]}
    # floor is ~10% of equity vs 50% target → far outside band → flag
    assert by_key["floor"]["status"] == "flag"
    assert h["verdict"]["status"] == "RED"
