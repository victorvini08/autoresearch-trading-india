"""Quality screen for the Indian-equities universe.

The strategy ranks names by 12-1 momentum but, before selecting the top
decile, removes names that fail a basic quality screen — adapted from the
classical "Quality Minus Junk" (Asness, Frazzini, Pedersen 2019) and
"Profitability premium" (Novy-Marx 2013) literature, tightened for the
Indian-market context where mid-cap accounting risk is higher.

A name passes the quality screen iff (rule applied at the post-momentum-
rank step):

  1. Return on Equity (TTM) >= percentile cutoff of the candidate cohort
  2. Debt / Equity <= 2.0 (EXCEPT for FINANCIAL_SERVICES sector)
  3. Operating margin (TTM EBIT / Revenue) > 0

The screen reads pre-computed fundamentals from `storage/fundamentals.duckdb`,
populated by a later phase. When the table is missing the screen is a no-op
(returns all candidates) so the pipeline still functions; this is a
deliberate soft-degradation for v1 paper smoke-tests before fundamentals
ingest is wired up.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

from data.sectors import SectorAssignment

logger = logging.getLogger(__name__)

DEFAULT_ROE_PERCENTILE = 50
DEFAULT_DE_MAX_NONFIN = 2.0
DEFAULT_OPMARGIN_FLOOR = 0.0


@dataclass(frozen=True)
class FundamentalsRow:
    ticker: str
    as_of_date: date
    roe_ttm: float | None
    debt_to_equity: float | None
    op_margin_ttm: float | None
    is_financial: bool


@dataclass(frozen=True)
class ScreenResult:
    ticker: str
    passed: bool
    reasons: tuple[str, ...]


def load_fundamentals(
    fundamentals_db: Path,
    tickers: list[str],
    as_of_date: date,
) -> dict[str, FundamentalsRow]:
    """Read the most recent fundamentals row per ticker on or before `as_of_date`.

    Returns {} if the DB or `fundamentals_quarterly` table doesn't exist
    (soft-degrade — pipeline still functions, screen becomes a no-op).

    Accepts a str OR Path: loop-proposed strategies frequently pass the raw
    `self.p.fundamentals_db_path` string (a `str`), which previously crashed
    prepare.evaluate with "'str' object has no attribute 'exists'" and
    wasted the iteration (observed 2026-05-15). Coerce defensively.
    """
    fundamentals_db = Path(fundamentals_db)
    if not fundamentals_db.exists():
        logger.warning(
            "quality_screen: %s does not exist; screen is a no-op until "
            "fundamentals ingest is wired",
            fundamentals_db,
        )
        return {}
    conn = duckdb.connect(str(fundamentals_db), read_only=True)
    try:
        tbl = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'fundamentals_quarterly'"
        ).fetchone()
        if not tbl:
            logger.warning(
                "quality_screen: fundamentals_quarterly table missing; no-op"
            )
            return {}
        placeholders = ",".join("?" * len(tickers))
        rows = conn.execute(
            f"""
            WITH ranked AS (
              SELECT ticker, as_of_date, roe_ttm, debt_to_equity, op_margin_ttm,
                     ROW_NUMBER() OVER (
                       PARTITION BY ticker ORDER BY as_of_date DESC
                     ) AS rn
                FROM fundamentals_quarterly
               WHERE ticker IN ({placeholders})
                 AND as_of_date <= ?
            )
            SELECT ticker, as_of_date, roe_ttm, debt_to_equity, op_margin_ttm
              FROM ranked
             WHERE rn = 1
            """,
            (*tickers, as_of_date),
        ).fetchall()
    finally:
        conn.close()
    out: dict[str, FundamentalsRow] = {}
    for ticker, d, roe, de, opm in rows:
        out[ticker] = FundamentalsRow(
            ticker=ticker,
            as_of_date=d,
            roe_ttm=roe,
            debt_to_equity=de,
            op_margin_ttm=opm,
            is_financial=False,
        )
    return out


def apply_quality_screen(
    candidates: list[str],
    fundamentals: dict[str, FundamentalsRow],
    sector_map: dict[str, SectorAssignment] | None = None,
    *,
    roe_percentile: float = DEFAULT_ROE_PERCENTILE,
    de_max_nonfin: float = DEFAULT_DE_MAX_NONFIN,
    opmargin_floor: float = DEFAULT_OPMARGIN_FLOOR,
) -> tuple[list[str], dict[str, ScreenResult]]:
    """Apply the quality screen to `candidates`.

    Returns (passed_tickers, results). `passed_tickers` preserves the input
    order, filtered to only the names that passed all criteria.

    If `fundamentals` is empty, soft-degrade: return all candidates as passed
    with a 'no_fundamentals_data' reason logged for each.
    """
    results: dict[str, ScreenResult] = {}

    if not fundamentals:
        passed = list(candidates)
        for t in candidates:
            results[t] = ScreenResult(
                ticker=t,
                passed=True,
                reasons=("no_fundamentals_data",),
            )
        return passed, results

    roe_values = [
        fundamentals[t].roe_ttm
        for t in candidates
        if t in fundamentals and fundamentals[t].roe_ttm is not None
    ]
    if roe_values:
        roe_values_sorted = sorted(roe_values)
        idx = int(len(roe_values_sorted) * (roe_percentile / 100.0))
        idx = min(idx, len(roe_values_sorted) - 1)
        roe_cutoff = roe_values_sorted[idx]
    else:
        roe_cutoff = None

    passed_list: list[str] = []
    for ticker in candidates:
        fund = fundamentals.get(ticker)
        if fund is None:
            results[ticker] = ScreenResult(
                ticker=ticker,
                passed=False,
                reasons=("no_fundamentals_data",),
            )
            continue
        reasons: list[str] = []

        if fund.roe_ttm is None:
            reasons.append("roe_missing")
        elif roe_cutoff is not None and fund.roe_ttm < roe_cutoff:
            reasons.append("roe_below_pct")

        sa = sector_map.get(ticker) if sector_map else None
        is_fin = sa is not None and sa.sector == "FINANCIAL_SERVICES"
        if not is_fin:
            if fund.debt_to_equity is not None and fund.debt_to_equity > de_max_nonfin:
                reasons.append("de_too_high")
            if (
                fund.op_margin_ttm is not None
                and fund.op_margin_ttm <= opmargin_floor
            ):
                reasons.append("op_margin_non_positive")
        else:
            if fund.op_margin_ttm is not None and fund.op_margin_ttm <= opmargin_floor:
                reasons.append("nim_non_positive")

        passed = not reasons
        results[ticker] = ScreenResult(
            ticker=ticker,
            passed=passed,
            reasons=tuple(reasons),
        )
        if passed:
            passed_list.append(ticker)

    return passed_list, results


__all__ = [
    "FundamentalsRow",
    "ScreenResult",
    "load_fundamentals",
    "apply_quality_screen",
    "DEFAULT_ROE_PERCENTILE",
    "DEFAULT_DE_MAX_NONFIN",
    "DEFAULT_OPMARGIN_FLOOR",
]
