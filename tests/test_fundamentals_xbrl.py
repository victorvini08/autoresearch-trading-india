"""Tests for data.fundamentals_xbrl — parsed against a REAL committed NSE
results XBRL fixture (tests/fixtures/nse_result_tcs.xml, TCS Q3 FY25),
plus a synthetic-malformed case and a network-mocked fetch.

The earlier mock-only suite gave false confidence (it never exercised the
real schema and missed that BSE attachments are PDFs). This suite asserts
the real document parses to the right *quarter* numbers.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

import data.fundamentals_xbrl as fx
from data.fundamentals_xbrl import (
    NseFetchError,
    NseResultRow,
    parse_xbrl_facts,
)

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


def test_fetch_nse_results_raises_when_unreachable(monkeypatch) -> None:
    """A persistent throttle/network failure must raise NseFetchError
    (so the backfill counts it as a gap), NOT return [] (which would look
    like the symbol genuinely has no filings)."""
    monkeypatch.setattr(fx.time, "sleep", lambda *_a, **_k: None)

    class _Resp:
        status_code = 503

        def raise_for_status(self) -> None: ...

        def json(self): return []

    class _S:
        headers: dict = {}

        def get(self, *a, **k): return _Resp()

    monkeypatch.setattr(fx, "_nse_session", lambda: _S())
    with pytest.raises(NseFetchError):
        fx.fetch_nse_results("ANYSYM")


# ── Integrated-Filing migration (NSE moved Mar-2025+ quarters here) ──────

_INTEG_JSON = Path(__file__).parent / "fixtures" / "nse_integrated_results_tcs.json"
_INTEG_XBRL = Path(__file__).parent / "fixtures" / "nse_integrated_indas_tcs.xml"


def test_parse_integrated_indas_real_fixture() -> None:
    """The Integrated-Filing XBRL is the SAME IND-AS taxonomy — the
    existing parser must read the standalone quarter unchanged (schema-era
    regression guard; real committed fixture, TCS Q3 FY26 standalone)."""
    f = parse_xbrl_facts(_INTEG_XBRL.read_bytes(), date(2025, 12, 31))
    assert f is not None
    assert f.period_end_date == date(2025, 12, 31)
    assert f.is_consolidated is False
    assert f.revenue == 555_670_000_000.0
    assert f.eps_basic == 28.16


def _fake_session(monkeypatch, *, legacy, integrated):
    """A session whose .get dispatches by endpoint to the given JSON."""
    class _Resp:
        status_code = 200

        def __init__(self, payload): self._p = payload

        def raise_for_status(self) -> None: ...

        def json(self): return self._p

    class _S:
        headers: dict = {}

        def get(self, url, *a, **k):
            if "integrated-filing-results" in url:
                return _Resp(integrated)
            return _Resp(legacy)

    monkeypatch.setattr(fx, "_nse_session", lambda: _S())


def test_fetch_integrated_results_filters_and_parses(monkeypatch) -> None:
    payload = json.loads(_INTEG_JSON.read_text())
    _fake_session(monkeypatch, legacy=[], integrated=payload)
    rows = fx.fetch_nse_results("TCS")
    # 3 Financials rows kept; the "Integrated Filing- Governance" row dropped.
    assert len(rows) == 3
    assert all(r.period_end.year == 2025 for r in rows)
    assert {r.period_end for r in rows} == {date(2025, 6, 30), date(2025, 9, 30)}
    assert all(r.xbrl_url.lower().endswith(".xml") for r in rows)
    assert {r.is_consolidated for r in rows} == {True, False}
    # broadcast_Date parsed from the upper/mixed-case integrated field.
    assert any(r.broadcast_date == date(2025, 7, 10) for r in rows)


def test_fetch_merges_legacy_and_integrated_and_dedups(monkeypatch) -> None:
    legacy = [
        {"symbol": "TCS", "isin": "INE467B01029", "toDate": "31-Dec-2024",
         "broadCastDate": "16-Jan-2025 20:20:21", "consolidated":
         "Consolidated", "xbrl": "https://x/legacy.xml"},
    ]
    integrated = json.loads(_INTEG_JSON.read_text())
    _fake_session(monkeypatch, legacy=legacy, integrated=integrated)
    rows = fx.fetch_nse_results("TCS")
    pes = {r.period_end for r in rows}
    assert date(2024, 12, 31) in pes          # legacy pre-migration
    assert date(2025, 9, 30) in pes           # integrated post-migration
    assert len(rows) == 4                      # 1 legacy + 3 financials
    # Idempotent: exact-duplicate rows across a re-merge collapse.
    seen = {(r.period_end, r.is_consolidated, r.xbrl_url) for r in rows}
    assert len(seen) == len(rows)


def test_fetch_survives_one_endpoint_down(monkeypatch) -> None:
    """Legacy throttled but integrated OK ⇒ still returns integrated rows
    (must NOT raise — only a BOTH-down outage is a real gap)."""
    monkeypatch.setattr(fx.time, "sleep", lambda *_a, **_k: None)
    payload = json.loads(_INTEG_JSON.read_text())

    class _Resp:
        def __init__(self, code, p): self.status_code = code; self._p = p

        def raise_for_status(self) -> None: ...

        def json(self): return self._p

    class _S:
        headers: dict = {}

        def get(self, url, *a, **k):
            if "integrated-filing-results" in url:
                return _Resp(200, payload)
            return _Resp(503, [])

    monkeypatch.setattr(fx, "_nse_session", lambda: _S())
    rows = fx.fetch_nse_results("TCS")
    assert len(rows) == 3 and all(r.period_end.year == 2025 for r in rows)
