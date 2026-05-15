"""Earnings-calendar ingest — built on top of `data.ingest_news` (NSE filings).

NSE's corporate-announcements feed carries a `category` field for each filing.
"Financial Results" is the category that contains quarterly results. We extract
those rows into a dedicated `earnings_calendar` table so the strategy can
gate exposure around result dates (Indian large-cap results move ±10-15%
commonly).

For backfill, we read filings already in `storage/news.duckdb` with
`source='nse_filing'` and parse a result-date out of the title / subject —
NSE titles look like "Financial Results for the quarter ended 31-MAR-2025".
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

_RESULT_CATEGORY_PATTERNS = (
    re.compile(r"\bFinancial Results\b", re.IGNORECASE),
    re.compile(r"\bQuarterly Results\b", re.IGNORECASE),
    re.compile(r"\bAudited Financial\b", re.IGNORECASE),
    re.compile(r"\bUnaudited Financial\b", re.IGNORECASE),
)

_QUARTER_END_PATTERNS = (
    re.compile(r"quarter\s+ended\s+(\d{1,2})[\-\s]([A-Za-z]{3})[\-\s](\d{2,4})", re.IGNORECASE),
    re.compile(r"period\s+ended\s+(\d{1,2})[\-\s]([A-Za-z]{3})[\-\s](\d{2,4})", re.IGNORECASE),
    re.compile(r"(\d{1,2})[\-\s]([A-Za-z]{3})[\-\s](\d{2,4})", re.IGNORECASE),
)


@dataclass(frozen=True)
class EarningsEvent:
    ticker: str
    announcement_date: date     # when the filing was made (signal date)
    period_end_date: date | None  # quarter end the results pertain to
    title: str
    source: str = "nse_filing"


def _parse_period_end(title: str, summary: str) -> date | None:
    text = f"{title} {summary}"
    for rx in _QUARTER_END_PATTERNS:
        m = rx.search(text)
        if not m:
            continue
        day_s, mon_s, year_s = m.group(1), m.group(2), m.group(3)
        if len(year_s) == 2:
            year_s = "20" + year_s
        try:
            return datetime.strptime(f"{day_s}-{mon_s}-{year_s}", "%d-%b-%Y").date()
        except ValueError:
            continue
    return None


def _is_results_filing(title: str) -> bool:
    return any(rx.search(title or "") for rx in _RESULT_CATEGORY_PATTERNS)


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS earnings_calendar (
            ticker VARCHAR NOT NULL,
            announcement_date DATE NOT NULL,
            period_end_date DATE,
            title VARCHAR,
            source VARCHAR DEFAULT 'nse_filing',
            eps_estimate DOUBLE,
            eps_reported DOUBLE,
            surprise_pct DOUBLE,
            PRIMARY KEY (ticker, announcement_date)
        )
        """
    )
    # Tolerate a pre-existing table from an older schema (add columns if absent)
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='earnings_calendar'"
        ).fetchall()
    }
    for col in ("eps_estimate", "eps_reported", "surprise_pct"):
        if col not in existing:
            conn.execute(f"ALTER TABLE earnings_calendar ADD COLUMN {col} DOUBLE")


def extract_from_news(news_db: Path, earnings_db: Path | None = None) -> int:
    """Scan news.duckdb for results filings; populate earnings_calendar.

    If `earnings_db` is None, writes back into `news_db` (single-file deployment
    is common for our setup). Idempotent: PK (ticker, announcement_date).
    """
    target_db = earnings_db or news_db
    conn_in = duckdb.connect(str(news_db), read_only=True)
    try:
        rows = conn_in.execute(
            """
            SELECT ticker, dt, title, COALESCE(summary, '') AS summary
              FROM articles
             WHERE source = 'nse_filing'
               AND ticker IS NOT NULL
            """
        ).fetchall()
    finally:
        conn_in.close()

    events: list[EarningsEvent] = []
    for ticker, dt, title, summary in rows:
        if not _is_results_filing(title):
            continue
        period_end = _parse_period_end(title, summary)
        events.append(
            EarningsEvent(
                ticker=ticker,
                announcement_date=dt,
                period_end_date=period_end,
                title=title,
            )
        )

    if not events:
        return 0

    conn = duckdb.connect(str(target_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            for e in events:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO earnings_calendar
                        (ticker, announcement_date, period_end_date, title, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (e.ticker, e.announcement_date, e.period_end_date, e.title, e.source),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    logger.info("earnings_calendar: extracted %d events", len(events))
    return len(events)


def load_calendar(
    earnings_db: Path,
    tickers: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[EarningsEvent]:
    """Read the calendar with optional filters."""
    if not earnings_db.exists():
        return []
    conn = duckdb.connect(str(earnings_db), read_only=True)
    try:
        clauses = []
        params: list = []
        if tickers:
            placeholders = ",".join("?" * len(tickers))
            clauses.append(f"ticker IN ({placeholders})")
            params.extend(tickers)
        if start:
            clauses.append("announcement_date >= ?")
            params.append(start)
        if end:
            clauses.append("announcement_date <= ?")
            params.append(end)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"""
            SELECT ticker, announcement_date, period_end_date, title, source
              FROM earnings_calendar
              {where}
             ORDER BY announcement_date, ticker
            """,
            params,
        ).fetchall()
    finally:
        conn.close()
    return [
        EarningsEvent(
            ticker=t,
            announcement_date=ad,
            period_end_date=pe,
            title=ti,
            source=src,
        )
        for (t, ad, pe, ti, src) in rows
    ]


def ingest_yfinance_earnings(
    tickers: list[str],
    earnings_db: Path,
    *,
    limit: int = 60,
    polite_delay_sec: float = 0.3,
) -> int:
    """PRIMARY earnings path. Pull historical earnings dates + EPS surprise
    per ticker from Yahoo Finance (`<TICKER>.NS`).

    `get_earnings_dates` returns a DataFrame indexed by the earnings datetime
    with columns `EPS Estimate`, `Reported EPS`, `Surprise(%)`. Yahoo carries
    5-18 years of dates for NSE blue-chips — far deeper than any free Indian
    filing API, and the surprise% directly feeds the beat/miss event signal.

    Idempotent on (ticker, announcement_date). `source='yfinance'`.
    """
    import time

    import yfinance as yf

    rows: list[tuple] = []
    for t in tickers:
        try:
            yt = yf.Ticker(f"{t}.NS")
            df = yt.get_earnings_dates(limit=limit)
        except Exception as e:
            logger.warning("yfinance earnings %s failed: %s", t, e)
            time.sleep(polite_delay_sec * 3)
            continue
        if df is None or df.empty:
            continue
        for ts, r in df.iterrows():
            d = ts.date() if hasattr(ts, "date") else ts
            def _f(v):
                try:
                    fv = float(v)
                    return None if fv != fv else fv  # NaN → None
                except (TypeError, ValueError):
                    return None
            rows.append(
                (
                    t,
                    d,
                    None,                         # period_end_date (not from yf)
                    "Earnings (yfinance)",
                    "yfinance",
                    _f(r.get("EPS Estimate")),
                    _f(r.get("Reported EPS")),
                    _f(r.get("Surprise(%)")),
                )
            )
        time.sleep(polite_delay_sec)

    if not rows:
        return 0
    conn = duckdb.connect(str(earnings_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            for row in rows:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO earnings_calendar
                      (ticker, announcement_date, period_end_date, title,
                       source, eps_estimate, eps_reported, surprise_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    logger.info("yfinance earnings: wrote %d rows for %d tickers", len(rows), len(tickers))
    return len(rows)


def ingest_earnings(news_db: Path | None = None, earnings_db: Path | None = None) -> int:
    """Predecessor-compatible alias for `extract_from_news`.

    Uses the default storage paths if not supplied. The yfinance path
    (`ingest_yfinance_earnings`) is the primary source for 5y backfill;
    this news-extraction remains as a same-day cross-source supplement.
    """
    news_db = news_db or Path("storage/news.duckdb")
    return extract_from_news(news_db=news_db, earnings_db=earnings_db)


__all__ = [
    "EarningsEvent",
    "extract_from_news",
    "load_calendar",
    "ingest_earnings",
    "ingest_yfinance_earnings",
]
