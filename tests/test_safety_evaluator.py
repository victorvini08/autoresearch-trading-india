"""Step 2.b — daily safety evaluator: persistence + side-effect files.

Tests the thin glue between portfolio.duckdb, the pure state machine
(data/safety_state.py), and the on-disk artifacts the executor + halt
gate consume.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from data.safety_state import SafetyState
from scripts.safety_evaluator import (
    evaluate_and_persist,
    load_prior_state,
    save_state,
    write_halt,
    write_risk_multiplier,
)
from storage import portfolio_db

MODE = "dhan-paper"

# dhan-paper bootstraps with ₹1L cash in get_cash_balance — drain it so
# the synthesized position IS the equity for state-machine math.
_INITIAL_DEPOSIT_INR = 100_000.0


def _drain_initial_cash(conn, *, d=date(2026, 1, 1), mode=MODE):
    """Withdraw the implicit ₹1L paper-mode bootstrap so test equity
    equals position mark_value exactly."""
    conn.execute(
        "INSERT INTO cash_ledger (entry_id, entry_at, as_of_date, kind, "
        "amount_usd, notes, mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [uuid.uuid4().hex, datetime.combine(d, datetime.min.time()), d,
         "commission", -_INITIAL_DEPOSIT_INR, "test-drain", mode],
    )


def _seed_equity_snapshot(conn, *, d, equity, mode=MODE):
    """Drop an EQUITY-equivalent broker_positions snapshot. After the
    initial-cash drain, equity = position mark_value."""
    conn.execute(
        "INSERT INTO broker_positions (snapshot_date, ticker, quantity, "
        "avg_entry_price, mark_price, mark_value, mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, "SYNTH", 1.0, equity, equity, equity, mode],
    )


@pytest.fixture
def db(tmp_path) -> Path:
    p = tmp_path / "portfolio.duckdb"
    portfolio_db.connect(p).close()
    return p


# === Round-trip ============================================================

def test_safety_state_json_round_trip(tmp_path):
    s = SafetyState(
        state="WATCH",
        as_of=date(2026, 5, 28),
        today_equity=92_000.0,
        peak_equity=100_000.0,
        dd_pct=0.08,
        risk_multiplier=1.0,
        halted=False,
        transitioned_today=True,
        entered_state_at=date(2026, 5, 25),
        days_in_state=3,
        reason="DD 8% ≥ 8%; observation.",
    )
    p = tmp_path / "safety_state.json"
    save_state(s, p)
    loaded = load_prior_state(p)
    assert loaded is not None
    assert loaded.state == "WATCH"
    assert loaded.as_of == s.as_of
    assert loaded.entered_state_at == s.entered_state_at
    assert loaded.dd_pct == s.dd_pct
    assert loaded.days_in_state == 3


def test_load_prior_state_missing_file_returns_None(tmp_path):
    assert load_prior_state(tmp_path / "missing.json") is None


def test_load_prior_state_corrupt_file_returns_None(tmp_path):
    p = tmp_path / "corrupt.json"
    p.write_text("{not valid json")
    assert load_prior_state(p) is None


# === No equity history → no state written =================================

def test_evaluate_and_persist_returns_None_when_no_equity_history(
    db, tmp_path,
):
    state_dir = tmp_path / "state"
    out = evaluate_and_persist(mode=MODE, db_path=db, state_dir=state_dir)
    assert out is None
    assert not (state_dir / "safety_state.json").exists()
    assert not (state_dir / "risk_multiplier.json").exists()


# === Happy path: NORMAL state, files written =============================

def test_evaluate_and_persist_writes_all_files_in_NORMAL(db, tmp_path):
    state_dir = tmp_path / "state"
    with portfolio_db.connect(db) as c:
        _drain_initial_cash(c)
        _seed_equity_snapshot(c, d=date(2026, 5, 26), equity=100_000.0)
        _seed_equity_snapshot(c, d=date(2026, 5, 27), equity=101_000.0)
        _seed_equity_snapshot(c, d=date(2026, 5, 28), equity=100_500.0)
    out = evaluate_and_persist(mode=MODE, db_path=db, state_dir=state_dir)
    assert out is not None
    assert out.state == "NORMAL"
    assert out.risk_multiplier == 1.0
    # Both state files exist
    assert (state_dir / "safety_state.json").exists()
    assert (state_dir / "risk_multiplier.json").exists()
    # risk_multiplier.json payload
    rm = json.loads((state_dir / "risk_multiplier.json").read_text())
    assert rm["multiplier"] == 1.0
    assert rm["state"] == "NORMAL"


# === Escalation: RISK_REDUCED persists multiplier 0.5 ====================

def test_RISK_REDUCED_writes_multiplier_half(db, tmp_path):
    state_dir = tmp_path / "state"
    with portfolio_db.connect(db) as c:
        _drain_initial_cash(c)
        _seed_equity_snapshot(c, d=date(2026, 5, 1), equity=100_000.0)
        _seed_equity_snapshot(c, d=date(2026, 5, 28), equity=87_000.0)  # 13% DD
    out = evaluate_and_persist(mode=MODE, db_path=db, state_dir=state_dir)
    assert out is not None
    assert out.state == "RISK_REDUCED"
    assert out.risk_multiplier == 0.5
    rm = json.loads((state_dir / "risk_multiplier.json").read_text())
    assert rm["multiplier"] == 0.5


# === HALTED_REVIEW writes halt.json =======================================

def test_HALTED_REVIEW_writes_halt_file(tmp_path):
    halt_path = tmp_path / "halt.json"
    s = SafetyState(
        state="HALTED_REVIEW",
        as_of=date(2026, 5, 28),
        today_equity=83_000.0,
        peak_equity=100_000.0,
        dd_pct=0.17,
        risk_multiplier=0.0,
        halted=True,
        transitioned_today=True,
        entered_state_at=date(2026, 5, 28),
        days_in_state=0,
        reason="DD 17% ≥ 16%; halting.",
    )
    write_halt(s, halt_path)
    assert halt_path.exists()
    payload = json.loads(halt_path.read_text())
    assert payload["halted"] is True
    assert "safety_state=HALTED_REVIEW" in payload["reason"]


def test_non_halted_state_does_NOT_touch_halt_file(tmp_path):
    """Safety eval must never clear halt.json — only the user can."""
    halt_path = tmp_path / "halt.json"
    halt_path.write_text(json.dumps({"halted": True, "reason": "user"}))
    s = SafetyState(
        state="NORMAL",
        as_of=date(2026, 5, 28),
        today_equity=100_000.0,
        peak_equity=100_000.0,
        dd_pct=0.0,
        risk_multiplier=1.0,
        halted=False,
        transitioned_today=False,
        entered_state_at=date(2026, 5, 25),
        days_in_state=3,
        reason="OK",
    )
    write_halt(s, halt_path)
    # File untouched (still says user-halted)
    payload = json.loads(halt_path.read_text())
    assert payload["halted"] is True
    assert payload["reason"] == "user"


# === Prior-state continuity across runs ===================================

def test_days_in_state_advances_across_persistence(db, tmp_path):
    """Two consecutive runs in NORMAL → day counter advances."""
    state_dir = tmp_path / "state"
    with portfolio_db.connect(db) as c:
        _drain_initial_cash(c)
        _seed_equity_snapshot(c, d=date(2026, 5, 26), equity=100_000.0)
        _seed_equity_snapshot(c, d=date(2026, 5, 27), equity=100_500.0)
    s1 = evaluate_and_persist(mode=MODE, db_path=db, state_dir=state_dir)
    assert s1.days_in_state == 0
    with portfolio_db.connect(db) as c:
        _seed_equity_snapshot(c, d=date(2026, 5, 28), equity=100_300.0)
    s2 = evaluate_and_persist(mode=MODE, db_path=db, state_dir=state_dir)
    assert s2.state == "NORMAL"
    assert s2.days_in_state == 1
    assert s2.transitioned_today is False


# === Dry-run does NOT write =============================================

def test_dry_run_does_not_write_any_state_files(db, tmp_path):
    state_dir = tmp_path / "state"
    with portfolio_db.connect(db) as c:
        _drain_initial_cash(c)
        _seed_equity_snapshot(c, d=date(2026, 5, 28), equity=100_000.0)
    out = evaluate_and_persist(
        mode=MODE, db_path=db, state_dir=state_dir, dry_run=True,
    )
    assert out is not None
    assert out.state == "NORMAL"
    assert not (state_dir / "safety_state.json").exists()
    assert not (state_dir / "risk_multiplier.json").exists()


# === Atomicity guarantees =================================================

def test_save_state_uses_atomic_rename(tmp_path):
    """If save_state writes via a tmp file, the final file shouldn't exist
    until the write is complete — and no stray .tmp should remain after."""
    p = tmp_path / "safety_state.json"
    s = SafetyState(
        state="NORMAL", as_of=date(2026, 5, 28), today_equity=100.0,
        peak_equity=100.0, dd_pct=0.0, risk_multiplier=1.0, halted=False,
        transitioned_today=False, entered_state_at=date(2026, 5, 28),
        days_in_state=0, reason="ok",
    )
    save_state(s, p)
    assert p.exists()
    # No leftover .tmp sibling
    assert not (tmp_path / "safety_state.json.tmp").exists()


def test_write_risk_multiplier_is_idempotent(tmp_path):
    """Self-healing: re-writing produces the same content."""
    p = tmp_path / "risk_multiplier.json"
    s = SafetyState(
        state="NORMAL", as_of=date(2026, 5, 28), today_equity=100.0,
        peak_equity=100.0, dd_pct=0.0, risk_multiplier=1.0, halted=False,
        transitioned_today=False, entered_state_at=date(2026, 5, 28),
        days_in_state=0, reason="ok",
    )
    write_risk_multiplier(s, p)
    first = p.read_text()
    write_risk_multiplier(s, p)
    second = p.read_text()
    # written_at differs by timestamp; multiplier/state stable
    assert json.loads(first)["multiplier"] == json.loads(second)["multiplier"]
    assert json.loads(first)["state"] == json.loads(second)["state"]
