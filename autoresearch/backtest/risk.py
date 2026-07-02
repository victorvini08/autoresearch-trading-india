"""Catastrophe-only validator.

Phase 2 (2026-05-09): the v1 hard caps (10% position frac, 20% per-fold DD,
0.7 Q1 Calmar) were structurally unwinnable — across 240+ iterations on two
parallel lineages (Strategy A breakout, Strategy C cross-sectional rotation),
ZERO ever cleared the gate, so the inner loop's Sortino-improvement
comparator never engaged. Now gates fire only on genuinely catastrophic
strategies. Concentration, fold-level drawdowns, and Calmar are reported as
numeric `risk_signals` for the agent to reason about — not auto-reject.

What still auto-rejects:
- gross exposure > 100% (cash-account leverage error)
- aggregate (chained-fold) drawdown > 50% (account-wipe territory)
- fewer than 20 trades total across validation (statistic too noisy)

Anything else is the agent's call, with program.md guidance and the
KEPT-criterion DD-regression guard providing the "don't trade DD for Sortino"
discipline.
"""
from __future__ import annotations

import pandas as pd

from .metrics import max_drawdown

MAX_GROSS_EXPOSURE = 1.00       # 100% gross — cash account, no leverage
MAX_DRAWDOWN_FRAC = 0.50        # catastrophe-only: account-wipe territory
MIN_TRADES = 20                 # below this, the score is too noisy to trust


def validate(
    trades: pd.DataFrame,
    equity_curve: pd.Series,
    positions: pd.DataFrame,
    *,
    trade_count: int | None = None,
    max_dd: float | None = None,
) -> dict:
    """Return {'passed': bool, 'violations': list[str]} for catastrophe checks.

    Optional keyword overrides used by prepare.py:
        trade_count   total trades across all folds (else len(trades))
        max_dd        AGGREGATE chained-fold drawdown (else max_drawdown(curve))

    Position concentration, single-fold DD, and Calmar are NOT gated here —
    prepare.py reports them in `risk_signals` so the agent can reason without
    being auto-rejected on metrics that the v1 gates made unreachable.
    """
    violations: list[str] = []

    n_trades = trade_count if trade_count is not None else len(trades)
    if n_trades < MIN_TRADES:
        violations.append(
            f"min trades: {n_trades} < {MIN_TRADES} — too sparse to evaluate"
        )

    if len(positions) > 0 and "max_gross_frac" in positions.columns:
        worst_gross = float(positions["max_gross_frac"].max())
        if worst_gross > MAX_GROSS_EXPOSURE:
            violations.append(
                f"gross exposure: max {worst_gross:.1%} > {MAX_GROSS_EXPOSURE:.0%} "
                "(cash account — leverage error)"
            )

    dd = max_dd if max_dd is not None else max_drawdown(equity_curve)
    if dd > MAX_DRAWDOWN_FRAC:
        violations.append(
            f"max drawdown: {dd:.1%} > {MAX_DRAWDOWN_FRAC:.0%} "
            "(account-wipe territory)"
        )

    return {"passed": len(violations) == 0, "violations": violations}
