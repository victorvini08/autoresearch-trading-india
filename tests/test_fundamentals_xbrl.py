"""Unit tests for data.fundamentals_xbrl."""
from __future__ import annotations

import data.fundamentals_xbrl as fx
from data.fundamentals_xbrl import XbrlFacts, parse_xbrl_facts

# Minimal synthetic XBRL — pre-Mar-2025 results taxonomy (in-bse-fin namespace).
_OLD_ERA = b"""<?xml version="1.0"?>
<xbrl xmlns:inbse="http://www.bseindia.com/xbrl/fin/2016-03-31/in-bse-fin">
  <inbse:RevenueFromOperations contextRef="C">5000000</inbse:RevenueFromOperations>
  <inbse:ProfitBeforeTax contextRef="C">900000</inbse:ProfitBeforeTax>
  <inbse:ProfitLossForPeriod contextRef="C">650000</inbse:ProfitLossForPeriod>
  <inbse:ProfitBeforeInterestAndTax contextRef="C">1100000</inbse:ProfitBeforeInterestAndTax>
  <inbse:BasicEarningsPerShare contextRef="C">12.5</inbse:BasicEarningsPerShare>
  <inbse:DilutedEarningsPerShare contextRef="C">12.1</inbse:DilutedEarningsPerShare>
  <inbse:EquityShareCapital contextRef="C">100000</inbse:EquityShareCapital>
  <inbse:OtherEquity contextRef="C">4000000</inbse:OtherEquity>
  <inbse:Borrowings contextRef="C">2000000</inbse:Borrowings>
  <inbse:PaidUpEquityShareCapital contextRef="C">52000</inbse:PaidUpEquityShareCapital>
  <inbse:DateOfEndOfReportingPeriod contextRef="C">2024-12-31</inbse:DateOfEndOfReportingPeriod>
  <inbse:NatureOfReportStandaloneConsolidated contextRef="C">Consolidated</inbse:NatureOfReportStandaloneConsolidated>
</xbrl>"""

# Mar-2025+ Integrated Filing taxonomy: different namespace, same local-names.
_NEW_ERA = _OLD_ERA.replace(
    b"fin/2016-03-31/in-bse-fin",
    b"capmkt/2024-09-30/in-capmkt",
)


def test_parses_old_era() -> None:
    f = parse_xbrl_facts(_OLD_ERA)
    assert f is not None
    assert f.revenue == 5_000_000.0
    assert f.pat == 650_000.0
    assert f.ebit == 1_100_000.0
    assert f.eps_basic == 12.5
    assert f.eps_diluted == 12.1
    assert f.equity == 4_100_000.0  # EquityShareCapital + OtherEquity
    assert f.debt == 2_000_000.0
    assert f.is_consolidated is True
    assert f.period_end_date is not None
    assert f.period_end_date.isoformat() == "2024-12-31"


def test_parses_new_era_same_shape() -> None:
    f = parse_xbrl_facts(_NEW_ERA)
    assert f is not None
    assert f.revenue == 5_000_000.0
    assert f.pat == 650_000.0


def test_malformed_returns_none() -> None:
    assert parse_xbrl_facts(b"not xml") is None
    assert parse_xbrl_facts(b"<xbrl></xbrl>") is None  # no financial facts


def test_download_attachment_empty_is_none() -> None:
    assert fx.download_attachment("") is None


def test_download_attachment_uses_live_then_hist(monkeypatch) -> None:
    calls: list[str] = []

    class _Resp:
        status_code = 200
        content = b"<xbrl/>"

        def raise_for_status(self) -> None:
            ...

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return _Resp()

    monkeypatch.setattr(fx.requests, "get", fake_get)
    out = fx.download_attachment("ABC123.xml", polite_delay_sec=0.0)
    assert out == b"<xbrl/>"
    assert calls and "AttachLive" in calls[0]
