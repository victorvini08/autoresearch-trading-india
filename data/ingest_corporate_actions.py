"""Corporate-actions ingest (splits, bonuses, dividends).

Source: NSE corporate-actions endpoint (`/api/corporates-corporateActions`).
This is the same domain as the corporate-announcements feed used by
`data.ingest_news`; it carries the structured ex-date / ratio fields that are
not present in the announcements feed.

Storage: `storage/corp_actions.duckdb` table `corp_actions(ticker, ex_date,
record_date, action_type, ratio_num, ratio_den, raw)`.

`action_type` ∈ {'SPLIT', 'BONUS', 'DIVIDEND', 'RIGHTS', 'OTHER'}.

The backtester adjusts historical bars for SPLIT and BONUS ex-dates; DIVIDEND
adjustments are applied at ledger-write time when the cash dividend is
credited (handled by `storage.portfolio_db`).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_NSE_CORP_ACTIONS_URL = (
    "https://www.nseindia.com/api/corporates-corporateActions"
    "?index=equities&from_date={from_d}&to_date={to_d}"
)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)

_SPLIT_RX = re.compile(r"face\s*value\s*split.*?(\d+\.?\d*)\s*/?[-]?\s*to\s*(\d+\.?\d*)", re.IGNORECASE)
_BONUS_RX = re.compile(r"bonus.*?(\d+)\s*:\s*(\d+)", re.IGNORECASE)
_DIV_RX = re.compile(r"dividend.*?(?:rs\.?|₹|inr)?\s*(\d+\.?\d*)", re.IGNORECASE)


@dataclass(frozen=True)
class CorpAction:
    ticker: str
    ex_date: date
    record_date: date | None
    action_type: str       # 'SPLIT' | 'BONUS' | 'DIVIDEND' | 'RIGHTS' | 'OTHER'
    ratio_num: float | None
    ratio_den: float | None
    raw_subject: str


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.0, min=1, max=20),
    reraise=True,
)
def fetch_corp_actions(from_d: date, to_d: date) -> list[CorpAction]:
    """Pull NSE corporate-actions JSON for the date range."""
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": _BROWSER_UA,
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/companies-listing/corporate-actions",
        }
    )
    sess.get("https://www.nseindia.com/", timeout=15)
    url = _NSE_CORP_ACTIONS_URL.format(
        from_d=from_d.strftime("%d-%m-%Y"),
        to_d=to_d.strftime("%d-%m-%Y"),
    )
    resp = sess.get(url, timeout=30)
    resp.raise_for_status()
    try:
        payload = resp.json()
    except ValueError:
        logger.error("NSE corp-actions response was not JSON")
        return []
    return [
        _row_to_action(row)
        for row in (payload if isinstance(payload, list) else [])
        if _row_to_action(row) is not None
    ]


def _row_to_action(row: dict) -> CorpAction | None:
    symbol = (row.get("symbol") or "").strip().upper()
    if not symbol:
        return None
    subject = (row.get("subject") or row.get("purpose") or "").strip()
    ex_dt_s = (row.get("exDate") or "").strip()
    rec_dt_s = (row.get("recDate") or "").strip()
    try:
        ex_date = datetime.strptime(ex_dt_s[:10], "%d-%b-%Y").date()
    except ValueError:
        try:
            ex_date = datetime.strptime(ex_dt_s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    try:
        record_date = datetime.strptime(rec_dt_s[:10], "%d-%b-%Y").date()
    except ValueError:
        record_date = None
    action_type, ratio_num, ratio_den = _classify(subject)
    return CorpAction(
        ticker=symbol,
        ex_date=ex_date,
        record_date=record_date,
        action_type=action_type,
        ratio_num=ratio_num,
        ratio_den=ratio_den,
        raw_subject=subject,
    )


def _classify(subject: str) -> tuple[str, float | None, float | None]:
    s = subject.lower()
    if "split" in s:
        m = _SPLIT_RX.search(subject)
        if m:
            return ("SPLIT", float(m.group(1)), float(m.group(2)))
        return ("SPLIT", None, None)
    if "bonus" in s:
        m = _BONUS_RX.search(subject)
        if m:
            return ("BONUS", float(m.group(1)), float(m.group(2)))
        return ("BONUS", None, None)
    if "dividend" in s:
        m = _DIV_RX.search(subject)
        if m:
            return ("DIVIDEND", float(m.group(1)), 1.0)
        return ("DIVIDEND", None, None)
    if "rights" in s:
        return ("RIGHTS", None, None)
    return ("OTHER", None, None)


# ──────────────────────────────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────────────────────────────


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS corp_actions (
            ticker VARCHAR NOT NULL,
            ex_date DATE NOT NULL,
            record_date DATE,
            action_type VARCHAR NOT NULL,
            ratio_num DOUBLE,
            ratio_den DOUBLE,
            raw_subject VARCHAR,
            PRIMARY KEY (ticker, ex_date, action_type)
        )
        """
    )


def write_actions(corp_db: Path, actions: list[CorpAction]) -> int:
    if not actions:
        return 0
    conn = duckdb.connect(str(corp_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            for a in actions:
                conn.execute(
                    "DELETE FROM corp_actions WHERE ticker=? AND ex_date=? AND action_type=?",
                    (a.ticker, a.ex_date, a.action_type),
                )
                conn.execute(
                    """
                    INSERT INTO corp_actions
                        (ticker, ex_date, record_date, action_type, ratio_num,
                         ratio_den, raw_subject)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a.ticker,
                        a.ex_date,
                        a.record_date,
                        a.action_type,
                        a.ratio_num,
                        a.ratio_den,
                        a.raw_subject,
                    ),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return len(actions)


def ingest_range(corp_db: Path, from_d: date, to_d: date) -> int:
    """Top-level: pull NSE corp-actions for [from_d, to_d] and write to DB."""
    try:
        actions = fetch_corp_actions(from_d, to_d)
    except Exception as e:
        logger.error("corp-actions fetch failed: %s", e)
        return 0
    n = write_actions(corp_db, actions)
    logger.info("corp_actions: wrote %d (range %s..%s)", n, from_d, to_d)
    return n


def load_splits_bonuses(
    corp_db: Path,
    ticker: str,
    on_or_before: date,
) -> list[CorpAction]:
    """Return splits + bonuses for `ticker` on or before `on_or_before` — what the
    backtest engine needs for back-adjusting historical bars.
    """
    if not corp_db.exists():
        return []
    conn = duckdb.connect(str(corp_db), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT ticker, ex_date, record_date, action_type,
                   ratio_num, ratio_den, raw_subject
              FROM corp_actions
             WHERE ticker = ?
               AND action_type IN ('SPLIT', 'BONUS')
               AND ex_date <= ?
             ORDER BY ex_date
            """,
            (ticker, on_or_before),
        ).fetchall()
    finally:
        conn.close()
    return [CorpAction(*r) for r in rows]


__all__ = [
    "CorpAction",
    "fetch_corp_actions",
    "write_actions",
    "ingest_range",
    "load_splits_bonuses",
]
