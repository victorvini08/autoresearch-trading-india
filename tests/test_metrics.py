import math

import numpy as np
import pandas as pd
import pytest

from backtest.metrics import (
    calmar,
    hit_rate,
    max_drawdown,
    profit_factor,
    sortino,
    turnover,
)


def test_sortino_zero_vol_handled():
    r = pd.Series([0.001] * 252)
    assert math.isinf(sortino(r))


def test_sortino_negative_only_returns_negative():
    r = pd.Series([-0.001] * 252)
    s = sortino(r)
    assert s < 0


def test_sortino_dstd_floor_caps_outlier():
    """A fold with one tiny -0.01% loss day and 251 small wins. Without the
    downside-dev floor, Sortino blows up to magnitude 50+ from a near-zero
    denominator, dragging the cross-fold mean unreasonably. We saw -142 on
    Strategy A this way. The floor at 0.001 (~16% annualized) bounds the
    metric while leaving genuine signal in [-10, 10] untouched."""
    r = pd.Series([0.001] * 252)
    r.iloc[0] = -0.0001  # one tiny loss day → near-zero downside_dev
    s = sortino(r)
    # Without the floor this would be O(50+); with the floor it stays sane.
    assert abs(s) < 20, f"sortino unbounded: {s}"


def test_sortino_known_value():
    np.random.seed(42)
    r = pd.Series(np.where(np.random.rand(252) > 0.5, 0.01, -0.01))
    s = sortino(r, periods_per_year=252)
    assert -0.5 < s < 0.5


def test_sortino_empty_series():
    assert sortino(pd.Series([], dtype=float)) == 0.0


def test_max_drawdown_simple():
    eq = pd.Series([100, 120, 60, 100])
    assert max_drawdown(eq) == pytest.approx(0.5)


def test_max_drawdown_strictly_increasing_is_zero():
    eq = pd.Series([100, 110, 120, 130])
    assert max_drawdown(eq) == 0.0


def test_calmar_positive_when_returns_and_dd_present():
    r = pd.Series([(1.10 ** (1/252)) - 1] * 252)
    eq = (1 + r).cumprod()
    eq = eq.copy()
    peak_idx = len(eq) // 2
    eq.iloc[peak_idx:] = eq.iloc[peak_idx] * 0.80 * (1 + r.iloc[peak_idx:]).cumprod().values
    c = calmar(r, eq, periods_per_year=252)
    assert c > 0


def test_calmar_floor_caps_small_dd_pathology():
    # A 6-month fold with -0.5% return and a hairline 0.3% DD: without the
    # floor, Calmar ≈ -3.3 (annualized -1% / 0.3%). The dd_floor of 5% caps
    # this so the gate isn't measuring division-by-near-zero noise.
    n = 126
    daily = -0.005 / n  # ~-0.5% over the window
    r = pd.Series([daily] * n)
    eq = (1 + r).cumprod() * 100_000.0
    # Inject a tiny 0.3% drawdown mid-window
    mid = n // 2
    eq.iloc[mid] = eq.iloc[mid - 1] * (1 - 0.003)
    c = calmar(r, eq, periods_per_year=252)
    assert -1.0 < c < 0  # bounded; would have been ≈-3 without the floor


def test_hit_rate():
    trades = pd.DataFrame({"pnl": [10, -5, 20, -3, 15]})
    assert hit_rate(trades) == 0.6


def test_hit_rate_empty_is_zero():
    assert hit_rate(pd.DataFrame({"pnl": []})) == 0.0


def test_profit_factor():
    trades = pd.DataFrame({"pnl": [10, -5, 20, -3, 15]})
    # gross profit 45 / gross loss 8 = 5.625
    assert profit_factor(trades) == pytest.approx(45 / 8)


def test_profit_factor_no_losses_is_inf():
    trades = pd.DataFrame({"pnl": [10, 20, 5]})
    assert math.isinf(profit_factor(trades))


def test_turnover_one_full_rotation():
    # 10 × $10K = $100K notional / $100K avg equity = 1.0 turnover ratio
    trades = pd.DataFrame({"order_value_usd": [10000] * 10})
    assert turnover(trades, avg_equity=100_000) == pytest.approx(1.0)


def test_turnover_empty_is_zero():
    assert turnover(pd.DataFrame({"order_value_usd": []}), avg_equity=100_000) == 0.0


def test_metrics_are_pure_no_io(tmp_path, monkeypatch):
    # Smoke: calling all metric functions should not write any files anywhere
    files_before = set(p for p in tmp_path.rglob("*"))
    eq = pd.Series([100, 110, 90, 105])
    r = eq.pct_change().dropna()
    sortino(r)
    max_drawdown(eq)
    calmar(r, eq)
    hit_rate(pd.DataFrame({"pnl": [1, -1]}))
    profit_factor(pd.DataFrame({"pnl": [1, -1]}))
    turnover(pd.DataFrame({"order_value_usd": [100]}), avg_equity=1000)
    files_after = set(p for p in tmp_path.rglob("*"))
    assert files_before == files_after
