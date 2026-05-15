"""Audit-2026-05-15 Fix 1 regression: indicator warm-up + scoring-slice.

Proves (a) given >274 trading days of history the momentum strategy actually
trades (the inert-backtest bug is conceptually resolved), and (b) `score_start`
excludes all warm-up bars/trades from every returned metric/series.
"""
from datetime import date

import numpy as np
import pandas as pd

from prepare import _as_date, _score_window
from strategy import IndiaMomentumQualityRegime


def _feeds(n_days: int = 520, n_tickers: int = 30) -> dict[str, pd.DataFrame]:
    """Synthetic OHLCV with CYCLIC leadership: each ticker's drift rotates
    in/out of strength on a phase offset, so the 12-1 momentum ranking
    reshuffles across rebalances → the strategy both holds (gross>0) and
    rotates (closed round-trips), exercising entries AND exits."""
    idx = pd.bdate_range("2021-01-01", periods=n_days)
    t = np.arange(n_days)
    period = 130.0
    feeds = {}
    for k in range(n_tickers):
        # Drift oscillates around a small positive mean; phase per ticker.
        drift = 0.0010 + 0.0016 * np.sin(2 * np.pi * (t / period + k / n_tickers))
        close = 100.0 * np.exp(np.cumsum(drift))
        df = pd.DataFrame(
            {
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 1_000_000,
            },
            index=idx,
        )
        feeds[f"T{k:02d}"] = df
    return feeds


def test_as_date_normalizes():
    assert _as_date(date(2022, 5, 1)) == date(2022, 5, 1)
    assert _as_date(pd.Timestamp("2022-05-01")) == date(2022, 5, 1)
    assert _as_date("2022-05-01") == date(2022, 5, 1)


def test_strategy_trades_when_warmed():
    """With >274 trading days fed, momentum computes and the strategy takes
    positions. The true 'not inert' signal is non-zero gross exposure (the
    pre-Fix-1 bug left the book in cash forever); rotation additionally
    yields closed round-trips. This is the core proof Fix 1 works."""
    out = _score_window(IndiaMomentumQualityRegime, _feeds())
    g = out["gross_exposure_daily"]
    assert len(g) > 0 and float(g.max()) > 0.0, (
        "strategy never took a position with full history — still inert"
    )
    assert out["trade_count"] > 0, "rotating data should close round-trips"


def test_score_start_excludes_warmup():
    feeds = _feeds()
    cut = date(2022, 4, 1)  # well after the ~274-bar warm-up requirement

    full = _score_window(IndiaMomentumQualityRegime, feeds)
    sliced = _score_window(IndiaMomentumQualityRegime, feeds, score_start=cut)

    # Equity curve and daily returns start at/after the cut.
    eq = sliced["equity_curve"]
    assert len(eq) > 0
    assert min(_as_date(i) for i in eq.index) >= cut

    # No trade attributed before the cut; count matches the filtered frame.
    tr = sliced["trades"]
    if len(tr) > 0:
        assert all(_as_date(v) >= cut for v in tr["exit_date"])
    assert sliced["trade_count"] == len(tr)

    # Gross-exposure series also sliced.
    g = sliced["gross_exposure_daily"]
    if len(g) > 0:
        assert min(_as_date(i) for i in g.index) >= cut

    # The slice genuinely changed the scored window (warm-up excluded):
    # fewer scored days and (almost surely) fewer closed trades than full.
    assert len(sliced["equity_curve"]) < len(full["equity_curve"])
    assert sliced["trade_count"] <= full["trade_count"]


def test_score_start_none_is_legacy_behaviour():
    """score_start=None must reproduce the pre-Fix-1 path exactly (whole fed
    window scored) so signal_today / existing callers are unaffected."""
    feeds = _feeds()
    a = _score_window(IndiaMomentumQualityRegime, feeds)
    b = _score_window(IndiaMomentumQualityRegime, feeds, score_start=None)
    assert a["trade_count"] == b["trade_count"]
    assert len(a["equity_curve"]) == len(b["equity_curve"])
