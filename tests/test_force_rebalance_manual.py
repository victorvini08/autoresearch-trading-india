"""Manual off-schedule rebalance: execute_day(force_rebalance=True) forces a
rebalance decision on a non-rebalance day / non-empty book, and run_live's
force path bypasses the execution-window guard (a deliberate manual run is
intentional, not a stale late-cron). Distinct from the dhan-live first-day
bootstrap, which is auto-derived from an empty book.
"""
from datetime import date, datetime, time
from pathlib import Path
from unittest.mock import patch

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
            "CREATE TABLE daily_bars (ticker VARCHAR NOT NULL, dt DATE NOT NULL, "
            "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, "
            "value_inr_crores DOUBLE, PRIMARY KEY (ticker, dt))"
        )
        for tk, px in [("RELIANCE", 1200.0), ("LIQUIDCASE", 100.0)]:
            conn.execute("INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?,?)",
                         (tk, date(2026, 5, 13), px, px, px, px, 100000, 1.0))
    finally:
        conn.close()
    return p


@pytest.fixture
def halt_file(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "halt.json"
    import storage.portfolio_db as pdb
    monkeypatch.setattr(pdb, "HALT_FILE_PATH", p)
    return p


def _capture(seen):
    def _fn(*, target_date, strategy_module_name, force_rebalance=False, **kw):
        seen["force"] = force_rebalance
        return {"targets": {"RELIANCE": 0.10}}
    return _fn


def _executor(prices_db, tmp_path):
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    return DhanExecutor(mode="dhan-paper", prices_db=prices_db,
                        portfolio_db=tmp_path / "pf.duckdb", broker=mock,
                        initial_cash_inr=50_000.0)


def test_execute_day_threads_force_rebalance_true(prices_db, tmp_path, halt_file, monkeypatch):
    monkeypatch.setenv("DHAN_MOCK", "1")
    ex = _executor(prices_db, tmp_path)
    seen = {}
    with patch("scripts.signal_today.generate_signals", side_effect=_capture(seen)):
        ex.execute_day(date(2026, 5, 13), force_rebalance=True)
    assert seen["force"] is True


def test_execute_day_default_does_not_force(prices_db, tmp_path, halt_file, monkeypatch):
    monkeypatch.setenv("DHAN_MOCK", "1")
    ex = _executor(prices_db, tmp_path)
    seen = {}
    with patch("scripts.signal_today.generate_signals", side_effect=_capture(seen)):
        ex.execute_day(date(2026, 5, 13))
    assert seen["force"] is False


def test_run_live_force_rebalance_bypasses_execution_window(monkeypatch):
    """Out-of-window (noon) run_live SKIPS normally, but force_rebalance runs it."""
    import scripts.run_live as run_live

    captured = {}

    class _StubExecutor:
        def execute_day(self, as_of_date, **kw):
            captured.update(kw)
            from scripts.executors.protocol import ExecutionSummary
            return ExecutionSummary(mode="dhan-paper", as_of_date=as_of_date,
                                    fill_date=as_of_date, n_orders=1, n_fills=1)

    monkeypatch.setattr(run_live, "_build_executor", lambda mode: _StubExecutor())
    monkeypatch.setattr(run_live, "_safe_report", lambda *a, **k: None)
    monkeypatch.setattr(run_live, "premarket_scan",
                        type("_p", (), {"load": staticmethod(lambda d: None)}))
    # simulate "outside the execution window": without force this SKIPS
    monkeypatch.setattr(run_live, "_within_execution_window", lambda *a, **k: False)

    code, summary = run_live.run(mode="dhan-paper", today_ist=date(2026, 5, 13),
                                 force_rebalance=True)
    assert code == 0
    assert summary.n_orders == 1
    assert captured.get("force_rebalance") is True
