"""Sealed-data budget for the on-demand validator (Step 5.d).

A held-out test set is a CONSUMABLE, not a reusable: its statistical validity
comes precisely from being untouched by any selection decision. The
2025-01..2026-05 window was already spent selecting the locked strategy, so it
is permanently burned — re-revealing it would let the validator hill-climb a
fixed window (multiple comparisons) and would compare every challenger against
an incumbent that already had home-field advantage on it.

So this module's whole job is to answer ONE question conservatively: is there a
stretch of genuinely-NEW forward data — accrued strictly AFTER the last sealed
boundary — long enough to constitute a fresh, never-revealed test, and have we
not already spent our quarterly reveal? If yes, a single reveal on THAT forward
window is allowed. If not (the default, and the reality for many months), the
candidate is routed to the shadow book, which is the renewable out-of-sample
gate. The fresh window can never include the burned boundary by construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# The end of the burned sealed window (= prepare.BACKTEST_END). Mirrored as a
# literal so this module need not import the heavy prepare/backtrader stack;
# test_sealed_budget pins it against prepare.BACKTEST_END so it can't drift.
INITIAL_FROZEN_BOUNDARY = date(2026, 5, 14)

# A fresh forward window must be at least this many months long to mean
# anything as a sealed test (a validation fold is ~6 months; a shorter window
# is pure noise). Conservative on purpose.
MIN_FRESH_SEALED_MONTHS = 6


@dataclass(frozen=True)
class SealedBudgetDecision:
    available: bool
    status: str                 # "AVAILABLE" | "DEFERRED_TO_SHADOW"
    window_start: date | None   # start of the fresh, never-revealed window
    window_end: date | None
    reason: str


def _months_between(a: date, b: date) -> int:
    """Whole months from `a` to `b` (0 if b < a within the same month)."""
    months = (b.year - a.year) * 12 + (b.month - a.month)
    if b.day < a.day:
        months -= 1
    return months


def _quarter(d: date) -> tuple[int, int]:
    return (d.year, (d.month - 1) // 3)


def assess_sealed_budget(
    today: date,
    *,
    frozen_boundary: date = INITIAL_FROZEN_BOUNDARY,
    last_reveal_at: date | None = None,
    min_fresh_months: int = MIN_FRESH_SEALED_MONTHS,
) -> SealedBudgetDecision:
    """Pure: decide whether a fresh sealed reveal is permitted today.

    `frozen_boundary` is the end of the most-recently-revealed (burned) window;
    a fresh window can only start the day AFTER it. `last_reveal_at` is when the
    last fresh reveal happened (for the one-per-quarter budget). The default
    arguments encode the live situation: boundary at the burned 2026-05-14, no
    reveal yet."""
    fresh_start = frozen_boundary + timedelta(days=1)
    fresh_months = _months_between(fresh_start, today)

    if fresh_months < min_fresh_months:
        return SealedBudgetDecision(
            available=False,
            status="DEFERRED_TO_SHADOW",
            window_start=None,
            window_end=None,
            reason=(
                f"only {max(fresh_months, 0)} month(s) of genuinely-fresh "
                f"post-lock data since the last sealed boundary {frozen_boundary} "
                f"(need {min_fresh_months}); routing to the shadow book"
            ),
        )

    if last_reveal_at is not None and _quarter(last_reveal_at) == _quarter(today):
        return SealedBudgetDecision(
            available=False,
            status="DEFERRED_TO_SHADOW",
            window_start=None,
            window_end=None,
            reason=(
                f"a fresh sealed reveal was already spent this quarter "
                f"({last_reveal_at}); routing to the shadow book"
            ),
        )

    return SealedBudgetDecision(
        available=True,
        status="AVAILABLE",
        window_start=fresh_start,
        window_end=today,
        reason=(
            f"{fresh_months} months of never-revealed forward data "
            f"[{fresh_start}..{today}] available for one reveal"
        ),
    )
