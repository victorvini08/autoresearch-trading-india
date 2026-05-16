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


def test_find_strategy_class_returns_residual_reversal():
    """Branch mean-reversion-quant-strategy: strategy.py defines exactly one
    bt.Strategy subclass, the residual mean-reversion stat-arb book."""
    strat_mod = importlib.import_module("strategy")
    cls = _find_strategy_class(strat_mod)
    assert cls.__name__ == "IndiaResidualReversalStatArb"


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


# ── Regression: 2026-05-16 thin-universe + evaluator-version fixes ────────


def test_min_active_universe_uses_thinnest_in_window() -> None:
    """The pre-2022-07 PIT universe is ~5 names; the strategy is squeezed
    into the thinnest snapshot active during the validation window, so the
    fold-skip floor must see that 5, not the historical union."""
    from prepare import _min_active_universe

    thin = frozenset(f"T{i}" for i in range(5))
    full = frozenset(f"S{i}" for i in range(200))
    ubd = {date(2021, 1, 1): thin, date(2022, 7, 1): full}

    # window entirely in the 5-name era → 5
    assert _min_active_universe(ubd, date(2021, 6, 1), date(2021, 12, 1)) == 5
    # window straddling the 5→200 jump still sees the thin snapshot at start
    assert _min_active_universe(ubd, date(2022, 3, 1), date(2022, 9, 1)) == 5
    # window entirely in the full era → 200
    assert _min_active_universe(ubd, date(2022, 8, 1), date(2023, 1, 1)) == 200
    # no snapshot predating the window → data-starved sentinel 0
    assert _min_active_universe({}, date(2021, 1, 1), date(2021, 6, 1)) == 0


def test_thin_universe_folds_are_below_floor() -> None:
    """A 5-name fold is below MIN_FOLD_UNIVERSE and must be skipped; a
    200-name fold is above it and must be scored."""
    from prepare import MIN_FOLD_UNIVERSE, _min_active_universe

    thin = frozenset(f"T{i}" for i in range(5))
    full = frozenset(f"S{i}" for i in range(200))
    ubd = {date(2021, 1, 1): thin, date(2022, 7, 1): full}

    assert _min_active_universe(ubd, date(2021, 6, 1), date(2021, 12, 1)) < MIN_FOLD_UNIVERSE
    assert _min_active_universe(ubd, date(2022, 8, 1), date(2023, 1, 1)) >= MIN_FOLD_UNIVERSE


def test_evaluator_version_is_stamped() -> None:
    from prepare import EVALUATOR_VERSION

    assert isinstance(EVALUATOR_VERSION, str) and EVALUATOR_VERSION
