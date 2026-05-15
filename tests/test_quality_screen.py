"""Unit tests for `data.quality_screen`."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from data.quality_screen import (
    FundamentalsRow,
    apply_quality_screen,
    load_fundamentals,
)
from data.sectors import SectorAssignment


def _fund(ticker: str, roe: float, de: float, opm: float) -> FundamentalsRow:
    return FundamentalsRow(
        ticker=ticker,
        as_of_date=date(2026, 3, 31),
        roe_ttm=roe,
        debt_to_equity=de,
        op_margin_ttm=opm,
        is_financial=False,
    )


def test_soft_degrade_passes_all_when_fundamentals_empty() -> None:
    """When fundamentals db is missing we soft-pass everything with a reason."""
    passed, results = apply_quality_screen(
        candidates=["A", "B", "C"],
        fundamentals={},
        sector_map=None,
    )
    assert passed == ["A", "B", "C"]
    assert all(r.passed for r in results.values())
    assert all("no_fundamentals_data" in r.reasons for r in results.values())


def test_missing_fundamentals_db_does_not_warn(caplog, tmp_path) -> None:
    """Missing fundamentals DB is expected in v1 paper and must not spam logs."""
    missing = tmp_path / "fundamentals.duckdb"

    out = load_fundamentals(missing, ["A", "B"], date(2026, 5, 15))

    assert out == {}
    assert "quality_screen:" not in caplog.text


def test_excludes_high_de_non_financial() -> None:
    funds = {
        "GOOD": _fund("GOOD", roe=0.25, de=1.0, opm=0.20),
        "BAD": _fund("BAD", roe=0.25, de=4.0, opm=0.20),  # D/E > 2
    }
    passed, results = apply_quality_screen(
        candidates=["GOOD", "BAD"],
        fundamentals=funds,
        sector_map=None,
    )
    assert "GOOD" in passed
    assert "BAD" not in passed
    assert "de_too_high" in results["BAD"].reasons


def test_excludes_non_positive_op_margin() -> None:
    funds = {
        "GOOD": _fund("GOOD", roe=0.25, de=1.0, opm=0.10),
        "LOSS": _fund("LOSS", roe=0.25, de=1.0, opm=-0.05),  # OPM < 0
    }
    passed, _ = apply_quality_screen(
        candidates=["GOOD", "LOSS"],
        fundamentals=funds,
        sector_map=None,
    )
    assert "GOOD" in passed
    assert "LOSS" not in passed


def test_financial_skips_de_check() -> None:
    """Banks: D/E is meaningless; the screen must NOT exclude on D/E for financials."""
    sector_map = {
        "BANK": SectorAssignment("BANK", "FINANCIAL_SERVICES", "Banks"),
    }
    funds = {
        # D/E 8 would fail for non-financials; banks routinely have higher leverage
        "BANK": _fund("BANK", roe=0.18, de=8.0, opm=0.15),
    }
    passed, results = apply_quality_screen(
        candidates=["BANK"],
        fundamentals=funds,
        sector_map=sector_map,
    )
    # Pass if the financials-skip works (BANK is the only candidate, so percentile
    # cutoff = its own ROE, so ROE >= cutoff is True)
    assert "BANK" in passed
    assert "de_too_high" not in results["BANK"].reasons


def test_roe_percentile_cut_relative_to_candidates() -> None:
    funds = {
        "LOW_ROE": _fund("LOW_ROE", roe=0.05, de=0.5, opm=0.10),
        "HIGH_ROE": _fund("HIGH_ROE", roe=0.30, de=0.5, opm=0.10),
    }
    passed, results = apply_quality_screen(
        candidates=["LOW_ROE", "HIGH_ROE"],
        fundamentals=funds,
        sector_map=None,
        roe_percentile=50,
    )
    # With 2 candidates and 50pct cutoff (index = 1, value = HIGH_ROE), only
    # ROE >= 0.30 passes
    assert "HIGH_ROE" in passed
    assert "LOW_ROE" not in passed
    assert "roe_below_pct" in results["LOW_ROE"].reasons


def test_missing_ticker_is_failed() -> None:
    funds = {"A": _fund("A", roe=0.2, de=0.5, opm=0.10)}
    passed, results = apply_quality_screen(
        candidates=["A", "B"],
        fundamentals=funds,
    )
    assert passed == ["A"]
    assert "no_fundamentals_data" in results["B"].reasons
