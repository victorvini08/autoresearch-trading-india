"""Shadow book — Step 5.e.

The bridge between "passes the backtests" and "works in reality". A qualified
CHALLENGER from the validator is NOT swapped into the live book. It is activated
SHADOW_ACTIVE and scored forward on genuinely-new data — the days that have
accrued since activation, which nobody has used for any selection decision —
head-to-head against the incumbent. After >=MIN_SHADOW_CYCLES rebalance cycles,
if the challenger did at least as well risk-adjusted AND did not draw down
materially deeper, it becomes eligible for a MANUAL promotion (5.f).

This is the renewable out-of-sample gate that stands in for the spent sealed
test: every week generates fresh, uncontaminated evidence, and the comparison
is a clean two-strategy A/B (incumbent vs ONE challenger), not a fish among
many candidates.

Reduced-form by design (per the Codex review that made shadow gating
non-optional): the forward score is a backtest over the accrued window, not yet
a tick-by-tick parallel paper book. Promotion stays human-in-the-loop.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import scripts.review_schedule as sched
from storage import realworld_db

# Minimum rebalance cycles a challenger must run in shadow before it can be
# promoted (spec §10 / Codex: >=4 cycles or 8-12 weeks).
MIN_SHADOW_CYCLES = 4
# How much deeper the challenger's forward drawdown may be vs the incumbent's
# before it is disqualified, even at equal risk-adjusted return.
SHADOW_DD_TOLERANCE = 0.02


@dataclass(frozen=True)
class ShadowComparison:
    version_hash: str
    cycles_elapsed: int
    eligible: bool
    challenger: dict
    incumbent: dict
    window_start: str
    window_end: str
    summary: str


def count_rebalance_cycles(start: date, end: date) -> int:
    """Number of rebalance-SIGNAL Fridays in (start, end] — i.e. how many live
    rebalances the challenger has been observed through since activation. Start
    is exclusive (activation day itself isn't a completed cycle)."""
    n = 0
    d = start + timedelta(days=1)
    while d <= end:
        if sched.is_rebalance_signal_date(d):
            n += 1
        d += timedelta(days=1)
    return n


def activate_shadow(conn, version_hash: str, *, now: datetime) -> bool:
    """Begin a shadow trial: CHALLENGER → SHADOW_ACTIVE. Returns False if the
    version is missing or not a fresh CHALLENGER (already activated / promoted /
    retired), so it is safe to call idempotently."""
    v = realworld_db.get_strategy_version(conn, version_hash)
    if v is None or v["status"] != "CHALLENGER":
        return False
    realworld_db.update_strategy_version_status(
        conn, version_hash, "SHADOW_ACTIVE", updated_at=now)
    return True


def _is_eligible(cycles: int, challenger: dict, incumbent: dict, min_cycles: int) -> bool:
    if cycles < min_cycles:
        return False
    cs, is_ = challenger.get("test_sortino"), incumbent.get("test_sortino")
    if cs is None or is_ is None:
        return False
    if cs < is_:                                  # worse risk-adjusted return
        return False
    cdd, idd = challenger.get("test_max_dd"), incumbent.get("test_max_dd")
    if cdd is not None and idd is not None and cdd > idd + SHADOW_DD_TOLERANCE:
        return False                              # materially deeper drawdown
    return True


def evaluate_shadow(
    version_hash: str,
    *,
    today: date,
    mode: str = "dhan-paper",
    realworld_db_path: Path | str | None = None,
    strategy_path: Path | str | None = None,
    min_cycles: int = MIN_SHADOW_CYCLES,
    score_fn=None,
) -> ShadowComparison | None:
    """Score the challenger vs the incumbent over the forward window since the
    challenger's shadow began, and report promotion eligibility. Returns None if
    the version is unknown. `score_fn(strategy_text, start, end) -> {test_*}` is
    injected in tests; by default it is the validator's forward-window backtest."""
    if score_fn is None:
        from scripts.realworld_validator import run_fresh_sealed_reveal
        score_fn = run_fresh_sealed_reveal
    if strategy_path is None:
        from scripts.realworld_validator import STRATEGY_PATH
        strategy_path = STRATEGY_PATH

    db_path = (Path(realworld_db_path) if realworld_db_path is not None
               else realworld_db.DEFAULT_DB_PATH)
    conn = realworld_db.connect(db_path)
    try:
        v = realworld_db.get_strategy_version(conn, version_hash)
        if v is None:
            return None
        start = v["status_updated_at"] or v["created_at"]
        start_date = start.date() if isinstance(start, datetime) else start

        cycles = count_rebalance_cycles(start_date, today)
        challenger = score_fn(Path(v["snapshot_path"]).read_text(), start_date, today)
        incumbent = score_fn(Path(strategy_path).read_text(), start_date, today)
        eligible = _is_eligible(cycles, challenger, incumbent, min_cycles)

        summary = (
            f"{cycles} shadow cycle(s) since {start_date}: challenger Sortino "
            f"{challenger.get('test_sortino')} vs incumbent {incumbent.get('test_sortino')}, "
            f"maxDD {challenger.get('test_max_dd')} vs {incumbent.get('test_max_dd')} — "
            f"{'ELIGIBLE for manual promotion' if eligible else 'not yet eligible'}")
        return ShadowComparison(
            version_hash=version_hash,
            cycles_elapsed=cycles,
            eligible=eligible,
            challenger=challenger,
            incumbent=incumbent,
            window_start=start_date.isoformat(),
            window_end=today.isoformat(),
            summary=summary,
        )
    finally:
        conn.close()
