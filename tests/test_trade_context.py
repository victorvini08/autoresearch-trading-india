"""Step 3.a — trade context: held-position drift + closed-trade attribution.

Strategy: unit-test the pure flag/cause logic exhaustively with controlled
inputs; integration-test the real PIT scorer once against synthetic rising
prices; and test the assembly (compute_trade_context_for_date) by
monkeypatching _pit_scores to controlled rankings + seeding the ledger.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import pytest

import scripts.trade_context as tc
from scripts.trade_context import (
    _dominant_cause,
    _drift_flag,
    _pit_scores,
    compute_trade_context_for_date,
)
from storage import portfolio_db

MODE = "dhan-paper"


# === Pure flag logic =======================================================

def test_drift_flag_on_track():
    s, label = _drift_flag(entry_decile=10, current_rank=3, current_decile=10)
    assert s == "ok"
    assert "top-25" in label


def test_drift_flag_collapsed_when_no_current_score():
    s, label = _drift_flag(entry_decile=10, current_rank=None, current_decile=None)
    assert s == "flag"
    assert "collapsed" in label


def test_drift_flag_rank_decay_out_of_top_n():
    s, label = _drift_flag(entry_decile=8, current_rank=32, current_decile=7)
    assert s == "warn"
    assert "#32" in label


def test_drift_flag_decile_decay():
    # Still in top-25 by rank, but decile dropped 10→6 (>=3) → warn.
    s, label = _drift_flag(entry_decile=10, current_rank=12, current_decile=6)
    assert s == "warn"
    assert "10→6" in label


# === Pure dominant-cause logic =============================================

@pytest.mark.parametrize(
    "return_pct, excess_pct, entry_decile, cost_bps, expected",
    [
        (5.0, 2.0, 9, 30, "clean-alpha"),     # won + beat
        (3.0, -1.0, 9, 30, "beta-only"),      # won but lagged
        (-2.0, 1.0, 9, 30, "market-drag"),    # lost but beat (market fell more)
        (-5.0, -3.0, 2, 30, "signal-was-weak"),  # lost+lagged, weak entry
        (-0.3, -0.3, 9, 40, "cost-heavy"),    # tiny loss, cost dominates
        (-5.0, -3.0, 9, 30, "signal-failure"),   # lost+lagged, strong entry
    ],
)
def test_dominant_cause(return_pct, excess_pct, entry_decile, cost_bps, expected):
    assert _dominant_cause(return_pct, excess_pct, entry_decile, cost_bps) == expected


def test_dominant_cause_no_benchmark_falls_back_to_sign():
    # excess None + positive return → treated as beat → clean-alpha
    assert _dominant_cause(4.0, None, 8, 20) == "clean-alpha"
    # excess None + negative return → not beat → strong-entry → signal-failure
    assert _dominant_cause(-4.0, None, 8, 20) == "signal-failure"


# === Fixtures for assembly + PIT integration ===============================

def _bdays(end: date, n: int) -> list[date]:
    """`n` business days ending at `end` (ascending)."""
    out: list[date] = []
    d = end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


@pytest.fixture
def prices_db(tmp_path) -> Path:
    """6 tickers, ~310 business days of rising closes at distinct slopes so
    the momentum-quality scorer produces a clean cross-sectional ranking."""
    p = tmp_path / "prices.duckdb"
    conn = duckdb.connect(str(p))
    try:
        conn.execute(
            "CREATE TABLE daily_bars (ticker VARCHAR, dt DATE, open DOUBLE, "
            "high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, "
            "value_inr_crores DOUBLE, PRIMARY KEY (ticker, dt))"
        )
        days = _bdays(date(2026, 5, 29), 310)
        # growth per day; steeper = stronger momentum
        slopes = {
            "AAA": 0.0020, "BBB": 0.0016, "CCC": 0.0012,
            "DDD": 0.0008, "EEE": 0.0005, "FFF": 0.0003,
        }
        for ticker, g in slopes.items():
            base = 100.0
            for i, d in enumerate(days):
                close = base * ((1.0 + g) ** i)
                vol = 1_000_000
                conn.execute(
                    "INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?,?)",
                    [ticker, d, close * 0.999, close * 1.001, close * 0.998,
                     close, vol, close * vol / 1e7],
                )
    finally:
        conn.close()
    return p


@pytest.fixture
def universe_db(tmp_path) -> Path:
    p = tmp_path / "universe.duckdb"
    conn = duckdb.connect(str(p))
    try:
        conn.execute(
            "CREATE TABLE universe_snapshot (as_of_date DATE, ticker VARCHAR, "
            "rank_by_adv INTEGER)"
        )
        for i, t in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]):
            conn.execute(
                "INSERT INTO universe_snapshot VALUES (?, ?, ?)",
                [date(2026, 1, 1), t, i + 1],
            )
    finally:
        conn.close()
    return p


@pytest.fixture
def macro_db(tmp_path) -> Path:
    p = tmp_path / "macro.duckdb"
    conn = duckdb.connect(str(p))
    try:
        conn.execute(
            "CREATE TABLE macro_daily (series_id VARCHAR, dt DATE, value DOUBLE)"
        )
        # Nifty: 100 on buy date, 105 on sell date (≈ +5% over window)
        conn.execute("INSERT INTO macro_daily VALUES ('index_nifty_50', ?, ?)",
                     [date(2026, 5, 1), 100.0])
        conn.execute("INSERT INTO macro_daily VALUES ('index_nifty_50', ?, ?)",
                     [date(2026, 5, 20), 105.0])
    finally:
        conn.close()
    return p


@pytest.fixture
def portfolio(tmp_path) -> Path:
    p = tmp_path / "portfolio.duckdb"
    portfolio_db.connect(p).close()
    return p


# === PIT scorer integration ================================================

def test_pit_scores_ranks_steeper_risers_higher(prices_db, universe_db):
    cache: dict = {}
    scores, size = _pit_scores(date(2026, 5, 29), prices_db, universe_db, cache)
    assert size >= 5, scores
    # AAA has the steepest slope → should rank best (#1), FFF worst.
    assert scores["AAA"]["rank"] == 1
    assert scores["AAA"]["decile"] == 10
    # Monotonic-ish: steeper slope → better (smaller) rank
    assert scores["AAA"]["rank"] < scores["FFF"]["rank"]
    # Second call hits the cache (same object identity in the dict)
    assert date(2026, 5, 29) in cache


def test_pit_scores_empty_when_universe_missing(prices_db, tmp_path):
    empty_univ = tmp_path / "empty_universe.duckdb"
    duckdb.connect(str(empty_univ)).execute(
        "CREATE TABLE universe_snapshot (as_of_date DATE, ticker VARCHAR, "
        "rank_by_adv INTEGER)"
    )
    scores, size = _pit_scores(date(2026, 5, 29), prices_db, empty_univ, {})
    assert scores == {} and size == 0


# === Assembly: held drift ==================================================

def _seed_position(conn, *, ticker, qty, buy_price, mark_price, buy_date,
                   snap_date, mode=MODE):
    conn.execute(
        "INSERT INTO broker_positions (snapshot_date, ticker, quantity, "
        "avg_entry_price, mark_price, mark_value, mode) VALUES (?,?,?,?,?,?,?)",
        [snap_date, ticker, qty, None, mark_price, qty * mark_price, mode],
    )
    conn.execute(
        "INSERT INTO position_lots (lot_id, ticker, buy_fill_id, buy_date, "
        "buy_price, qty_open, qty_total, mode) VALUES (?,?,?,?,?,?,?,?)",
        [uuid.uuid4().hex, ticker, uuid.uuid4().hex, buy_date, buy_price,
         qty, qty, mode],
    )


def test_held_drift_assembly_with_controlled_scores(
    prices_db, universe_db, macro_db, portfolio, monkeypatch,
):
    d = date(2026, 5, 29)
    entry = date(2026, 5, 1)
    with portfolio_db.connect(portfolio) as c:
        # ONGC: bought at 100, now 96 (-4%); strong at entry, collapses now
        _seed_position(c, ticker="ONGC", qty=10, buy_price=100.0,
                       mark_price=96.0, buy_date=entry, snap_date=d)
        # SAIL: bought at 50, now 55 (+10%); stays top
        _seed_position(c, ticker="SAIL", qty=20, buy_price=50.0,
                       mark_price=55.0, buy_date=entry, snap_date=d)

    # Controlled PIT scores: entry date both strong; today ONGC collapses,
    # SAIL stays #2.
    controlled = {
        entry: ({"ONGC": {"rank": 4, "score": 5.0, "decile": 10},
                 "SAIL": {"rank": 2, "score": 6.0, "decile": 10}}, 50),
        d: ({"SAIL": {"rank": 2, "score": 6.0, "decile": 10}}, 50),  # ONGC absent
    }
    monkeypatch.setattr(
        tc, "_pit_scores",
        lambda sd, pdb, udb, cache: controlled.get(sd, ({}, 0)),
    )

    out = compute_trade_context_for_date(
        d, mode=MODE, db_path=portfolio, prices_db=prices_db,
        universe_db=universe_db, macro_db=macro_db,
    )
    held = {h["ticker"]: h for h in out["held"]}
    assert held["ONGC"]["flag"] == "flag"  # collapsed (absent today)
    assert held["ONGC"]["entry_rank"] == 4
    assert held["ONGC"]["current_rank"] is None
    assert abs(held["ONGC"]["unrealized_pct"] - (-4.0)) < 1e-6
    assert held["SAIL"]["flag"] == "ok"
    assert abs(held["SAIL"]["unrealized_pct"] - 10.0) < 1e-6
    assert held["SAIL"]["holding_days"] == (d - entry).days


# === Assembly: closed-trade attribution ====================================

def _seed_realized_trade(conn, *, ticker, buy_date, sell_date, buy_price,
                         sell_price, qty=10, mode=MODE):
    pnl = (sell_price - buy_price) * qty
    holding = (sell_date - buy_date).days
    conn.execute(
        "INSERT INTO realized_trades (trade_id, sell_fill_id, buy_lot_id, "
        "ticker, buy_date, sell_date, qty, buy_price, sell_price, "
        "realized_pnl_usd, holding_days, tax_paid_usd, mode) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex, ticker,
         buy_date, sell_date, qty, buy_price, sell_price, pnl, holding,
         max(0.0, pnl) * 0.15, mode],
    )


def test_closed_attribution_clean_alpha(
    prices_db, universe_db, macro_db, portfolio, monkeypatch,
):
    buy, sell = date(2026, 5, 1), date(2026, 5, 20)
    d = date(2026, 5, 29)
    with portfolio_db.connect(portfolio) as c:
        # +20% vs Nifty +5% → clean-alpha
        _seed_realized_trade(c, ticker="WINNER", buy_date=buy, sell_date=sell,
                             buy_price=100.0, sell_price=120.0)
    monkeypatch.setattr(
        tc, "_pit_scores",
        lambda sd, pdb, udb, cache: (
            {"WINNER": {"rank": 1, "score": 6.0, "decile": 10}}, 50),
    )
    out = compute_trade_context_for_date(
        d, mode=MODE, db_path=portfolio, prices_db=prices_db,
        universe_db=universe_db, macro_db=macro_db,
    )
    assert len(out["closed"]) == 1
    row = out["closed"][0]
    assert abs(row["return_pct"] - 20.0) < 1e-6
    assert abs(row["nifty_pct"] - 5.0) < 1e-6
    assert abs(row["excess_pct"] - 15.0) < 1e-6
    assert row["entry_decile"] == 10
    assert row["dominant_cause"] == "clean-alpha"
    assert row["cost_bps"] > 0  # DP + STT always charged


def test_closed_attribution_beta_only(
    prices_db, universe_db, macro_db, portfolio, monkeypatch,
):
    buy, sell = date(2026, 5, 1), date(2026, 5, 20)
    d = date(2026, 5, 29)
    with portfolio_db.connect(portfolio) as c:
        # +2% vs Nifty +5% → made money but lagged → beta-only
        _seed_realized_trade(c, ticker="LAGGARD", buy_date=buy, sell_date=sell,
                             buy_price=100.0, sell_price=102.0)
    monkeypatch.setattr(
        tc, "_pit_scores",
        lambda sd, pdb, udb, cache: (
            {"LAGGARD": {"rank": 8, "score": 4.0, "decile": 8}}, 50),
    )
    out = compute_trade_context_for_date(
        d, mode=MODE, db_path=portfolio, prices_db=prices_db,
        universe_db=universe_db, macro_db=macro_db,
    )
    assert out["closed"][0]["dominant_cause"] == "beta-only"


def test_empty_day_returns_empty_lists(
    prices_db, universe_db, macro_db, portfolio,
):
    out = compute_trade_context_for_date(
        date(2026, 5, 29), mode=MODE, db_path=portfolio, prices_db=prices_db,
        universe_db=universe_db, macro_db=macro_db,
    )
    assert out["held"] == []
    assert out["closed"] == []
