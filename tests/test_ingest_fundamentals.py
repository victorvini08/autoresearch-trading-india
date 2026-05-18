"""Unit tests for data.ingest_fundamentals."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

import data.ingest_fundamentals as ingf
from data.fundamentals_xbrl import XbrlFacts
from data.ingest_fundamentals import (
    QuarterFacts,
    coverage_report,
    derive_ttm,
)
from data.quality_screen import load_fundamentals


def _q(pe: str, rev, ebit, pat, eq, debt) -> QuarterFacts:
    return QuarterFacts(
        ticker="X",
        period_end=date.fromisoformat(pe),
        broadcast_date=date.fromisoformat(pe),
        facts=XbrlFacts(
            rev, ebit, None, pat, None, None, eq, debt,
            date.fromisoformat(pe), True,
        ),
    )


def test_ttm_ratios() -> None:
    qs = [
        _q("2024-03-31", 100, 20, 10, 500, 250),
        _q("2024-06-30", 110, 22, 11, 510, 250),
        _q("2024-09-30", 120, 24, 12, 520, 260),
        _q("2024-12-31", 130, 26, 13, 540, 270),
    ]
    r = derive_ttm(qs)
    assert round(r.op_margin_ttm, 4) == round(92 / 460, 4)
    assert round(r.roe_ttm, 4) == round(46 / 540, 4)
    assert round(r.debt_to_equity, 4) == round(270 / 540, 4)


def test_ttm_missing_inputs_yield_none() -> None:
    qs = [_q("2024-12-31", None, None, 13, 0, 270)]
    r = derive_ttm(qs)
    assert r.op_margin_ttm is None
    assert r.roe_ttm is None  # equity 0
    assert r.debt_to_equity is None


def test_ingest_writes_pit_rows_and_quarantines(tmp_path, monkeypatch) -> None:
    fdb = tmp_path / "fundamentals.duckdb"

    monkeypatch.setattr(ingf, "_pit_universe", lambda *_: {"ACME": "IN0ACME"})
    monkeypatch.setattr(ingf, "_scrip_for_isin", lambda *_: "500001")
    monkeypatch.setattr(ingf, "build_scrip_map", lambda *a, **k: {})
    monkeypatch.setattr(ingf, "_is_financial", lambda *_: False)

    good = XbrlFacts(100, 20, 18, 12, 5.0, 4.9, 600, 300,
                      date(2024, 12, 31), True)
    monkeypatch.setattr(
        ingf, "_fetch_result_filings",
        lambda scrip, sym, s, e: [
            ingf.RawFiling("ACME", date(2025, 2, 12),
                           date(2024, 12, 31), good),
            ingf.RawFiling("ACME", date(2024, 1, 1),  # before period_end
                           date(2024, 12, 31), good),
        ],
    )

    n = ingf.ingest_fundamentals(
        universe_db=Path("ignored"), fundamentals_db=fdb,
        start=date(2024, 1, 1), end=date(2025, 6, 30),
    )
    assert n == 1  # the look-ahead row quarantined

    rows = load_fundamentals(fdb, ["ACME"], date(2025, 3, 1))
    assert "ACME" in rows
    assert rows["ACME"].as_of_date == date(2025, 2, 12)  # broadcast, not Q-end
    assert load_fundamentals(fdb, ["ACME"], date(2025, 1, 1)) == {}


def test_clean_db_passes_and_leak_trips(tmp_path) -> None:
    from data.ingest_fundamentals import LookaheadError, assert_no_lookahead

    p = tmp_path / "f.duckdb"
    c = duckdb.connect(str(p))
    c.execute(
        "CREATE TABLE fundamentals_quarterly "
        "(ticker VARCHAR, period_end_date DATE, as_of_date DATE)"
    )
    c.execute(
        "INSERT INTO fundamentals_quarterly VALUES "
        "('A', DATE '2024-12-31', DATE '2025-02-10')"
    )
    c.close()
    assert_no_lookahead(p)  # clean → no raise

    c = duckdb.connect(str(p))
    c.execute(
        "INSERT INTO fundamentals_quarterly VALUES "
        "('B', DATE '2024-12-31', DATE '2024-06-01')"
    )
    c.close()
    import pytest

    with pytest.raises(LookaheadError):
        assert_no_lookahead(p)


def test_coverage_report(tmp_path) -> None:
    p = tmp_path / "f.duckdb"
    c = duckdb.connect(str(p))
    c.execute(
        "CREATE TABLE fundamentals_quarterly "
        "(ticker VARCHAR, period_end_date DATE, as_of_date DATE)"
    )
    c.execute(
        "INSERT INTO fundamentals_quarterly VALUES "
        "('A', DATE '2024-12-31', DATE '2025-02-12')"
    )
    c.close()
    rep = coverage_report(p)
    assert rep["by_year"][2025] == 1
    assert rep["lag_buckets"]["20-50d"] == 1


def test_snapshot_live_stamps_capture_date(tmp_path, monkeypatch) -> None:
    fdb = tmp_path / "f.duckdb"
    monkeypatch.setattr(ingf, "_pit_universe", lambda *_: {"ACME": "IN0ACME"})
    monkeypatch.setattr(ingf, "_scrip_for_isin", lambda *_: "500001")
    monkeypatch.setattr(ingf, "build_scrip_map", lambda *a, **k: {})
    monkeypatch.setattr(ingf, "_is_financial", lambda *_: False)
    fx = XbrlFacts(100, 20, 18, 12, 5.0, 4.9, 600, 300,
                   date(2024, 12, 31), True)
    monkeypatch.setattr(
        ingf, "_fetch_result_filings",
        lambda *_: [ingf.RawFiling("ACME", None, date(2024, 12, 31), fx)],
    )
    n = ingf.snapshot_live(Path("x"), fdb, on_date=date(2025, 2, 12))
    assert n == 1
    c = duckdb.connect(str(fdb), read_only=True)
    ao = c.execute(
        "SELECT as_of_date FROM fundamentals_quarterly"
    ).fetchone()[0]
    c.close()
    assert ao == date(2025, 2, 12)  # capture date, not SEBI fallback
