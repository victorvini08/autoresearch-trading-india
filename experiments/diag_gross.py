"""Forensic diagnosis of the gross>100% breaches: re-run the locked book over
the 2023 breach window with an analyzer that records, per bar: broker cash,
broker value, summed position value, and every HELD name whose feed is STALE
(its data's current bar date lags the master clock — suspended/delisted/merged
while held, e.g. the HDFC->HDFCBANK July-2023 merger).

Run:  PREPARE_MAX_WORKERS=1 uv run python -m experiments.diag_gross
"""
from __future__ import annotations

import importlib
from datetime import date, timedelta

import backtrader as bt
import duckdb
import pandas as pd

import prepare
from prepare import (
    WARMUP_CALENDAR_DAYS,
    _find_strategy_class,
    _load_feeds,
    _pit_universe,
)
from backtest.engine import (
    DhanDeliveryCommission,
)
from backtest.costs import DEFAULT_SLIPPAGE_BPS

CASH = 500_000
SPAN_START = date(2019, 1, 1)   # full path — breach is path-dependent
SPAN_END = date(2024, 12, 31)


class Forensic(bt.Analyzer):
    def __init__(self) -> None:
        self.rows = []

    def next(self) -> None:
        st = self.strategy
        clock = max(
            (d.datetime.datetime(0) for d in st.datas if len(d)),
            default=None,
        )
        bv = float(st.broker.get_value())
        cash = float(st.broker.get_cash())
        posval = 0.0
        stale_held = []
        for d in st.datas:
            pos = st.broker.getposition(d)
            if pos.size == 0:
                continue
            v = abs(pos.size) * float(d.close[0])
            posval += v
            if len(d) and clock and d.datetime.datetime(0) < clock:
                stale_held.append(
                    (d._name, d.datetime.date(0).isoformat(), round(v))
                )
        self.rows.append({
            "clock": clock.date().isoformat() if clock else None,
            "value": bv, "cash": cash, "posval": posval,
            "gross": posval / bv if bv > 0 else float("nan"),
            "stale_held": stale_held,
        })


def main() -> None:
    prepare.INITIAL_CASH = CASH
    base = _find_strategy_class(importlib.import_module("strategy"))
    cls = type("BookCont", (base,), {"prenext": lambda self: self.next()})

    members, ubd = _pit_universe(SPAN_END)
    con = duckdb.connect("storage/prices.duckdb", read_only=True)
    try:
        meta = {
            r[0]: (r[1], -r[2])
            for r in con.execute(
                "SELECT ticker, min(dt), count(*) FROM daily_bars "
                "WHERE ticker IN (SELECT unnest(?::varchar[])) GROUP BY ticker",
                [list(members)],
            ).fetchall()
        }
    finally:
        con.close()
    members = sorted(members, key=lambda t: (*meta.get(t, (date.max, 0)), t))
    feeds = _load_feeds(
        SPAN_START - timedelta(days=WARMUP_CALENDAR_DAYS), SPAN_END, members
    )
    print(f"feeds {len(feeds)}", flush=True)

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.addstrategy(cls, universe_by_date=ubd)
    cerebro.broker.set_cash(CASH)
    cerebro.broker.addcommissioninfo(DhanDeliveryCommission())
    cerebro.broker.set_slippage_perc(
        DEFAULT_SLIPPAGE_BPS / 10_000, slip_open=True
    )
    for tkr, df in feeds.items():
        cerebro.adddata(bt.feeds.PandasData(dataname=df), name=tkr)
    cerebro.addanalyzer(Forensic, _name="forensic")
    res = cerebro.run(tradehistory=True, runonce=False)
    rows = res[0].analyzers.forensic.rows

    breaches = [r for r in rows if r["gross"] > 1.005]
    print(f"bars: {len(rows)}  breach bars (>100.5%): {len(breaches)}")
    shown = 0
    for r in rows:
        if r["gross"] > 1.005 and shown < 8:
            shown += 1
            print(f"{r['clock']}  value {r['value']:>10.0f}  cash "
                  f"{r['cash']:>10.0f}  posval {r['posval']:>10.0f}  "
                  f"gross {r['gross']*100:6.1f}%  stale_held={r['stale_held']}")
    # also show the bar before the first breach
    if breaches:
        i = rows.index(breaches[0])
        for j in (max(0, i - 2), max(0, i - 1)):
            r = rows[j]
            print(f"PRE  {r['clock']}  value {r['value']:>10.0f}  cash "
                  f"{r['cash']:>10.0f}  posval {r['posval']:>10.0f}  "
                  f"gross {r['gross']*100:6.1f}%  stale_held={r['stale_held']}")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
