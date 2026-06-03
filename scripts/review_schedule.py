"""When to fire the monthly LLM review (Step 4.e).

The review runs at day-end of the month's LAST rebalance-execution day, folded
into the existing 15:35 IST daily_report job (no new launchd job). Two facts
decide it:

  rebalanced_on()  — ledger ground truth: did run_live write desired_targets
                     with source='strategy' today? This is implementation- and
                     holiday-agnostic — far more robust than recomputing the
                     biweekly parity, which the strategy's own comments flag as
                     fragile when the rolling window crosses week boundaries.
  is_last_...()    — is the NEXT rebalance signal in a later month? If so,
                     today is this month's final rebalance.

already_reviewed_this_month() guards against a second run if daily_report fires
twice on the trigger day.
"""
from __future__ import annotations

from datetime import date, timedelta

import duckdb

# Mirror of strategy.py's rebalance calendar, kept local so the daily cron path
# need not import backtrader. test_review_schedule pins _REBALANCE_PARITY
# against strategy.py so it can't silently drift.
_REBALANCE_WEEKDAY = 4        # Friday (strategy rebalance_weekday default)
_REBALANCE_PERIOD_WEEKS = 2   # biweekly (strategy rebalance_period_weeks default)
_REBALANCE_PARITY = 0         # strategy._REBALANCE_PARITY


def is_rebalance_signal_date(d: date) -> bool:
    """A rebalance SIGNAL fires on Fridays of even-parity ISO weeks. (Execution
    lands the next trading day, when that Friday's NSE bhav is ingested.)"""
    return (d.weekday() == _REBALANCE_WEEKDAY
            and d.isocalendar().week % _REBALANCE_PERIOD_WEEKS == _REBALANCE_PARITY)


def next_rebalance_signal_date(d: date) -> date | None:
    """The next rebalance-signal Friday strictly after `d` (bounded scan)."""
    nd = d + timedelta(days=1)
    for _ in range(70):  # ~2.5 months is always enough at biweekly cadence
        if is_rebalance_signal_date(nd):
            return nd
        nd += timedelta(days=1)
    return None


def most_recent_signal_on_or_before(d: date) -> date | None:
    """The rebalance-signal Friday whose bhav we acted on for a rebalance
    executed on `d`. Friday's bhav is ingested the next trading day, so a
    Monday execution acts on the previous Friday's signal — we anchor the
    trigger to that SIGNAL date, not the execution date, so a month's last
    rebalance is attributed to its own month even when execution rolls into the
    next calendar month."""
    nd = d
    for _ in range(70):
        if is_rebalance_signal_date(nd):
            return nd
        nd -= timedelta(days=1)
    return None


def is_last_rebalance_of_month(
    d: date, next_signal_date: date | None, *, rebalanced_today: bool
) -> bool:
    """Pure: today is the month's last rebalance iff a rebalance executed today
    and the next rebalance signal falls in a later month (or none remains)."""
    if not rebalanced_today:
        return False
    if next_signal_date is None:
        return True
    return (next_signal_date.year, next_signal_date.month) != (d.year, d.month)


def is_review_trigger_day(d: date, *, rebalanced_today: bool) -> bool:
    """Fire iff a rebalance executed today AND the signal it acted on was the
    last rebalance signal of that signal's month. Anchoring to the signal date
    (not `d`) keeps the month attribution correct across the bhav-lag boundary
    (e.g. Fri May 29 signal -> Mon Jun 1 execution still counts as May's last)."""
    if not rebalanced_today:
        return False
    sig = most_recent_signal_on_or_before(d)
    if sig is None:
        return False
    return is_last_rebalance_of_month(
        sig, next_rebalance_signal_date(sig), rebalanced_today=True)


def rebalanced_on(conn: duckdb.DuckDBPyConnection, d: date, mode: str) -> bool:
    """Ground truth: did run_live persist real strategy intent today? Only
    source='strategy' counts — backfill rows (source='backfill_from_fills')
    are reconstructed history, not a live rebalance."""
    row = conn.execute(
        "SELECT COUNT(*) FROM desired_targets "
        "WHERE as_of_date = ? AND mode = ? AND source = 'strategy'",
        [d, mode],
    ).fetchone()
    return bool(row and row[0])


def already_reviewed_on(
    conn: duckdb.DuckDBPyConnection, mode: str, d: date
) -> bool:
    """True if a monthly review already ran on date `d` — so daily_report
    firing twice on the trigger day doesn't double-run. Keyed per-DAY, not
    per-month: across the bhav-lag boundary two months' reviews can both land
    in one calendar month (May's on Jun 1, June's on Jun 29), and both must
    be allowed."""
    row = conn.execute(
        "SELECT COUNT(*) FROM audit "
        "WHERE mode = ? AND trigger = 'monthly' AND CAST(run_at AS DATE) = ?",
        [mode, d],
    ).fetchone()
    return bool(row and row[0])
