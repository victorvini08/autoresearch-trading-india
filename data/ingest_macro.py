"""Ingest Indian macro indicators.

Sources (all free):
- FRED API: India CPI (INDCPIALLAINMEI), interest rate (INTDSRINM193N), USD/INR (DEXINUS)
- yfinance: India VIX (^INDIAVIX), Nifty 50 (^NSEI), Nifty Bank (^NSEBANK),
  Nifty 100, Nifty Midcap 150 — for historical daily levels (FRED doesn't carry these)
- NSE public APIs: today's FII/DII net flows, current indices snapshot
- moneycontrol.com FII/DII history page: historical daily FII/DII (for backfill)

Storage: `storage/macro.duckdb` with tables:
- `macro_daily(series_id, dt, value)` — FRED + index levels (single-series, time-keyed)
- `fii_dii_daily(dt, fii_net_cr, dii_net_cr)` — daily FII/DII net flows in ₹ crore
- `india_vix_daily(dt, vix_close)` — convenience subset

All ingest is idempotent: re-running for the same date overwrites that date's
rows. Failures on one series do not abort the others (the regime gate uses
multiple inputs; partial data is OK if soft-degradation is applied at read time).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import duckdb
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# FRED series IDs we use for the Indian macro regime
FRED_SERIES = {
    "india_cpi_yoy": "INDCPIALLAINMEI",
    "india_interest_rate": "INTDSRINM193N",
    "usd_inr": "DEXINUS",
}

# yfinance tickers for Indian indices (free, decent history)
YFINANCE_INDEX_TICKERS = {
    "india_vix": "^INDIAVIX",
    "nifty_50": "^NSEI",
    "nifty_bank": "^NSEBANK",
    "nifty_500": "^CRSLDX",
}

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)


# ──────────────────────────────────────────────────────────────────────
# FRED
# ──────────────────────────────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1.0, min=1, max=20),
    reraise=True,
)
def fetch_fred_series(
    series_id: str,
    api_key: str,
    start: date | None = None,
    end: date | None = None,
) -> list[tuple[date, float]]:
    """Return [(dt, value)] for the FRED series. Missing values ('.') are skipped."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    if start:
        params["observation_start"] = start.isoformat()
    if end:
        params["observation_end"] = end.isoformat()
    resp = requests.get(_FRED_BASE, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    out: list[tuple[date, float]] = []
    for obs in payload.get("observations", []):
        v = obs.get("value", "")
        if v in ("", "."):
            continue
        try:
            out.append((datetime.strptime(obs["date"], "%Y-%m-%d").date(), float(v)))
        except (KeyError, ValueError):
            continue
    return out


# ──────────────────────────────────────────────────────────────────────
# yfinance — for Indian indices history
# ──────────────────────────────────────────────────────────────────────


def fetch_yfinance_history(
    yf_ticker: str,
    start: date,
    end: date | None = None,
) -> list[tuple[date, float]]:
    """Fetch daily Close levels for `yf_ticker` from yfinance.

    yfinance is a free wrapper around Yahoo's API; reliable for Indian indices
    where Yahoo's coverage is good. Used here instead of NSE direct because
    NSE's indicesHistory endpoint requires session cookies and is fragile.
    """
    import yfinance as yf

    end_inclusive = end + timedelta(days=1) if end else None
    df = yf.download(
        yf_ticker,
        start=start.isoformat(),
        end=end_inclusive.isoformat() if end_inclusive else None,
        progress=False,
        auto_adjust=False,
    )
    out: list[tuple[date, float]] = []
    if df is None or df.empty:
        return out
    # yfinance 0.2.x returns a MultiIndex column structure: (Price, Ticker).
    # Pull Close → scalar Series whether the columns are MultiIndex or not.
    closes = df["Close"]
    if hasattr(closes, "columns"):
        # MultiIndex case → single-ticker download still gives DataFrame; flatten
        closes = closes.iloc[:, 0]
    for ts, val in closes.items():
        # NaN in numpy/pandas returns False for `== None`; check both
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        d = ts.date() if hasattr(ts, "date") else ts
        out.append((d, v))
    return out


# ──────────────────────────────────────────────────────────────────────
# NSE FII/DII (current snapshot)
# ──────────────────────────────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.0, min=1, max=15),
    reraise=True,
)
def fetch_nse_fii_dii_current() -> list[tuple[date, float, float]]:
    """Return [(dt, fii_net_cr, dii_net_cr)] for the most-recent trading days NSE exposes.

    The /api/fiidiiTradeReact endpoint returns the latest ~3 trading days.
    For historical backfill, use `fetch_moneycontrol_fii_dii_history`.
    """
    headers = {
        "User-Agent": _BROWSER_UA,
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/reports/fii-dii",
    }
    sess = requests.Session()
    sess.headers.update(headers)
    # Warm-up cookie set required by NSE
    sess.get("https://www.nseindia.com/", timeout=15)
    resp = sess.get(
        "https://www.nseindia.com/api/fiidiiTradeReact",
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    by_date: dict[date, dict[str, float]] = {}
    for row in payload if isinstance(payload, list) else []:
        d_str = row.get("date")
        try:
            d = datetime.strptime(d_str, "%d-%b-%Y").date()
        except (TypeError, ValueError):
            continue
        category = (row.get("category") or "").upper()
        net_value = row.get("netValue")
        try:
            net = float(net_value)
        except (TypeError, ValueError):
            continue
        by_date.setdefault(d, {})[category] = net
    out: list[tuple[date, float, float]] = []
    for d, rec in by_date.items():
        fii = rec.get("FII/FPI") or rec.get("FII")
        dii = rec.get("DII")
        if fii is None or dii is None:
            continue
        out.append((d, fii, dii))
    out.sort()
    return out


# ──────────────────────────────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────────────────────────────


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS macro_daily (
            series_id VARCHAR NOT NULL,
            dt DATE NOT NULL,
            value DOUBLE NOT NULL,
            PRIMARY KEY (series_id, dt)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fii_dii_daily (
            dt DATE PRIMARY KEY,
            fii_net_cr DOUBLE NOT NULL,
            dii_net_cr DOUBLE NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS india_vix_daily (
            dt DATE PRIMARY KEY,
            vix_close DOUBLE NOT NULL
        )
        """
    )


def write_macro_series(
    macro_db: Path,
    series_id: str,
    points: list[tuple[date, float]],
) -> int:
    if not points:
        return 0
    conn = duckdb.connect(str(macro_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            for d, v in points:
                conn.execute(
                    "DELETE FROM macro_daily WHERE series_id = ? AND dt = ?",
                    (series_id, d),
                )
                conn.execute(
                    "INSERT INTO macro_daily (series_id, dt, value) VALUES (?, ?, ?)",
                    (series_id, d, v),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return len(points)


def write_fii_dii(
    macro_db: Path,
    points: list[tuple[date, float, float]],
) -> int:
    if not points:
        return 0
    conn = duckdb.connect(str(macro_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            for d, fii, dii in points:
                conn.execute("DELETE FROM fii_dii_daily WHERE dt = ?", (d,))
                conn.execute(
                    "INSERT INTO fii_dii_daily (dt, fii_net_cr, dii_net_cr) VALUES (?, ?, ?)",
                    (d, fii, dii),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return len(points)


def read_macro_window(macro_db: Path, series_id: str, start, end):
    """Return [(dt, value)] for `series_id` in [start, end] (ascending).

    Distinct from data.ingest_macro.read_macro (which reads the default
    DB_PATH and returns a DataFrame) — this takes an explicit db path and
    returns plain tuples so the LLM classifier can stay pandas-light.
    """
    if not Path(macro_db).exists():
        return []
    conn = duckdb.connect(str(macro_db), read_only=True)
    try:
        rows = conn.execute(
            "SELECT dt, value FROM macro_daily WHERE series_id=? "
            "AND dt BETWEEN ? AND ? ORDER BY dt",
            (series_id, start, end),
        ).fetchall()
    finally:
        conn.close()
    return [(r[0], float(r[1])) for r in rows if r[1] is not None]


def read_fii_dii(macro_db: Path, start, end):
    """Return [(dt, fii_net_cr, dii_net_cr)] in [start, end] (ascending).

    Empty list if the table is missing or the window has no rows — callers
    must degrade gracefully (FII history is v2; today only ~1 row exists).
    """
    if not Path(macro_db).exists():
        return []
    conn = duckdb.connect(str(macro_db), read_only=True)
    try:
        tbl = conn.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name='fii_dii_daily'"
        ).fetchone()
        if not tbl:
            return []
        rows = conn.execute(
            "SELECT dt, fii_net_cr, dii_net_cr FROM fii_dii_daily "
            "WHERE dt BETWEEN ? AND ? ORDER BY dt",
            (start, end),
        ).fetchall()
    finally:
        conn.close()
    return [(r[0], float(r[1]), float(r[2])) for r in rows]


def write_india_vix(macro_db: Path, points: list[tuple[date, float]]) -> int:
    if not points:
        return 0
    conn = duckdb.connect(str(macro_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            for d, v in points:
                conn.execute("DELETE FROM india_vix_daily WHERE dt = ?", (d,))
                conn.execute(
                    "INSERT INTO india_vix_daily (dt, vix_close) VALUES (?, ?)",
                    (d, v),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return len(points)


# ──────────────────────────────────────────────────────────────────────
# Top-level orchestrators
# ──────────────────────────────────────────────────────────────────────


def ingest_fred(
    macro_db: Path,
    start: date,
    end: date | None = None,
    api_key: str | None = None,
) -> dict[str, int]:
    """Ingest all FRED India series. Returns {series_id: row_count}."""
    api_key = api_key or os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY not set in env")
    counts: dict[str, int] = {}
    for name, series_id in FRED_SERIES.items():
        try:
            points = fetch_fred_series(series_id, api_key, start=start, end=end)
        except Exception as e:
            logger.error("FRED fetch %s failed: %s", series_id, e)
            counts[series_id] = -1
            continue
        counts[series_id] = write_macro_series(macro_db, series_id, points)
        logger.info("FRED %s: wrote %d points", series_id, counts[series_id])
    return counts


def ingest_yfinance_indices(
    macro_db: Path,
    start: date,
    end: date | None = None,
) -> dict[str, int]:
    """Ingest historical daily closes for Indian indices (incl. India VIX)."""
    counts: dict[str, int] = {}
    for name, yf_ticker in YFINANCE_INDEX_TICKERS.items():
        try:
            points = fetch_yfinance_history(yf_ticker, start, end)
        except Exception as e:
            logger.error("yfinance %s failed: %s", yf_ticker, e)
            counts[name] = -1
            continue
        n = write_macro_series(macro_db, f"index_{name}", points)
        counts[name] = n
        if name == "india_vix":
            write_india_vix(macro_db, points)
        logger.info("yfinance %s (%s): wrote %d points", name, yf_ticker, n)
    return counts


def ingest_fii_dii_recent(macro_db: Path) -> int:
    """Ingest the most recent FII/DII rows NSE exposes via its public API."""
    try:
        points = fetch_nse_fii_dii_current()
    except Exception as e:
        logger.error("NSE FII/DII fetch failed: %s", e)
        return -1
    return write_fii_dii(macro_db, points)


# ──────────────────────────────────────────────────────────────────────
# Compatibility shims (predecessor interface preservation)
# ──────────────────────────────────────────────────────────────────────


DB_PATH = Path("storage/macro.duckdb")


def read_macro(series_id: str, start, end):
    """Return a pandas DataFrame with cols (dt, value) for the given series."""
    import pandas as pd

    if isinstance(start, str):
        start_d = datetime.fromisoformat(start).date()
    else:
        start_d = start
    if isinstance(end, str):
        end_d = datetime.fromisoformat(end).date()
    else:
        end_d = end
    if not DB_PATH.exists():
        return pd.DataFrame(columns=["dt", "value"])
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = conn.execute(
            """
            SELECT dt, value FROM macro_daily
             WHERE series_id = ? AND dt BETWEEN ? AND ?
             ORDER BY dt
            """,
            (series_id, start_d, end_d),
        ).fetchdf()
    finally:
        conn.close()
    return df


def ingest_macro(start: date | None = None, end: date | None = None) -> dict[str, int]:
    """One-call orchestrator: refresh FRED + yfinance indices + FII/DII recent."""
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=400)
    counts: dict[str, int] = {}
    counts.update(ingest_fred(DB_PATH, start, end))
    counts.update(ingest_yfinance_indices(DB_PATH, start, end))
    counts["fii_dii_recent"] = ingest_fii_dii_recent(DB_PATH)
    return counts


__all__ = [
    "FRED_SERIES",
    "YFINANCE_INDEX_TICKERS",
    "DB_PATH",
    "fetch_fred_series",
    "fetch_yfinance_history",
    "fetch_nse_fii_dii_current",
    "write_macro_series",
    "write_fii_dii",
    "write_india_vix",
    "ingest_fred",
    "ingest_yfinance_indices",
    "ingest_fii_dii_recent",
    "read_macro",
    "read_macro_window",
    "read_fii_dii",
    "ingest_macro",
]
