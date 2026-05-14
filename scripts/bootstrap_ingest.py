"""Bootstrap-time ingest of safe / fast / public data sources.

Runs ALL of these in sequence (sequential is fine — none of them are slow
enough to bother parallelising and serial gives cleaner error reporting):

  1. FRED India macro indicators (CPI, repo proxy, USD/INR)
  2. yfinance Indian indices history (India VIX, Nifty 50, Bank Nifty)
  3. NSE FII/DII recent days (current public endpoint, last ~3 sessions)
  4. NSE bhav archive — last N trading days (default 30) for current
     constituents

NOT included here (run separately — supervised, long-running, or token-gated):
  - 5y NSE bhav backfill — `data/ingest_prices.ingest_range(start, end)`
  - 5y MoneyControl per-ticker news scrape — `data/ingest_news_historical`
  - NSE corporate filings 5y archive (works but takes hours; same module)
  - Dhan historical candles — needs access token (paid Data API tier we don't use)

Usage:
  uv run python -m scripts.bootstrap_ingest                # default: last 30 trading days bhav
  uv run python -m scripts.bootstrap_ingest --days 90      # extend bhav range
  uv run python -m scripts.bootstrap_ingest --skip-fred --skip-yf  # only do NSE pieces
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # source .env so the script can be invoked standalone

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=int, default=30, help="last N trading days of NSE bhav")
    p.add_argument("--skip-fred", action="store_true")
    p.add_argument("--skip-yf", action="store_true")
    p.add_argument("--skip-fii-dii", action="store_true")
    p.add_argument("--skip-bhav", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    end = date.today()
    macro_start = end - timedelta(days=400)
    bhav_start = end - timedelta(days=args.days * 2 + 30)

    summary: dict[str, object] = {}

    if not args.skip_fred:
        if not os.environ.get("FRED_API_KEY"):
            logger.error("FRED_API_KEY not set; skipping FRED ingest")
            summary["fred"] = "SKIPPED:no_key"
        else:
            logger.info("=== FRED India macros ===")
            from data.ingest_macro import DB_PATH, ingest_fred
            try:
                counts = ingest_fred(DB_PATH, macro_start, end)
                summary["fred"] = counts
            except Exception as e:
                logger.exception("FRED ingest failed: %s", e)
                summary["fred"] = f"ERROR:{e}"

    if not args.skip_yf:
        logger.info("=== yfinance Indian indices history ===")
        from data.ingest_macro import DB_PATH, ingest_yfinance_indices
        try:
            counts = ingest_yfinance_indices(DB_PATH, macro_start, end)
            summary["yfinance"] = counts
        except Exception as e:
            logger.exception("yfinance ingest failed: %s", e)
            summary["yfinance"] = f"ERROR:{e}"

    if not args.skip_fii_dii:
        logger.info("=== NSE FII/DII recent ===")
        from data.ingest_macro import DB_PATH, ingest_fii_dii_recent
        try:
            n = ingest_fii_dii_recent(DB_PATH)
            summary["fii_dii_recent"] = n
        except Exception as e:
            logger.exception("FII/DII ingest failed: %s", e)
            summary["fii_dii_recent"] = f"ERROR:{e}"

    if not args.skip_bhav:
        logger.info("=== NSE bhav (last ~%d trading days) ===", args.days)
        from data.ingest_prices import DB_PATH, ingest_range
        try:
            result = ingest_range(DB_PATH, bhav_start, end)
            summary["nse_bhav"] = result
        except Exception as e:
            logger.exception("NSE bhav ingest failed: %s", e)
            summary["nse_bhav"] = f"ERROR:{e}"

    print("\n========== bootstrap_ingest summary ==========")
    for k, v in summary.items():
        print(f"  {k:18s}  {v}")
    print("==============================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
