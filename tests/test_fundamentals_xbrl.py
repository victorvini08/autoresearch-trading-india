"""Tests for data.fundamentals_xbrl — parsed against a REAL committed NSE
results XBRL fixture (tests/fixtures/nse_result_tcs.xml, TCS Q3 FY25),
plus a synthetic-malformed case and a network-mocked fetch.

The earlier mock-only suite gave false confidence (it never exercised the
real schema and missed that BSE attachments are PDFs). This suite asserts
the real document parses to the right *quarter* numbers.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import data.fundamentals_xbrl as fx
from data.fundamentals_xbrl import NseResultRow, parse_xbrl_facts

_FIX = Path(__file__).parent / "fixtures" / "nse_result_tcs.xml"
_PERIOD_END = date(2024, 12, 31)


def test_parses_real_nse_quarter_facts() -> None:
    f = parse_xbrl_facts(_FIX.read_bytes(), _PERIOD_END)
    assert f is not None
    # Quarter (OneD context), NOT the cumulative YTD (FourD).
    assert f.revenue == 639_730_000_000.0
    assert f.revenue != 1_908_450_000_000.0  # would be the 9-month cumulative
    assert f.pbt == 166_660_000_000.0
    assert f.pat == 124_440_000_000.0
    assert f.eps_basic == 34.21
    assert f.eps_diluted == 34.21
    assert f.period_end_date == _PERIOD_END
    assert f.is_consolidated is True


def test_period_end_autodetect_matches_explicit() -> None:
    a = parse_xbrl_facts(_FIX.read_bytes(), _PERIOD_END)
    b = parse_xbrl_facts(_FIX.read_bytes())  # discover period_end
    assert a is not None and b is not None
    assert b.revenue == a.revenue and b.pat == a.pat


def test_malformed_returns_none() -> None:
    assert parse_xbrl_facts(b"not xml") is None
    assert parse_xbrl_facts(b"<xbrli:xbrl></xbrli:xbrl>") is None


def test_download_xbrl_empty_is_none() -> None:
    assert fx.download_xbrl("") is None


def test_fetch_nse_results_parses_rows(monkeypatch) -> None:
    sample = [
        {
            "symbol": "TCS",
            "isin": "INE467B01029",
            "toDate": "31-Dec-2024",
            "broadCastDate": "16-Jan-2025 20:20:21",
            "consolidated": "Consolidated",
            "xbrl": "https://nsearchives.nseindia.com/corporate/xbrl/x.xml",
        },
        {  # no xbrl → skipped
            "symbol": "TCS", "toDate": "30-Sep-2024",
            "broadCastDate": "10-Oct-2024 18:00:00", "xbrl": "",
        },
    ]

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None: ...

        def json(self): return sample

    class _S:
        headers: dict = {}

        def get(self, *a, **k): return _Resp()

    monkeypatch.setattr(fx, "_nse_session", lambda: _S())
    rows = fx.fetch_nse_results("TCS")
    assert len(rows) == 1
    r = rows[0]
    assert isinstance(r, NseResultRow)
    assert r.period_end == date(2024, 12, 31)
    assert r.broadcast_date == date(2025, 1, 16)
    assert r.is_consolidated is True
    assert r.xbrl_url.endswith(".xml")
