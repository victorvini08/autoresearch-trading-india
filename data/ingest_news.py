"""Daily forward news ingest.

We pull from two sources for live operation:

  1. **Pulse by Zerodha RSS** (`https://pulse.zerodha.com/feed.php`)
     — aggregates MoneyControl, ET, Business Standard, Bloomberg Quint, Mint, etc.
     This is the primary "what happened today" firehose.

  2. **NSE corporate filings** (per-ticker structured events: earnings, M&A,
     board changes, regulatory orders) — high signal, low noise. Pulled
     daily as a delta against what's already in our DB.

Per-ticker historical news (5+ year archives from MoneyControl) lives in
`data/ingest_news_historical.py` — that script does a one-time bulk crawl
and is not part of the daily pipeline.

Storage: `storage/news.duckdb` table `articles(article_id, dt, source, ticker,
title, url, summary, body)`. Dedup key is SHA-1 of (title, source, dt).
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_PULSE_RSS_URL = "https://pulse.zerodha.com/feed.php"
_NSE_FILINGS_URL = (
    "https://www.nseindia.com/api/corporate-announcements"
    "?index=equities&from_date={from_d}&to_date={to_d}"
)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)


@dataclass(frozen=True)
class Article:
    article_id: str           # SHA-1 of (title, source, dt)
    dt: date
    source: str               # 'pulse_rss' | 'nse_filing' | 'moneycontrol' | 'rbi' | 'sebi'
    ticker: str | None        # NSE symbol, or None for macro-level news
    title: str
    url: str
    summary: str
    body: str                 # may be empty for pulse RSS (only summary available)


def _hash_id(title: str, source: str, dt: date) -> str:
    h = hashlib.sha1(f"{source}|{dt.isoformat()}|{title.strip().lower()}".encode())
    return h.hexdigest()


# ──────────────────────────────────────────────────────────────────────
# Pulse RSS
# ──────────────────────────────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.0, min=1, max=15),
    reraise=True,
)
def fetch_pulse_rss(timeout: int = 30) -> list[Article]:
    """Fetch the current Pulse RSS feed (~30 most-recent headlines)."""
    resp = requests.get(
        _PULSE_RSS_URL,
        headers={"User-Agent": _BROWSER_UA, "Accept": "application/rss+xml,application/xml,text/xml"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return _parse_pulse_rss(resp.content)


def _parse_pulse_rss(xml_bytes: bytes) -> list[Article]:
    out: list[Article] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.error("pulse RSS parse error: %s", e)
        return out
    channel = root.find("channel")
    if channel is None:
        return out
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date_str = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()
        if not title:
            continue
        try:
            # RFC822 format: 'Wed, 14 May 2026 09:12:00 +0530'
            dt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z").date()
        except ValueError:
            dt = date.today()
        out.append(
            Article(
                article_id=_hash_id(title, "pulse_rss", dt),
                dt=dt,
                source="pulse_rss",
                ticker=None,  # pulse doesn't pre-tag tickers reliably
                title=title,
                url=link,
                summary=_strip_html(description),
                body="",
            )
        )
    return out


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return _HTML_TAG_RE.sub("", s or "").strip()


# ──────────────────────────────────────────────────────────────────────
# NSE corporate filings (today / recent)
# ──────────────────────────────────────────────────────────────────────


def fetch_nse_filings(from_d: date, to_d: date) -> list[Article]:
    """Pull NSE corporate-announcements for the date range. Structured events."""
    headers = {
        "User-Agent": _BROWSER_UA,
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
    }
    sess = requests.Session()
    sess.headers.update(headers)
    sess.get("https://www.nseindia.com/", timeout=15)
    url = _NSE_FILINGS_URL.format(
        from_d=from_d.strftime("%d-%m-%Y"),
        to_d=to_d.strftime("%d-%m-%Y"),
    )
    try:
        resp = sess.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("NSE filings fetch failed: %s", e)
        return []
    out: list[Article] = []
    for row in payload if isinstance(payload, list) else []:
        symbol = (row.get("symbol") or "").strip().upper() or None
        subject = (row.get("subject") or row.get("desc") or "").strip()
        title = f"[{row.get('category', 'FILING')}] {subject}".strip()
        an_dt_str = (row.get("an_dt") or row.get("date") or "").strip()
        try:
            dt = datetime.strptime(an_dt_str[:10], "%Y-%m-%d").date()
        except ValueError:
            try:
                dt = datetime.strptime(an_dt_str[:10], "%d-%b-%Y").date()
            except ValueError:
                dt = date.today()
        if not title:
            continue
        url_attach = (row.get("attchmntFile") or row.get("attchmntFileName") or "").strip()
        out.append(
            Article(
                article_id=_hash_id(title, "nse_filing", dt),
                dt=dt,
                source="nse_filing",
                ticker=symbol,
                title=title,
                url=url_attach,
                summary=subject,
                body="",
            )
        )
    return out


# ──────────────────────────────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────────────────────────────


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            article_id VARCHAR PRIMARY KEY,
            dt DATE NOT NULL,
            source VARCHAR NOT NULL,
            ticker VARCHAR,
            title VARCHAR NOT NULL,
            url VARCHAR,
            summary VARCHAR,
            body VARCHAR
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS articles_dt_idx ON articles(dt)")
    conn.execute("CREATE INDEX IF NOT EXISTS articles_ticker_dt_idx ON articles(ticker, dt)")


def write_articles(news_db: Path, articles: list[Article]) -> int:
    if not articles:
        return 0
    conn = duckdb.connect(str(news_db))
    try:
        _ensure_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        try:
            inserted = 0
            for a in articles:
                # INSERT OR IGNORE on PK = SHA-1 dedup
                exists = conn.execute(
                    "SELECT 1 FROM articles WHERE article_id = ?", (a.article_id,)
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    """
                    INSERT INTO articles
                        (article_id, dt, source, ticker, title, url, summary, body)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a.article_id,
                        a.dt,
                        a.source,
                        a.ticker,
                        a.title,
                        a.url,
                        a.summary,
                        a.body,
                    ),
                )
                inserted += 1
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return inserted


# ──────────────────────────────────────────────────────────────────────
# Top-level
# ──────────────────────────────────────────────────────────────────────


def ingest_bse_for_universe(
    news_db: Path,
    universe_db: Path,
    from_d: date,
    to_d: date,
    *,
    as_of_universe: date | None = None,
    polite_delay_sec: float = 0.5,
) -> dict[str, int]:
    """PRIMARY historical-news path. For each ticker in the universe snapshot,
    resolve its BSE scrip code (ISIN-first) and pull BSE announcements for
    [from_d, to_d], writing them as Article rows with source='bse'.

    BSE's API has 9+ years of per-scrip regulatory disclosures, no bot-wall —
    unlike NSE's recent-only live API or Akamai-blocked moneycontrol.
    """
    import time

    from data.bse import (
        build_scrip_map,
        fetch_bse_announcements,
        resolve_scrip_code,
    )
    from data.universe import UniverseRow, load_universe

    snap_date = as_of_universe
    if snap_date is None:
        # use the latest snapshot available
        conn = duckdb.connect(str(universe_db), read_only=True)
        try:
            row = conn.execute("SELECT MAX(as_of_date) FROM universe_snapshot").fetchone()
        finally:
            conn.close()
        snap_date = row[0] if row and row[0] else None
    if snap_date is None:
        logger.error("no universe snapshot; run data.universe.compute_universe first")
        return {"bse": -1}

    universe: list[UniverseRow] = load_universe(universe_db, snap_date)
    scrip_map = build_scrip_map()

    total = 0
    unresolved = 0
    for u in universe:
        code = resolve_scrip_code(scrip_map, isin=u.isin, nse_symbol=u.ticker)
        if not code:
            unresolved += 1
            continue
        try:
            anns = fetch_bse_announcements(code, from_d, to_d, u.ticker)
        except Exception as e:
            logger.warning("BSE fetch failed for %s (%s): %s", u.ticker, code, e)
            time.sleep(polite_delay_sec * 4)
            continue
        articles = [
            Article(
                article_id=_hash_id(a.subject or a.headline[:80], "bse", a.dt),
                dt=a.dt,
                source="bse",
                ticker=u.ticker,
                title=a.subject or a.headline[:120],
                url=(
                    f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{a.attachment}"
                    if a.attachment
                    else ""
                ),
                summary=a.headline[:1000],
                body="",
            )
            for a in anns
        ]
        total += write_articles(news_db, articles)
        time.sleep(polite_delay_sec)
    logger.info(
        "BSE backfill %s..%s: %d articles, %d tickers unresolved",
        from_d, to_d, total, unresolved,
    )
    return {"bse": total, "unresolved": unresolved}


def ingest_today(news_db: Path) -> dict[str, int]:
    """Daily forward run: Pulse RSS + NSE filings for today."""
    counts: dict[str, int] = {}
    try:
        pulse = fetch_pulse_rss()
    except Exception as e:
        logger.error("pulse RSS failed: %s", e)
        pulse = []
    counts["pulse_rss"] = write_articles(news_db, pulse)
    today = date.today()
    try:
        nse = fetch_nse_filings(today, today)
    except Exception as e:
        logger.error("NSE filings failed: %s", e)
        nse = []
    counts["nse_filing"] = write_articles(news_db, nse)
    return counts


# ──────────────────────────────────────────────────────────────────────
# Compatibility shims (predecessor interface preservation)
# ──────────────────────────────────────────────────────────────────────


DB_PATH = Path("storage/news.duckdb")


def _upsert(rows: list[dict]) -> int:
    """Predecessor test-fixture entry point.

    `rows` accepts the legacy schema with keys:
      ticker, published_at (datetime), headline, summary, source_name | source,
      source_id, url, [body]
    Maps to our Article(article_id, dt, source, ticker, title, url, summary, body)
    and upserts into the default `storage/news.duckdb`. Returns # rows inserted.
    """
    articles: list[Article] = []
    for r in rows:
        pub = r.get("published_at")
        if hasattr(pub, "date"):
            dt = pub.date()
        elif isinstance(pub, str):
            dt = datetime.fromisoformat(pub).date()
        else:
            dt = pub or date.today()
        source = r.get("source") or r.get("source_name") or r.get("source_id") or "unknown"
        title = r.get("headline") or r.get("title") or ""
        articles.append(
            Article(
                article_id=_hash_id(title, source, dt),
                dt=dt,
                source=source,
                ticker=(r.get("ticker") or "").upper() or None,
                title=title,
                url=r.get("url", ""),
                summary=r.get("summary", ""),
                body=r.get("body", ""),
            )
        )
    return write_articles(DB_PATH, articles)


def count_news(ticker: str | None, on_date) -> int:
    """Number of articles for `ticker` on the given date (None matches macro news)."""
    if isinstance(on_date, str):
        on_date = datetime.fromisoformat(on_date).date()
    if not DB_PATH.exists():
        return 0
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        if ticker is None:
            row = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE dt = ? AND ticker IS NULL",
                (on_date,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE ticker = ? AND dt = ?",
                (ticker.upper(), on_date),
            ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def read_news(ticker: str | None, start, end):
    """Return articles for `ticker` over [start, end] inclusive (DataFrame)."""
    import pandas as pd

    if isinstance(start, str):
        start = datetime.fromisoformat(start).date()
    if isinstance(end, str):
        end = datetime.fromisoformat(end).date()
    if not DB_PATH.exists():
        return pd.DataFrame(
            columns=["article_id", "dt", "source", "ticker", "title", "url", "summary", "body"]
        )
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        if ticker is None:
            df = conn.execute(
                "SELECT * FROM articles WHERE ticker IS NULL AND dt BETWEEN ? AND ? ORDER BY dt",
                (start, end),
            ).fetchdf()
        else:
            df = conn.execute(
                "SELECT * FROM articles WHERE ticker = ? AND dt BETWEEN ? AND ? ORDER BY dt",
                (ticker.upper(), start, end),
            ).fetchdf()
    finally:
        conn.close()
    return df


__all__ = [
    "Article",
    "DB_PATH",
    "fetch_pulse_rss",
    "fetch_nse_filings",
    "write_articles",
    "ingest_today",
    "ingest_bse_for_universe",
    "count_news",
    "read_news",
]
