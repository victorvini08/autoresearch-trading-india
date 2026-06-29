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


def _stub_signals(*, target_date, strategy_module_name, **_kwargs):
    """Return fixed targets — equal-weighted 6 names at ~₹50k capital.

    Kwarg names match signal_today.generate_signals' actual signature
    (target_date / strategy_module_name); the executor passes both by name.
    """
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


@pytest.fixture
def risk_multiplier_file(tmp_path: Path, monkeypatch) -> Path:
    """Reroute scripts.safety_evaluator.RISK_MULTIPLIER_PATH to a temp file so
    Step 2.c tests don't touch the real state/ directory."""
    import scripts.safety_evaluator as se
    p = tmp_path / "risk_multiplier.json"
    monkeypatch.setattr(se, "RISK_MULTIPLIER_PATH", p)
    return p


def test_executor_halves_orders_when_risk_multiplier_is_half(
    prices_db: Path,
    portfolio_db: Path,
    halt_file: Path,
    risk_multiplier_file: Path,
    monkeypatch,
) -> None:
    """Step 2.c regression: writing risk_multiplier.json = {"multiplier": 0.5}
    must produce orders at half the target weight. Without this wiring the
    safety state machine is decorative."""
    import json
    monkeypatch.setenv("DHAN_MOCK", "1")
    risk_multiplier_file.write_text(
        json.dumps({"multiplier": 0.5, "state": "RISK_REDUCED", "as_of": "2026-05-13",
                    "reason": "test"})
    )
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

    # Half-targets → roughly half the gross_buy of the baseline test.
    # Baseline (mult=1.0) at ₹50k equity: ≈₹45-50k gross buy.
    # With mult=0.5: ≈₹19-25k gross buy. Wide tolerance because per-name
    # integer-share rounding eats a few percent at ₹4k/name targets.
    # The key assertion: 0.5× is clearly < 0.7× baseline.
    assert not result.skipped, f"unexpected skip: {result.skipped_reason}"
    assert 15_000 <= result.gross_buy_usd <= 30_000, (
        f"expected roughly-half gross_buy at 0.5×, got ₹{result.gross_buy_usd:,.0f}"
    )


def test_executor_skips_when_risk_multiplier_is_zero(
    prices_db: Path,
    portfolio_db: Path,
    halt_file: Path,
    risk_multiplier_file: Path,
    monkeypatch,
) -> None:
    """multiplier=0 (HALTED_REVIEW path) → all targets become 0 → no buys.
    Note: even at HALTED_REVIEW the safety machine ALSO writes halt.json
    which would early-exit earlier; this test specifically covers the
    multiplier-arithmetic safety net."""
    import json
    monkeypatch.setenv("DHAN_MOCK", "1")
    risk_multiplier_file.write_text(
        json.dumps({"multiplier": 0.0, "state": "HALTED_REVIEW",
                    "as_of": "2026-05-13", "reason": "test"})
    )
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0)
    executor = DhanExecutor(
        mode="dhan-paper",
        prices_db=prices_db,
        portfolio_db=portfolio_db,
        broker=mock,
    )
    with patch("scripts.signal_today.generate_signals", side_effect=_stub_signals):
        result = executor.execute_day(date(2026, 5, 13))

    # Either: every order is too small to clear MIN_ORDER_INR (suppressed),
    # OR gross_buy is 0. Either way no real buys.
    assert result.gross_buy_usd == 0.0


def test_executor_missing_risk_multiplier_file_defaults_to_one(
    prices_db: Path,
    portfolio_db: Path,
    halt_file: Path,
    risk_multiplier_file: Path,
    monkeypatch,
) -> None:
    """Fail-open: no risk_multiplier.json = treat as 1.0 (NORMAL).
    Fresh installations and missing-file edge cases must NOT accidentally
    halve gross."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    # risk_multiplier_file fixture sets RISK_MULTIPLIER_PATH but does NOT
    # create the file — perfect for this test.
    assert not risk_multiplier_file.exists()
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

    # Should match the baseline test's ≈₹50k gross_buy
    assert not result.skipped
    assert result.gross_buy_usd >= 40_000, (
        f"expected ≈₹50k baseline, got ₹{result.gross_buy_usd:,.0f}"
    )


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


def _force_capturing_stub(seen: list):
    """generate_signals stub that records the `force_rebalance` kwarg the
    executor passes, then returns the standard fixed targets."""

    def _stub(*, target_date, strategy_module_name, force_rebalance=False, **_kw):
        seen.append(force_rebalance)
        return _stub_signals(
            target_date=target_date, strategy_module_name=strategy_module_name
        )

    return _stub


def test_first_day_live_bootstrap_forces_and_marks(
    prices_db: Path, portfolio_db: Path, halt_file: Path, tmp_path: Path, monkeypatch
) -> None:
    """First dhan-live run on an empty book forces a rebalance AND writes the
    one-time marker."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    import scripts.executors.dhan as dhanmod

    marker = tmp_path / "live_bootstrapped.json"
    monkeypatch.setattr(dhanmod, "LIVE_BOOTSTRAP_MARKER", marker)

    seen: list = []
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    executor = DhanExecutor(
        mode="dhan-live", prices_db=prices_db, portfolio_db=portfolio_db,
        broker=mock, initial_cash_inr=50_000.0,
    )
    with patch(
        "scripts.signal_today.generate_signals",
        side_effect=_force_capturing_stub(seen),
    ):
        result = executor.execute_day(date(2026, 5, 13))

    assert seen == [True]                      # bootstrap forced exactly once
    assert marker.exists()                     # marker recorded
    assert not result.skipped, result.skipped_reason


def test_marker_present_suppresses_force_on_empty_book(
    prices_db: Path, portfolio_db: Path, halt_file: Path, tmp_path: Path, monkeypatch
) -> None:
    """A pre-existing marker suppresses the force even on an empty live book —
    the bootstrap is strictly one-time."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    import scripts.executors.dhan as dhanmod

    marker = tmp_path / "live_bootstrapped.json"
    marker.write_text("{}")                    # bootstrap already consumed
    monkeypatch.setattr(dhanmod, "LIVE_BOOTSTRAP_MARKER", marker)

    seen: list = []
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    executor = DhanExecutor(
        mode="dhan-live", prices_db=prices_db, portfolio_db=portfolio_db,
        broker=mock, initial_cash_inr=50_000.0,
    )
    with patch(
        "scripts.signal_today.generate_signals",
        side_effect=_force_capturing_stub(seen),
    ):
        executor.execute_day(date(2026, 5, 13))

    assert seen == [False]


def test_paper_mode_never_force_bootstraps(
    prices_db: Path, portfolio_db: Path, halt_file: Path, tmp_path: Path, monkeypatch
) -> None:
    """The bootstrap is scoped to dhan-live: an empty dhan-paper book must NOT
    force (paper runs daily on the mock with no idle-cash cost)."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    import scripts.executors.dhan as dhanmod

    marker = tmp_path / "live_bootstrapped.json"
    monkeypatch.setattr(dhanmod, "LIVE_BOOTSTRAP_MARKER", marker)

    seen: list = []
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    executor = DhanExecutor(
        mode="dhan-paper", prices_db=prices_db, portfolio_db=portfolio_db,
        broker=mock, initial_cash_inr=50_000.0,
    )
    with patch(
        "scripts.signal_today.generate_signals",
        side_effect=_force_capturing_stub(seen),
    ):
        executor.execute_day(date(2026, 5, 13))

    assert seen == [False]
    assert not marker.exists()


def test_low_capital_live_run_keeps_bootstrap_armed(
    prices_db: Path, portfolio_db: Path, halt_file: Path, tmp_path: Path, monkeypatch
) -> None:
    """A low-capital live run (e.g. a ₹1k API shakedown) FORCES the rebalance
    signal but builds no whole-share equity orders at that capital — so the
    one-time bootstrap marker must NOT be written. It stays armed for the real
    funded start; otherwise the ₹1k test would silently burn the one-shot."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    import scripts.executors.dhan as dhanmod

    marker = tmp_path / "live_bootstrapped.json"
    monkeypatch.setattr(dhanmod, "LIVE_BOOTSTRAP_MARKER", marker)

    seen: list = []
    # ₹1,000 capital: 1/6 ≈ ₹166/name vs share prices ₹1,100–3,500 → 0 shares
    # buildable for every name → order_reqs empty → bootstrap stays armed.
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=1_000.0, slippage_bps=0.0)
    executor = DhanExecutor(
        mode="dhan-live", prices_db=prices_db, portfolio_db=portfolio_db,
        broker=mock, initial_cash_inr=1_000.0,
    )
    with patch(
        "scripts.signal_today.generate_signals",
        side_effect=_force_capturing_stub(seen),
    ):
        executor.execute_day(date(2026, 5, 13))

    assert seen == [True]            # the force WAS computed (empty book, no marker)
    assert not marker.exists()       # but NOT consumed — no buildable equity order
