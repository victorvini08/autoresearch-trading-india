"""Safety state machine — deterministic equity-driven circuit breaker.

Four states. Hard-coded thresholds. No LLM. No human override except for the
final halt.

States and transitions (all peak-equity drawdowns; equity is mark-to-market
end-of-day from portfolio.duckdb):

    NORMAL ──peak DD ≥ 8%──►   WATCH
                 ◄──recover within 3% of peak for 20 sessions──
                 (observation only; risk_multiplier = 1.0)

    WATCH ──peak DD ≥ 12%──►   RISK_REDUCED
                 ◄──recover within 5% of peak for 20 sessions──
                 (writes risk_multiplier = 0.5; executor halves gross
                  at next rebalance)

    RISK_REDUCED ──peak DD ≥ 16%──►   HALTED_REVIEW
                 ◄──manual user reset only
                 (writes halt.json halted=true; run_live exits before
                  placing any orders)

Threshold calibration is OUR strategy, not Wright Research's published
10%. Aggregate walk-forward max DD was 12.2%; worst single fold was 7.2%.
  - 8%  = "one step beyond worst observed fold"            → observe
  - 12% = "at aggregate backtest max DD"                   → de-risk
  - 16% = "~1.3× aggregate max DD, clearly out-of-regime"  → halt

This module is PURE: no DB access, no file I/O. The daily evaluator
(scripts/safety_evaluator.py, run inside daily_report) provides the
equity history and prior state, persists the result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

# Drawdown escalation thresholds (peak-to-trough fraction).
DD_WATCH = 0.08
DD_RISK_REDUCED = 0.12
DD_HALTED_REVIEW = 0.16

# Recovery: how close to peak (fraction) and for how many sessions.
WATCH_TO_NORMAL_BAND = 0.03
WATCH_TO_NORMAL_SESSIONS = 20

RISK_REDUCED_TO_WATCH_BAND = 0.05
RISK_REDUCED_TO_WATCH_SESSIONS = 20

# Risk multiplier per state — executor multiplies target_fraction by this
# before submitting orders.
_RISK_MULTIPLIER = {
    "NORMAL": 1.0,
    "WATCH": 1.0,
    "RISK_REDUCED": 0.5,
    "HALTED_REVIEW": 0.0,
}

StateName = Literal["NORMAL", "WATCH", "RISK_REDUCED", "HALTED_REVIEW"]


@dataclass(frozen=True)
class SafetyState:
    """The evaluator's output. Immutable.

    Persisted as JSON in state/safety_state.json — every field round-trips.
    """
    state: StateName
    as_of: date
    today_equity: float
    peak_equity: float
    dd_pct: float                # 0.0 – 1.0
    risk_multiplier: float       # 1.0 / 1.0 / 0.5 / 0.0
    halted: bool                 # True iff state == HALTED_REVIEW
    transitioned_today: bool     # state != prior_state's state
    entered_state_at: date       # when the CURRENT state was first entered
    reason: str                  # one-line human-readable explanation
    days_in_state: int = field(default=0)


def evaluate_state(
    equity_history: list[tuple[date, float]],
    prior_state: SafetyState | None,
) -> SafetyState:
    """Pure transition function.

    Args:
        equity_history: (date, equity) tuples, ordered ascending by date.
                        The LAST entry is today. Must be non-empty.
        prior_state:    The SafetyState from yesterday's evaluation, or None
                        on the first ever run (bootstraps NORMAL).

    Returns:
        Today's SafetyState.

    State escalation rules (checked top-to-bottom; first match wins):
      1. HALTED_REVIEW is absorbing — once entered, only manual reset escapes.
      2. dd ≥ 16%       → HALTED_REVIEW
      3. dd ≥ 12%       → RISK_REDUCED (regardless of prior state)
      4. prior == RISK_REDUCED:
            recovery met → step down to WATCH
            else         → stay RISK_REDUCED  (no auto-recovery on dd alone)
      5. dd ≥ 8%        → WATCH
      6. prior == WATCH:
            recovery met → step down to NORMAL
            else         → stay WATCH         (no auto-recovery on dd alone)
      7. else            → NORMAL

    Two-level recovery (WATCH→NORMAL, RISK_REDUCED→WATCH) is by design:
    a fast crash that pierces through WATCH and lands in RISK_REDUCED must
    walk back through WATCH on the way out, not jump straight to NORMAL.
    """
    if not equity_history:
        raise ValueError("evaluate_state requires non-empty equity_history")

    today_date, today_equity = equity_history[-1]
    peak = max(e for _, e in equity_history)
    dd_pct = 0.0 if peak <= 0 else max(0.0, (peak - today_equity) / peak)

    prior_name: StateName = (
        prior_state.state if prior_state is not None else "NORMAL"
    )

    # --- transition logic ---
    if prior_name == "HALTED_REVIEW":
        new_state: StateName = "HALTED_REVIEW"
        reason = "HALTED_REVIEW is absorbing; user must manually reset."
    elif dd_pct >= DD_HALTED_REVIEW:
        new_state = "HALTED_REVIEW"
        reason = (
            f"DD {dd_pct*100:.2f}% ≥ {DD_HALTED_REVIEW*100:.0f}%; halting."
        )
    elif dd_pct >= DD_RISK_REDUCED:
        new_state = "RISK_REDUCED"
        reason = (
            f"DD {dd_pct*100:.2f}% ≥ {DD_RISK_REDUCED*100:.0f}%; "
            "halving gross."
        )
    elif prior_name == "RISK_REDUCED":
        if _within_recovery_band(
            equity_history,
            band=RISK_REDUCED_TO_WATCH_BAND,
            sessions=RISK_REDUCED_TO_WATCH_SESSIONS,
        ):
            new_state = "WATCH"
            reason = (
                f"Recovered: ≤{RISK_REDUCED_TO_WATCH_BAND*100:.0f}% of peak "
                f"for {RISK_REDUCED_TO_WATCH_SESSIONS} sessions; stepping "
                "down to WATCH."
            )
        else:
            new_state = "RISK_REDUCED"
            reason = (
                f"DD {dd_pct*100:.2f}%; staying in RISK_REDUCED until "
                f"≤{RISK_REDUCED_TO_WATCH_BAND*100:.0f}% recovery for "
                f"{RISK_REDUCED_TO_WATCH_SESSIONS} sessions."
            )
    elif dd_pct >= DD_WATCH:
        new_state = "WATCH"
        reason = (
            f"DD {dd_pct*100:.2f}% ≥ {DD_WATCH*100:.0f}%; observation."
        )
    elif prior_name == "WATCH":
        if _within_recovery_band(
            equity_history,
            band=WATCH_TO_NORMAL_BAND,
            sessions=WATCH_TO_NORMAL_SESSIONS,
        ):
            new_state = "NORMAL"
            reason = (
                f"Recovered: ≤{WATCH_TO_NORMAL_BAND*100:.0f}% of peak for "
                f"{WATCH_TO_NORMAL_SESSIONS} sessions; back to NORMAL."
            )
        else:
            new_state = "WATCH"
            reason = (
                f"DD {dd_pct*100:.2f}%; staying in WATCH until "
                f"≤{WATCH_TO_NORMAL_BAND*100:.0f}% recovery for "
                f"{WATCH_TO_NORMAL_SESSIONS} sessions."
            )
    else:
        new_state = "NORMAL"
        reason = f"DD {dd_pct*100:.2f}% within NORMAL band."

    transitioned = (new_state != prior_name)
    if transitioned or prior_state is None:
        entered_at = today_date
        days_in_state = 0
    else:
        entered_at = prior_state.entered_state_at
        days_in_state = prior_state.days_in_state + 1

    return SafetyState(
        state=new_state,
        as_of=today_date,
        today_equity=float(today_equity),
        peak_equity=float(peak),
        dd_pct=float(dd_pct),
        risk_multiplier=_RISK_MULTIPLIER[new_state],
        halted=(new_state == "HALTED_REVIEW"),
        transitioned_today=transitioned,
        entered_state_at=entered_at,
        days_in_state=days_in_state,
        reason=reason,
    )


def _within_recovery_band(
    equity_history: list[tuple[date, float]],
    *,
    band: float,
    sessions: int,
) -> bool:
    """For the LAST `sessions` consecutive entries, equity stayed within
    `band` (fraction) of the running peak through those sessions.

    Running peak is computed continuously from history start, so a new ATH
    during the recovery window counts as legitimate recovery (peak ratchets
    up, DD measured from the new high).
    """
    if len(equity_history) < sessions:
        return False
    cutoff_idx = len(equity_history) - sessions
    running_peak = 0.0
    for i, (_, e) in enumerate(equity_history):
        if e > running_peak:
            running_peak = e
        if i >= cutoff_idx and running_peak > 0:
            dd = (running_peak - e) / running_peak
            if dd > band:
                return False
    return True


def manual_reset_from_halted(
    prior_state: SafetyState, today_date: date,
) -> SafetyState:
    """User-initiated escape from HALTED_REVIEW.

    Drops to RISK_REDUCED (NOT NORMAL) per the design — re-entry to NORMAL
    must walk through the recovery rules. Caller is responsible for setting
    the today_equity/peak_equity correctly from the current ledger.
    """
    if prior_state.state != "HALTED_REVIEW":
        raise ValueError(
            "manual_reset_from_halted called on non-HALTED_REVIEW state: "
            f"{prior_state.state}"
        )
    return SafetyState(
        state="RISK_REDUCED",
        as_of=today_date,
        today_equity=prior_state.today_equity,
        peak_equity=prior_state.peak_equity,
        dd_pct=prior_state.dd_pct,
        risk_multiplier=_RISK_MULTIPLIER["RISK_REDUCED"],
        halted=False,
        transitioned_today=True,
        entered_state_at=today_date,
        days_in_state=0,
        reason="Manual user reset from HALTED_REVIEW → RISK_REDUCED.",
    )
