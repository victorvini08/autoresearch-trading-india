"""Long-running 5-year historical backfills. Kick off in background — these take hours.

Run with `--source` to pick a single source, or `--all` for everything.
Each source can be resumed safely if interrupted (DuckDB upserts + the
ingest_progress table for the news scraper).

Usage:
  uv run python -m scripts.backfill_5y --source bhav         # NSE EOD prices, ~2h
  uv run python -m scripts.backfill_5y --source filings      # NSE corp filings, ~30 min
  uv run python -m scripts.backfill_5y --source rbi          # RBI press releases, ~2 min
  uv run python -m scripts.backfill_5y --source sebi         # SEBI press releases, ~2 min
  uv run python -m scripts.backfill_5y --source macro_long   # FRED extended (5y), ~1 min
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _bhav_5y() -> dict:
    from data.ingest_prices import DB_PATH, ingest_range

    end = date.today()
    start = end - timedelta(days=5 * 365 + 30)
    logger.info("NSE bhav backfill %s → %s", start, end)
    return ingest_range(DB_PATH, start, end, tickers=None, polite_delay_sec=0.8)


def _filings_5y() -> int:
    from data.ingest_news_historical import backfill_nse_filings

    news_db = Path("storage/news.duckdb")
    end = date.today()
    start = end - timedelta(days=5 * 365 + 30)
    logger.info("NSE filings backfill %s → %s", start, end)
    return backfill_nse_filings(news_db, start, end, window_days=7, polite_delay_sec=1.5)


def _rbi_5y() -> int:
    from data.ingest_news import write_articles
    from data.ingest_news_historical import fetch_rbi_press_releases

    news_db = Path("storage/news.duckdb")
    end = date.today()
    start = end - timedelta(days=5 * 365 + 30)
    logger.info("RBI press backfill %s → %s", start, end)
    articles = fetch_rbi_press_releases(start, end)
    return write_articles(news_db, articles)


def _sebi_5y() -> int:
    from data.ingest_news import write_articles
    from data.ingest_news_historical import fetch_sebi_press_releases

    news_db = Path("storage/news.duckdb")
    end = date.today()
    start = end - timedelta(days=5 * 365 + 30)
    logger.info("SEBI press backfill %s → %s", start, end)
    articles = fetch_sebi_press_releases(start, end)
    return write_articles(news_db, articles)


def _macro_long() -> dict:
    """Re-run FRED with a 5-year lookback so monthly series (CPI, repo) populate."""
    import os

    from data.ingest_macro import DB_PATH, ingest_fred, ingest_yfinance_indices

    end = date.today()
    start = end - timedelta(days=5 * 365 + 30)
    out = {}
    api_key = os.environ.get("FRED_API_KEY")
    if api_key:
        out["fred"] = ingest_fred(DB_PATH, start, end, api_key=api_key)
    out["yfinance"] = ingest_yfinance_indices(DB_PATH, start, end)
    return out


def _bse_news_5y() -> dict:
    """PRIMARY 5y per-ticker news: BSE announcements API (9+ years, no bot-wall)."""
    from data.ingest_news import ingest_bse_for_universe

    news_db = Path("storage/news.duckdb")
    universe_db = Path("storage/universe.duckdb")
    end = date.today()
    start = end - timedelta(days=5 * 365 + 30)
    logger.info("BSE news backfill %s → %s (universe-scoped)", start, end)
    return ingest_bse_for_universe(news_db, universe_db, start, end)


def _earnings_5y() -> int:
    """PRIMARY 5y earnings: yfinance .NS get_earnings_dates for the universe."""
    from data.ingest_earnings import ingest_yfinance_earnings
    from data.universe import get_live_universe

    universe_db = Path("storage/universe.duckdb")
    earnings_db = Path("storage/news.duckdb")  # earnings_calendar lives alongside news
    tickers = get_live_universe(universe_db)
    if not tickers:
        logger.error("no universe snapshot; run compute_universe first")
        return -1
    # Bound to the backtest window (BACKTEST_START=2020-01-01) with ~1y of
    # margin; yfinance otherwise returns 20+ years for blue-chips which we
    # never read.
    since = date(2019, 1, 1)
    logger.info("yfinance earnings backfill for %d tickers since %s", len(tickers), since)
    return ingest_yfinance_earnings(tickers, earnings_db, limit=60, since=since)


_SOURCES = {
    "bhav": _bhav_5y,
    "filings": _filings_5y,
    "bse_news": _bse_news_5y,
    "earnings": _earnings_5y,
    "rbi": _rbi_5y,
    "sebi": _sebi_5y,
    "macro_long": _macro_long,
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", choices=list(_SOURCES.keys()), help="run a single source")
    p.add_argument("--all", action="store_true", help="run every source sequentially")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not args.source and not args.all:
        p.error("must pass --source or --all")

    sources = list(_SOURCES.keys()) if args.all else [args.source]
    summary: dict[str, object] = {}
    for name in sources:
        try:
            summary[name] = _SOURCES[name]()
        except Exception as e:
            logger.exception("%s failed: %s", name, e)
            summary[name] = f"ERROR:{e}"
    print("\n==== backfill_5y summary ====")
    for k, v in summary.items():
        print(f"  {k:14s}  {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
