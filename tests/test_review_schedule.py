"""Tests for scripts/review_schedule.py (Step 4.e).

The monthly review fires at day-end of the month's LAST rebalance-execution
day. "Rebalanced today" is ledger ground truth (desired_targets written with
source='strategy'), not recomputed parity — the strategy's own comments warn
that deriving the rebalance set from the calendar is holiday-fragile. "Last of
the month" compares the calendar of the NEXT rebalance signal against today.
"""
from __future__ import annotations

from datetime import date

import pytest

from storage import portfolio_db
import scripts.review_schedule as sched


# ---- pure calendar -------------------------------------------------------

def test_non_friday_is_never_a_signal_date():
    assert not sched.is_rebalance_signal_date(date(2026, 5, 28))  # Thursday


def test_consecutive_fridays_alternate_parity():
    # Biweekly => two consecutive Fridays are consecutive ISO weeks => exactly
    # one of them is a rebalance-signal Friday.
    f1 = date(2026, 5, 22)
    f2 = date(2026, 5, 29)
    assert f1.weekday() == 4 and f2.weekday() == 4
    assert sched.is_rebalance_signal_date(f1) != sched.is_rebalance_signal_date(f2)


def test_next_rebalance_is_a_future_signal_date():
    d = date(2026, 5, 4)
    nxt = sched.next_rebalance_signal_date(d)
    assert nxt > d
    assert sched.is_rebalance_signal_date(nxt)


def test_local_parity_matches_strategy():
    import strategy
    assert sched._REBALANCE_PARITY == strategy._REBALANCE_PARITY


# ---- pure "last of month" ------------------------------------------------

def test_not_last_when_not_rebalanced_today():
    assert not sched.is_last_rebalance_of_month(
        date(2026, 5, 29), date(2026, 6, 12), rebalanced_today=False)


def test_last_when_next_signal_is_a_later_month():
    assert sched.is_last_rebalance_of_month(
        date(2026, 5, 29), date(2026, 6, 12), rebalanced_today=True)


def test_not_last_when_next_signal_is_same_month():
    assert not sched.is_last_rebalance_of_month(
        date(2026, 5, 4), date(2026, 5, 18), rebalanced_today=True)


def test_last_when_no_further_signal():
    assert sched.is_last_rebalance_of_month(
        date(2026, 5, 29), None, rebalanced_today=True)


def test_trigger_day_consistent_with_next_signal():
    d = date(2026, 5, 29)
    nxt = sched.next_rebalance_signal_date(d)
    expected = (nxt.year, nxt.month) != (d.year, d.month)
    assert sched.is_review_trigger_day(d, rebalanced_today=True) == expected


def test_most_recent_signal_on_or_before():
    # On Mon Jun 1, the bhav we acted on is Fri May 29's — the most recent
    # signal date on or before today.
    assert sched.most_recent_signal_on_or_before(date(2026, 6, 1)) == date(2026, 5, 29)
    assert sched.most_recent_signal_on_or_before(date(2026, 5, 29)) == date(2026, 5, 29)


def test_trigger_fires_on_execution_day_after_month_last_signal():
    # May's last rebalance SIGNAL is Fri 2026-05-29; execution lands Mon Jun 1.
    # The review must still fire on Jun 1, attributed to May's cycle — keying
    # off the execution day alone would wrongly fold May into June.
    assert sched.is_review_trigger_day(date(2026, 6, 1), rebalanced_today=True)


def test_trigger_does_not_fire_on_midmonth_execution():
    # Jun 15 executes the Jun-12 signal; June still has a later rebalance
    # (Jun 26), so this is not June's last.
    assert not sched.is_review_trigger_day(date(2026, 6, 15), rebalanced_today=True)


# ---- ledger ground truth -------------------------------------------------

def test_rebalanced_on_detects_strategy_targets(tmp_path):
    conn = portfolio_db.connect(tmp_path / "p.duckdb")
    portfolio_db.upsert_target(
        conn, as_of_date=date(2026, 5, 29), ticker="RELIANCE",
        target_fraction=0.1, source="strategy", mode="dhan-paper")
    assert sched.rebalanced_on(conn, date(2026, 5, 29), "dhan-paper")
    assert not sched.rebalanced_on(conn, date(2026, 5, 28), "dhan-paper")
    conn.close()


def test_backfill_targets_do_not_count_as_rebalance(tmp_path):
    # 2026-05-26 era rows are source='backfill_from_fills' (the desired_targets
    # bug meant intent wasn't recorded). Those must not trigger a review.
    conn = portfolio_db.connect(tmp_path / "p.duckdb")
    portfolio_db.upsert_target(
        conn, as_of_date=date(2026, 5, 26), ticker="RELIANCE",
        target_fraction=0.1, source="backfill_from_fills", mode="dhan-paper")
    assert not sched.rebalanced_on(conn, date(2026, 5, 26), "dhan-paper")
    conn.close()


# ---- duplicate-run guard (per-day, not per-month) ------------------------

def _seed_monthly_audit(rw, review_id, run_at):
    from storage import realworld_db
    realworld_db.insert_audit(
        rw, review_id=review_id, run_at=run_at,
        mode="dhan-paper", trigger="monthly", input_snapshot_hash="h",
        prompt_version="v1", model_id="m", output_json="{}",
        validator_version="v1", validator_result="passed",
        validator_failures_json="[]", n_realized_trades=0,
        safety_state="NORMAL", cold_start=True)


def test_already_reviewed_on_same_day(tmp_path):
    from datetime import datetime
    from storage import realworld_db
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    assert not sched.already_reviewed_on(rw, "dhan-paper", date(2026, 6, 1))
    _seed_monthly_audit(rw, "rev-1", datetime(2026, 6, 1, 16, 0, 0))
    # same day -> blocked (daily_report fired twice)
    assert sched.already_reviewed_on(rw, "dhan-paper", date(2026, 6, 1))
    rw.close()


def test_two_reviews_in_one_calendar_month_both_allowed(tmp_path):
    # May's review executes Jun 1, June's executes Jun 29 — both land in the
    # June calendar. A per-DAY guard must let both run; a per-month guard would
    # wrongly block June.
    from datetime import datetime
    from storage import realworld_db
    rw = realworld_db.connect(tmp_path / "rw.duckdb")
    _seed_monthly_audit(rw, "rev-may", datetime(2026, 6, 1, 16, 0, 0))
    assert not sched.already_reviewed_on(rw, "dhan-paper", date(2026, 6, 29))
    rw.close()
