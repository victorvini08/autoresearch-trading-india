"""Integration smoke test for `scripts.executors.dhan.DhanExecutor`.

Sets up a tiny in-memory prices.duckdb + mock broker + monkeypatched
`scripts.signal_today.generate_signals` that returns fixed targets, then runs
one `execute_day` and asserts the executor produced orders, fills, and a
valid ExecutionSummary.

This is the closest thing to an end-to-end dhan-paper run we can do without
a real Dhan account and without the full strategy/walk-forward stack — it
exercises the executor's pre-flight → signal-extract → order-build → fill
→ summary chain in one fast test.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest

from brokers.dhan_mock import DhanMock
from scripts.executors.dhan import DhanExecutor


@pytest.fixture
def prices_db(tmp_path: Path) -> Path:
    p = tmp_path / "prices.duckdb"
    conn = duckdb.connect(str(p))
    try:
        conn.execute(
            """
            CREATE TABLE daily_bars (
                ticker VARCHAR NOT NULL, dt DATE NOT NULL,
                open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
                volume BIGINT, value_inr_crores DOUBLE,
                PRIMARY KEY (ticker, dt)
            )
            """
        )
        # 6 candidate tickers with current prices
        for ticker, price in [
            ("RELIANCE", 1200.0),
            ("INFY", 1500.0),
            ("TCS", 3500.0),
            ("HDFCBANK", 1600.0),
            ("ICICIBANK", 1100.0),
            ("BHARTIARTL", 1450.0),
        ]:
            conn.execute(
                "INSERT INTO daily_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ticker, date(2026, 5, 13), price * 0.99, price * 1.01, price * 0.98, price, 100000, 1.0),
            )
    finally:
        conn.close()
    return p


@pytest.fixture
def portfolio_db(tmp_path: Path) -> Path:
    return tmp_path / "portfolio.duckdb"


@pytest.fixture
def halt_file(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "halt.json"
    # Reroute storage.portfolio_db.HALT_FILE_PATH to our temp
    import storage.portfolio_db as pdb

    monkeypatch.setattr(pdb, "HALT_FILE_PATH", p)
    return p


def _stub_signals(*, as_of_date, strategy_module, **_kwargs):
    """Return fixed targets — equal-weighted 6 names at ~₹50k capital."""
    target_each = 1.0 / 6.0
    return {
        "targets": {
            "RELIANCE": target_each,
            "INFY": target_each,
            "TCS": target_each,
            "HDFCBANK": target_each,
            "ICICIBANK": target_each,
            "BHARTIARTL": target_each,
        }
    }


def test_dhan_executor_paper_runs_end_to_end(
    prices_db: Path,
    portfolio_db: Path,
    halt_file: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    executor = DhanExecutor(
        mode="dhan-paper",
        prices_db=prices_db,
        portfolio_db=portfolio_db,
        broker=mock,
        initial_cash_inr=50_000.0,
    )
    with patch("scripts.signal_today.generate_signals", side_effect=_stub_signals):
        result = executor.execute_day(date(2026, 5, 13))

    # Result: not skipped, has orders + fills (we have 6 fresh buys)
    assert not result.skipped, f"unexpected skip: {result.skipped_reason}"
    assert result.n_orders == 6
    assert result.n_fills == 6
    assert result.gross_buy_usd > 0
    assert result.gross_sell_usd == 0  # nothing held at start; just buys


def test_dhan_executor_respects_halt(
    prices_db: Path,
    portfolio_db: Path,
    halt_file: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0)
    executor = DhanExecutor(
        mode="dhan-paper",
        prices_db=prices_db,
        portfolio_db=portfolio_db,
        broker=mock,
    )
    # Set halt
    from scripts.halt import set_halt

    set_halt("test halt", set_by="pytest")
    try:
        result = executor.execute_day(date(2026, 5, 13))
        assert result.skipped
        assert "halt.json" in (result.skipped_reason or "")
        assert result.n_orders == 0
    finally:
        from scripts.halt import clear_halt

        clear_halt(force=True)


def test_dhan_executor_empty_targets_skips(
    prices_db: Path,
    portfolio_db: Path,
    halt_file: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0)
    executor = DhanExecutor(
        mode="dhan-paper",
        prices_db=prices_db,
        portfolio_db=portfolio_db,
        broker=mock,
    )

    def empty_signals(**_kwargs):
        return {"targets": {}}

    with patch("scripts.signal_today.generate_signals", side_effect=empty_signals):
        result = executor.execute_day(date(2026, 5, 13))
    assert result.skipped
    assert "non-rebalance day" in (result.skipped_reason or "") or "empty" in (
        result.skipped_reason or ""
    )
