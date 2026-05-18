"""PIT-clean fundamentals pipeline → storage/fundamentals.duckdb.

Source: NSE ``corporates-financial-results`` (see data.fundamentals_xbrl).
``as_of_date`` is ALWAYS the NSE ``broadCastDate`` (when the market
learned the number), never the period-end. Spec
docs/superpowers/specs/2026-05-18-pit-fundamentals-pead-signal-design.md
§3, §4.

Quarterly results XBRL is P&L-centric: EPS/revenue/PBT/PAT are present
(SUE works); net worth & borrowings usually are not, so roe_ttm /
op_margin_ttm are often None and debt_to_equity falls back to the
filing's own reported DebtEquityRatio when available. The PEAD gate
soft-degrades on missing conditioner fields by design.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import duckdb

from data.fundamentals_xbrl import (
    XbrlFacts,
    _nse_session,
    download_xbrl,
    fetch_nse_results,
    parse_xbrl_facts,
)
from data.sectors import assign_sectors
from data.universe import load_universe, snapshot_dates

logger = logging.getLogger(__name__)

DEFAULT_FUNDAMENTALS_DB = Path("storage/fundamentals.duckdb")
_PIT_BAND_DAYS = 75


@dataclass(frozen=True)
class QuarterFacts:
    ticker: str
    period_end: date
    broadcast_date: date
    facts: XbrlFacts


@dataclass(frozen=True)
class DerivedRatios:
    roe_ttm: float | None
    debt_to_equity: float | None
    op_margin_ttm: float | None


@dataclass(frozen=True)
class RawFiling:
    ticker: str
    broadcast_date: date | None
    period_end: date
    facts: XbrlFacts


class LookaheadError(RuntimeError):
    """Raised when fundamentals_quarterly contains a look-ahead row."""


# ──────────────────────────────────────────────────────────────────────
# Pure ratio derivation
# ──────────────────────────────────────────────────────────────────────


def _sum(vals: list[float | None]) -> float | None:
    present = [v for v in vals if v is not None]
    return sum(present) if vals and len(present) == len(vals) else None


def derive_ttm(quarters: list[QuarterFacts]) -> DerivedRatios:
    """quarters ascending by period_end, length 1..4 (trailing window).

    op_margin / roe need EBIT / net-worth which quarterly results XBRL
    usually lacks → None then. debt_to_equity prefers a real
    debt/equity, else the filing's own reported DebtEquityRatio.
    """
    qs = sorted(quarters, key=lambda q: q.period_end)[-4:]
    latest = qs[-1].facts
    rev = _sum([q.facts.revenue for q in qs])
    ebit = _sum([q.facts.ebit for q in qs])
    pat = _sum([q.facts.pat for q in qs])
    eq = latest.equity
    debt = latest.debt

    op_margin = (
        ebit / rev if (ebit is not None and rev not in (None, 0)) else None
    )
    roe = (
        pat / eq
        if (pat is not None and eq not in (None, 0) and eq and eq > 0)
        else None
    )
    if debt is not None and eq not in (None, 0) and eq and eq > 0:
        de: float | None = debt / eq
    else:
        de = latest.debt_equity_ratio  # filing's own reported ratio
    return DerivedRatios(roe_ttm=roe, debt_to_equity=de, op_margin_ttm=op_margin)


# ──────────────────────────────────────────────────────────────────────
# Source helpers (monkeypatched in tests)
# ──────────────────────────────────────────────────────────────────────


def _sebi_fallback(period_end: date) -> date:
    days = 60 if (period_end.month == 3 and period_end.day == 31) else 45
    return period_end + timedelta(days=days)


def _pit_universe(
    universe_db: Path, start: date, end: date
) -> dict[str, str]:
    """Union of {ticker: isin} across every PIT snapshot in [start, end]."""
    out: dict[str, str] = {}
    for snap in snapshot_dates(universe_db):
        if snap < start or snap > end:
            continue
        for row in load_universe(universe_db, snap):
            out.setdefault(row.ticker, row.isin)
    return out


def _is_financial(ticker: str, industry: str) -> bool:
    row = type("R", (), {"ticker": ticker, "industry": industry})()
    sa = assign_sectors([row])
    return ticker in sa and sa[ticker].sector == "FINANCIAL_SERVICES"


# One NSE session reused across ALL symbols + XBRL downloads in a run
# (the per-symbol fresh-session bootstrap was the dominant slowdown and a
# throttle magnet). Created lazily on first real fetch; tests monkeypatch
# _fetch_result_filings so no session/network is created under pytest.
_SHARED: dict = {}
_INTER_SYMBOL_DELAY = 0.4  # polite gap between symbols (real network only)


def _shared_session():
    s = _SHARED.get("s")
    if s is None:
        s = _SHARED["s"] = _nse_session()
    return s


def _fetch_result_filings(
    ticker: str, start: date, end: date, *, session=None
) -> list[RawFiling]:
    """Quarterly result filings for `ticker` whose broadcast date is in
    [start, end], via NSE's structured results API + its XBRL URL. Reuses
    a single bootstrapped session across the whole run."""
    s = session or _shared_session()
    out: list[RawFiling] = []
    for nr in fetch_nse_results(ticker, session=s):
        if nr.broadcast_date < start or nr.broadcast_date > end:
            continue
        blob = download_xbrl(nr.xbrl_url, session=s)
        if not blob:
            continue
        facts = parse_xbrl_facts(blob, nr.period_end)
        if facts is None:
            continue
        out.append(
            RawFiling(ticker, nr.broadcast_date, nr.period_end, facts)
        )
    time.sleep(_INTER_SYMBOL_DELAY)  # politeness; skipped under mocked tests
    return out


# ──────────────────────────────────────────────────────────────────────
# Schema + write
# ──────────────────────────────────────────────────────────────────────

_COLS = (
    "ticker, period_end_date, as_of_date, broadcast_date, "
    "roe_ttm, debt_to_equity, op_margin_ttm, is_financial, "
    "eps_basic, eps_diluted, revenue, ebit, pat, equity, debt, "
    "is_consolidated, source"
)


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
            ticker VARCHAR NOT NULL,
            period_end_date DATE NOT NULL,
            as_of_date DATE NOT NULL,
            broadcast_date DATE,
            roe_ttm DOUBLE, debt_to_equity DOUBLE, op_margin_ttm DOUBLE,
            is_financial BOOLEAN,
            eps_basic DOUBLE, eps_diluted DOUBLE,
            revenue DOUBLE, ebit DOUBLE, pat DOUBLE,
            equity DOUBLE, debt DOUBLE,
            is_consolidated BOOLEAN, source VARCHAR DEFAULT 'nse_xbrl',
            PRIMARY KEY (ticker, period_end_date)
        )
        """
    )


def _row(
    sym: str, f: RawFiling, aod: date, ratios: DerivedRatios, source: str
) -> tuple:
    return (
        sym,
        f.period_end,
        aod,
        f.broadcast_date,
        ratios.roe_ttm,
        ratios.debt_to_equity,
        ratios.op_margin_ttm,
        _is_financial(sym, ""),
        f.facts.eps_basic,
        f.facts.eps_diluted,
        f.facts.revenue,
        f.facts.ebit,
        f.facts.pat,
        f.facts.equity,
        f.facts.debt,
        f.facts.is_consolidated,
        source,
    )


def ingest_fundamentals(
    universe_db: Path,
    fundamentals_db: Path = DEFAULT_FUNDAMENTALS_DB,
    *,
    start: date,
    end: date,
) -> int:
    """Backfill fundamentals_quarterly over the PIT universe (NSE source).

    Returns rows written (quarantined look-ahead rows excluded).
    """
    uni = _pit_universe(universe_db, start, end)
    written = 0
    fundamentals_db.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(fundamentals_db))
    try:
        _ensure_schema(conn)
        for sym in sorted(uni):
            filings = sorted(
                _fetch_result_filings(sym, start, end),
                key=lambda f: f.period_end,
            )
            history: list[QuarterFacts] = []
            for f in filings:
                aod = f.broadcast_date or _sebi_fallback(f.period_end)
                if not (
                    f.period_end
                    <= aod
                    <= f.period_end + timedelta(days=_PIT_BAND_DAYS)
                ):
                    logger.warning(
                        "QUARANTINE %s %s: as_of %s outside PIT band",
                        sym,
                        f.period_end,
                        aod,
                    )
                    continue
                history.append(
                    QuarterFacts(sym, f.period_end, aod, f.facts)
                )
                ratios = derive_ttm(history)
                conn.execute(
                    f"INSERT OR REPLACE INTO fundamentals_quarterly "
                    f"({_COLS}) VALUES ({','.join('?' * 17)})",
                    _row(sym, f, aod, ratios, "nse_xbrl"),
                )
                written += 1
    finally:
        conn.close()
    logger.info(
        "fundamentals: wrote %d rows for %d names", written, len(uni)
    )
    return written


def snapshot_live(
    universe_db: Path,
    fundamentals_db: Path = DEFAULT_FUNDAMENTALS_DB,
    *,
    on_date: date,
) -> int:
    """Live capture: stamp as_of_date = on_date for filings broadcast
    today. PIT-clean by construction (value recorded the day we see it),
    so the live path does not depend on a reliable historical timestamp.
    """
    written = 0
    fundamentals_db.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(fundamentals_db))
    try:
        _ensure_schema(conn)
        existing = {
            (t, pe)
            for t, pe in conn.execute(
                "SELECT ticker, period_end_date FROM fundamentals_quarterly"
            ).fetchall()
        }
        uni = _pit_universe(universe_db, on_date, on_date)
        if not uni:
            snaps = snapshot_dates(universe_db)
            if snaps:
                uni = {
                    r.ticker: r.isin
                    for r in load_universe(universe_db, snaps[-1])
                }
        for sym in sorted(uni):
            for f in _fetch_result_filings(sym, on_date, on_date):
                if (sym, f.period_end) in existing:
                    continue
                ratios = derive_ttm(
                    [QuarterFacts(sym, f.period_end, on_date, f.facts)]
                )
                conn.execute(
                    f"INSERT OR REPLACE INTO fundamentals_quarterly "
                    f"({_COLS}) VALUES ({','.join('?' * 17)})",
                    _row(sym, f, on_date, ratios, "nse_live"),
                )
                written += 1
    finally:
        conn.close()
    return written


# ──────────────────────────────────────────────────────────────────────
# Validation firewall
# ──────────────────────────────────────────────────────────────────────


def assert_no_lookahead(fundamentals_db: Path) -> None:
    conn = duckdb.connect(str(fundamentals_db), read_only=True)
    try:
        bad = conn.execute(
            f"""
            SELECT ticker, period_end_date, as_of_date
              FROM fundamentals_quarterly
             WHERE as_of_date < period_end_date
                OR as_of_date > period_end_date
                   + INTERVAL {_PIT_BAND_DAYS} DAY
            """
        ).fetchall()
    finally:
        conn.close()
    if bad:
        raise LookaheadError(f"{len(bad)} look-ahead rows, e.g. {bad[:3]}")


def coverage_report(fundamentals_db: Path) -> dict:
    conn = duckdb.connect(str(fundamentals_db), read_only=True)
    try:
        by_year = dict(
            conn.execute(
                "SELECT EXTRACT(year FROM as_of_date)::INT, COUNT(*) "
                "FROM fundamentals_quarterly GROUP BY 1 ORDER BY 1"
            ).fetchall()
        )
        lag = conn.execute(
            """
            SELECT
              SUM(CASE WHEN as_of_date - period_end_date < 20
                       THEN 1 ELSE 0 END),
              SUM(CASE WHEN as_of_date - period_end_date BETWEEN 20 AND 50
                       THEN 1 ELSE 0 END),
              SUM(CASE WHEN as_of_date - period_end_date > 50
                       THEN 1 ELSE 0 END)
            FROM fundamentals_quarterly
            """
        ).fetchone()
    finally:
        conn.close()
    return {
        "by_year": {int(k): int(v) for k, v in by_year.items()},
        "lag_buckets": {
            "<20d": int(lag[0] or 0),
            "20-50d": int(lag[1] or 0),
            "50-75d": int(lag[2] or 0),
        },
    }


__all__ = [
    "QuarterFacts",
    "DerivedRatios",
    "RawFiling",
    "LookaheadError",
    "derive_ttm",
    "ingest_fundamentals",
    "snapshot_live",
    "assert_no_lookahead",
    "coverage_report",
    "DEFAULT_FUNDAMENTALS_DB",
]


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--universe-db", default="storage/universe.duckdb")
    ap.add_argument(
        "--fundamentals-db", default=str(DEFAULT_FUNDAMENTALS_DB)
    )
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    fdb = Path(a.fundamentals_db)
    ingest_fundamentals(
        Path(a.universe_db),
        fdb,
        start=date.fromisoformat(a.start),
        end=date.fromisoformat(a.end),
    )
    try:
        assert_no_lookahead(fdb)
    except LookaheadError as e:
        print(f"LOOK-AHEAD TRIPWIRE FIRED: {e}", file=sys.stderr)
        sys.exit(1)
    print(coverage_report(fdb))
