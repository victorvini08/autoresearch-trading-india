"""BSE India helpers — scrip-code mapping + corporate-announcements fetch.

BSE's public API exposes 9+ years of per-scrip regulatory disclosures with no
bot-wall (only a Referer header). This is our PRIMARY historical news source
(NSE's live API is recent-only; moneycontrol is Akamai-blocked).

Two endpoints:

  ListofScripData — full active equity list with NSE-style symbol + ISIN:
    GET https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w
        ?Group=&Scripcode=&industry=&segment=Equity&status=Active
    → [{SCRIP_CD, Scrip_Name, ISIN_NUMBER, scrip_id (=NSE symbol), ...}]

  AnnGetData — paginated corporate announcements for a scrip + date range:
    GET https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w
        ?strCat=-1&strPrevDate=YYYYMMDD&strToDate=YYYYMMDD
        &strScrip=<bse_code>&strSearch=P&strType=C
    → {Table: [{NEWSID, SCRIP_CD, NEWSSUB, NEWS_DT, HEADLINE,
                 ATTACHMENTNAME, ...}], Table1: [{ROWCNT/TotalPageCnt}]}

Mapping strategy: join our universe's ISIN → BSE ISIN_NUMBER (most robust;
symbols occasionally differ between exchanges). Fall back to scrip_id == NSE
symbol. The map is cached locally and refreshed weekly.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_BSE_BASE = "https://api.bseindia.com/BseIndiaAPI/api"
_SCRIP_LIST_URL = (
    f"{_BSE_BASE}/ListofScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
)
_ANN_URL = f"{_BSE_BASE}/AnnGetData/w"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
    ),
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}

SCRIP_MAP_CACHE = Path("storage/bse_scrip_map.json")


@dataclass(frozen=True)
class BseAnnouncement:
    scrip_code: str
    nse_symbol: str | None
    dt: date
    subject: str
    headline: str
    attachment: str
    news_id: str


# ──────────────────────────────────────────────────────────────────────
# Scrip-code map
# ──────────────────────────────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1.0, min=1, max=30),
    reraise=True,
)
def fetch_scrip_list() -> list[dict]:
    resp = requests.get(_SCRIP_LIST_URL, headers=_HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.json()


def build_scrip_map(
    cache_path: Path = SCRIP_MAP_CACHE,
    *,
    max_age_days: float = 7.0,
    force: bool = False,
) -> dict:
    """Return {'by_isin': {ISIN: scrip_code}, 'by_symbol': {NSE_SYM: scrip_code}}.

    Cached to `cache_path`; refreshed if older than `max_age_days`.
    """
    if not force and cache_path.exists():
        age = (time.time() - cache_path.stat().st_mtime) / 86400.0
        if age < max_age_days:
            try:
                return json.loads(cache_path.read_text())
            except (OSError, ValueError):
                pass

    rows = fetch_scrip_list()
    by_isin: dict[str, str] = {}
    by_symbol: dict[str, str] = {}
    for r in rows:
        code = str(r.get("SCRIP_CD") or "").strip()
        if not code:
            continue
        isin = (r.get("ISIN_NUMBER") or "").strip().upper()
        sym = (r.get("scrip_id") or "").strip().upper()
        if isin:
            by_isin.setdefault(isin, code)
        if sym:
            by_symbol.setdefault(sym, code)
    out = {"by_isin": by_isin, "by_symbol": by_symbol}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(out))
    logger.info(
        "BSE scrip map: %d ISINs, %d symbols", len(by_isin), len(by_symbol)
    )
    return out


def resolve_scrip_code(
    scrip_map: dict,
    *,
    isin: str | None = None,
    nse_symbol: str | None = None,
) -> str | None:
    """ISIN first (cross-exchange-stable), then NSE symbol."""
    if isin:
        code = scrip_map.get("by_isin", {}).get(isin.strip().upper())
        if code:
            return code
    if nse_symbol:
        return scrip_map.get("by_symbol", {}).get(nse_symbol.strip().upper())
    return None


# ──────────────────────────────────────────────────────────────────────
# Announcements
# ──────────────────────────────────────────────────────────────────────


def _parse_news_dt(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:26] if "." in s else s[:19], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.0, min=1, max=20),
    reraise=True,
)
def _fetch_ann_page(
    scrip_code: str, from_d: date, to_d: date, page: int
) -> dict:
    params = {
        "strCat": "-1",
        "strPrevDate": from_d.strftime("%Y%m%d"),
        "strToDate": to_d.strftime("%Y%m%d"),
        "strScrip": scrip_code,
        "strSearch": "P",
        "strType": "C",
        "pageno": str(page),
    }
    resp = requests.get(_ANN_URL, headers=_HEADERS, params=params, timeout=45)
    resp.raise_for_status()
    return resp.json()


def parse_announcements(
    payload: dict, scrip_code: str, nse_symbol: str | None
) -> list[BseAnnouncement]:
    out: list[BseAnnouncement] = []
    for row in payload.get("Table", []) or []:
        d = _parse_news_dt(row.get("NEWS_DT") or row.get("DT_TM") or "")
        if d is None:
            continue
        out.append(
            BseAnnouncement(
                scrip_code=str(row.get("SCRIP_CD") or scrip_code),
                nse_symbol=nse_symbol,
                dt=d,
                subject=(row.get("NEWSSUB") or "").strip(),
                headline=(row.get("HEADLINE") or "").strip(),
                attachment=(row.get("ATTACHMENTNAME") or "").strip(),
                news_id=str(row.get("NEWSID") or ""),
            )
        )
    return out


def _total_pages(payload: dict) -> int:
    t1 = payload.get("Table1") or []
    if t1 and isinstance(t1, list):
        for k in ("TotalPageCnt", "ROWCNT", "PageCnt"):
            v = t1[0].get(k)
            if v:
                try:
                    n = int(v)
                    # ROWCNT is row count; assume 50/page
                    return n if k.endswith("PageCnt") else max(1, (n + 49) // 50)
                except (TypeError, ValueError):
                    pass
    return 1


def fetch_bse_announcements(
    scrip_code: str,
    from_d: date,
    to_d: date,
    nse_symbol: str | None = None,
    *,
    max_pages: int = 40,
    polite_delay_sec: float = 0.6,
) -> list[BseAnnouncement]:
    """Fetch all announcements for a scrip in [from_d, to_d], following pagination."""
    first = _fetch_ann_page(scrip_code, from_d, to_d, 1)
    anns = parse_announcements(first, scrip_code, nse_symbol)
    pages = min(_total_pages(first), max_pages)
    for p in range(2, pages + 1):
        time.sleep(polite_delay_sec)
        try:
            payload = _fetch_ann_page(scrip_code, from_d, to_d, p)
        except requests.RequestException as e:
            logger.warning("BSE %s page %d failed: %s", scrip_code, p, e)
            break
        page_anns = parse_announcements(payload, scrip_code, nse_symbol)
        if not page_anns:
            break
        anns.extend(page_anns)
    return anns


__all__ = [
    "BseAnnouncement",
    "fetch_scrip_list",
    "build_scrip_map",
    "resolve_scrip_code",
    "fetch_bse_announcements",
    "parse_announcements",
    "SCRIP_MAP_CACHE",
]
