"""premarket_scan with injected quote fetcher.

TWEAKS from US repo:
- VIX symbol: '^VIX' (yfinance Cboe VIX) -> 'INDIAVIX' (India VIX symbol)
- Mode tag on seeded positions: 'paper' -> 'dhan-paper' (default mode read by scan)
- Function kwarg: `yf_fetch=fetch` -> `quote_fetch=fetch` (data source moved
  from yfinance to a NSE-pre-open / Dhan-quote backend in Phase 6)
- Positional date arg: today_et -> today_ist (orchestrator runs on IST clock)
"""
from __future__ import annotations

import json
from datetime import date

import duckdb
import pytest

from scripts import premarket_scan
from storage import portfolio_db


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Tiny portfolio.duckdb with one held position + isolated state/."""
    db_path = tmp_path / "portfolio.duckdb"
    halt_file = tmp_path / "halt.json"
    monkeypatch.setattr(portfolio_db, "HALT_FILE_PATH", halt_file)

    # Build schema and seed one position. TWEAK: mode='dhan-paper'.
    _conn = portfolio_db.connect(db_path)
    portfolio_db.init_schema(_conn)
    _conn.close()
    conn = duckdb.connect(str(db_path))
    conn.execute(
        "INSERT INTO broker_positions VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2026, 5, 12), "NVDA", 10, None, 100.0, 1000.0, "dhan-paper"],
    )
    conn.execute(
        "INSERT INTO broker_positions VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2026, 5, 12), "META", 5, None, 700.0, 3500.0, "dhan-paper"],
    )
    conn.close()

    return {"db_path": db_path, "out_dir": tmp_path / "state"}


def _mock_fetch(prices: dict[str, tuple[float, float]]):
    """Build a fetcher returning {prior_close, premarket_price} per ticker.

    TWEAK: keys can include 'INDIAVIX' (NSE) instead of '^VIX' (yfinance).
    """
    def fetch(ticker: str):
        if ticker not in prices:
            return None
        prior, live = prices[ticker]
        return {"prior_close": prior, "premarket_price": live}
    return fetch


def test_flat_market_no_flags(env):
    fetch = _mock_fetch({
        "NVDA": (100.0, 100.5),  # +0.5% — no gap
        "META": (700.0, 699.0),  # -0.14% — no gap
        "INDIAVIX": (16.0, 16.0),    # quiet
    })
    payload = premarket_scan.scan(
        date(2026, 5, 13),
        db_path=env["db_path"],
        out_dir=env["out_dir"],
        quote_fetch=fetch,
    )
    assert payload["tickers"]["NVDA"]["gap_flag"] is False
    assert payload["tickers"]["META"]["gap_flag"] is False
    assert payload["vix"]["flag"] is False
    assert payload["halt_recommendations"] == []


def test_gap_flag_fires_at_5pct(env):
    fetch = _mock_fetch({
        "NVDA": (100.0, 106.0),  # +6%
        "META": (700.0, 700.0),
        "INDIAVIX": (18.0, 18.0),
    })
    payload = premarket_scan.scan(
        date(2026, 5, 13),
        db_path=env["db_path"],
        out_dir=env["out_dir"],
        quote_fetch=fetch,
    )
    assert payload["tickers"]["NVDA"]["gap_flag"] is True
    assert payload["tickers"]["NVDA"]["hard_halt"] is False
    assert "NVDA" in premarket_scan.tickers_to_skip(payload)


def test_hard_halt_recommended_above_15pct(env):
    fetch = _mock_fetch({
        "NVDA": (100.0, 120.0),  # +20% — extreme
        "META": (700.0, 700.0),
        "INDIAVIX": (18.0, 18.0),
    })
    payload = premarket_scan.scan(
        date(2026, 5, 13),
        db_path=env["db_path"],
        out_dir=env["out_dir"],
        quote_fetch=fetch,
    )
    assert payload["tickers"]["NVDA"]["hard_halt"] is True
    assert any("NVDA" in r for r in payload["halt_recommendations"])


def test_vix_flag_fires_above_35(env):
    fetch = _mock_fetch({
        "NVDA": (100.0, 100.0),
        "META": (700.0, 700.0),
        "INDIAVIX": (40.0, 40.0),
    })
    payload = premarket_scan.scan(
        date(2026, 5, 13),
        db_path=env["db_path"],
        out_dir=env["out_dir"],
        quote_fetch=fetch,
    )
    assert payload["vix"]["flag"] is True
    assert premarket_scan.vix_scale_down(payload) == 0.5


def test_per_ticker_fetch_error_doesnt_break_others(env):
    def fetch(ticker):
        if ticker == "NVDA":
            raise RuntimeError("boom")
        if ticker == "META":
            return {"prior_close": 700.0, "premarket_price": 700.0}
        return {"prior_close": 18.0, "premarket_price": 18.0}
    payload = premarket_scan.scan(
        date(2026, 5, 13),
        db_path=env["db_path"],
        out_dir=env["out_dir"],
        quote_fetch=fetch,
    )
    assert "error" in payload["tickers"]["NVDA"]
    assert payload["tickers"]["META"]["gap_flag"] is False


def test_output_written_to_expected_path(env):
    fetch = _mock_fetch({"NVDA": (100.0, 100.0), "META": (700.0, 700.0), "INDIAVIX": (18.0, 18.0)})
    premarket_scan.scan(date(2026, 5, 13), db_path=env["db_path"], out_dir=env["out_dir"], quote_fetch=fetch)
    expected = env["out_dir"] / "premarket_2026-05-13.json"
    assert expected.exists()
    data = json.loads(expected.read_text())
    assert data["as_of_date"] == "2026-05-13"


def test_load_returns_none_when_no_scan(env):
    assert premarket_scan.load(date(2026, 5, 13), scan_dir=env["out_dir"]) is None


def test_load_roundtrips(env):
    fetch = _mock_fetch({"NVDA": (100.0, 100.0), "META": (700.0, 700.0), "INDIAVIX": (18.0, 18.0)})
    written = premarket_scan.scan(date(2026, 5, 13), db_path=env["db_path"], out_dir=env["out_dir"], quote_fetch=fetch)
    loaded = premarket_scan.load(date(2026, 5, 13), scan_dir=env["out_dir"])
    assert loaded == written


def test_no_held_positions_produces_empty_tickers(env, tmp_path):
    # Fresh empty DB
    empty_db = tmp_path / "empty_portfolio.duckdb"
    _conn = portfolio_db.connect(empty_db)
    portfolio_db.init_schema(_conn)
    _conn.close()
    fetch = _mock_fetch({"INDIAVIX": (18.0, 18.0)})
    payload = premarket_scan.scan(
        date(2026, 5, 13),
        db_path=empty_db,
        out_dir=env["out_dir"],
        quote_fetch=fetch,
    )
    assert payload["tickers"] == {}
    assert payload["halt_recommendations"] == []


def test_vix_scale_down_returns_1_when_no_scan():
    assert premarket_scan.vix_scale_down(None) == 1.0


def test_tickers_to_skip_returns_empty_when_no_scan():
    assert premarket_scan.tickers_to_skip(None) == set()
