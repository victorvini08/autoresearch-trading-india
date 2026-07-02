"""Scoring metrics. Sortino is the primary optimization target for the
autoresearch loop; everything else is reported on the side panel for journal
reasoning, never optimized against directly.

All functions are pure: take pandas inputs, return scalars, no I/O.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


# Floor for the downside-deviation denominator. Without it, a fold with very
# few losing days (e.g. a sideways window where one tiny -0.01% day is the
# only loser) produces a near-zero downside_dev and a Sortino of magnitude
# 50+ that dominates the cross-fold mean. We saw a single fold drag the
# 25-fold mean to -142 on Strategy A this way. The floor of 0.001 ≈ 16%
# annualized vol — roughly a broad large-cap-index level — sanity-bounds the
# metric without touching legitimate strategies, whose dstd sits well above.
SORTINO_DSTD_FLOOR = 0.001


def sortino(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized Sortino ratio. Uses downside std (negative-return std only).

    Edge cases:
      - empty series → 0.0
      - all returns >= 0 (no downside): +inf if mean > 0, else 0.0
      - dstd below SORTINO_DSTD_FLOOR: clamped to floor (prevents the
        -142 / +90 numerical artifacts seen when one tiny loss day produces
        a near-zero denominator)
    """
    if len(returns) == 0:
        return 0.0
    mean = float(returns.mean())
    downside = returns[returns < 0]
    if len(downside) == 0:
        return math.inf if mean > 0 else 0.0
    dstd_raw = float(downside.std(ddof=1))
    if np.isnan(dstd_raw):
        dstd_raw = 0.0
    dstd = max(dstd_raw, SORTINO_DSTD_FLOOR)
    return (mean / dstd) * math.sqrt(periods_per_year)


def max_drawdown(equity_curve: pd.Series) -> float:
    """Max peak-to-trough drawdown as a positive fraction (0.20 = 20%)."""
    if len(equity_curve) == 0:
        return 0.0
    rolling_peak = equity_curve.cummax()
    dd = (rolling_peak - equity_curve) / rolling_peak
    return float(dd.max())


def calmar(
    returns: pd.Series,
    equity_curve: pd.Series,
    periods_per_year: int = 252,
    dd_floor: float = 0.05,
) -> float:
    """Annualized return / max drawdown.

    `dd_floor` clamps the denominator from below. Without it, the metric is
    pathologically unstable when max_dd → 0: a slightly-losing 6-month fold
    with 0.3% drawdown becomes Calmar ≈ -3.3 — that's noise amplification, not
    risk measurement. 5% is roughly 1x monthly broad large-cap vol; below it, the
    strategy hasn't engaged enough risk to be measured. The 20% absolute-DD
    gate handles real drawdown blow-ups separately, so the floor doesn't mask
    danger — it just prevents division-by-near-zero from dominating the gate.
    """
    if len(returns) == 0:
        return 0.0
    cagr = (1 + returns).prod() ** (periods_per_year / len(returns)) - 1
    dd = max(max_drawdown(equity_curve), dd_floor)
    return float(cagr / dd)


def hit_rate(trades: pd.DataFrame) -> float:
    """Fraction of trades with positive P&L. Requires a 'pnl' column."""
    if len(trades) == 0:
        return 0.0
    return float((trades["pnl"] > 0).mean())


def profit_factor(trades: pd.DataFrame) -> float:
    """Gross profit / gross loss (absolute). Requires 'pnl' column."""
    if len(trades) == 0:
        return 0.0
    gp = float(trades.loc[trades["pnl"] > 0, "pnl"].sum())
    gl = float(-trades.loc[trades["pnl"] < 0, "pnl"].sum())
    if gl == 0:
        return math.inf if gp > 0 else 0.0
    return gp / gl


def turnover(trades: pd.DataFrame, avg_equity: float) -> float:
    """Turnover ratio: total notional traded / average equity. Not annualized.

    A value of 1.0 means the strategy rotated through its full equity once over
    the period. Requires 'order_value_usd' on each trade row.
    """
    if len(trades) == 0 or avg_equity == 0:
        return 0.0
    return float(trades["order_value_usd"].sum() / avg_equity)
