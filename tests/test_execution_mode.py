"""Every cron entrypoint must resolve its book from EXECUTION_MODE.

`run_live` did; `daily_report` and `safety_evaluator` hardcoded `dhan-paper`.
Because the 15:35 cron runs daily_report — which in turn drives the safety
evaluator AND the monthly review — the live book's drawdown was invisible to
the safety circuit-breaker: it kept scoring a frozen paper book at dd=0.00%
and writing risk_multiplier=1.0, which `executors/dhan.py` then applied to
live targets. A real 20% live drawdown would not have de-risked anything.
"""
from datetime import date

import pytest

import scripts.daily_report as dr
import scripts.safety_evaluator as se
from autoresearch.storage import portfolio_db
from scripts.execution_mode import resolve_execution_mode

PAPER_CURVE = [(date(2026, 7, 9), 50_000.0), (date(2026, 7, 10), 50_000.0)]
LIVE_CURVE = [(date(2026, 7, 9), 50_000.0), (date(2026, 7, 10), 40_000.0)]


def test_resolve_defaults_to_paper_when_env_unset(monkeypatch):
    monkeypatch.delenv("EXECUTION_MODE", raising=False)
    assert resolve_execution_mode() == "dhan-paper"


def test_resolve_reads_execution_mode_env(monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "dhan-live")
    assert resolve_execution_mode() == "dhan-live"


def test_resolve_explicit_argument_beats_env(monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "dhan-live")
    assert resolve_execution_mode("dhan-paper") == "dhan-paper"


@pytest.fixture
def seeded_db(tmp_path):
    """A paper book sitting flat, and a live book 20% off its peak."""
    db = tmp_path / "portfolio.duckdb"
    with portfolio_db.connect(db) as conn:
        for mode, curve in (("dhan-paper", PAPER_CURVE), ("dhan-live", LIVE_CURVE)):
            for d, equity in curve:
                conn.execute(
                    "INSERT INTO broker_positions VALUES (?,?,?,?,?,?,?)",
                    [d, "ACME", 1.0, equity, equity, equity, mode],
                )
    return db


def test_safety_evaluator_scores_the_live_book_when_execution_mode_is_live(
    seeded_db, tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("EXECUTION_MODE", "dhan-live")
    monkeypatch.setattr(se, "STATE_DIR", tmp_path)

    assert se.main(["--dry-run", "--db-path", str(seeded_db)]) == 0

    out = capsys.readouterr().out
    assert "dd=20.00%" in out, f"safety scored the wrong book: {out!r}"


def test_explicit_mode_flag_still_overrides_the_env(seeded_db, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EXECUTION_MODE", "dhan-live")
    monkeypatch.setattr(se, "STATE_DIR", tmp_path)

    assert se.main(["--dry-run", "--db-path", str(seeded_db), "--mode", "dhan-paper"]) == 0

    assert "dd=0.00%" in capsys.readouterr().out


def test_safety_evaluator_defaults_to_paper_when_env_unset(seeded_db, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("EXECUTION_MODE", raising=False)
    monkeypatch.setattr(se, "STATE_DIR", tmp_path)

    assert se.main(["--dry-run", "--db-path", str(seeded_db)]) == 0

    assert "dd=0.00%" in capsys.readouterr().out


def test_daily_report_threads_live_mode_into_report_safety_and_review(
    seeded_db, monkeypatch
):
    """One resolution bug poisoned three consumers; assert all three get it."""
    monkeypatch.setenv("EXECUTION_MODE", "dhan-live")
    real_connect = portfolio_db.connect
    monkeypatch.setattr(dr.portfolio_db, "connect", lambda *a, **k: real_connect(seeded_db))

    seen = {}
    monkeypatch.setattr(dr, "generate", lambda summary: seen.setdefault("report", summary.mode))

    import scripts.realworld_review as rr
    monkeypatch.setattr(se, "evaluate_and_persist",
                        lambda *, mode, **k: seen.setdefault("safety", mode))
    monkeypatch.setattr(rr, "maybe_run_monthly_review",
                        lambda *, d, mode: seen.setdefault("review", mode))

    assert dr.main(["--date", "2026-07-10"]) == 0

    assert seen == {"report": "dhan-live", "safety": "dhan-live", "review": "dhan-live"}


def test_premarket_scan_resolves_execution_mode(monkeypatch, capsys):
    """premarket_scan's cron invocation passes no --mode; it must scan the
    EXECUTION_MODE book, not default to the frozen dhan-paper one (live bug
    2026-07-16: gap protection watched 5 paper names, missing 4 live names)."""
    import scripts.premarket_scan as pm

    seen = {}

    def _fake_scan(d, *, mode="dhan-paper"):
        seen["mode"] = mode
        return {"tickers": {}, "vix": {"flag": False}, "halt_recommendations": []}

    monkeypatch.setattr(pm, "scan", _fake_scan)
    monkeypatch.setenv("EXECUTION_MODE", "dhan-live")
    assert pm.main(["--date", "2026-07-16"]) == 0
    assert seen["mode"] == "dhan-live"

    monkeypatch.delenv("EXECUTION_MODE", raising=False)
    assert pm.main(["--date", "2026-07-16"]) == 0
    assert seen["mode"] == "dhan-paper"      # safe fallback unchanged

    assert pm.main(["--date", "2026-07-16", "--mode", "dhan-paper"]) == 0
    assert seen["mode"] == "dhan-paper"      # explicit flag still wins


def test_daily_update_corporate_actions_uses_execution_mode(monkeypatch):
    """daily_update's CA ingest hardcoded dhan-paper: splits/bonuses were only
    fetched for PAPER-held names, leaving live names (the book real money
    holds) exposed to the unadjusted-split phantom-loss bug (June repair)."""
    import scripts.ingest_corporate_actions as ica

    seen = {}
    monkeypatch.setattr(ica, "update_corporate_actions",
                        lambda *, mode, lookback_days: seen.setdefault("mode", mode) or 0)
    monkeypatch.setenv("EXECUTION_MODE", "dhan-live")

    from scripts.daily_update import _run_corporate_actions_step
    _run_corporate_actions_step()
    assert seen["mode"] == "dhan-live"
