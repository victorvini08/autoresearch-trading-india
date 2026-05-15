"""Unit tests for data.bse — parsing + scrip-code resolution (no network)."""

from __future__ import annotations

from datetime import date

from data.bse import (
    parse_announcements,
    resolve_scrip_code,
)

_SAMPLE_PAYLOAD = {
    "Table": [
        {
            "NEWSID": "abc-1",
            "SCRIP_CD": 500325,
            "NEWSSUB": "Board Meeting Intimation for Quarterly Results",
            "NEWS_DT": "2021-01-22T17:30:00.03",
            "DT_TM": "2021-01-22T17:30:00.03",
            "HEADLINE": "RIL to consider Q3 FY21 results on 22 Jan 2021.",
            "ATTACHMENTNAME": "xyz.pdf",
        },
        {
            "NEWSID": "abc-2",
            "SCRIP_CD": 500325,
            "NEWSSUB": "Compliances-Reg. 39(3)",
            "NEWS_DT": "2021-01-29T18:35:33.03",
            "HEADLINE": "Loss of certificate notice.",
            "ATTACHMENTNAME": "",
        },
        {
            "NEWSID": "bad",
            "SCRIP_CD": 500325,
            "NEWSSUB": "no date row",
            "NEWS_DT": "",
            "HEADLINE": "should be skipped (unparseable date)",
        },
    ],
    "Table1": [{"TotalPageCnt": "2"}],
}


def test_parse_announcements_basic() -> None:
    anns = parse_announcements(_SAMPLE_PAYLOAD, "500325", "RELIANCE")
    # third row has no date → skipped
    assert len(anns) == 2
    a0 = anns[0]
    assert a0.scrip_code == "500325"
    assert a0.nse_symbol == "RELIANCE"
    assert a0.dt == date(2021, 1, 22)
    assert "Quarterly Results" in a0.subject
    assert a0.news_id == "abc-1"
    assert a0.attachment == "xyz.pdf"


def test_parse_announcements_handles_missing_attachment() -> None:
    anns = parse_announcements(_SAMPLE_PAYLOAD, "500325", "RELIANCE")
    assert anns[1].attachment == ""
    assert anns[1].dt == date(2021, 1, 29)


def test_parse_announcements_empty_table() -> None:
    assert parse_announcements({"Table": []}, "1", None) == []
    assert parse_announcements({}, "1", None) == []


def test_resolve_scrip_code_isin_first() -> None:
    smap = {
        "by_isin": {"INE002A01018": "500325"},
        "by_symbol": {"RELIANCE": "999999"},  # deliberately wrong to prove ISIN wins
    }
    assert resolve_scrip_code(smap, isin="INE002A01018", nse_symbol="RELIANCE") == "500325"


def test_resolve_scrip_code_symbol_fallback() -> None:
    smap = {"by_isin": {}, "by_symbol": {"INFY": "500209"}}
    assert resolve_scrip_code(smap, isin="UNKNOWN", nse_symbol="INFY") == "500209"
    assert resolve_scrip_code(smap, isin=None, nse_symbol="infy") == "500209"  # case-insensitive


def test_resolve_scrip_code_unresolved() -> None:
    smap = {"by_isin": {}, "by_symbol": {}}
    assert resolve_scrip_code(smap, isin="X", nse_symbol="Y") is None
    assert resolve_scrip_code(smap) is None
