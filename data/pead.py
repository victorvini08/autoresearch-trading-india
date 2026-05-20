"""Point-in-time PEAD accessor.

Theory-pinned constants (NOT strategy hyperparameters — kept here, not on
strategy.params, so prepare.count_hyperparameters is unchanged; same
convention as strategy._structural_ma_window):

  DRIFT_WINDOW_TD : PEAD drift horizon ~64 trading days (literature) → 60.
  SUE_BLOCK       : standard PEAD decile-ish boundary, |SUE| ~ 1σ.
  SUE_SEVERE      : sever a held name on a ~2σ negative miss.

The quality conditioner reuses data.quality_screen's ROE / D-E /
op-margin thresholds (single source of truth) to tighten the block cut
for weak fundamentals and loosen it for strong ones.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import duckdb

from data.quality_screen import load_fundamentals

logger = logging.getLogger(__name__)

DRIFT_WINDOW_TD = 60
_DRIFT_CAL_DAYS = 90  # ~60 trading days, calendar-approx upper bound
SUE_BLOCK = 1.0
SUE_SEVERE = 2.0


def _quality_cut(ticker: str, today: date, fundamentals_db: Path) -> float:
    """Tighten the block threshold for weak fundamentals, loosen for strong."""
    try:
        funds = load_fundamentals(fundamentals_db, [ticker], today)
    except Exception:  # noqa: BLE001 — accessor must never break the strategy
        funds = {}
    f = funds.get(ticker)
    if f is None:
        return SUE_BLOCK
    weak = (
        (f.roe_ttm is not None and f.roe_ttm < 0.0)
        or (f.debt_to_equity is not None and f.debt_to_equity > 2.0)
        or (f.op_margin_ttm is not None and f.op_margin_ttm <= 0.0)
    )
    strong = (
        (f.roe_ttm or 0.0) > 0.15
        and (f.debt_to_equity is None or f.debt_to_equity < 0.5)
        and (f.op_margin_ttm or 0.0) > 0.10
    )
    if weak:
        return 0.5
    if strong:
        return 1.5
    return SUE_BLOCK


def pead_signal(
    ticker: str,
    today: date,
    *,
    earnings_db: Path,
    fundamentals_db: Path,
) -> dict | None:
    """Most recent in-drift-window quality-conditioned surprise verdict.

    Returns {'sue', 'days_since', 'block', 'sever'} or None when there is
    no usable signal (soft-degrade — the strategy treats None as "no
    signal", never as a block).
    """
    earnings_db = Path(earnings_db)
    if not earnings_db.exists():
        return None
    conn = duckdb.connect(str(earnings_db), read_only=True)
    try:
        row = conn.execute(
            """
            SELECT announcement_date, sue
              FROM earnings_calendar
             WHERE ticker = ? AND sue IS NOT NULL
               AND announcement_date <= ?
               AND announcement_date >= ?
             ORDER BY announcement_date DESC
             LIMIT 1
            """,
            (ticker, today, today - timedelta(days=_DRIFT_CAL_DAYS)),
        ).fetchone()
    except Exception:  # noqa: BLE001 — accessor must never break the strategy
        return None
    finally:
        conn.close()
    if row is None or row[1] is None:
        return None
    ad, sue = row
    sue = float(sue)
    cut = _quality_cut(ticker, today, Path(fundamentals_db))
    return {
        "sue": sue,
        "days_since": (today - ad).days,
        "block": sue <= -cut,
        "sever": sue <= -SUE_SEVERE,
    }


__all__ = [
    "DRIFT_WINDOW_TD",
    "SUE_BLOCK",
    "SUE_SEVERE",
    "pead_signal",
]
