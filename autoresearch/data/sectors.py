"""NSE sector classification used for the 25% sector-cap risk control.

NSE publishes a sector ("Industry") for every Nifty 500 constituent in its
constituent CSV. We standardise those into a canonical list of buckets so the
strategy's sector-cap logic and the autoresearch loop's regime reasoning have
a stable vocabulary across reconstitutions.

The canonical buckets below are the ones NSE Indices actually uses (the column
labelled "Industry" in the Nifty 500 / Nifty 100 / Nifty Midcap 150 CSVs).
A name's bucket is whatever NSE assigns; if NSE omits the field, we tag it
'OTHER' and the sector cap treats 'OTHER' like any other bucket (so the cap
still binds, just over a coarser pool).

Concentration note (Q1 2026): top-5 Nifty 100 weights ≈ 24% of the index;
financials (Banks + Financial Services) are 35-38% of the broad index. The
25% sector cap is calibrated against this empirical concentration. Reducing
it tighter risks producing portfolios that can't be filled; loosening it
defeats the cap.
"""

from __future__ import annotations

from dataclasses import dataclass

# Canonical sector buckets. The order doesn't matter for the logic; we keep
# it alphabetical for readability and stable display in dashboards.
CANONICAL_SECTORS: tuple[str, ...] = (
    "AUTOMOBILE_AND_AUTO_COMPONENTS",
    "CAPITAL_GOODS",
    "CEMENT_AND_CEMENT_PRODUCTS",
    "CHEMICALS",
    "CONSTRUCTION",
    "CONSTRUCTION_MATERIALS",
    "CONSUMER_DURABLES",
    "CONSUMER_SERVICES",
    "DIVERSIFIED",
    "FAST_MOVING_CONSUMER_GOODS",
    "FINANCIAL_SERVICES",
    "FOREST_MATERIALS",
    "HEALTHCARE",
    "INFORMATION_TECHNOLOGY",
    "MEDIA_ENTERTAINMENT_AND_PUBLICATION",
    "METALS_AND_MINING",
    "OIL_GAS_AND_CONSUMABLE_FUELS",
    "POWER",
    "REALTY",
    "SERVICES",
    "TELECOMMUNICATION",
    "TEXTILES",
    "OTHER",
)

# NSE writes sector names with various casings / hyphens / ampersands. The map
# normalises common variants to our canonical bucket. Anything that doesn't
# match falls through to 'OTHER'.
_NSE_ALIASES: dict[str, str] = {
    "automobile and auto components": "AUTOMOBILE_AND_AUTO_COMPONENTS",
    "automobile & auto components": "AUTOMOBILE_AND_AUTO_COMPONENTS",
    "automobiles": "AUTOMOBILE_AND_AUTO_COMPONENTS",
    "auto components": "AUTOMOBILE_AND_AUTO_COMPONENTS",
    "capital goods": "CAPITAL_GOODS",
    "industrials": "CAPITAL_GOODS",
    "cement & cement products": "CEMENT_AND_CEMENT_PRODUCTS",
    "cement and cement products": "CEMENT_AND_CEMENT_PRODUCTS",
    "cement": "CEMENT_AND_CEMENT_PRODUCTS",
    "chemicals": "CHEMICALS",
    "construction": "CONSTRUCTION",
    "construction materials": "CONSTRUCTION_MATERIALS",
    "consumer durables": "CONSUMER_DURABLES",
    "consumer services": "CONSUMER_SERVICES",
    "diversified": "DIVERSIFIED",
    "fast moving consumer goods": "FAST_MOVING_CONSUMER_GOODS",
    "fmcg": "FAST_MOVING_CONSUMER_GOODS",
    "financial services": "FINANCIAL_SERVICES",
    "banks": "FINANCIAL_SERVICES",
    "banking": "FINANCIAL_SERVICES",
    "nbfc": "FINANCIAL_SERVICES",
    "forest materials": "FOREST_MATERIALS",
    "healthcare": "HEALTHCARE",
    "pharmaceuticals": "HEALTHCARE",
    "hospitals": "HEALTHCARE",
    "information technology": "INFORMATION_TECHNOLOGY",
    "it": "INFORMATION_TECHNOLOGY",
    "it - software": "INFORMATION_TECHNOLOGY",
    "it - services": "INFORMATION_TECHNOLOGY",
    "media entertainment & publication": "MEDIA_ENTERTAINMENT_AND_PUBLICATION",
    "media entertainment and publication": "MEDIA_ENTERTAINMENT_AND_PUBLICATION",
    "media": "MEDIA_ENTERTAINMENT_AND_PUBLICATION",
    "metals & mining": "METALS_AND_MINING",
    "metals and mining": "METALS_AND_MINING",
    "metals": "METALS_AND_MINING",
    "mining": "METALS_AND_MINING",
    "oil gas & consumable fuels": "OIL_GAS_AND_CONSUMABLE_FUELS",
    "oil, gas & consumable fuels": "OIL_GAS_AND_CONSUMABLE_FUELS",
    "oil and gas": "OIL_GAS_AND_CONSUMABLE_FUELS",
    "energy": "OIL_GAS_AND_CONSUMABLE_FUELS",
    "power": "POWER",
    "realty": "REALTY",
    "real estate": "REALTY",
    "services": "SERVICES",
    "telecommunication": "TELECOMMUNICATION",
    "telecom": "TELECOMMUNICATION",
    "textiles": "TEXTILES",
}


@dataclass(frozen=True)
class SectorAssignment:
    ticker: str
    sector: str
    raw_nse_industry: str


def canonicalise(nse_industry: str) -> str:
    """Map any NSE 'Industry' string to one of CANONICAL_SECTORS.

    Empty / unknown values map to 'OTHER'.
    """
    if not nse_industry:
        return "OTHER"
    key = nse_industry.strip().lower()
    if key in _NSE_ALIASES:
        return _NSE_ALIASES[key]
    for alias, bucket in _NSE_ALIASES.items():
        if alias in key:
            return bucket
    return "OTHER"


def assign_sectors(universe_rows: list) -> dict[str, SectorAssignment]:
    """Build {ticker: SectorAssignment} from a list of UniverseRow objects.

    Accepts duck-typed objects with `.ticker` and `.industry` attributes.
    """
    out: dict[str, SectorAssignment] = {}
    for row in universe_rows:
        raw = getattr(row, "industry", "") or ""
        sector = canonicalise(raw)
        out[row.ticker] = SectorAssignment(
            ticker=row.ticker,
            sector=sector,
            raw_nse_industry=raw,
        )
    return out


def sector_weights(
    target_fractions: dict[str, float],
    sector_map: dict[str, SectorAssignment],
) -> dict[str, float]:
    """Aggregate position fractions by sector.

    Returns {sector: total_fraction}. Tickers without a sector mapping fall
    into 'OTHER'. Used by the sector-cap risk check.
    """
    out: dict[str, float] = dict.fromkeys(CANONICAL_SECTORS, 0.0)
    for ticker, frac in target_fractions.items():
        sa = sector_map.get(ticker)
        bucket = sa.sector if sa else "OTHER"
        out[bucket] = out.get(bucket, 0.0) + frac
    return out


def enforce_sector_cap(
    ranked_candidates: list[str],
    target_fraction_each: float,
    sector_map: dict[str, SectorAssignment],
    *,
    max_sector_fraction: float = 0.25,
    n_target: int,
) -> list[str]:
    """Pick the next `n_target` names from `ranked_candidates`, skipping any
    that would push their sector above `max_sector_fraction`.

    `ranked_candidates` is in priority order (best signal first).
    `target_fraction_each` is the fraction each selected name will receive
    (e.g. 1/n_target for equal-weight).

    Returns the chosen tickers (in priority order). Will pick fewer than
    `n_target` if the cap binds and we exhaust the candidate list.
    """
    chosen: list[str] = []
    sector_totals: dict[str, float] = dict.fromkeys(CANONICAL_SECTORS, 0.0)
    for ticker in ranked_candidates:
        if len(chosen) >= n_target:
            break
        sa = sector_map.get(ticker)
        bucket = sa.sector if sa else "OTHER"
        prospective = sector_totals.get(bucket, 0.0) + target_fraction_each
        if prospective > max_sector_fraction + 1e-9:
            continue
        sector_totals[bucket] = prospective
        chosen.append(ticker)
    return chosen


__all__ = [
    "CANONICAL_SECTORS",
    "SectorAssignment",
    "canonicalise",
    "assign_sectors",
    "sector_weights",
    "enforce_sector_cap",
]
