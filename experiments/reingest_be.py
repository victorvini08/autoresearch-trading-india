"""Wholesale re-ingest of the bhav archive 2017-07 -> today with the EQ+BE
series filter (T2T-hole repair). Resumable: appends each completed date to
a done-log and skips dates already there on restart.

Run:  uv run python -m experiments.reingest_be
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

from data.ingest_prices import ingest_date

DB = Path("storage/prices.duckdb")
DONE = Path("experiments/results/be_reingest_done.log")
START = date(2016, 1, 1)
END = date(2026, 6, 9)


def main() -> None:
    done: set[str] = set()
    if DONE.exists():
        done = set(DONE.read_text().split())
    d = START
    one = timedelta(days=1)
    n_days = 0
    t0 = time.time()
    while d <= END:
        if d.weekday() >= 5 or d.isoformat() in done:
            d += one
            continue
        try:
            rows = ingest_date(DB, d)
        except Exception as e:  # noqa: BLE001 — log and continue
            print(f"{d} ERROR {e}", flush=True)
            time.sleep(2.0)
            d += one
            continue
        with DONE.open("a") as fh:
            fh.write(d.isoformat() + "\n")
        n_days += 1
        if n_days % 100 == 0:
            rate = n_days / (time.time() - t0)
            print(f"{d}  rows={rows}  done={n_days}  "
                  f"({rate*60:.0f} days/min)", flush=True)
        time.sleep(0.35)
        d += one
    print(f"COMPLETE: {n_days} days re-ingested", flush=True)


if __name__ == "__main__":
    main()
