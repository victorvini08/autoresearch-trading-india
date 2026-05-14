"""Ingest daily OHLCV bars from the NSE bhav archive.

Primary source: NSE's daily "sec_bhavdata_full_DDMMYYYY.csv" — published end-of-day
(usually by ~19:00 IST) and again as historical archive. Each daily file contains
EOD bars for every NSE listed instrument in a single CSV. We filter to SERIES=EQ
and (optionally) to a specific ticker universe.

URL forms (both work as of 2026-05; we try the new domain first):
    https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv
    https://archives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv

CSV columns (typical):
    SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE,
    LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS,
    NO_OF_TRADES, DELIV_QTY, DELIV_PER

We write to `storage/prices.duckdb` table `daily_bars(ticker, dt, open, high,
low, close, volume, value_inr_crores)` — schema chosen to be a drop-in for
the US repo's interfaces.

Reliability:
- Each bhav file is independently retrieved, with retry/backoff (tenacity).
- Idempotent: re-ingesting a date OVERWRITES that day's slice.
- yfinance is available as a cross-source validation fallback (not primary).
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

_NEW_BASE = "https://nsearchives.nseindia.com/products/content"
_OLD_BASE = "https://archives.nseindia.com/products/content"

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)

_REQUIRED_COLUMNS = {
    "SYMBOL",
    "SERIES",
    "OPEN_PRICE",
    "HIGH_PRICE",
    "LOW_PRICE",
    "CLOSE_PRICE",
    "TTL_TRD_QNTY",
    "TURNOVER_LACS",
}


@dataclass(frozen=True)
class DailyBar:
    ticker: str
    dt: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    value_inr_crores: float       # daily traded value, ₹ crore


# ──────────────────────────────────────────────────────────────────────
# Fetching
# ──────────────────────────────────────────────────────────────────────


def _bhav_filename(d: date) -> str:
    return f"sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv"


@retry(
    retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1.0, min=1, max=30),
    reraise=True,
)
def _fetch_url(url: str, timeout: int = 30) -> bytes | None:
    headers = {
        "User-Agent": _BROWSER_UA,
        "Accept": "text/csv,application/zip,*/*",
        "Referer": "https://www.nseindia.com/",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.content


def fetch_bhav_csv(d: date) -> bytes | None:
    """Return the raw CSV bytes for date `d`, or None if NSE has no file
    (typically because `d` is a non-trading day).

    Tries the new archives domain first, then the legacy one.
    """
    fn = _bhav_filename(d)
    for base in (_NEW_BASE, _OLD_BASE):
        url = f"{base}/{fn}"
        try:
            data = _fetch_url(url)
        except requests.RequestException as e:
            logger.warning("bhav fetch failed for %s @ %s: %s", d, url, e)
            continue
        if data is None:
            continue
        # NSE sometimes returns a ZIP instead of plain CSV on the new domain
        if data[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                csv_name = next(
                    (n for n in zf.namelist() if n.lower().endswith(".csv")),
                    None,
                )
                if not csv_name:
                    logger.warning("bhav ZIP for %s contained no CSV", d)
                    continue
                return zf.read(csv_name)
        return data
    return None


# ──────────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────────


def parse_bhav_csv(
    csv_bytes: bytes,
    tickers: set[str] | None = None,
    series_filter: tuple[str, ...] = ("EQ",),
) -> list[DailyBar]:
    """Parse the NSE bhav CSV. Filters to SERIES in `series_filter` (default EQ-only).

    If `tickers` is provided, restricts to that set (universe slice).
    """
    text = csv_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or "").strip().upper() for h in (reader.fieldnames or [])}
    if not _REQUIRED_COLUMNS.issubset(headers):
        missing = _REQUIRED_COLUMNS - headers
        raise ValueError(f"bhav CSV missing required columns: {missing}")

    bars: list[DailyBar] = []
    for row in reader:
        # strip whitespace from keys+values
        row = {(k or "").strip().upper(): (v or "").strip() for k, v in row.items()}
        series = row.get("SERIES", "")
        if series_filter and series not in series_filter:
            continue
        symbol = row["SYMBOL"]
        if tickers and symbol not in tickers:
            continue
        try:
            d_str = row.get("DATE1") or row.get("DATE")
            d = datetime.strptime(d_str, "%d-%b-%Y").date()
            open_p = float(row["OPEN_PRICE"])
            high = float(row["HIGH_PRICE"])
            low = float(row["LOW_PRICE"])
            close = float(row["CLOSE_PRICE"])
            volume = int(float(row["TTL_TRD_QNTY"] or 0))
            turnover_lacs = float(row.get("TURNOVER_LACS") or 0)
        except (KeyError, ValueError) as e:
            logger.debug("skipping row %s (%s)", row.get("SYMBOL"), e)
            continue
        bars.append(
            DailyBar(
                ticker=symbol,
                dt=d,
                open=open_p,
                high=high,
                low=low,
                close=close,
                volume=volume,
                value_inr_crores=turnover_lacs / 100.0,
            )
        )
    return bars


# ──────────────────────────────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────────────────────────────


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_bars (
            ticker VARCHAR NOT NULL,
            dt DATE NOT NULL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            value_inr_crores DOUBLE,
            PRIMARY KEY (ticker, dt)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS daily_bars_dt_idx ON daily_bars(dt)"
    )


def write_bars(prices_db: Path, bars: list[DailyBar]) -> int:
    """Upsert `bars` into `daily_bars`. Returns row count written.

    Idempotent by (ticker, dt) primary key — re-running for the same date
    OVERWRITES that slice.
    """
    if not bars:
        return 0
    conn = duckdb.connect(str(prices_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            # Delete affected (ticker, dt) keys first to make the insert clean
            dates_seen = {b.dt for b in bars}
            for d in dates_seen:
                tickers_for_d = [b.ticker for b in bars if b.dt == d]
                placeholders = ",".join("?" * len(tickers_for_d))
                conn.execute(
                    f"DELETE FROM daily_bars WHERE dt = ? AND ticker IN ({placeholders})",
                    (d, *tickers_for_d),
                )
            for b in bars:
                conn.execute(
                    """
                    INSERT INTO daily_bars
                        (ticker, dt, open, high, low, close, volume, value_inr_crores)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        b.ticker,
                        b.dt,
                        b.open,
                        b.high,
                        b.low,
                        b.close,
                        b.volume,
                        b.value_inr_crores,
                    ),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return len(bars)


# ──────────────────────────────────────────────────────────────────────
# Higher-level API
# ──────────────────────────────────────────────────────────────────────


def ingest_date(
    prices_db: Path,
    d: date,
    tickers: set[str] | None = None,
) -> int:
    """Fetch the bhav for `d`, filter to `tickers` (if given), write to DB.

    Returns row count written. Returns 0 if NSE has no file for `d` (non-trading day).
    """
    raw = fetch_bhav_csv(d)
    if raw is None:
        logger.info("no NSE bhav for %s (non-trading day or not yet posted)", d)
        return 0
    bars = parse_bhav_csv(raw, tickers=tickers)
    return write_bars(prices_db, bars)


def ingest_range(
    prices_db: Path,
    start: date,
    end: date,
    tickers: set[str] | None = None,
    *,
    polite_delay_sec: float = 0.8,
) -> dict[str, int]:
    """Ingest every trading day from `start` to `end` inclusive.

    Iterates calendar days, skipping weekends and any day NSE doesn't have a
    file (auto-detects holidays). Polite delay between requests to stay friendly
    with NSE archives.
    """
    import time

    total = 0
    skipped = 0
    one_day = timedelta(days=1)
    d = start
    while d <= end:
        # Skip weekends (NSE closed Sat/Sun)
        if d.weekday() >= 5:
            d += one_day
            continue
        try:
            n = ingest_date(prices_db, d, tickers=tickers)
        except Exception as e:
            logger.error("failed to ingest %s: %s", d, e)
            n = -1
        if n > 0:
            total += n
        else:
            skipped += 1
        time.sleep(polite_delay_sec)
        d += one_day
    return {"rows_written": total, "days_skipped": skipped}


# ──────────────────────────────────────────────────────────────────────
# Compatibility shims — predecessor (US) modules used these names; we keep
# them so the carried-over orchestrators import cleanly. Internals delegate
# to the India-specific bhav-based helpers above.
# ──────────────────────────────────────────────────────────────────────


DB_PATH = Path("storage/prices.duckdb")


def read_prices(ticker: str, start, end):
    """Return a pandas DataFrame indexed by date with OHLCV cols for `ticker`.

    `start`/`end` may be a date, datetime, or ISO string. Soft-degrades to an
    empty DataFrame if the DB or row is missing.
    """
    import pandas as pd

    if isinstance(start, str):
        start_d = datetime.fromisoformat(start).date()
    elif hasattr(start, "date"):
        start_d = start.date() if callable(getattr(start, "date")) else start
    else:
        start_d = start
    if isinstance(end, str):
        end_d = datetime.fromisoformat(end).date()
    elif hasattr(end, "date"):
        end_d = end.date() if callable(getattr(end, "date")) else end
    else:
        end_d = end
    if not DB_PATH.exists():
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "value_inr_crores"])
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = conn.execute(
            """
            SELECT dt, open, high, low, close, volume, value_inr_crores
              FROM daily_bars
             WHERE ticker = ? AND dt BETWEEN ? AND ?
             ORDER BY dt
            """,
            (ticker.upper(), start_d, end_d),
        ).fetchdf()
    finally:
        conn.close()
    # Predecessor (US) modules expected a "date" column (not an index) so the
    # downstream prepare.py / engine code can call df["date"]. We rename `dt`
    # → `date` and keep it as a regular column.
    if not df.empty:
        df = df.rename(columns={"dt": "date"})
    return df


def ingest_prices(tickers: set[str] | None = None, start: date | None = None, end: date | None = None) -> int:
    """Convenience wrapper: ingest the date range into the default `DB_PATH`.

    Mirrors the predecessor interface so carried-over orchestrators
    (`daily_update`, `precompute_macro_cache`) work without per-call path wiring.
    """
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=2)
    result = ingest_range(DB_PATH, start, end, tickers=tickers)
    return result["rows_written"]


__all__ = [
    "DailyBar",
    "DB_PATH",
    "fetch_bhav_csv",
    "parse_bhav_csv",
    "write_bars",
    "ingest_date",
    "ingest_range",
    "read_prices",
    "ingest_prices",
]
