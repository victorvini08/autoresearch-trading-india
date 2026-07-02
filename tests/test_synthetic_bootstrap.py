"""The synthetic bootstrap produces stores matching the library's read schema."""

from datetime import date

import duckdb

from autoresearch.data.synthetic import generate


def test_synthetic_prices_and_universe_schema(tmp_path):
    prices = tmp_path / "prices.duckdb"
    universe = tmp_path / "universe.duckdb"
    generate(prices, universe, n_tickers=55, start=date(2019, 1, 1),
             end=date(2020, 12, 31), seed=1)

    pcols = {r[1] for r in duckdb.connect(str(prices)).execute(
        "PRAGMA table_info('daily_bars')").fetchall()}
    assert {"ticker", "dt", "open", "high", "low", "close",
            "volume", "value_inr_crores", "prev_close"} <= pcols

    ucols = {r[1] for r in duckdb.connect(str(universe)).execute(
        "PRAGMA table_info('universe_snapshot')").fetchall()}
    assert {"as_of_date", "ticker", "industry", "adv_20d_cr", "rank_by_adv"} <= ucols

    # >= MIN_FOLD_UNIVERSE tickers so evaluator folds are not auto-skipped.
    n = duckdb.connect(str(universe)).execute(
        "SELECT COUNT(DISTINCT ticker) FROM universe_snapshot").fetchone()[0]
    assert n >= 50


def test_synthetic_is_deterministic(tmp_path):
    a, b = tmp_path / "a.duckdb", tmp_path / "b.duckdb"
    ua, ub = tmp_path / "ua.duckdb", tmp_path / "ub.duckdb"
    generate(a, ua, n_tickers=50, start=date(2019, 1, 1), end=date(2019, 6, 30), seed=7)
    generate(b, ub, n_tickers=50, start=date(2019, 1, 1), end=date(2019, 6, 30), seed=7)
    ra = duckdb.connect(str(a)).execute(
        "SELECT close FROM daily_bars ORDER BY ticker, dt").fetchall()
    rb = duckdb.connect(str(b)).execute(
        "SELECT close FROM daily_bars ORDER BY ticker, dt").fetchall()
    assert ra == rb
