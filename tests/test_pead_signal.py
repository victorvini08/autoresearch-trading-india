"""Unit tests for SUE computation and the PEAD PIT accessor."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from data.ingest_earnings import compute_sue_from_fundamentals


def _seed_fundamentals(
    p: Path, eps_series: list[tuple[str, str, float]]
) -> None:
    c = duckdb.connect(str(p))
    c.execute(
        "CREATE TABLE fundamentals_quarterly "
        "(ticker VARCHAR, period_end_date DATE, as_of_date DATE, "
        " eps_basic DOUBLE)"
    )
    for pe, ao, eps in eps_series:
        c.execute(
            "INSERT INTO fundamentals_quarterly "
            "(ticker, period_end_date, as_of_date, eps_basic) "
            "VALUES ('Z', ?, ?, ?)",
            (pe, ao, eps),
        )
    c.close()


def test_sue_seasonal_random_walk(tmp_path) -> None:
    fdb = tmp_path / "f.duckdb"
    edb = tmp_path / "e.duckdb"
    rows = []
    for i, eps in enumerate([5, 6, 4, 7, 6, 7, 5, 9, 14]):
        y = 2023 + (i // 4)
        m = [3, 6, 9, 12][i % 4]
        rows.append((f"{y}-{m:02d}-28", f"{y}-{m:02d}-28", float(eps)))
    _seed_fundamentals(fdb, rows)
    n = compute_sue_from_fundamentals(fdb, edb)
    assert n >= 1
    c = duckdb.connect(str(edb), read_only=True)
    sue = c.execute(
        "SELECT sue FROM earnings_calendar WHERE ticker='Z' "
        "ORDER BY announcement_date DESC LIMIT 1"
    ).fetchone()[0]
    c.close()
    assert sue is not None and sue > 0  # 14 vs prior-year 7 → positive


def test_sue_rejects_exceptional_item_and_clips(tmp_path) -> None:
    """A one-off exceptional-item EPS spike (e.g. discontinued-ops /
    split artifact: ~1.0 normal, one quarter at 120) must NOT produce a
    monster SUE. The spike quarter emits no SUE (soft-degrade), the
    seasonal-RW denominator is not contaminated by it, and every emitted
    |SUE| is within the robust clip band."""
    from data.ingest_earnings import _SUE_CLIP

    fdb = tmp_path / "f.duckdb"
    edb = tmp_path / "e.duckdb"
    eps = [1.4, 1.2, 0.7, 1.0, 1.1, 1.2, 1.1, 1.0, 120.7, 1.9, 1.0, 1.1]
    rows = []
    for i, v in enumerate(eps):
        y = 2022 + (i // 4)
        m = [3, 6, 9, 12][i % 4]
        rows.append((f"{y}-{m:02d}-28", f"{y}-{m:02d}-28", float(v)))
    _seed_fundamentals(fdb, rows)
    compute_sue_from_fundamentals(fdb, edb)
    c = duckdb.connect(str(edb), read_only=True)
    got = c.execute(
        "SELECT announcement_date, sue FROM earnings_calendar "
        "WHERE ticker='Z' AND sue IS NOT NULL ORDER BY announcement_date"
    ).fetchall()
    c.close()
    # No artifact: nothing anywhere near the ~1300σ the naive estimator
    # produced for this series; everything inside the robust clip.
    assert got, "expected at least one clean SUE row"
    for _ad, s in got:
        assert abs(s) <= _SUE_CLIP + 1e-9
    assert max(abs(s) for _a, s in got) < _SUE_CLIP  # no row even hit clip


def test_sue_preserves_genuine_large_surprise(tmp_path) -> None:
    """A real, non-pathological doubling of EPS vs the prior-year quarter
    stays a positive signal (the PEAD signal we WANT) — the exceptional-
    item guard must not nuke genuine large beats."""
    fdb = tmp_path / "f.duckdb"
    edb = tmp_path / "e.duckdb"
    rows = []
    for i, v in enumerate([5, 6, 4, 7, 6, 7, 5, 9, 14]):
        y = 2023 + (i // 4)
        m = [3, 6, 9, 12][i % 4]
        rows.append((f"{y}-{m:02d}-28", f"{y}-{m:02d}-28", float(v)))
    _seed_fundamentals(fdb, rows)
    n = compute_sue_from_fundamentals(fdb, edb)
    assert n >= 1
    c = duckdb.connect(str(edb), read_only=True)
    sue = c.execute(
        "SELECT sue FROM earnings_calendar WHERE ticker='Z' "
        "AND sue IS NOT NULL ORDER BY announcement_date DESC LIMIT 1"
    ).fetchone()[0]
    c.close()
    assert sue is not None and sue > 0


def _seed_earn(p: Path, ticker: str, ad: date, sue: float) -> None:
    c = duckdb.connect(str(p))
    c.execute(
        "CREATE TABLE IF NOT EXISTS earnings_calendar "
        "(ticker VARCHAR, announcement_date DATE, title VARCHAR, "
        " source VARCHAR, eps_estimate DOUBLE, eps_reported DOUBLE, "
        " surprise_pct DOUBLE, period_end_date DATE, "
        " surprise_eps DOUBLE, sue DOUBLE, expectation_basis VARCHAR)"
    )
    c.execute(
        "INSERT INTO earnings_calendar (ticker, announcement_date, sue) "
        "VALUES (?,?,?)",
        (ticker, ad, sue),
    )
    c.close()


def test_negative_surprise_blocks(tmp_path) -> None:
    from data.pead import pead_signal

    edb = tmp_path / "e.duckdb"
    _seed_earn(edb, "ACME", date(2025, 2, 10), -1.4)
    sig = pead_signal(
        "ACME", date(2025, 2, 20),
        earnings_db=edb, fundamentals_db=tmp_path / "missing.db",
    )
    assert sig is not None
    assert sig["block"] is True and sig["sever"] is False


def test_positive_surprise_no_block(tmp_path) -> None:
    from data.pead import pead_signal

    edb = tmp_path / "e.duckdb"
    _seed_earn(edb, "ACME", date(2025, 2, 10), 2.0)
    sig = pead_signal(
        "ACME", date(2025, 2, 20),
        earnings_db=edb, fundamentals_db=tmp_path / "x.db",
    )
    assert sig["block"] is False


def test_stale_surprise_soft_degrades(tmp_path) -> None:
    from data.pead import pead_signal

    edb = tmp_path / "e.duckdb"
    _seed_earn(edb, "ACME", date(2024, 1, 1), -3.0)
    sig = pead_signal(
        "ACME", date(2025, 2, 20),
        earnings_db=edb, fundamentals_db=tmp_path / "x.db",
    )
    assert sig is None  # outside drift window → no signal


def test_no_earnings_db_returns_none(tmp_path) -> None:
    from data.pead import pead_signal

    assert (
        pead_signal(
            "ACME", date(2025, 2, 20),
            earnings_db=tmp_path / "nope.db",
            fundamentals_db=tmp_path / "x.db",
        )
        is None
    )


def test_severe_negative_sets_sever(tmp_path) -> None:
    from data.pead import pead_signal

    edb = tmp_path / "e.duckdb"
    _seed_earn(edb, "ACME", date(2025, 2, 10), -2.5)
    sig = pead_signal(
        "ACME", date(2025, 2, 20),
        earnings_db=edb, fundamentals_db=tmp_path / "x.db",
    )
    assert sig["block"] is True and sig["sever"] is True
