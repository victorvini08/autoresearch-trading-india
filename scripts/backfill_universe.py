"""Backfill historical point-in-time universe snapshots (audit 2026-05-15 Fix A).

Monthly survivorship-free snapshots across the backtest window so the
evaluator can read the PIT universe at each rebalance instead of falling
back to today's universe for all of history.

    uv run python -m scripts.backfill_universe
    uv run python -m scripts.backfill_universe --start 2020-01-01 --end 2026-05-14
"""
from __future__ import annotations

import argparse
import logging
from datetime import date

from data.ingest_prices import DB_PATH as PRICES_DB
from data.universe import DEFAULT_UNIVERSE_DB, backfill_snapshots


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=date.fromisoformat, default=date(2020, 1, 1))
    p.add_argument("--end", type=date.fromisoformat, default=date(2026, 5, 14))
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    res = backfill_snapshots(PRICES_DB, DEFAULT_UNIVERSE_DB, args.start, args.end)
    sizes = sorted(res.items())
    print(f"\nwrote {len(sizes)} snapshots")
    print("first 6:", [(d.isoformat(), n) for d, n in sizes[:6]])
    print("last 6: ", [(d.isoformat(), n) for d, n in sizes[-6:]])
    thin = [(d.isoformat(), n) for d, n in sizes if n < 50]
    if thin:
        print(f"WARNING: {len(thin)} thin snapshots (<50 members), "
              f"data-availability limited: {thin[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
