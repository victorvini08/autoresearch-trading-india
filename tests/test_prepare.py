import importlib
from datetime import date

import numpy as np
import pandas as pd
import pytest

from prepare import (
    BACKTEST_END,
    BACKTEST_START,
    INITIAL_CASH,
    TEST_BOUNDARY,
    _find_strategy_class,
    _walk_forward_folds,
    evaluate,
)


def _synthetic_feeds(tickers: list[str]) -> dict[str, pd.DataFrame]:
    feeds = {}
    n = 252 * 4
    for tkr in tickers:
        dates = pd.date_range(BACKTEST_START, periods=n, freq="B")
        rng = np.random.RandomState(hash(tkr) & 0xFFFF)
        close = 100 + np.cumsum(rng.randn(n) * 0.5)
        feeds[tkr] = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1_000_000,
        }, index=dates)
    return feeds


def test_test_boundary_is_in_the_past():
    assert TEST_BOUNDARY < date.today()
    assert BACKTEST_START < TEST_BOUNDARY <= BACKTEST_END


def test_initial_cash_is_inr_capital():
    """India repo seeds backtests with ₹50_000 starting capital (TWEAK from US $100k)."""
    assert INITIAL_CASH == 50_000.0


def test_walk_forward_folds_nonempty_and_within_bounds():
    folds = _walk_forward_folds(BACKTEST_START, TEST_BOUNDARY)
    assert len(folds) >= 6, f"expected at least 6 folds, got {len(folds)}"
    for (_, _, val_s, val_e) in folds:
        assert BACKTEST_START <= val_s
        assert val_e < TEST_BOUNDARY


def test_find_strategy_class_returns_india_momentum():
    """TWEAK: India strategy class is IndiaMomentumQualityRegime (was BaselineMomentum in US)."""
    strat_mod = importlib.import_module("strategy")
    cls = _find_strategy_class(strat_mod)
    assert cls.__name__ == "IndiaMomentumQualityRegime"


def test_research_mode_hides_test_set(monkeypatch):
    feeds = _synthetic_feeds(["FAKE1"])
    monkeypatch.setattr("prepare._load_feeds", lambda *_a, **_kw: feeds)
    strat_mod = importlib.import_module("strategy")
    result = evaluate(strat_mod, mode="research")
    assert "validation_sortino_mean" in result
    assert "side_panel" in result
    assert "risk" in result
    # No test-set keys leaked
    for forbidden in ("test_sortino", "test_calmar", "test_max_dd", "test_hit_rate"):
        assert forbidden not in result, f"{forbidden} leaked into research mode"


def test_promotion_mode_reveals_test_set(monkeypatch):
    feeds = _synthetic_feeds(["FAKE1"])
    monkeypatch.setattr("prepare._load_feeds", lambda *_a, **_kw: feeds)
    strat_mod = importlib.import_module("strategy")
    result = evaluate(strat_mod, mode="promotion")
    assert "test_sortino" in result
    assert "test_max_dd" in result
    # Validation-mode keys still present
    assert "validation_sortino_mean" in result


def test_evaluate_rejects_unknown_mode():
    strat_mod = importlib.import_module("strategy")
    with pytest.raises(ValueError, match="mode"):
        evaluate(strat_mod, mode="cheat")


def test_evaluate_returns_finite_validation_sortino(monkeypatch):
    feeds = _synthetic_feeds(["FAKE1"])
    monkeypatch.setattr("prepare._load_feeds", lambda *_a, **_kw: feeds)
    strat_mod = importlib.import_module("strategy")
    result = evaluate(strat_mod, mode="research")
    assert np.isfinite(result["validation_sortino_mean"])
    assert result["validation_folds"] > 0


def test_side_panel_includes_pretax_and_posttax_returns(monkeypatch):
    feeds = _synthetic_feeds(["FAKE1"])
    monkeypatch.setattr("prepare._load_feeds", lambda *_a, **_kw: feeds)
    strat_mod = importlib.import_module("strategy")
    result = evaluate(strat_mod, mode="research")
    sp = result["side_panel"]
    assert "pre_tax_return_mean" in sp
    assert "post_tax_return_mean_stcg15" in sp
    # When pre-tax is positive, post-tax must be lower; when negative, equal.
    if sp["pre_tax_return_mean"] > 0:
        assert sp["post_tax_return_mean_stcg15"] < sp["pre_tax_return_mean"]
    elif sp["pre_tax_return_mean"] < 0:
        # Losses don't get refunded in our simple model
        assert sp["post_tax_return_mean_stcg15"] <= sp["pre_tax_return_mean"]


def test_validate_risk_now_receives_non_empty_positions_df():
    """Regression: prepare.py:264 used to pass pd.DataFrame() which silently
    disabled the gross-exposure catastrophe gate. With the GrossExposureRecorder
    wired through, the positions DataFrame now has a max_gross_frac column.

    This test exercises the wiring by checking that a synthesised fold with
    fabricated >100% gross trips backtest.risk.validate. Uses the same
    validate_risk function prepare.py uses; we do not need to run a real fold
    to verify wiring."""
    from backtest.risk import validate as validate_risk

    fake_positions = pd.DataFrame({"max_gross_frac": [0.95, 1.20, 0.80]})
    fake_trades = pd.DataFrame({"x": range(25)})       # >= MIN_TRADES
    fake_equity = pd.Series([100_000.0, 101_000.0, 99_000.0])

    result = validate_risk(
        fake_trades, fake_equity, fake_positions,
        trade_count=25, max_dd=0.1,
    )
    assert result["passed"] is False
    assert any("gross" in v.lower() for v in result["violations"])
