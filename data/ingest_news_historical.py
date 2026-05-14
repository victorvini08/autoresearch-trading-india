"""Bulk historical news scrape — one-time backfill, NOT part of the daily pipeline.

Scope: 5+ years of per-ticker news for the ~200-name universe, plus RBI / SEBI
press releases (macro signal). Each source has a distinct strategy:

  - **MoneyControl per-ticker** (primary): polite scrape (~1 req/sec, browser
    User-Agent) of `https://www.moneycontrol.com/india/news/<slug>/.../<ticker_code>`
    archive pages. Pagination via `?pgno=N`. Saves ~150k articles total.

  - **NSE corporate filings archive** (structured events): already covered by
    `data.ingest_news.fetch_nse_filings` over historical date ranges. This
    module orchestrates the date-range loop.

  - **RBI press release archive**: HTML pages indexed by month at
    `rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=...`. Pull the listing,
    parse each release.

  - **SEBI press release archive**: structured XML feed +
    `sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=10`.

This module is intentionally fragile-tolerant: each source can fail without
killing the others, and progress is checkpointed in `storage/news.duckdb` so
re-running picks up where the last run died. **Run supervised** — the user
should kick this off when awake; it takes ~10-12 hours total.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from data.ingest_news import (
    Article,
    _hash_id,
    fetch_nse_filings,
    write_articles,
)

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)


@dataclass(frozen=True)
class IngestProgress:
    source: str
    ticker: str | None
    last_dt_completed: date | None
    last_offset: int       # cursor into source's pagination (page number / offset)


def _ensure_progress_table(news_db: Path) -> None:
    conn = duckdb.connect(str(news_db))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_progress (
                source VARCHAR NOT NULL,
                ticker VARCHAR,
                last_dt_completed DATE,
                last_offset INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source, COALESCE(ticker, ''))
            )
            """
        )
    finally:
        conn.close()


def get_progress(news_db: Path, source: str, ticker: str | None = None) -> IngestProgress | None:
    if not news_db.exists():
        return None
    conn = duckdb.connect(str(news_db), read_only=True)
    try:
        # Check if table exists
        tbl = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name='ingest_progress'"
        ).fetchone()
        if not tbl:
            return None
        row = conn.execute(
            "SELECT last_dt_completed, last_offset FROM ingest_progress "
            "WHERE source=? AND COALESCE(ticker,'')=COALESCE(?,'')",
            (source, ticker),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return IngestProgress(source=source, ticker=ticker, last_dt_completed=row[0], last_offset=row[1])


def update_progress(
    news_db: Path,
    source: str,
    ticker: str | None,
    last_dt: date | None,
    last_offset: int,
) -> None:
    _ensure_progress_table(news_db)
    conn = duckdb.connect(str(news_db))
    try:
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute(
                "DELETE FROM ingest_progress WHERE source=? AND COALESCE(ticker,'')=COALESCE(?,'')",
                (source, ticker),
            )
            conn.execute(
                """
                INSERT INTO ingest_progress (source, ticker, last_dt_completed, last_offset)
                VALUES (?, ?, ?, ?)
                """,
                (source, ticker, last_dt, last_offset),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────
# MoneyControl per-ticker archive
# ──────────────────────────────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2.0, min=2, max=60),
    reraise=True,
)
def _mc_page(url: str, timeout: int = 30) -> str | None:
    resp = requests.get(
        url,
        headers={"User-Agent": _BROWSER_UA, "Accept": "text/html"},
        timeout=timeout,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.text


def scrape_moneycontrol_ticker(
    ticker_slug: str,
    ticker_code: str,
    nse_symbol: str,
    *,
    start_date: date,
    max_pages: int = 200,
    polite_delay_sec: float = 1.0,
) -> list[Article]:
    """Walk MoneyControl's per-ticker news pages backwards until articles
    predate `start_date` or `max_pages` is reached.

    URL form (varies by name; the slug+code combination uniquely identifies a stock):
        https://www.moneycontrol.com/india/news/<ticker_slug>/<ticker_code>?pgno=N

    `nse_symbol` is what we'll write into `articles.ticker` for join compatibility.
    """
    out: list[Article] = []
    for page in range(1, max_pages + 1):
        url = (
            f"https://www.moneycontrol.com/news/tags/{ticker_slug}.html?pgno={page}"
        )
        try:
            html = _mc_page(url)
        except requests.RequestException as e:
            logger.warning("MC %s p%d failed: %s", nse_symbol, page, e)
            time.sleep(polite_delay_sec * 4)
            continue
        if html is None:
            break
        soup = BeautifulSoup(html, "lxml")
        items = soup.select("li.clearfix, article.clearfix, li.article_list")
        if not items:
            break
        oldest_on_page: date | None = None
        for li in items:
            title_el = li.select_one("h2 a, a.heading") or li.select_one("a")
            date_el = li.select_one("span.gray11, span.article-date, span.fl_arial")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            url_attach = title_el.get("href", "")
            dt: date | None = None
            if date_el:
                txt = date_el.get_text(strip=True)
                for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y"):
                    try:
                        dt = datetime.strptime(txt[: len(fmt) + 4], fmt).date()
                        break
                    except ValueError:
                        continue
            if dt is None:
                dt = date.today()
            if dt < start_date:
                oldest_on_page = dt
                continue
            out.append(
                Article(
                    article_id=_hash_id(title, "moneycontrol", dt),
                    dt=dt,
                    source="moneycontrol",
                    ticker=nse_symbol,
                    title=title,
                    url=url_attach,
                    summary="",
                    body="",
                )
            )
            oldest_on_page = dt if oldest_on_page is None or dt < oldest_on_page else oldest_on_page
        time.sleep(polite_delay_sec)
        if oldest_on_page is not None and oldest_on_page < start_date:
            break
    return out


# ──────────────────────────────────────────────────────────────────────
# RBI press releases
# ──────────────────────────────────────────────────────────────────────


def fetch_rbi_press_releases(start: date, end: date) -> list[Article]:
    """Walk the RBI press-release listing pages. The format is monthly.

    Source: https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx
    """
    out: list[Article] = []
    listing_url = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
    try:
        resp = requests.get(
            listing_url,
            headers={"User-Agent": _BROWSER_UA, "Accept": "text/html"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.error("RBI listing fetch failed: %s", e)
        return out
    for a in soup.select("a"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if not title or "PressReleaseDisplay" not in href:
            continue
        # RBI listing tends to lack inline dates; we attempt the row's parent for a sibling date cell
        parent = a.find_parent("tr") or a.parent
        dt = None
        if parent:
            cells = parent.find_all("td") if hasattr(parent, "find_all") else []
            for cell in cells:
                txt = cell.get_text(strip=True)
                for fmt in ("%b %d, %Y", "%d %b %Y"):
                    try:
                        dt = datetime.strptime(txt[: len(fmt) + 4], fmt).date()
                        break
                    except ValueError:
                        continue
                if dt:
                    break
        if dt is None:
            dt = date.today()
        if not (start <= dt <= end):
            continue
        url = href if href.startswith("http") else "https://www.rbi.org.in/" + href.lstrip("/")
        out.append(
            Article(
                article_id=_hash_id(title, "rbi", dt),
                dt=dt,
                source="rbi",
                ticker=None,
                title=title,
                url=url,
                summary="",
                body="",
            )
        )
    return out


# ──────────────────────────────────────────────────────────────────────
# SEBI press releases
# ──────────────────────────────────────────────────────────────────────


def fetch_sebi_press_releases(start: date, end: date) -> list[Article]:
    """Walk SEBI press releases. Source: sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=10"""
    out: list[Article] = []
    url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=10&smid=0"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _BROWSER_UA, "Accept": "text/html"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.error("SEBI listing fetch failed: %s", e)
        return out
    for a in soup.select("a"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if not title or "/cms" not in href:
            continue
        parent = a.find_parent("tr") or a.parent
        dt = None
        if parent:
            cells = parent.find_all("td") if hasattr(parent, "find_all") else []
            for cell in cells:
                txt = cell.get_text(strip=True)
                for fmt in ("%b %d, %Y", "%d %b %Y", "%d-%b-%Y"):
                    try:
                        dt = datetime.strptime(txt[: len(fmt) + 4], fmt).date()
                        break
                    except ValueError:
                        continue
                if dt:
                    break
        if dt is None:
            continue
        if not (start <= dt <= end):
            continue
        link = href if href.startswith("http") else "https://www.sebi.gov.in" + href
        out.append(
            Article(
                article_id=_hash_id(title, "sebi", dt),
                dt=dt,
                source="sebi",
                ticker=None,
                title=title,
                url=link,
                summary="",
                body="",
            )
        )
    return out


# ──────────────────────────────────────────────────────────────────────
# NSE filings historical (date-range loop over the daily endpoint)
# ──────────────────────────────────────────────────────────────────────


def backfill_nse_filings(
    news_db: Path,
    start: date,
    end: date,
    *,
    window_days: int = 7,
    polite_delay_sec: float = 1.5,
) -> int:
    """Walk NSE corporate-announcements API in rolling windows.

    NSE limits each query window to ~30 days; we use a smaller window for safety
    and idempotent restartability. Resumes from `ingest_progress`.
    """
    progress = get_progress(news_db, "nse_filing_historical")
    cursor = progress.last_dt_completed + timedelta(days=1) if progress and progress.last_dt_completed else start
    total = 0
    while cursor <= end:
        window_end = min(cursor + timedelta(days=window_days - 1), end)
        try:
            articles = fetch_nse_filings(cursor, window_end)
            n = write_articles(news_db, articles)
            total += n
            logger.info(
                "NSE filings backfill %s..%s: %d new", cursor, window_end, n
            )
        except Exception as e:
            logger.error("NSE backfill window %s..%s failed: %s", cursor, window_end, e)
        update_progress(news_db, "nse_filing_historical", None, window_end, 0)
        cursor = window_end + timedelta(days=1)
        time.sleep(polite_delay_sec)
    return total


# ──────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────


def backfill_macro_press_releases(
    news_db: Path,
    start: date,
    end: date,
) -> dict[str, int]:
    """Backfill RBI + SEBI press releases (lighter than ticker-news scraping)."""
    out: dict[str, int] = {}
    try:
        rbi = fetch_rbi_press_releases(start, end)
        out["rbi"] = write_articles(news_db, rbi)
    except Exception as e:
        logger.error("RBI backfill failed: %s", e)
        out["rbi"] = -1
    try:
        sebi = fetch_sebi_press_releases(start, end)
        out["sebi"] = write_articles(news_db, sebi)
    except Exception as e:
        logger.error("SEBI backfill failed: %s", e)
        out["sebi"] = -1
    return out


__all__ = [
    "IngestProgress",
    "get_progress",
    "update_progress",
    "scrape_moneycontrol_ticker",
    "fetch_rbi_press_releases",
    "fetch_sebi_press_releases",
    "backfill_nse_filings",
    "backfill_macro_press_releases",
]
