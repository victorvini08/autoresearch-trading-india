"""Two defects surfaced by the 2026-07-13/14 live rebalances:

1. SUPPRESSOR BUG: FRACTION_CHANGE_THRESHOLD compared today's target against
   the previously RECORDED target (desired_targets is written even when every
   order fails), silently assuming the previous target was ACHIEVED. A failed
   rebalance day therefore made the next day's retry look like "no change" and
   suppressed it (live: ADANIPORTS stayed 1 share despite a 10% target).
   Fix: compare against the ACTUAL held fraction of the book.

2. FLOOR ROUND-TRIP: the rebalance sold the cash-floor ETF down to its
   fraction target FIRST, then the floor-sweep re-parked whatever the equity
   buys didn't absorb (live: sold 91 LIQUIDCASE, re-bought 54). Fix: size the
   floor SELL to what the buys actually need (net funding); floor BUYS happen
   only in the post-fill floor-sweep (so a missed buy's cash is re-parked).
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from autoresearch.brokers.dhan_mock import DhanMock
from scripts.executors.dhan import DhanExecutor

FLOOR = "LIQUIDCASE"
FLOOR_PX = 100.0
D1, D2 = date(2026, 5, 13), date(2026, 5, 14)


@pytest.fixture
def prices_db(tmp_path: Path) -> Path:
    p = tmp_path / "prices.duckdb"
    conn = duckdb.connect(str(p))
    try:
        conn.execute(
            "CREATE TABLE daily_bars (ticker VARCHAR NOT NULL, dt DATE NOT NULL, "
            "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, "
            "value_inr_crores DOUBLE, PRIMARY KEY (ticker, dt))"
        )
        for tk, px in [("AAA", 1500.0), ("BBB", 1500.0), ("CCC", 1500.0),
                       ("XXX", 1600.0), ("RELIANCE", 1800.0), (FLOOR, FLOOR_PX)]:
            conn.execute("INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?,?)",
                         (tk, D1, px, px, px, px, 100000, 1.0))
    finally:
        conn.close()
    return p


@pytest.fixture
def halt_file(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "halt.json"
    import autoresearch.storage.portfolio_db as pdb
    monkeypatch.setattr(pdb, "HALT_FILE_PATH", p)
    return p


class SelectiveRejectMock(DhanMock):
    """DhanMock that rejects orders matching (side, ticker) pairs in
    `self.reject`, or everything while `self.reject_all` is True."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.reject: set[tuple[str, str]] = set()
        self.reject_all = False

    def place_order(self, req, *, as_of_date=None):
        if self.reject_all or (req.transaction_type.upper(), req.ticker.upper()) in self.reject:
            from autoresearch.brokers.dhan_mock import STATUS_REJECTED
            from autoresearch.brokers.dhan import OrderResponse
            return OrderResponse(order_id="", status=STATUS_REJECTED)
        return super().place_order(req, as_of_date=as_of_date)


def _executor(prices_db, tmp_path, mock):
    return DhanExecutor(mode="dhan-paper", prices_db=prices_db,
                        portfolio_db=tmp_path / "pf.duckdb", broker=mock,
                        initial_cash_inr=float(mock.get_cash()["availableBalance"]))


def _stub(targets):
    def _fn(*, target_date, strategy_module_name, **kw):
        return {"targets": dict(targets)}
    return _fn


def _qty(mock, ticker):
    return next((p.quantity for p in mock.get_positions() if p.ticker == ticker), 0)


# --- 1. suppressor: failed-rebalance retry must NOT be suppressed -----------

def test_retry_after_failed_rebalance_is_not_suppressed(prices_db, tmp_path, halt_file, monkeypatch):
    """Day 1 records target 10% RELIANCE but every order is rejected (the
    2026-07-13 DH-906 wall). Day 2 retries the same 10% — it must trade,
    not be suppressed by the recorded-but-unfilled day-1 wish."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = SelectiveRejectMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    ex = _executor(prices_db, tmp_path, mock)
    with patch("scripts.signal_today.generate_signals", side_effect=_stub({"RELIANCE": 0.10})):
        mock.reject_all = True
        ex.execute_day(D1)          # wish recorded, nothing fills
        assert _qty(mock, "RELIANCE") == 0
        mock.reject_all = False
        ex.execute_day(D2)          # the retry — must NOT be suppressed
    assert _qty(mock, "RELIANCE") == 2, "failed-rebalance retry was suppressed"


def test_mark_drift_within_threshold_is_still_suppressed(prices_db, tmp_path, halt_file, monkeypatch):
    """Hard-constraint #4's purpose survives: a book within 0.5pp of target
    (here 9.6% actual vs 10.0% target -> a 1-share, >=MIN_ORDER_INR delta)
    must still be suppressed — no mark-drift churn."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = SelectiveRejectMock(prices_db=prices_db, initial_cash_inr=500_000.0, slippage_bps=0.0)
    ex = _executor(prices_db, tmp_path, mock)
    with patch("scripts.signal_today.generate_signals", side_effect=_stub({"XXX": 0.096})):
        ex.execute_day(D1)
    assert _qty(mock, "XXX") == 30          # 0.096*500k/1600 = 30
    with patch("scripts.signal_today.generate_signals", side_effect=_stub({"XXX": 0.10})):
        ex.execute_day(D2)                  # |0.100 - ~0.096| < 0.005
    assert _qty(mock, "XXX") == 30, "mark-drift 1-share churn was not suppressed"


# --- 2. floor netting: sell only what the buys need, park misses later ------

def _seed_big_floor(prices_db, tmp_path, mock):
    """Day 1: one small equity name; the floor-sweep parks the rest (~435 sh).
    Leaves: AAA 1 sh, floor ~435 sh, cash ~ buffer."""
    ex = _executor(prices_db, tmp_path, mock)
    with patch("scripts.signal_today.generate_signals", side_effect=_stub({"AAA": 0.05})):
        ex.execute_day(D1)
    return ex


def test_floor_sell_sized_to_fund_buys_no_roundtrip(prices_db, tmp_path, halt_file, monkeypatch):
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = SelectiveRejectMock(prices_db=prices_db, initial_cash_inr=46_000.0, slippage_bps=0.0)
    ex = _seed_big_floor(prices_db, tmp_path, mock)
    floor_before = _qty(mock, FLOOR)
    cash_before = float(mock.get_cash()["availableBalance"])
    assert floor_before > 400                      # big floor, tiny cash

    with patch("scripts.signal_today.generate_signals",
               side_effect=_stub({"AAA": 0.10, "BBB": 0.10, "CCC": 0.10})):
        summary = ex.execute_day(D2)

    assert _qty(mock, "AAA") == 3 and _qty(mock, "BBB") == 3 and _qty(mock, "CCC") == 3
    # buys funded: 2+3+3 shares @1500 = 12,000. The floor sell must be sized
    # to (need - cash), NOT down to the floor's fraction target.
    buys_notional = (2 + 3 + 3) * 1500.0
    expected_sell = math.ceil((buys_notional * 1.005 - cash_before) / FLOOR_PX)
    floor_after = _qty(mock, FLOOR)
    assert floor_before - floor_after == expected_sell, (
        f"floor sell {floor_before - floor_after} != funding need {expected_sell}")
    # and NO same-run floor re-buy (the old sell-91-rebuy-54 round-trip)
    rebuys = [n for n in (summary.notes or []) if "floor-sweep: parked" in n]
    assert not rebuys, f"round-trip: floor re-bought in the same run: {rebuys}"


def test_missed_buy_cash_is_reparked_into_floor(prices_db, tmp_path, halt_file, monkeypatch):
    """User-specified behavior: if an equity buy never fills, the cash raised
    for it goes back into the floor (and the note reports the ACTUAL qty)."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = SelectiveRejectMock(prices_db=prices_db, initial_cash_inr=46_000.0, slippage_bps=0.0)
    ex = _seed_big_floor(prices_db, tmp_path, mock)
    floor_before = _qty(mock, FLOOR)
    cash_before = float(mock.get_cash()["availableBalance"])

    mock.reject = {("BUY", "BBB")}                 # BBB can never fill
    with patch("scripts.signal_today.generate_signals",
               side_effect=_stub({"AAA": 0.10, "BBB": 0.10, "CCC": 0.10})):
        summary = ex.execute_day(D2)

    assert _qty(mock, "BBB") == 0
    assert _qty(mock, "AAA") == 3 and _qty(mock, "CCC") == 3
    # BBB's ~4,500 came back into the floor via the floor-sweep
    floor_after = _qty(mock, FLOOR)
    sold = math.ceil(((2 + 3 + 3) * 1500.0 * 1.005 - cash_before) / FLOOR_PX)
    reparked = floor_after - (floor_before - sold)
    assert reparked >= 30, f"missed buy's cash was not re-parked (reparked={reparked})"
    # the note must report the ACTUAL parked qty (was: counted placed, not filled)
    park_notes = [n for n in (summary.notes or []) if "floor-sweep: parked" in n]
    assert park_notes and f"+{reparked}" in park_notes[0], (
        f"floor-sweep note wrong: {park_notes}")
    # and the run is honestly flagged incomplete
    assert any("INCOMPLETE" in n for n in (summary.notes or []))
