"""Step 1.d — submitted_orders terminal-status derivation.

End-of-day `submitted_orders.status` must reflect realised fills, not the
mid-flight broker status. ledger_writer derives:

  sum(fills) == requested  →  TRADED
  0 < sum(fills) < req      →  PART_TRADED
  no fills                  →  whatever the broker reported (REJECTED, etc.)

These tests exercise that derivation directly, bypassing the executor.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from scripts.ledger_writer import write_execution_result
from storage import portfolio_db

MODE = "dhan-paper"


def _order(*, order_id, ticker, qty, status):
    return SimpleNamespace(
        order_id=order_id,
        submitted_at=datetime(2026, 5, 26, 10, 30),
        ticker=ticker,
        side="buy",
        order_type="MARKET",
        quantity=qty,
        limit_price=None,
        status=status,
    )


def _fill(*, fill_id, order_id, ticker, qty, price):
    return SimpleNamespace(
        fill_id=fill_id,
        order_id=order_id,
        filled_at=datetime(2026, 5, 26, 10, 31),
        ticker=ticker,
        side="buy",
        quantity=qty,
        fill_price=price,
        commission=0.0,
        slippage_bps=None,
    )


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "portfolio.duckdb"
    portfolio_db.connect(path).close()
    return path


def _status_of(db, order_id):
    with portfolio_db.connect(db) as c:
        row = c.execute(
            "SELECT status FROM submitted_orders WHERE order_id = ?",
            [order_id],
        ).fetchone()
    return row[0]


def test_full_fill_resolves_to_TRADED(db):
    oid = uuid.uuid4().hex
    with portfolio_db.connect(db) as c:
        write_execution_result(
            c, as_of_date=date(2026, 5, 26), mode=MODE,
            orders=[_order(order_id=oid, ticker="ONGC", qty=10, status="PENDING")],
            fills=[_fill(fill_id=uuid.uuid4().hex, order_id=oid,
                         ticker="ONGC", qty=10, price=280.0)],
            new_positions={"ONGC": (10, 280.0)},
        )
    assert _status_of(db, oid) == "TRADED"


def test_partial_fill_resolves_to_PART_TRADED(db):
    oid = uuid.uuid4().hex
    with portfolio_db.connect(db) as c:
        write_execution_result(
            c, as_of_date=date(2026, 5, 26), mode=MODE,
            orders=[_order(order_id=oid, ticker="ONGC", qty=10, status="PART_TRADED")],
            # Single fill smaller than requested — broker filled 6, dropped 4.
            fills=[_fill(fill_id=uuid.uuid4().hex, order_id=oid,
                         ticker="ONGC", qty=6, price=280.0)],
            new_positions={"ONGC": (6, 280.0)},
        )
    assert _status_of(db, oid) == "PART_TRADED"


def test_split_partial_fills_resolves_to_TRADED_when_summed_match(db):
    """Two fills (3 + 7 = 10) for a 10-qty request → TRADED, not PART_TRADED.

    Mirrors the live-Dhan flow where a single order can return N trade legs."""
    oid = uuid.uuid4().hex
    with portfolio_db.connect(db) as c:
        write_execution_result(
            c, as_of_date=date(2026, 5, 26), mode=MODE,
            orders=[_order(order_id=oid, ticker="RELIANCE", qty=10, status="PART_TRADED")],
            fills=[
                _fill(fill_id="leg-1", order_id=oid,
                      ticker="RELIANCE", qty=3, price=2400.0),
                _fill(fill_id="leg-2", order_id=oid,
                      ticker="RELIANCE", qty=7, price=2400.5),
            ],
            new_positions={"RELIANCE": (10, 2400.5)},
        )
    assert _status_of(db, oid) == "TRADED"


def test_rejected_order_with_no_fills_keeps_REJECTED(db):
    oid = uuid.uuid4().hex
    with portfolio_db.connect(db) as c:
        write_execution_result(
            c, as_of_date=date(2026, 5, 26), mode=MODE,
            orders=[_order(order_id=oid, ticker="ONGC", qty=10, status="REJECTED")],
            fills=[],
            new_positions={},
        )
    assert _status_of(db, oid) == "REJECTED"
