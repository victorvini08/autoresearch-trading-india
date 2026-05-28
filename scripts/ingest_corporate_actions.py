"""Fetch corporate actions for held tickers from yfinance.

Updates storage/corporate_actions.json idempotently (no duplicate rows
per (ticker, ex_date, type) key). Designed to be invoked daily from the
existing `daily_update` cron — yfinance is rate-limited but light at our
universe size (~6-15 held tickers at any time).

Usage:
    uv run python -m scripts.ingest_corporate_actions
    uv run python -m scripts.ingest_corporate_actions --mode dhan-paper --lookback-days 180

Notes:
- yfinance covers dividends + splits cleanly. Bonuses, demergers, rights,
  ISIN/symbol changes, and suspensions require NSE bulletins — those land
  in the ledger via manual entry until we hook a real CA feed.
- We fetch only tickers we have ever held (broker_positions OR
  realized_trades), not the full universe. Smaller blast radius if
  yfinance rate-limits us.
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta
from pathlib import Path

from data.corporate_actions import (
    DEFAULT_CA_PATH,
    CorporateAction,
    load_corporate_actions,
    save_corporate_actions,
    upsert_action,
)
from storage.portfolio_db import connect

logger = logging.getLogger(__name__)


def held_or_historical_tickers(mode: str = "dhan-paper") -> list[str]:
    """All tickers we currently hold OR have ever traded.

    We track CAs for historical tickers too — a delisting/ISIN-change on
    a name we closed last month can still affect the realized-trade view
    (sell price was the delisting cash-out, not market close).
    """
    with connect() as c:
        rows = c.execute(
            "SELECT DISTINCT ticker FROM broker_positions WHERE mode = ? "
            "UNION SELECT DISTINCT ticker FROM realized_trades WHERE mode = ?",
            [mode, mode],
        ).fetchall()
    return sorted({r[0] for r in rows})


def fetch_yfinance_actions(
    ticker: str, lookback_days: int = 90,
) -> list[CorporateAction]:
    """Pull dividends + splits for one NSE ticker over the last lookback_days.

    yfinance returns historical actions sorted by date; we clip to the
    lookback window and translate into CorporateAction records.
    """
    import yfinance as yf  # local import — keeps tests that don't need
                            # yfinance from paying the import cost

    yf_symbol = ticker + ".NS"
    t = yf.Ticker(yf_symbol)
    cutoff = date.today() - timedelta(days=lookback_days)
    out: list[CorporateAction] = []

    try:
        dividends = t.dividends  # pandas Series indexed by Timestamp
    except Exception as e:  # noqa: BLE001
        logger.warning("yfinance dividends for %s failed: %s", ticker, e)
        dividends = None
    if dividends is not None:
        for ts, amt in dividends.items():
            ex_d = ts.date() if hasattr(ts, "date") else ts
            if ex_d >= cutoff and amt > 0:
                out.append(CorporateAction(
                    ex_date=ex_d,
                    ticker=ticker,
                    type="dividend",
                    value=float(amt),
                    notes=f"yfinance dividend ₹{amt:.2f}/share",
                ))

    try:
        splits = t.splits  # pandas Series; value = ratio (e.g. 2.0 = 1→2)
    except Exception as e:  # noqa: BLE001
        logger.warning("yfinance splits for %s failed: %s", ticker, e)
        splits = None
    if splits is not None:
        for ts, ratio in splits.items():
            ex_d = ts.date() if hasattr(ts, "date") else ts
            if ex_d >= cutoff and ratio > 0:
                out.append(CorporateAction(
                    ex_date=ex_d,
                    ticker=ticker,
                    type="split",
                    value=float(ratio),
                    notes=f"yfinance split ratio {ratio:g}",
                ))

    return out


def update_corporate_actions(
    mode: str = "dhan-paper",
    lookback_days: int = 90,
    ca_path: Path = DEFAULT_CA_PATH,
) -> int:
    """Merge fresh yfinance CAs for held/historical tickers into the ledger.

    Returns the number of NEW records added (existing rows are not modified).
    """
    existing = load_corporate_actions(ca_path)
    added = 0
    for ticker in held_or_historical_tickers(mode):
        try:
            fetched = fetch_yfinance_actions(ticker, lookback_days)
        except Exception as e:  # noqa: BLE001 — never crash on a per-ticker fail
            logger.warning("CA fetch failed for %s: %s", ticker, e)
            continue
        for ca in fetched:
            existing, was_added = upsert_action(existing, ca)
            if was_added:
                added += 1

    if added:
        existing = sorted(existing, key=lambda c: (c.ex_date, c.ticker))
        save_corporate_actions(existing, ca_path)
    return added


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest corporate actions for held tickers")
    p.add_argument("--mode", default="dhan-paper")
    p.add_argument("--lookback-days", type=int, default=90)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)
    n = update_corporate_actions(mode=args.mode, lookback_days=args.lookback_days)
    print(f"corporate_actions: {n} new record(s) added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
