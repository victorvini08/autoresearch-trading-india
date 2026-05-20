"""run_live orchestrator — pre-flight gates, executor dispatch, report rendering.

TWEAKS from US repo:
- Mode names: 'paper'/'ibkr-paper'/'ibkr-live' -> 'dhan-paper'/'dhan-live'
- Timing kwarg: today_et -> today_ist (orchestrator runs on IST clock)
- Execution window: 10:00-15:00 IST (was 10:30-15:00 ET)
- Both Indian modes are intraday (signal-on-T, fills-on-T), so there is no
  "paper skips window check" behavior — paper enforces the same window as
  live. Adjusted test_paper_mode_skips_window_check accordingly (renamed
  to express that paper RESPECTS the window).
"""
from __future__ import annotations

import json
from datetime import date, datetime

import pytest

from scripts import run_live, premarket_scan, daily_report, dashboard
from scripts.executors.protocol import ExecutionSummary, PreflightSkipped
from storage import portfolio_db


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated halt file + reports dir + scan dir."""
    halt_file = tmp_path / "halt.json"
    reports_dir = tmp_path / "reports"
    scan_dir = tmp_path / "scans"
    db_path = tmp_path / "portfolio.duckdb"

    monkeypatch.setattr(run_live, "HALT_FILE_PATH", halt_file)
    monkeypatch.setattr(portfolio_db, "HALT_FILE_PATH", halt_file)
    monkeypatch.setattr(daily_report, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(dashboard, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(premarket_scan, "SCAN_DIR", scan_dir)

    _conn = portfolio_db.connect(db_path)
    portfolio_db.init_schema(_conn)
    _conn.close()
    return {
        "halt_file": halt_file,
        "reports_dir": reports_dir,
        "scan_dir": scan_dir,
        "db_path": db_path,
    }


def _stub_executor(*, summary: ExecutionSummary = None,
                   raise_exc: Exception | None = None):
    """A duck-typed Executor double that returns a canned summary or raises."""

    class Stub:
        mode = "dhan-paper"

        def execute_day(self, as_of_date, *, strategy_module="strategy", source_tag="run_live", skips=None):
            if raise_exc is not None:
                raise raise_exc
            if summary is not None:
                return summary
            return ExecutionSummary(
                mode="dhan-paper",
                as_of_date=as_of_date,
                fill_date=as_of_date,
                n_orders=1,
                n_fills=1,
                gross_buy_usd=100.0,
                gross_sell_usd=0.0,
                total_commission_usd=1.0,
            )

    return Stub()


def test_halt_file_blocks_run(env, monkeypatch):
    env["halt_file"].write_text(json.dumps({
        "reason": "manual pause",
        "set_at": "2026-05-13T00:00:00+00:00",
        "set_by": "manual",
        "resume_token": "tok",
    }))
    # We never reach the executor in this path; stubbing _build_executor
    # is precautionary so any accidental call raises clearly.
    monkeypatch.setattr(run_live, "_build_executor", lambda mode: _stub_executor())

    code, summary = run_live.run(mode="dhan-paper", today_ist=date(2026, 5, 13))
    assert code == 1
    assert summary.halt_set is True
    assert summary.skipped is True
    assert "manual pause" in summary.skipped_reason


def test_outside_window_skips_in_live_mode(env, monkeypatch):
    monkeypatch.setattr(run_live, "_within_execution_window", lambda now: False)
    monkeypatch.setattr(run_live, "_build_executor", lambda mode: _stub_executor())

    code, summary = run_live.run(mode="dhan-live", today_ist=date(2026, 5, 13))
    assert code == 0  # skipping is not a failure
    assert summary.skipped is True
    assert "Outside execution window" in summary.skipped_reason


def test_paper_mode_respects_window_check(env, monkeypatch):
    """TWEAK: In the India repo BOTH modes (dhan-paper / dhan-live) are intraday
    signal-on-T fills-on-T, so paper-mode also enforces the IST execution
    window — there is no overnight backfill exception (unlike the US repo).
    Test now asserts the window-check fires the same way for dhan-paper.
    """
    monkeypatch.setattr(run_live, "_within_execution_window", lambda now: False)
    monkeypatch.setattr(run_live, "_build_executor", lambda mode: _stub_executor())

    code, summary = run_live.run(mode="dhan-paper", today_ist=date(2026, 5, 13))
    assert code == 0  # skipping is not a failure
    assert summary.skipped is True
    assert "Outside execution window" in summary.skipped_reason


def test_preflight_skipped_propagates_to_report(env, monkeypatch):
    """Executor raising PreflightSkipped → orchestrator returns skip summary + report."""
    monkeypatch.setattr(run_live, "_within_execution_window", lambda now: True)
    monkeypatch.setattr(
        run_live, "_build_executor",
        lambda mode: _stub_executor(raise_exc=PreflightSkipped(
            "no trading day available", set_halt=False)),
    )
    monkeypatch.setattr(run_live, "_resolve_target_date",
                        lambda mode, today, prices_db=None: date(2026, 5, 12))

    code, summary = run_live.run(mode="dhan-paper", today_ist=date(2026, 5, 13))
    assert code == 0
    assert summary.skipped is True
    assert "no trading day" in summary.skipped_reason


def test_unhandled_exception_returns_2(env, monkeypatch):
    """A non-PreflightSkipped exception from the executor returns exit code 2."""
    monkeypatch.setattr(run_live, "_within_execution_window", lambda now: True)
    monkeypatch.setattr(
        run_live, "_build_executor",
        lambda mode: _stub_executor(raise_exc=RuntimeError("kaboom")),
    )
    monkeypatch.setattr(run_live, "_resolve_target_date",
                        lambda mode, today, prices_db=None: date(2026, 5, 12))

    code, summary = run_live.run(mode="dhan-paper", today_ist=date(2026, 5, 13))
    assert code == 2
    assert "RuntimeError" in summary.skipped_reason


def test_successful_run_writes_daily_report(env, monkeypatch):
    monkeypatch.setattr(run_live, "_within_execution_window", lambda now: True)
    stub_summary = ExecutionSummary(
        mode="dhan-paper", as_of_date=date(2026, 5, 12), fill_date=date(2026, 5, 13),
        n_orders=1, n_fills=1, gross_buy_usd=200.0, gross_sell_usd=0.0,
        total_commission_usd=1.5,
    )
    monkeypatch.setattr(run_live, "_build_executor",
                        lambda mode: _stub_executor(summary=stub_summary))
    monkeypatch.setattr(run_live, "_resolve_target_date",
                        lambda mode, today, prices_db=None: date(2026, 5, 12))
    # daily_report.generate calls into portfolio_db.connect(); we use the
    # empty fixture DB which is safe (sections fall back to "_(no...)_").
    monkeypatch.setattr(daily_report, "REPORTS_DIR", env["reports_dir"])
    monkeypatch.setattr(dashboard, "REPORTS_DIR", env["reports_dir"])
    # Patch daily_report's portfolio_db reference too
    monkeypatch.setattr(daily_report.portfolio_db, "DEFAULT_DB_PATH", env["db_path"])
    monkeypatch.setattr(dashboard.portfolio_db, "DEFAULT_DB_PATH", env["db_path"])

    code, summary = run_live.run(mode="dhan-paper", today_ist=date(2026, 5, 13))
    assert code == 0
    report_path = env["reports_dir"] / "2026-05-12.md"
    assert report_path.exists()
    body = report_path.read_text()
    assert "[OK]" in body
    # Dashboard is refreshed in the same orchestrator pass.
    dash_path = env["reports_dir"] / "dashboard.html"
    assert dash_path.exists()
    assert "<title>Trading Dashboard</title>" in dash_path.read_text()


def test_premarket_scan_payload_loaded_when_present(env, monkeypatch):
    monkeypatch.setattr(run_live, "_within_execution_window", lambda now: True)
    env["scan_dir"].mkdir(parents=True, exist_ok=True)
    (env["scan_dir"] / "premarket_2026-05-13.json").write_text(json.dumps({
        "as_of_date": "2026-05-13",
        "vix": {"level": 18.0, "flag": False},
        "tickers": {"NVDA": {"gap_flag": True}},
        "halt_recommendations": [],
    }))
    stub_summary = ExecutionSummary(
        mode="dhan-paper", as_of_date=date(2026, 5, 12), fill_date=date(2026, 5, 13),
        n_orders=0, n_fills=0,
    )
    monkeypatch.setattr(run_live, "_build_executor",
                        lambda mode: _stub_executor(summary=stub_summary))
    monkeypatch.setattr(run_live, "_resolve_target_date",
                        lambda mode, today, prices_db=None: date(2026, 5, 12))
    monkeypatch.setattr(daily_report, "REPORTS_DIR", env["reports_dir"])
    monkeypatch.setattr(dashboard, "REPORTS_DIR", env["reports_dir"])
    monkeypatch.setattr(daily_report.portfolio_db, "DEFAULT_DB_PATH", env["db_path"])
    monkeypatch.setattr(dashboard.portfolio_db, "DEFAULT_DB_PATH", env["db_path"])

    code, summary = run_live.run(mode="dhan-paper", today_ist=date(2026, 5, 13))
    assert code == 0
    body = (env["reports_dir"] / "2026-05-12.md").read_text()
    # Premarket section rendered with our 1 gap-flagged ticker
    assert "gap-flagged" in body


def test_within_execution_window_helper():
    """Window is 10:30-15:00 IST (was 10:00 before yfinance premarket
    scan moved to 10:00 — run_live now starts at 10:30 with the same
    30-min late tolerance)."""
    # Just inside the window
    assert run_live._within_execution_window(
        datetime(2026, 5, 13, 10, 35)
    ) is True
    # Before window (was true under old 10:00 start)
    assert run_live._within_execution_window(
        datetime(2026, 5, 13, 10, 5)
    ) is False
    # Past late tolerance (10:30 + 30 = 11:00)
    assert run_live._within_execution_window(
        datetime(2026, 5, 13, 11, 5)
    ) is False
    # Past official close-of-window
    assert run_live._within_execution_window(
        datetime(2026, 5, 13, 15, 30)
    ) is False
