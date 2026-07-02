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

# Legacy ("cm<DD><MON><YYYY>bhav.csv.zip") archive. Only this format exists for
# 2018/2019; the modern sec_bhavdata_full file 404s before ~2020-07.
_LEGACY_BASE = "https://nsearchives.nseindia.com/content/historical/EQUITIES"

# NSE switched the daily full-bhav file to the modern sec_bhavdata_full schema
# around mid-2020; dates strictly before this use the legacy fetch+parse path.
_LEGACY_CUTOVER = date(2020, 7, 1)

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

# Legacy cm<DD><MON><YYYY>bhav.csv columns. TOTTRDVAL is turnover in *rupees*
# (the modern file's TURNOVER_LACS is in lakhs) and TIMESTAMP replaces DATE1.
_REQUIRED_COLUMNS_LEGACY = {
    "SYMBOL",
    "SERIES",
    "OPEN",
    "HIGH",
    "LOW",
    "CLOSE",
    "TOTTRDQTY",
    "TOTTRDVAL",
    "TIMESTAMP",
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
    # Exchange-published previous close (2026-06-10). On a corporate-action
    # ex-date NSE publishes the ADJUSTED previous close here, so
    # raw_close(t-1) / prev_close(t) IS the exact split/bonus/special-dividend
    # factor — the authoritative input for back-adjusting price history
    # (read_prices applies it). None for rows ingested before this column.
    prev_close: float | None = None


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


_MONTHS = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)


def _legacy_bhav_url(d: date) -> str:
    """Build the legacy archive URL for date `d`.

    e.g. date(2018, 6, 1) ->
    .../EQUITIES/2018/JUN/cm01JUN2018bhav.csv.zip
    """
    mon = _MONTHS[d.month - 1]
    fn = f"cm{d.day:02d}{mon}{d.year}bhav.csv.zip"
    return f"{_LEGACY_BASE}/{d.year}/{mon}/{fn}"


def fetch_bhav_csv_legacy(d: date) -> bytes | None:
    """Return the raw legacy CSV bytes for date `d`, or None if NSE has no file
    (typically a non-trading day → HTTP 404).

    Mirrors `fetch_bhav_csv`'s retry/None semantics (via `_fetch_url`) but
    targets the legacy `cm<DD><MON><YYYY>bhav.csv.zip` archive, which is always
    a ZIP. Used for 2018–mid-2020 dates where the modern file does not exist.
    """
    url = _legacy_bhav_url(d)
    try:
        data = _fetch_url(url)
    except requests.RequestException as e:
        logger.warning("legacy bhav fetch failed for %s @ %s: %s", d, url, e)
        return None
    if data is None:
        return None
    if data[:2] != b"PK":
        logger.warning("legacy bhav for %s was not a ZIP (got %r…)", d, data[:8])
        return None
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        csv_name = next(
            (n for n in zf.namelist() if n.lower().endswith(".csv")),
            None,
        )
        if not csv_name:
            logger.warning("legacy bhav ZIP for %s contained no CSV", d)
            return None
        return zf.read(csv_name)


# ──────────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────────


def parse_bhav_csv(
    csv_bytes: bytes,
    tickers: set[str] | None = None,
    series_filter: tuple[str, ...] = ("EQ", "BE"),
) -> list[DailyBar]:
    """Parse the NSE bhav CSV. Filters to SERIES in `series_filter`.

    Default is EQ + BE (2026-06-10): BE is the Trade-to-Trade surveillance
    series — the SAME stocks, delivery-only settlement (CNC-compatible, which
    is all we do). EQ-only ingestion made a stock VANISH from daily_bars for
    the duration of every T2T stint (65 universe members affected, e.g.
    SUZLON's 2023-24 run), freezing held marks in backtests and producing
    phantom gross>100% risk-gate breaches. BZ etc. remain excluded.

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
            prev_close = (
                float(row["PREV_CLOSE"]) if row.get("PREV_CLOSE") else None
            )
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
                prev_close=prev_close,
            )
        )
    return bars


def parse_bhav_csv_legacy(
    csv_bytes: bytes,
    tickers: set[str] | None = None,
    series_filter: tuple[str, ...] = ("EQ", "BE"),
) -> list[DailyBar]:
    """Parse the LEGACY `cm<DD><MON><YYYY>bhav.csv` schema into `DailyBar`s.

    Same return type / filtering semantics as `parse_bhav_csv` (EQ+BE by
    default — see the T2T-hole note there), but maps the legacy columns:

        SYMBOL -> ticker
        OPEN/HIGH/LOW/CLOSE -> open/high/low/close
        TOTTRDQTY -> volume
        TOTTRDVAL (turnover in RUPEES) -> value_inr_crores = TOTTRDVAL / 1e7
        TIMESTAMP ("01-JUN-2018") -> dt

    The legacy header has a trailing comma (empty last field); `csv.DictReader`
    handles it (the blank key is ignored after upper/strip normalisation).
    """
    text = csv_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or "").strip().upper() for h in (reader.fieldnames or [])}
    if not _REQUIRED_COLUMNS_LEGACY.issubset(headers):
        missing = _REQUIRED_COLUMNS_LEGACY - headers
        raise ValueError(f"legacy bhav CSV missing required columns: {missing}")

    bars: list[DailyBar] = []
    for row in reader:
        # strip whitespace from keys+values; drop the trailing empty header key
        row = {(k or "").strip().upper(): (v or "").strip() for k, v in row.items()}
        series = row.get("SERIES", "")
        if series_filter and series not in series_filter:
            continue
        symbol = row["SYMBOL"]
        if tickers and symbol not in tickers:
            continue
        try:
            d = datetime.strptime(row["TIMESTAMP"], "%d-%b-%Y").date()
            open_p = float(row["OPEN"])
            high = float(row["HIGH"])
            low = float(row["LOW"])
            close = float(row["CLOSE"])
            volume = int(float(row["TOTTRDQTY"] or 0))
            turnover_rupees = float(row.get("TOTTRDVAL") or 0)
            prev_close = (
                float(row["PREVCLOSE"]) if row.get("PREVCLOSE") else None
            )
        except (KeyError, ValueError) as e:
            logger.debug("skipping legacy row %s (%s)", row.get("SYMBOL"), e)
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
                value_inr_crores=turnover_rupees / 1e7,
                prev_close=prev_close,
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
            prev_close DOUBLE,
            PRIMARY KEY (ticker, dt)
        )
        """
    )
    # Migration for DBs created before prev_close existed (2026-06-10).
    conn.execute(
        "ALTER TABLE daily_bars ADD COLUMN IF NOT EXISTS prev_close DOUBLE"
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
                        (ticker, dt, open, high, low, close, volume,
                         value_inr_crores, prev_close)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        b.prev_close,
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

    Format-aware by date: dates before `_LEGACY_CUTOVER` (2020-07-01) use the
    legacy `cm<DD><MON><YYYY>bhav.csv.zip` archive; dates on/after use the
    modern `sec_bhavdata_full` file. The modern path is unchanged.

    Returns row count written. Returns 0 if NSE has no file for `d` (non-trading day).
    """
    if d < _LEGACY_CUTOVER:
        raw = fetch_bhav_csv_legacy(d)
        if raw is None:
            logger.info("no NSE legacy bhav for %s (non-trading day or 404)", d)
            return 0
        bars = parse_bhav_csv_legacy(raw, tickers=tickers)
        return write_bars(prices_db, bars)

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
            SELECT dt, open, high, low, close, volume, value_inr_crores,
                   prev_close
              FROM daily_bars
             WHERE ticker = ? AND dt BETWEEN ? AND ?
             ORDER BY dt
            """,
            (ticker.upper(), start_d, end_d),
        ).fetchdf()
    finally:
        conn.close()
    # ── Corporate-action back-adjustment (2026-06-10) ──────────────────
    # Bhav prices are as-traded: a 10:1 split prints as a phantom -90% bar
    # (TATASTEEL 959.40 -> 100.35 on 2022-07-28), which a momentum book reads
    # as a crash — it books fake losses on held names, structurally exits
    # them, and vetoes genuine winners for the next year (companies split
    # AFTER run-ups).
    #
    # Detection: NSE's PREV_CLOSE is the RAW prior close (verified on the
    # TATASTEEL/IRCTC splits and the 2017 RELIANCE bonus — NSE does NOT
    # publish an adjusted base in the bhav), so prev_close(t)/open(t) is the
    # overnight gap measured inside a single row (robust to missing prior
    # rows, e.g. T2T stints). Legitimate gaps are capped by circuit bands at
    # 1.25x (20% band); CA ex-dates open at the re-based price (IRCTC
    # 4130.15/817.0 = 5.055, RELIANCE bonus 1645.40/823.0 = 1.999), and
    # genuine crashes unfold INTRADAY (YESBANK 2020-03-06 open-gap only
    # 1.085). Threshold 1.29 separates the two; the raw ratio is then
    # SNAPPED to the nearest small rational (the day's drift removed):
    # 5.055 -> 5, 1.999 -> 2, 9.6 -> 10. Reverse splits (consolidations)
    # are the mirrored case. A 5:4 split (1.25) sits below the threshold
    # and is knowingly missed (rare; 5% phantom move at worst).
    #
    # Application: divide all bars BEFORE each ex-date by the factor
    # (backward adjustment — current prices stay as-traded, so whole-share
    # sizing is untouched); scale volume inversely (₹-ADV invariant).
    # Events before the requested window rescale the whole window by a
    # constant that cancels in every return/momentum computation, so
    # per-window adjustment is exact for signals. Rows ingested before the
    # prev_close column exist as NULL -> no event -> unadjusted (legacy).
    if len(df) > 1 and "prev_close" in df.columns:
        import math

        import numpy as np

        def _snap(r: float) -> float:
            """Nearest small rational p/q within ~7% log-distance, else r."""
            best, bestd = r, 0.068
            for p in range(1, 21):
                for q in range(1, 7):
                    v = p / q
                    if not (1.28 <= v <= 25.0):
                        continue
                    d = abs(math.log(r / v))
                    if d < bestd:
                        best, bestd = v, d
            return best

        o = df["open"].to_numpy(dtype=float)
        pc = df["prev_close"].to_numpy(dtype=float)
        factors = np.ones(len(df))
        for i in range(1, len(df)):
            if (
                not np.isfinite(pc[i]) or pc[i] < 2.0
                or not np.isfinite(o[i]) or o[i] <= 0
            ):
                continue
            r = pc[i] / o[i]
            if 1.29 <= r <= 25.0:
                factors[i] = _snap(r)
            elif 0.04 <= r <= (1 / 1.29):
                factors[i] = 1.0 / _snap(1.0 / r)
        if (factors != 1.0).any():
            # cum[j] = product of event factors STRICTLY AFTER row j
            cum = np.ones(len(df))
            acc = 1.0
            for i in range(len(df) - 1, -1, -1):
                cum[i] = acc
                acc *= factors[i]
            for col in ("open", "high", "low", "close"):
                df[col] = df[col].to_numpy(dtype=float) / cum
            df["volume"] = (
                df["volume"].to_numpy(dtype=float) * cum
            ).round().astype("int64")
    df = df.drop(columns=["prev_close"])
    # Predecessor (US) modules expected a "date" column (not an index) so the
    # downstream prepare.py / engine code can call df["date"]. We rename `dt`
    # → `date` and keep it as a regular column.
    if not df.empty:
        df = df.rename(columns={"dt": "date"})
    return df


def ingest_prices(
    tickers: set[str] | None = None,
    start: date | str | None = None,
    end: date | str | None = None,
) -> int:
    """Convenience wrapper: ingest the date range into the default `DB_PATH`.

    Mirrors the predecessor interface so carried-over orchestrators
    (`daily_update`, `precompute_macro_cache`) work without per-call path
    wiring. Those orchestrators pass ISO-date *strings*; ingest_range
    requires `date` objects, so normalise both forms here (the documented
    entrypoint) rather than leak a str → `date.weekday()` AttributeError
    into the day loop.
    """
    if end is None:
        end = date.today()
    elif isinstance(end, str):
        end = date.fromisoformat(end)
    if start is None:
        start = end - timedelta(days=2)
    elif isinstance(start, str):
        start = date.fromisoformat(start)
    result = ingest_range(DB_PATH, start, end, tickers=tickers)
    return result["rows_written"]


__all__ = [
    "DailyBar",
    "DB_PATH",
    "fetch_bhav_csv",
    "fetch_bhav_csv_legacy",
    "parse_bhav_csv",
    "parse_bhav_csv_legacy",
    "write_bars",
    "ingest_date",
    "ingest_range",
    "read_prices",
    "ingest_prices",
]
