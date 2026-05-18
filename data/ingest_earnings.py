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
    since: date | None = None,
    polite_delay_sec: float = 0.3,
) -> int:
    """PRIMARY earnings path. Pull historical earnings dates + EPS surprise
    per ticker from Yahoo Finance (`<TICKER>.NS`).

    `get_earnings_dates` returns a DataFrame indexed by the earnings datetime
    with columns `EPS Estimate`, `Reported EPS`, `Surprise(%)`. Yahoo carries
    20+ years for blue-chips, but we only need the backtest window. `since`
    floors the ingested events (default: 2019-01-01 — one year of margin
    before BACKTEST_START=2020-01-01 for any trailing-window logic). Events
    older than `since` are dropped, not stored. Future-scheduled earnings
    rows (yfinance includes the next, not-yet-reported date) are kept — they
    carry NULL reported EPS and are harmless.

    Idempotent on (ticker, announcement_date). `source='yfinance'`.
    """
    import time

    import yfinance as yf

    if since is None:
        since = date(2019, 1, 1)

    rows: list[tuple] = []
    dropped_old = 0
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
            if d < since:
                dropped_old += 1
                continue
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
    logger.info(
        "yfinance earnings: wrote %d rows for %d tickers (dropped %d events "
        "older than %s)",
        len(rows), len(tickers), dropped_old, since,
    )
    return len(rows)


def ingest_earnings(news_db: Path | None = None, earnings_db: Path | None = None) -> int:
    """Predecessor-compatible alias for `extract_from_news`.

    Uses the default storage paths if not supplied. The yfinance path
    (`ingest_yfinance_earnings`) is the primary source for 5y backfill;
    this news-extraction remains as a same-day cross-source supplement.
    """
    news_db = news_db or Path("storage/news.duckdb")
    return extract_from_news(news_db=news_db, earnings_db=earnings_db)


# --- Robust-statistics constants (NOT tunable trading hyperparameters;
# standard robust-stat values, kept here in the ingest layer, never on
# strategy.params, so prepare.count_hyperparameters is unaffected — same
# status as the existing ">=3 errors / <=8-quarter window" choices in this
# function). They make the seasonal-RW SUE production-honest rather than
# fitted to a backtest. -------------------------------------------------
#
# Quarterly headline EPS ("...ContinuingAndDiscontinuedOperations" in the
# NSE XBRL) periodically carries a NON-recurring item — exceptional gain,
# discontinued-ops, demerger or an unadjusted split/bonus — that shows up
# as an order-of-magnitude one-off (observed: ASTERDM ~₹1 EPS with a
# single 120.67 quarter). A naive seasonal-RW SUE divides that ~119
# innovation by the firm's tiny normal forecast-error scale and emits a
# ~1300σ "surprise": pure artifact, and exactly where the defensive PEAD
# gate fires hardest. Hampel identifier with a deliberately CONSERVATIVE
# K removes only egregious non-recurring spikes (typically ≫10σ vs the
# firm's robust trailing EPS level) while preserving genuine large
# earnings surprises (<~5σ standardized — the PEAD signal we WANT). The
# final symmetric clip is defence-in-depth against residual
# denominator-collapse on near-constant-EPS firms.
_HAMPEL_K = 8.0          # conservative Hampel outlier identifier
_SUE_CLIP = 8.0          # symmetric SUE magnitude cap (≫ any PEAD decile)
_MAD_TO_SIGMA = 1.4826   # MAD → robust σ (Gaussian consistency constant)


def compute_sue_from_fundamentals(
    fundamentals_db: Path, earnings_db: Path
) -> int:
    """SUE via seasonal random walk on as-reported EPS (point-in-time),
    robustified against non-recurring exceptional items.

    E[EPS_q] = EPS_{q-4} (same quarter prior year, as-reported, known
    as-of). unexpected = EPS_q - E[EPS_q]. Standardized by the population
    std of up to the last 8 *strictly prior* seasonal forecast errors;
    needs >= 3 such errors else sue is left None.

    Robustification (PIT-clean — every input is strictly prior to the
    quarter being scored, the same guarantee the raw errs window already
    relied on): the current EPS and its seasonal comparator are each
    Hampel-tested against the firm's robust trailing EPS level (median /
    MAD over strictly-prior quarters). If either is an egregious
    non-recurring outlier the quarter emits NO SUE (soft-degrade — the
    gate's safe default — never a ±1000σ artifact). Outlier-contaminated
    quarters are likewise excluded from the denominator's error window so
    a one-off cannot inflate/deflate the scale. The final SUE is clipped
    to ±_SUE_CLIP. announcement_date is the fundamentals as_of_date (the
    broadcast date), so the surprise carries the same PIT guarantee as the
    underlying EPS.
    """
    import statistics

    def _robust_level(prior: list[float]) -> tuple[float, float]:
        """(median, robust σ) of strictly-prior EPS. σ via MAD, falling
        back to pstdev; 0.0 when EPS is (near-)constant — then no value
        can be an outlier, which is correct (a flat series has no
        non-recurring spike)."""
        med = statistics.median(prior)
        mad = statistics.median([abs(x - med) for x in prior])
        scale = _MAD_TO_SIGMA * mad
        if scale <= 1e-9 and len(prior) > 1:
            scale = statistics.pstdev(prior)
        return med, scale

    def _is_exceptional(x: float, med: float, scale: float) -> bool:
        return scale > 1e-9 and abs(x - med) > _HAMPEL_K * scale

    fc = duckdb.connect(str(fundamentals_db), read_only=True)
    try:
        rows = fc.execute(
            "SELECT ticker, period_end_date, as_of_date, eps_basic "
            "FROM fundamentals_quarterly "
            "WHERE eps_basic IS NOT NULL "
            "ORDER BY ticker, period_end_date"
        ).fetchall()
    finally:
        fc.close()

    by_t: dict[str, list[tuple]] = {}
    for t, pe, ao, eps in rows:
        by_t.setdefault(t, []).append((pe, ao, float(eps)))

    out: list[tuple] = []
    for t, series in by_t.items():
        eps_seq = [v[2] for v in series]
        for i in range(4, len(series)):
            _pe, ao, eps = series[i]
            comparator = eps_seq[i - 4]
            prior = eps_seq[:i]  # strictly prior → PIT-safe
            med, scale = _robust_level(prior)
            # Exceptional-item guard: a non-recurring spike in the current
            # EPS or its seasonal comparator makes the innovation
            # meaningless → emit no signal rather than a monster SUE.
            if _is_exceptional(eps, med, scale) or _is_exceptional(
                comparator, med, scale
            ):
                continue
            unexpected = eps - comparator
            # Clean seasonal forecast errors: drop any quarter whose own
            # value or its comparator is a non-recurring outlier so the
            # denominator is not contaminated by an exceptional item.
            errs = [
                eps_seq[j] - eps_seq[j - 4]
                for j in range(4, i)
                if not _is_exceptional(eps_seq[j], med, scale)
                and not _is_exceptional(eps_seq[j - 4], med, scale)
            ][-8:]
            if len(errs) < 3:
                continue
            sd = statistics.pstdev(errs)
            if sd <= 1e-9:
                continue
            sue = max(-_SUE_CLIP, min(_SUE_CLIP, unexpected / sd))
            out.append((t, ao, unexpected, sue, "seasonal_rw"))

    if not out:
        return 0
    conn = duckdb.connect(str(earnings_db))
    try:
        _ensure_schema(conn)
        existing = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='earnings_calendar'"
            ).fetchall()
        }
        for col, typ in (
            ("surprise_eps", "DOUBLE"),
            ("sue", "DOUBLE"),
            ("expectation_basis", "VARCHAR"),
        ):
            if col not in existing:
                conn.execute(
                    f"ALTER TABLE earnings_calendar ADD COLUMN {col} {typ}"
                )
        conn.execute("BEGIN TRANSACTION")
        try:
            for t, ao, ue, sue, basis in out:
                conn.execute(
                    """
                    INSERT INTO earnings_calendar
                        (ticker, announcement_date, title, source,
                         surprise_eps, sue, expectation_basis)
                    VALUES (?, ?, 'SUE (computed)', 'fundamentals_sue',
                            ?, ?, ?)
                    ON CONFLICT (ticker, announcement_date) DO UPDATE SET
                        surprise_eps = excluded.surprise_eps,
                        sue = excluded.sue,
                        expectation_basis = excluded.expectation_basis
                    """,
                    (t, ao, ue, sue, basis),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return len(out)


__all__ = [
    "EarningsEvent",
    "extract_from_news",
    "load_calendar",
    "ingest_earnings",
    "ingest_yfinance_earnings",
    "compute_sue_from_fundamentals",
]
