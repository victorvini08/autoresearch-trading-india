"""Step 2.a — pure safety state machine.

Twelve scenarios covering every transition + every absorbing edge.
All tests are pure (no DB, no files).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from data.safety_state import (
    DD_HALTED_REVIEW,
    DD_RISK_REDUCED,
    DD_WATCH,
    RISK_REDUCED_TO_WATCH_SESSIONS,
    SafetyState,
    WATCH_TO_NORMAL_SESSIONS,
    evaluate_state,
    manual_reset_from_halted,
)

D0 = date(2026, 1, 1)


def _curve(equities: list[float], start: date = D0) -> list[tuple[date, float]]:
    """Day 0, Day 1, … assigned to consecutive calendar dates."""
    return [(start + timedelta(days=i), float(e)) for i, e in enumerate(equities)]


# === Bootstrap ===

def test_first_run_no_prior_state_starts_NORMAL():
    out = evaluate_state(_curve([100_000.0]), prior_state=None)
    assert out.state == "NORMAL"
    assert out.peak_equity == 100_000.0
    assert out.dd_pct == 0.0
    assert out.risk_multiplier == 1.0
    assert out.halted is False
    assert out.days_in_state == 0


def test_first_run_with_deep_dd_escalates_directly_to_HALTED_REVIEW():
    """One-shot collapse trips HALTED_REVIEW even without prior state."""
    out = evaluate_state(
        _curve([100_000.0, 100_000.0, 82_000.0]),  # 18% DD
        prior_state=None,
    )
    assert out.state == "HALTED_REVIEW"
    assert out.halted is True
    assert out.risk_multiplier == 0.0


# === Escalation ===

def test_NORMAL_to_WATCH_at_8pct():
    out = evaluate_state(
        _curve([100_000.0, 100_000.0, 91_000.0]),  # 9% DD
        prior_state=None,
    )
    assert out.state == "WATCH"
    assert out.risk_multiplier == 1.0
    assert out.transitioned_today is True


def test_NORMAL_to_RISK_REDUCED_at_12pct():
    """Fast crash through WATCH lands in RISK_REDUCED in one tick."""
    out = evaluate_state(
        _curve([100_000.0, 100_000.0, 87_000.0]),  # 13% DD
        prior_state=None,
    )
    assert out.state == "RISK_REDUCED"
    assert out.risk_multiplier == 0.5
    assert out.halted is False


def test_NORMAL_to_HALTED_REVIEW_at_16pct():
    out = evaluate_state(
        _curve([100_000.0, 100_000.0, 83_000.0]),  # 17% DD
        prior_state=None,
    )
    assert out.state == "HALTED_REVIEW"
    assert out.halted is True


# === Absorbing HALTED_REVIEW ===

def test_HALTED_REVIEW_does_not_self_recover():
    """Equity bounces back to ATH; state stays HALTED_REVIEW (absorbing)."""
    prior = SafetyState(
        state="HALTED_REVIEW", as_of=D0, today_equity=83_000.0,
        peak_equity=100_000.0, dd_pct=0.17, risk_multiplier=0.0,
        halted=True, transitioned_today=True, entered_state_at=D0,
        days_in_state=5, reason="prior",
    )
    out = evaluate_state(_curve([83_000.0, 100_000.0]), prior_state=prior)
    assert out.state == "HALTED_REVIEW"
    assert out.halted is True


def test_manual_reset_from_halted_drops_to_RISK_REDUCED():
    prior = SafetyState(
        state="HALTED_REVIEW", as_of=D0, today_equity=83_000.0,
        peak_equity=100_000.0, dd_pct=0.17, risk_multiplier=0.0,
        halted=True, transitioned_today=False, entered_state_at=D0,
        days_in_state=3, reason="prior",
    )
    new = manual_reset_from_halted(prior, today_date=D0 + timedelta(days=10))
    assert new.state == "RISK_REDUCED"
    assert new.risk_multiplier == 0.5
    assert new.halted is False
    assert new.transitioned_today is True


def test_manual_reset_rejects_non_halted_state():
    prior = SafetyState(
        state="WATCH", as_of=D0, today_equity=92_000.0,
        peak_equity=100_000.0, dd_pct=0.08, risk_multiplier=1.0,
        halted=False, transitioned_today=False, entered_state_at=D0,
        days_in_state=5, reason="prior",
    )
    with pytest.raises(ValueError, match="HALTED_REVIEW"):
        manual_reset_from_halted(prior, today_date=D0 + timedelta(days=10))


# === No-auto-recovery on DD alone ===

def test_WATCH_stays_WATCH_when_dd_drops_but_recovery_window_not_met():
    """DD shrunk to 5% (below WATCH's 8% gate) but the 20-session
    window of staying within 3% of peak has NOT been achieved. State stays
    WATCH — escalation gates are not the same as recovery gates."""
    prior = SafetyState(
        state="WATCH", as_of=D0, today_equity=91_000.0,
        peak_equity=100_000.0, dd_pct=0.09, risk_multiplier=1.0,
        halted=False, transitioned_today=True, entered_state_at=D0,
        days_in_state=3, reason="prior",
    )
    # Recent: drop to 91k, then climb to 95k (still 5% below peak)
    history = _curve([100_000.0, 91_000.0, 95_000.0])
    out = evaluate_state(history, prior_state=prior)
    assert out.state == "WATCH"
    assert out.days_in_state == prior.days_in_state + 1


def test_RISK_REDUCED_stays_RISK_REDUCED_when_dd_drops_but_no_recovery_window():
    prior = SafetyState(
        state="RISK_REDUCED", as_of=D0, today_equity=87_000.0,
        peak_equity=100_000.0, dd_pct=0.13, risk_multiplier=0.5,
        halted=False, transitioned_today=True, entered_state_at=D0,
        days_in_state=1, reason="prior",
    )
    # Bounce to 6% off peak — within WATCH band but no 20-session window yet
    history = _curve([100_000.0, 87_000.0, 94_000.0])
    out = evaluate_state(history, prior_state=prior)
    assert out.state == "RISK_REDUCED"


# === Recovery (the 20-session bands) ===

def test_WATCH_to_NORMAL_after_full_recovery_window():
    """After WATCH_TO_NORMAL_SESSIONS days within 3% of peak → NORMAL."""
    prior = SafetyState(
        state="WATCH", as_of=D0, today_equity=92_000.0,
        peak_equity=100_000.0, dd_pct=0.08, risk_multiplier=1.0,
        halted=False, transitioned_today=True, entered_state_at=D0,
        days_in_state=5, reason="prior",
    )
    # Equity: brief dip to 92k (peak=100k), then 25 sessions all within 3%
    history = _curve(
        [100_000.0, 92_000.0]
        + [98_000.0] * WATCH_TO_NORMAL_SESSIONS
    )
    out = evaluate_state(history, prior_state=prior)
    assert out.state == "NORMAL"
    assert out.transitioned_today is True
    assert out.risk_multiplier == 1.0


def test_RISK_REDUCED_to_WATCH_after_full_recovery_window():
    prior = SafetyState(
        state="RISK_REDUCED", as_of=D0, today_equity=87_000.0,
        peak_equity=100_000.0, dd_pct=0.13, risk_multiplier=0.5,
        halted=False, transitioned_today=True, entered_state_at=D0,
        days_in_state=5, reason="prior",
    )
    # Recovery within 5% of peak for 20 sessions (all at 96k vs peak 100k = 4%)
    history = _curve(
        [100_000.0, 87_000.0]
        + [96_000.0] * RISK_REDUCED_TO_WATCH_SESSIONS
    )
    out = evaluate_state(history, prior_state=prior)
    assert out.state == "WATCH"
    assert out.transitioned_today is True
    assert out.risk_multiplier == 1.0


def test_RISK_REDUCED_to_WATCH_does_not_skip_to_NORMAL():
    """Even if recovery is deep enough for NORMAL band, RISK_REDUCED steps
    down to WATCH first — the staircase is asymmetric by design."""
    prior = SafetyState(
        state="RISK_REDUCED", as_of=D0, today_equity=87_000.0,
        peak_equity=100_000.0, dd_pct=0.13, risk_multiplier=0.5,
        halted=False, transitioned_today=True, entered_state_at=D0,
        days_in_state=5, reason="prior",
    )
    # 20 sessions all within 2% of peak (would qualify for NORMAL band)
    history = _curve(
        [100_000.0, 87_000.0]
        + [99_000.0] * RISK_REDUCED_TO_WATCH_SESSIONS
    )
    out = evaluate_state(history, prior_state=prior)
    assert out.state == "WATCH"  # NOT NORMAL


# === Re-escalation supersedes recovery ===

def test_RISK_REDUCED_escalates_to_HALTED_REVIEW_even_with_partial_recovery():
    """Mid-recovery, a deep new drop fires HALTED_REVIEW regardless."""
    prior = SafetyState(
        state="RISK_REDUCED", as_of=D0, today_equity=87_000.0,
        peak_equity=100_000.0, dd_pct=0.13, risk_multiplier=0.5,
        halted=False, transitioned_today=True, entered_state_at=D0,
        days_in_state=3, reason="prior",
    )
    # Recovery progress: 10 days within band, then crash to -17% DD today.
    history = _curve(
        [100_000.0]
        + [96_000.0] * 10
        + [83_000.0]
    )
    out = evaluate_state(history, prior_state=prior)
    assert out.state == "HALTED_REVIEW"
    assert out.halted is True


# === Days-in-state counter ===

def test_days_in_state_advances_when_no_transition():
    prior = SafetyState(
        state="WATCH", as_of=D0, today_equity=91_000.0,
        peak_equity=100_000.0, dd_pct=0.09, risk_multiplier=1.0,
        halted=False, transitioned_today=False, entered_state_at=D0,
        days_in_state=4, reason="prior",
    )
    history = _curve([100_000.0, 91_000.0, 91_500.0])  # still 8.5% DD
    out = evaluate_state(history, prior_state=prior)
    assert out.state == "WATCH"
    assert out.days_in_state == 5
    assert out.entered_state_at == D0  # unchanged


# === Threshold values ===

def test_thresholds_match_calibrated_values():
    assert DD_WATCH == 0.08
    assert DD_RISK_REDUCED == 0.12
    assert DD_HALTED_REVIEW == 0.16
