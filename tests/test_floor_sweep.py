"""Floor-sweep: residual idle cash (from a cap-blocked expensive name +
whole-share under-fill) gets parked into the cash-floor ETF, not left at 0%."""
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
            "CREATE TABLE daily_bars (ticker VARCHAR NOT NULL, dt DATE NOT NULL, "
            "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, "
            "value_inr_crores DOUBLE, PRIMARY KEY (ticker, dt))"
        )
        # EXPENSIVE @ ₹6,000 > the ₹5,000 (10%) cap at ₹50k -> unbuyable (like
        # CUMMINSIND). LIQUIDCASE (the floor) @ ₹100.
        for tk, px in [("EXPENSIVE", 6000.0), ("CHEAP", 150.0), ("LIQUIDCASE", 100.0)]:
            conn.execute("INSERT INTO daily_bars VALUES (?,?,?,?,?,?,?,?)",
                         (tk, date(2026, 5, 13), px, px, px, px, 100000, 1.0))
    finally:
        conn.close()
    return p


@pytest.fixture
def portfolio_db(tmp_path: Path) -> Path:
    return tmp_path / "portfolio.duckdb"


@pytest.fixture
def halt_file(tmp_path: Path, monkeypatch) -> Path:
    p = tmp_path / "halt.json"
    import storage.portfolio_db as pdb
    monkeypatch.setattr(pdb, "HALT_FILE_PATH", p)
    return p


def _stub_only_expensive(*, target_date, strategy_module_name, **_kw):
    # one equity name, priced above the 10% cap -> cap-blocked -> residual cash
    return {"targets": {"EXPENSIVE": 0.10}}


def test_floor_sweep_parks_capblocked_residual(prices_db, portfolio_db, halt_file, monkeypatch):
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    ex = DhanExecutor(mode="dhan-paper", prices_db=prices_db, portfolio_db=portfolio_db,
                      broker=mock, initial_cash_inr=50_000.0)
    with patch("scripts.signal_today.generate_signals", side_effect=_stub_only_expensive):
        ex.execute_day(date(2026, 5, 13))

    pos = {p.ticker: p.quantity for p in mock.get_positions() if p.quantity}
    # EXPENSIVE is cap-blocked (₹6,000 > ₹5,000) -> 0 shares
    assert "EXPENSIVE" not in pos
    # Floor injection put ~440 LIQUIDCASE (0.88 of ₹50k @ ₹100); the floor-SWEEP
    # then parked the cap-blocked ₹5,000 -> +50 more -> ~490 total.
    assert pos["LIQUIDCASE"] == 490, f"expected 490 LIQUIDCASE, got {pos.get('LIQUIDCASE')}"
    # Only the ~2% buffer (₹1,000) left as cash — NOT the ~₹6,000 it used to be.
    cash = float(mock.get_cash().get("availableBalance", 0.0))
    assert cash <= 1_100, f"expected ~₹1,000 residual cash, got ₹{cash:,.0f}"


def _stub_cheap(*, target_date, strategy_module_name, **_kw):
    # affordable name at the 10% cap (₹5k @ ₹150 = 33 shares); floor takes the rest
    return {"targets": {"CHEAP": 0.10}}


def test_floor_sweep_noop_when_no_excess(prices_db, portfolio_db, halt_file, monkeypatch):
    """When the floor already absorbed the idle cash (only the ~2% buffer + a
    sub-one-share sliver left), the floor-sweep adds nothing — no over-buy."""
    monkeypatch.setenv("DHAN_MOCK", "1")
    mock = DhanMock(prices_db=prices_db, initial_cash_inr=50_000.0, slippage_bps=0.0)
    ex = DhanExecutor(mode="dhan-paper", prices_db=prices_db, portfolio_db=portfolio_db,
                      broker=mock, initial_cash_inr=50_000.0)
    with patch("scripts.signal_today.generate_signals", side_effect=_stub_cheap):
        ex.execute_day(date(2026, 5, 13))
    pos = {p.ticker: p.quantity for p in mock.get_positions() if p.quantity}
    # CHEAP ~33 sh (₹4,950); floor injection took 0.88 -> 440 LIQUIDCASE. Residual
    # after = ~₹1,050 (buffer + a sub-₹100 sliver) -> below one LIQUIDCASE share,
    # so the floor-SWEEP buys 0 more (stays 440, not over-bought).
    assert pos["CHEAP"] == 33
    assert pos["LIQUIDCASE"] == 440, f"floor-sweep over-bought: {pos.get('LIQUIDCASE')}"
    assert float(mock.get_cash().get("availableBalance", 0.0)) <= 1_100
