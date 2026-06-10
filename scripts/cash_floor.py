"""Cash-floor policy: park idle (non-deployed) capital in a liquid ETF.

Locked as production policy 2026-06-05 (multi-engine campaign: the ONLY
robust idle-cash improvement, +~3pp/yr at unchanged drawdown) and wired into
the executor 2026-06-10 alongside the low-vol-filter promotion.

DESIGN NOTES
- This is a deterministic EXECUTOR-level allocation, not strategy code: the
  signal layer (strategy.py) never sees the floor instrument. The executor
  strips it from the position seed passed to signal_today (else the strategy
  would treat it as an off-universe holding and liquidate it) and folds its
  market value into the seeded cash so gross sizing is computed on true
  deployable equity.
- Instrument: LIQUIDCASE (growth-NAV overnight/liquid ETF) by default, NOT
  LIQUIDBEES — LIQUIDBEES pins its price at ~₹1,000 and pays its return as
  daily dividend UNITS, which (a) shows ~0% in any price series, breaking
  paper/backtest accounting, and (b) needs fractional-unit bookkeeping.
  LIQUIDCASE compounds in price, so paper, live, reconciliation and the
  dashboard all see the return with zero special-casing. Override with
  $CASH_FLOOR_TICKER if you prefer another growth-NAV liquid ETF.
- Why a liquid ETF and not NIFTYBEES: idle cash PEAKS in crashes (the
  vol-target cuts equity gross exactly then), so an index instrument here
  would add beta at the worst moments — the anti-defensive idle-cash overlay
  rejected in the 2026-06-04 multi-engine campaign. The floor must be
  capital-stable.
- BAND: floor adjustments fire only when the floor's current fraction drifts
  more than CASH_FLOOR_BAND from target (or when a sell is needed to fund
  equity buys). A liquid ETF sell costs the flat ₹14.75 DP charge; biweekly
  rebalancing of the floor would cost ~0.7%/yr at ₹50k. The band keeps it
  to a few adjustments per year.
- BUFFER: a small true-cash remainder for DP charges, STT and slippage so
  equity buys never fail on a few missing rupees.
"""
from __future__ import annotations

import os

CASH_FLOOR_TICKER = os.environ.get("CASH_FLOOR_TICKER", "LIQUIDCASE").upper()
CASH_FLOOR_ENABLED = os.environ.get("CASH_FLOOR_ENABLED", "1") == "1"
CASH_FLOOR_BUFFER = 0.02   # true cash kept aside for charges/slippage
CASH_FLOOR_BAND = 0.05     # min |drift| of floor fraction before adjusting


def floor_target_fraction(equity_target_sum: float) -> float:
    """Idle-cash fraction to park: whatever equity doesn't claim, minus
    the buffer. Never negative; equity targets always take precedence."""
    return max(0.0, 1.0 - max(0.0, float(equity_target_sum)) - CASH_FLOOR_BUFFER)


def banded_floor_target(
    equity_target_sum: float,
    current_floor_fraction: float,
) -> float:
    """The floor fraction to actually ORDER toward.

    Returns the fresh target when it differs from the current floor holding
    by more than CASH_FLOOR_BAND **or** when the floor must shrink to make
    room for equity (equity + current floor + buffer > 1 means the equity
    buys literally need the cash — always honor that). Otherwise returns the
    CURRENT fraction so the order builder sees ~zero delta and no churn."""
    fresh = floor_target_fraction(equity_target_sum)
    cur = max(0.0, float(current_floor_fraction))
    needs_room = (
        float(equity_target_sum) + cur + CASH_FLOOR_BUFFER > 1.0 + 1e-9
    )
    if needs_room or abs(fresh - cur) > CASH_FLOOR_BAND:
        return fresh
    return cur
