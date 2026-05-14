"""Unit tests for `data.sectors`."""

from __future__ import annotations

from dataclasses import dataclass

from data.sectors import (
    CANONICAL_SECTORS,
    SectorAssignment,
    assign_sectors,
    canonicalise,
    enforce_sector_cap,
    sector_weights,
)


@dataclass
class _Row:
    ticker: str
    industry: str


def test_canonicalise_known() -> None:
    assert canonicalise("Banks") == "FINANCIAL_SERVICES"
    assert canonicalise("Information Technology") == "INFORMATION_TECHNOLOGY"
    assert canonicalise("IT - Software") == "INFORMATION_TECHNOLOGY"
    assert canonicalise("Pharmaceuticals") == "HEALTHCARE"
    assert canonicalise("Automobiles") == "AUTOMOBILE_AND_AUTO_COMPONENTS"
    assert canonicalise("Telecom") == "TELECOMMUNICATION"


def test_canonicalise_unknown_falls_through_to_other() -> None:
    assert canonicalise("Hypothetical Sector") == "OTHER"
    assert canonicalise("") == "OTHER"


def test_canonicalise_substring_match() -> None:
    """A long NSE label that contains a known alias should match the alias."""
    # NSE sometimes emits 'Realty / Real Estate' or 'Pharma & Healthcare'
    assert canonicalise("Realty / Real Estate") == "REALTY"


def test_assign_sectors_roundtrip() -> None:
    rows = [
        _Row(ticker="HDFCBANK", industry="Banks"),
        _Row(ticker="INFY", industry="IT - Software"),
        _Row(ticker="RELIANCE", industry="Oil Gas & Consumable Fuels"),
    ]
    mapping = assign_sectors(rows)
    assert mapping["HDFCBANK"].sector == "FINANCIAL_SERVICES"
    assert mapping["INFY"].sector == "INFORMATION_TECHNOLOGY"
    assert mapping["RELIANCE"].sector == "OIL_GAS_AND_CONSUMABLE_FUELS"
    assert mapping["HDFCBANK"].raw_nse_industry == "Banks"


def test_sector_weights_aggregates() -> None:
    sector_map = {
        "HDFCBANK": SectorAssignment("HDFCBANK", "FINANCIAL_SERVICES", "Banks"),
        "ICICIBANK": SectorAssignment("ICICIBANK", "FINANCIAL_SERVICES", "Banks"),
        "INFY": SectorAssignment("INFY", "INFORMATION_TECHNOLOGY", "IT"),
    }
    weights = sector_weights({"HDFCBANK": 0.20, "ICICIBANK": 0.10, "INFY": 0.15}, sector_map)
    assert abs(weights["FINANCIAL_SERVICES"] - 0.30) < 1e-9
    assert abs(weights["INFORMATION_TECHNOLOGY"] - 0.15) < 1e-9
    assert weights["OTHER"] == 0.0


def test_enforce_sector_cap_blocks_overrun() -> None:
    """If 3 of the top-ranked names are all in one sector, the cap should skip 2."""
    sector_map = {
        "BANK1": SectorAssignment("BANK1", "FINANCIAL_SERVICES", "Banks"),
        "BANK2": SectorAssignment("BANK2", "FINANCIAL_SERVICES", "Banks"),
        "BANK3": SectorAssignment("BANK3", "FINANCIAL_SERVICES", "Banks"),
        "TECH1": SectorAssignment("TECH1", "INFORMATION_TECHNOLOGY", "IT"),
        "PHARMA1": SectorAssignment("PHARMA1", "HEALTHCARE", "Pharma"),
    }
    # 5 candidates, top-3 are all banks; target 4 names at 25% each
    chosen = enforce_sector_cap(
        ranked_candidates=["BANK1", "BANK2", "BANK3", "TECH1", "PHARMA1"],
        target_fraction_each=0.25,
        sector_map=sector_map,
        max_sector_fraction=0.25,
        n_target=4,
    )
    # 0.25 (BANK1) + 0.25 (BANK2)=0.50 > 0.25 cap → BANK2 + BANK3 skipped
    # We pick: BANK1, TECH1, PHARMA1 → only 3 chosen; n_target=4 unmet
    assert "BANK1" in chosen
    assert "TECH1" in chosen
    assert "PHARMA1" in chosen
    assert "BANK2" not in chosen
    assert "BANK3" not in chosen


def test_enforce_sector_cap_unmapped_treated_as_other() -> None:
    """Tickers without a sector entry fall into 'OTHER' and still consume the cap."""
    sector_map = {
        "KNOWN": SectorAssignment("KNOWN", "INFORMATION_TECHNOLOGY", "IT"),
    }
    chosen = enforce_sector_cap(
        ranked_candidates=["UNMAPPED_1", "UNMAPPED_2", "KNOWN"],
        target_fraction_each=0.20,
        sector_map=sector_map,
        max_sector_fraction=0.25,
        n_target=3,
    )
    # OTHER bucket can hold 0.20 only (one name) before cap binds (0.40 > 0.25)
    assert "UNMAPPED_1" in chosen
    assert "UNMAPPED_2" not in chosen
    assert "KNOWN" in chosen


def test_canonical_sectors_is_tuple() -> None:
    assert isinstance(CANONICAL_SECTORS, tuple)
    assert "FINANCIAL_SERVICES" in CANONICAL_SECTORS
    assert "OTHER" in CANONICAL_SECTORS
