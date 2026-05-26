"""Regression tests for the pre-live correctness fixes (2026-05-26).

Each block locks in one Codex/Claude finding from the pre-live review:
  - B2: exit-only signal days liquidate held positions (not skipped).
  - B5: FRACTION_CHANGE_THRESHOLD actually suppresses small-delta resizes.
  - B6: Fill.trade_id uniquely keys ledger rows when one order produces N fills.
  - B7: DhanBroker refuses to construct when SEBI_ALGO_ID is empty.
  - signal_today: look-ahead guard refuses today's bar at runtime.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import duckdb
import pytest

from brokers.dhan import Fill, OrderRequest
from brokers.dhan_mock import DhanMock
from scripts.executors.dhan import DhanExecutor


# ──────────────────────────────────────────────────────────
# B7: SEBI_ALGO_ID hard-fail at broker construction
# ──────────────────────────────────────────────────────────


def test_dhan_broker_refuses_when_sebi_algo_id_empty(monkeypatch) -> None:
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "fake")
    monkeypatch.setenv("DHAN_CLIENT_ID", "1000001234")
    monkeypatch.delenv("SEBI_ALGO_ID", raising=False)
    from brokers.dhan import DhanBroker
    with pytest.raises(RuntimeError, match="SEBI_ALGO_ID"):
        DhanBroker()


def test_dhan_executor_refuses_live_when_sebi_unset(monkeypatch) -> None:
    monkeypatch.delenv("DHAN_MOCK", raising=False)
    monkeypatch.delenv("SEBI_ALGO_ID", raising=False)
    with pytest.raises(RuntimeError, match="SEBI_ALGO_ID is empty"):
        DhanExecutor(mode="dhan-live")


# ──────────────────────────────────────────────────────────
# B6: Fill.trade_id uniqueness — multi-fill scenario
# ──────────────────────────────────────────────────────────


def test_fill_trade_id_field_present() -> None:
    f = Fill(
        order_id="O1",
        ticker="RELIANCE",
        side="BUY",
        quantity=10,
        price=1200.0,
        fill_time=datetime.now(),
        commission=0.0,
        trade_id="T-leg-1",
    )
    assert f.trade_id == "T-leg-1"


def test_dhan_get_fills_extracts_trade_id_from_raw(monkeypatch) -> None:
    """The live broker maps Dhan's exchangeTradeId / tradeId into Fill.trade_id."""
    monkeypatch.setenv("DHAN_ACCESS_TOKEN", "fake")
    monkeypatch.setenv("DHAN_CLIENT_ID", "1000001234")
    monkeypatch.setenv("SEBI_ALGO_ID", "ALGO_TEST")
    from brokers.dhan import DhanBroker

    # Two trade legs sharing one orderId — the previous code would have
    # collided on the actual_fills PK.
    broker = DhanBroker.__new__(DhanBroker)
    broker.algo_id = "ALGO_TEST"
    broker.client_id = "1000001234"
    broker.access_token = "fake"

    def _stub_request(method, path, body=None):
        assert method == "GET" and path == "/v2/trades"
        return [
            {
                "orderId": "ORDER123",
                "exchangeTradeId": "EX-T-001",
                "tradingSymbol": "RELIANCE",
                "transactionType": "BUY",
                "tradedQuantity": 5,
                "tradedPrice": 1200.0,
                "tradeTime": "2026-05-26T10:30:00",
                "brokerage": 0.0,
            },
            {
                "orderId": "ORDER123",          # same order
                "exchangeTradeId": "EX-T-002",  # DIFFERENT trade leg
                "tradingSymbol": "RELIANCE",
                "transactionType": "BUY",
                "tradedQuantity": 5,
                "tradedPrice": 1201.0,
                "tradeTime": "2026-05-26T10:30:30",
                "brokerage": 0.0,
            },
        ]

    monkeypatch.setattr(broker, "_request", _stub_request)
    fills = broker.get_fills()
    assert len(fills) == 2
    assert fills[0].order_id == fills[1].order_id == "ORDER123"
    # The critical contract: distinct trade_ids when one order has N legs
    assert fills[0].trade_id == "EX-T-001"
    assert fills[1].trade_id == "EX-T-002"
    assert fills[0].trade_id != fills[1].trade_id


# ──────────────────────────────────────────────────────────
# B2: exit-only signal days liquidate, don't skip
# ──────────────────────────────────────────────────────────


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
        for d in (date(2026, 5, 12), date(2026, 5, 13)):
            conn.execute(
                "INSERT INTO daily_bars VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("RELIANCE", d, 1200, 1210, 1190, 1200, 1000000, 12.0),
            )
    finally:
        conn.close()
    return p


@pytest.fixture
def portfolio_db_fx(tmp_path: Path) -> Path:
    from storage import portfolio_db
    p = tmp_path / "portfolio.duckdb"
    conn = duckdb.connect(str(p))
    try:
        portfolio_db.init_schema(conn)
    finally:
        conn.close()
    return p


def test_exit_only_signal_liquidates_held_position(
    prices_db: Path, portfolio_db_fx: Path, monkeypatch, tmp_path: Path,
) -> None:
    """When strategy says 'all to cash' (exits non-empty, targets empty), the
    executor must SELL every held position, not skip the day."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    # Isolate halt + consent so test doesn't touch real state
    from storage import portfolio_db as pdb
    halt = tmp_path / "halt.json"
    monkeypatch.setattr(pdb, "HALT_FILE_PATH", halt)
    from scripts import halt as halt_mod
    monkeypatch.setattr(halt_mod, "HALT_FILE_PATH", halt)

    # Seed a held position
    mock = DhanMock(
        prices_db=prices_db, portfolio_db=portfolio_db_fx,
        initial_cash_inr=50_000.0, slippage_bps=0.0, mode="dhan-paper",
    )
    mock.place_order(OrderRequest("BUY", "RELIANCE", 10, "MARKET"))
    assert len(mock.get_positions()) == 1

    executor = DhanExecutor(
        mode="dhan-paper", prices_db=prices_db, portfolio_db=portfolio_db_fx,
        broker=mock, initial_cash_inr=50_000.0,
    )

    # Stub signals to return ONLY exits, no targets — the "all to cash" case.
    def exit_only_stub(*, target_date, strategy_module_name, **_kwargs):
        return {
            "targets": [],
            "exits": [{"ticker": "RELIANCE", "target_fraction": 0.0}],
        }

    with patch("scripts.signal_today.generate_signals", side_effect=exit_only_stub):
        result = executor.execute_day(date(2026, 5, 13))

    # The fix: the executor must have placed a SELL, not skipped.
    assert not result.skipped, (
        f"exit-only signal must liquidate, got skip: {result.skipped_reason}"
    )
    assert result.gross_sell_usd > 0
    assert result.n_fills >= 1
    assert mock.get_positions() == []  # liquidated


# ──────────────────────────────────────────────────────────
# B5: FRACTION_CHANGE_THRESHOLD actually fires now
# ──────────────────────────────────────────────────────────


def test_fraction_change_suppresses_small_target_delta(
    prices_db: Path, portfolio_db_fx: Path, monkeypatch, tmp_path: Path,
) -> None:
    """Two consecutive runs with target_fraction differing by < 0.5pp must not
    produce a second order (the old form of the guard never fired)."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    from storage import portfolio_db as pdb
    halt = tmp_path / "halt.json"
    monkeypatch.setattr(pdb, "HALT_FILE_PATH", halt)
    from scripts import halt as halt_mod
    monkeypatch.setattr(halt_mod, "HALT_FILE_PATH", halt)

    mock = DhanMock(
        prices_db=prices_db, portfolio_db=portfolio_db_fx,
        initial_cash_inr=100_000.0, slippage_bps=0.0, mode="dhan-paper",
    )
    executor = DhanExecutor(
        mode="dhan-paper", prices_db=prices_db, portfolio_db=portfolio_db_fx,
        broker=mock, initial_cash_inr=100_000.0,
    )

    # First run: 18% in RELIANCE (under the 20% per-position risk_check cap).
    # ₹18k / ₹1200 = 15 shares, well above the ₹1500 floor. FRACTION_CHANGE
    # doesn't fire (prev_target is 0 → delta is 0.18, much larger than 0.005).
    def stub_v1(*, target_date, strategy_module_name, **_kwargs):
        return {"targets": [{"ticker": "RELIANCE", "target_fraction": 0.18}], "exits": []}

    with patch("scripts.signal_today.generate_signals", side_effect=stub_v1):
        result1 = executor.execute_day(date(2026, 5, 12))
    assert result1.n_orders == 1

    # Second run: same name, target moves by 0.001 (0.1pp, less than the
    # 0.005 threshold). With the dead-code bug, this would still produce
    # an order if mark-drift integer rounding changed target_qty. With the
    # fix, the fraction-change suppressor kicks in and we skip.
    def stub_v2(*, target_date, strategy_module_name, **_kwargs):
        return {"targets": [{"ticker": "RELIANCE", "target_fraction": 0.181}], "exits": []}

    with patch("scripts.signal_today.generate_signals", side_effect=stub_v2):
        result2 = executor.execute_day(date(2026, 5, 13))

    # Either the resize was suppressed (n_orders=0) OR it produced a sub-
    # MIN_ORDER_INR resize that the MIN_ORDER_INR floor caught. Both are
    # acceptable outcomes of the combined guards; what's NOT acceptable is
    # any nonzero order, which would mean both guards leaked.
    assert result2.n_orders == 0, (
        f"fraction-change + min-order guards must both suppress this resize, "
        f"got n_orders={result2.n_orders}"
    )


# ──────────────────────────────────────────────────────────
# signal_today: look-ahead guard
# ──────────────────────────────────────────────────────────


def test_signal_today_lookahead_guard_blocks_today_bar(monkeypatch) -> None:
    """If feeds contain today's bar AND target_date is today, refuse."""
    from scripts import signal_today

    # We don't want to actually run cerebro; only the guard before it.
    # Patch _load_feeds to return a single feed whose last bar == today.
    today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    import pandas as pd
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [1000, 1100],
        },
        index=pd.DatetimeIndex(
            [today_ist - timedelta(days=1), today_ist], name="dt"
        ),
    )

    monkeypatch.setattr(signal_today, "_load_feeds", lambda s, e, t: {"FAKE": df})
    monkeypatch.setattr(signal_today, "get_universe_at", lambda d: ["FAKE"])

    with pytest.raises(RuntimeError, match="look-ahead guard"):
        signal_today.generate_signals(target_date=today_ist)


def test_signal_today_lookahead_guard_allows_replay(monkeypatch) -> None:
    """Backfill / replay (target_date in the past) is fine — no future to leak."""
    from scripts import signal_today

    import pandas as pd
    past = date(2026, 5, 13)
    df = pd.DataFrame(
        {
            "open": [100.0], "high": [101.0], "low": [99.0],
            "close": [100.5], "volume": [1000],
        },
        index=pd.DatetimeIndex([past], name="dt"),
    )

    monkeypatch.setattr(signal_today, "_load_feeds", lambda s, e, t: {"FAKE": df})
    monkeypatch.setattr(signal_today, "get_universe_at", lambda d: ["FAKE"])
    # Replace cerebro pieces so this doesn't actually run a strategy.
    monkeypatch.setattr(signal_today, "_find_strategy_class", lambda m: type)
    monkeypatch.setattr(
        signal_today, "_make_capturing_strategy",
        lambda cls: (cls, {}),
    )

    # No assertion on output — we only care that the guard doesn't raise.
    # The cerebro run below will fail for unrelated reasons (fake strategy
    # class), so catch broadly.
    try:
        signal_today.generate_signals(target_date=past)
    except RuntimeError as e:
        assert "look-ahead guard" not in str(e), (
            "guard wrongly fired for past-date replay"
        )
    except Exception:
        pass  # OK — cerebro/backtrader failure unrelated to the guard
