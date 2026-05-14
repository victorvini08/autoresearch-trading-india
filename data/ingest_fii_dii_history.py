"""Historical FII/DII flow backfill via moneycontrol.

NSE's public `/api/fiidiiTradeReact` endpoint only returns the last ~3
trading days. For backtest we need 5+ years of daily FII (Foreign
Institutional Investor) and DII (Domestic Institutional Investor) net
flows — the strategy's regime gate uses the rolling 20-day FII net.

moneycontrol.com publishes the daily history at:
  https://www.moneycontrol.com/markets/indian-indices/fii-dii-activity-in-india

It is a paginated HTML table; we scrape page by page until older than
the requested start date.

Output goes to `storage/macro.duckdb` table `fii_dii_daily` (same schema
as the daily-forward ingest, so the strategy reads from a single table
regardless of source).
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from data.ingest_macro import DB_PATH, write_fii_dii

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)

_BASE_URL = "https://www.moneycontrol.com/markets/indian-indices/fii-dii-activity-in-india"


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.0, min=1, max=20),
    reraise=True,
)
def _fetch_page(url: str, timeout: int = 30) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": _BROWSER_UA, "Accept": "text/html"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


_DATE_RX = re.compile(r"(\d{1,2})[\s\-/](\d{1,2}|[A-Za-z]{3})[\s\-/](\d{2,4})")


def _parse_amount(text: str) -> float | None:
    """Parse '1,234.56' or '-1,234.56' → float (₹ crore)."""
    if not text:
        return None
    cleaned = text.replace(",", "").replace("₹", "").strip()
    cleaned = cleaned.replace("(", "-").replace(")", "")  # accountancy style
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _parse_date(text: str) -> date | None:
    text = text.strip()
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_fii_dii_table(html: str) -> list[tuple[date, float, float]]:
    """Extract [(dt, fii_net_cr, dii_net_cr)] from the moneycontrol page.

    Robust to layout variations: any table with rows containing a date in
    column 0 and 'crore' amounts that include FII and DII signs is processed.
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[tuple[date, float, float]] = []
    for tbl in soup.select("table"):
        headers = [c.get_text(strip=True).lower() for c in tbl.select("thead th")]
        if not headers:
            # Some tables have inline thead
            first_row = tbl.find("tr")
            if not first_row:
                continue
            headers = [c.get_text(strip=True).lower() for c in first_row.find_all(["th", "td"])]
        # Look for a column that mentions FII net and DII net
        try:
            idx_date = next(i for i, h in enumerate(headers) if "date" in h)
        except StopIteration:
            continue
        # Prefer "net" columns; fall back to position-based defaults below.
        try:
            idx_fii_net = next(
                i for i, h in enumerate(headers) if "fii" in h and "net" in h
            )
            idx_dii_net = next(
                i for i, h in enumerate(headers) if "dii" in h and "net" in h
            )
        except StopIteration:
            # Fallback: assume columns by position — moneycontrol has historically
            # used: Date | FII gross buy | FII gross sell | FII net | DII gross buy
            # | DII gross sell | DII net
            if len(headers) >= 7:
                idx_fii_net = 3
                idx_dii_net = 6
            else:
                continue
        for row in tbl.select("tbody tr") or tbl.find_all("tr")[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(idx_fii_net, idx_dii_net):
                continue
            d = _parse_date(cells[idx_date].get_text(strip=True))
            fii = _parse_amount(cells[idx_fii_net].get_text(strip=True))
            dii = _parse_amount(cells[idx_dii_net].get_text(strip=True))
            if d is None or fii is None or dii is None:
                continue
            out.append((d, fii, dii))
    # Dedup by date — keep first occurrence (newest-first scrape order)
    seen: dict[date, tuple[date, float, float]] = {}
    for row in out:
        seen.setdefault(row[0], row)
    return sorted(seen.values())


def backfill_fii_dii(
    start: date,
    end: date | None = None,
    *,
    macro_db: Path = DB_PATH,
    max_pages: int = 200,
    polite_delay_sec: float = 1.5,
) -> int:
    """Scrape moneycontrol's daily FII/DII history walking pages until older
    than `start`. Returns total rows written.

    The moneycontrol page uses a pagination via a hidden `?date=DD-MM-YYYY`
    query that anchors the table at a given month. We walk monthly anchors
    backwards from `end` to `start`.
    """
    if end is None:
        end = date.today()
    total = 0
    cursor = end
    pages_walked = 0
    while cursor >= start and pages_walked < max_pages:
        anchor = cursor.strftime("%d-%m-%Y")
        url = f"{_BASE_URL}?date={anchor}"
        try:
            html = _fetch_page(url)
            rows = parse_fii_dii_table(html)
        except Exception as e:
            logger.warning("FII/DII page %s failed: %s", anchor, e)
            cursor = cursor - timedelta(days=30)
            pages_walked += 1
            time.sleep(polite_delay_sec * 2)
            continue
        if not rows:
            logger.info("FII/DII page %s returned 0 rows; stopping", anchor)
            break
        # Filter to our window
        rows_in_window = [r for r in rows if start <= r[0] <= end]
        if rows_in_window:
            n = write_fii_dii(macro_db, rows_in_window)
            total += n
            logger.info(
                "FII/DII anchor %s: wrote %d rows (oldest %s, newest %s)",
                anchor, n, rows_in_window[0][0], rows_in_window[-1][0],
            )
        # Move cursor back to the page-oldest date - 1 day to avoid duplicates
        oldest = min(r[0] for r in rows)
        if oldest <= start:
            break
        cursor = oldest - timedelta(days=1)
        pages_walked += 1
        time.sleep(polite_delay_sec)
    return total


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Backfill FII/DII daily history from moneycontrol")
    p.add_argument("--start", type=str, default=None, help="YYYY-MM-DD (default: 5 years ago)")
    p.add_argument("--end", type=str, default=None, help="YYYY-MM-DD (default: today)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    end = date.fromisoformat(args.end) if args.end else date.today()
    start = (
        date.fromisoformat(args.start)
        if args.start
        else end - timedelta(days=5 * 365 + 30)
    )
    n = backfill_fii_dii(start, end)
    print(f"FII/DII backfill: {n} rows written")


__all__ = [
    "parse_fii_dii_table",
    "backfill_fii_dii",
]
