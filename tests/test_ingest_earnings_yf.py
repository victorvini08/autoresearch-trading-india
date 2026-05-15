"""Unit tests for the yfinance earnings path (network mocked)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from data.ingest_earnings import ingest_yfinance_earnings, load_calendar


def _fake_earnings_df() -> pd.DataFrame:
    idx = pd.to_datetime(["2025-01-22", "2024-10-30", "2024-07-19"])
    return pd.DataFrame(
        {
            "EPS Estimate": [22.5, 20.1, float("nan")],
            "Reported EPS": [24.0, 19.8, 18.0],
            "Surprise(%)": [6.7, -1.5, float("nan")],
        },
        index=idx,
    )


def test_ingest_yfinance_earnings_writes_rows(tmp_path: Path) -> None:
    edb = tmp_path / "news.duckdb"
    fake = MagicMock()
    fake.get_earnings_dates.return_value = _fake_earnings_df()
    with patch("yfinance.Ticker", return_value=fake) as yt:
        n = ingest_yfinance_earnings(["RELIANCE"], edb, limit=10, polite_delay_sec=0)
    yt.assert_called_once_with("RELIANCE.NS")
    assert n == 3
    cal = load_calendar(edb, tickers=["RELIANCE"])
    assert len(cal) == 3
    dates = {e.announcement_date for e in cal}
    assert date(2025, 1, 22) in dates
    assert all(e.source == "yfinance" for e in cal)


def test_ingest_yfinance_earnings_eps_fields(tmp_path: Path) -> None:
    import duckdb

    edb = tmp_path / "news.duckdb"
    fake = MagicMock()
    fake.get_earnings_dates.return_value = _fake_earnings_df()
    with patch("yfinance.Ticker", return_value=fake):
        ingest_yfinance_earnings(["RELIANCE"], edb, limit=10, polite_delay_sec=0)
    conn = duckdb.connect(str(edb), read_only=True)
    try:
        row = conn.execute(
            "SELECT eps_estimate, eps_reported, surprise_pct FROM earnings_calendar "
            "WHERE ticker='RELIANCE' AND announcement_date=?",
            (date(2025, 1, 22),),
        ).fetchone()
        # NaN surprise on the 3rd row must be stored as NULL, not NaN
        nan_row = conn.execute(
            "SELECT eps_estimate, surprise_pct FROM earnings_calendar "
            "WHERE ticker='RELIANCE' AND announcement_date=?",
            (date(2024, 7, 19),),
        ).fetchone()
    finally:
        conn.close()
    assert row == (22.5, 24.0, 6.7)
    assert nan_row[0] is None and nan_row[1] is None


def test_ingest_yfinance_earnings_idempotent(tmp_path: Path) -> None:
    edb = tmp_path / "news.duckdb"
    fake = MagicMock()
    fake.get_earnings_dates.return_value = _fake_earnings_df()
    with patch("yfinance.Ticker", return_value=fake):
        ingest_yfinance_earnings(["RELIANCE"], edb, limit=10, polite_delay_sec=0)
        ingest_yfinance_earnings(["RELIANCE"], edb, limit=10, polite_delay_sec=0)
    cal = load_calendar(edb, tickers=["RELIANCE"])
    assert len(cal) == 3  # no duplicates on re-run


def test_ingest_yfinance_earnings_handles_empty(tmp_path: Path) -> None:
    edb = tmp_path / "news.duckdb"
    fake = MagicMock()
    fake.get_earnings_dates.return_value = pd.DataFrame()
    with patch("yfinance.Ticker", return_value=fake):
        n = ingest_yfinance_earnings(["NEWCO"], edb, limit=10, polite_delay_sec=0)
    assert n == 0


def test_ingest_yfinance_earnings_survives_ticker_error(tmp_path: Path) -> None:
    edb = tmp_path / "news.duckdb"

    def _raise(*a, **k):
        raise RuntimeError("yahoo 404")

    with patch("yfinance.Ticker", side_effect=_raise):
        n = ingest_yfinance_earnings(["BADTKR"], edb, limit=10, polite_delay_sec=0)
    assert n == 0  # logged + skipped, no crash
