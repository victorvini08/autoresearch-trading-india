"""End-to-end smoke: real NSE data → prepare.evaluate() → finite score.

TWEAKS from US repo:
- Smoke tickers: Indian NSE blue chips instead of US mega-caps.
  AAPL/MSFT/NVDA/GOOGL/META  →  RELIANCE/TCS/INFY/HDFCBANK/ICICIBANK

Marked `integration` so the default `pytest` run stays offline. Run with:

    uv run pytest tests/test_e2e.py -v -m integration
"""
import importlib
import os

import numpy as np
import pytest

from data.ingest_prices import ingest_prices
from prepare import BACKTEST_END, BACKTEST_START, evaluate

# TWEAK: NSE blue-chip tickers, all in Nifty 500. ingest_prices appends
# '.NS' internally for yfinance.
SMOKE_TICKERS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="skipped on CI to avoid yfinance flakes",
)
def test_e2e_research_mode_runs_end_to_end():
    ingest_prices(
        set(SMOKE_TICKERS),
        BACKTEST_START,
        BACKTEST_END,
    )

    strat_mod = importlib.import_module("strategy")

    # Research mode — test set must be hidden
    result = evaluate(strat_mod, mode="research")
    assert "validation_sortino_mean" in result
    assert np.isfinite(result["validation_sortino_mean"]), \
        f"non-finite validation Sortino: {result['validation_sortino_mean']}"
    assert result["validation_folds"] > 0
    for forbidden in ("test_sortino", "test_calmar", "test_max_dd", "test_hit_rate"):
        assert forbidden not in result, f"{forbidden} leaked into research mode"

    # Promotion mode — test set now revealed
    result_p = evaluate(strat_mod, mode="promotion")
    assert "test_sortino" in result_p
    assert "test_max_dd" in result_p
    # Validation keys still present
    assert "validation_sortino_mean" in result_p
