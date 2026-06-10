"""Extended-era continuous runner: 2019-01 -> 2026-06 @ Rs5L on the rebuilt
2017-06+ PIT universe (109 monthly 200-name snapshots, survivorship-verified:
DHFL/JETAIRWAYS/RELCAPITAL exit on their real blow-up dates).

This span finally contains the regimes the 2022-07+ window lacked: the COVID
crash, the FY21 V-recovery (the locked book's diagnosed compound-killer), and
the 2019 NBFC-aftermath chop — so recovery-lag fixes and the parked low-vol
candidate become honestly adjudicable instead of 2-event curve-fits.

Reports per-FY returns vs Nifty50, 5 disjoint ~18-month sub-period Sortinos
(stationarity-style min/max ratio), full-span CAGR/maxDD/Sortino, avg gross,
crash-window DD (2020-02..2020-04) and recovery capture (2020-04..2021-03).
Cash floor (idle gross @6.5%/yr) shown alongside raw, as in production policy.

Run:  PREPARE_MAX_WORKERS=1 uv run python -m experiments.run_extended <module>
e.g.  PREPARE_MAX_WORKERS=1 uv run python -m experiments.run_extended strategy
"""
from __future__ import annotations

import importlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import (
    WARMUP_CALENDAR_DAYS,
    _find_strategy_class,
    _load_feeds,
    _pit_universe,
    _score_window,
)

MACRO_DB = Path("storage/macro.duckdb")
RESULTS = Path("experiments/results")
CASH = 500_000  # overridable via argv[2]
CASH_YIELD_DAILY = (1.065) ** (1 / 252) - 1

SPAN_START = date(2019, 1, 1)
SPAN_END = date(2026, 6, 5)

FYS = [
    ("FY19p", date(2019, 1, 1), date(2019, 3, 31), "chop (partial)"),
    ("FY20", date(2019, 4, 1), date(2020, 3, 31), "slowdown+COVID"),
    ("FY21", date(2020, 4, 1), date(2021, 3, 31), "V-recovery"),
    ("FY22", date(2021, 4, 1), date(2022, 3, 31), "bull"),
    ("FY23", date(2022, 4, 1), date(2023, 3, 31), "flat/bear"),
    ("FY24", date(2023, 4, 1), date(2024, 3, 31), "roaring bull"),
    ("FY25", date(2024, 4, 1), date(2025, 3, 31), "neutral+unwind"),
    ("FY26p", date(2025, 4, 1), SPAN_END, "risk-off+crash"),
]

BUCKETS = [
    ("2019-01..2020-06", date(2019, 1, 1), date(2020, 6, 30)),
    ("2020-07..2021-12", date(2020, 7, 1), date(2021, 12, 31)),
    ("2022-01..2023-06", date(2022, 1, 1), date(2023, 6, 30)),
    ("2023-07..2024-12", date(2023, 7, 1), date(2024, 12, 31)),
    ("2025-01..2026-06", date(2025, 1, 1), SPAN_END),
]


def _nifty(idx: pd.DatetimeIndex) -> pd.Series:
    con = duckdb.connect(str(MACRO_DB), read_only=True)
    try:
        df = con.execute(
            "SELECT dt, value FROM macro_daily WHERE series_id='index_nifty_50' "
            "ORDER BY dt"
        ).fetch_df()
    finally:
        con.close()
    s = pd.Series(
        df["value"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(pd.to_datetime(df["dt"])).normalize(),
    )
    s = s[~s.index.duplicated(keep="last")]
    p = s.reindex(s.index.union(idx)).ffill().reindex(idx)
    return p.pct_change().fillna(0.0)


def _maxdd(r: pd.Series) -> float:
    if len(r) == 0:
        return 0.0
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1.0).min())


def _sortino(r: pd.Series) -> float:
    if len(r) == 0:
        return float("nan")
    dn = r[r < 0]
    dd = float(np.sqrt(np.mean(dn**2))) if len(dn) else 0.0
    return float(r.mean() / dd * np.sqrt(252)) if dd > 0 else float("inf")


def _cagr(r: pd.Series) -> float:
    if len(r) == 0:
        return float("nan")
    return float((1 + r).prod()) ** (252.0 / len(r)) - 1.0


def _sl(r: pd.Series, a: date, b: date) -> pd.Series:
    return r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]


def main() -> int:
    global CASH
    mod_name = sys.argv[1] if len(sys.argv) > 1 else "strategy"
    if len(sys.argv) > 2:
        CASH = float(sys.argv[2])
    prepare.INITIAL_CASH = CASH
    base_cls = _find_strategy_class(importlib.import_module(mod_name))
    # ragged-feed prenext fix (returns_compare.py pattern)
    cls = type("BookCont", (base_cls,), {"prenext": lambda self: self.next()})

    members, ubd = _pit_universe(SPAN_END)
    # CLOCK FIX: the strategy reads its calendar from datas[0]
    # (_is_rebalance_today / next), and alphabetical order puts a late-listing
    # name (360ONE, first bar 2023-01-23) first — a dead clock that silently
    # disables ALL rebalances before that date. Order members so the feed
    # with the deepest, densest history is datas[0].
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
    anchor = next(iter(feeds))
    print(f"clock anchor (datas[0]): {anchor}  first_dt={meta.get(anchor)}",
          flush=True)
    print(f"[{mod_name}] feeds {len(feeds)}; continuous Rs{CASH:,.0f} "
          f"{SPAN_START}..{SPAN_END} ...", flush=True)
    score = _score_window(cls, feeds, ubd, score_start=SPAN_START)

    eq = score["equity_curve"].copy()
    gross = score["gross_exposure_daily"].copy()
    eq.index = pd.to_datetime(eq.index).normalize()
    gross.index = pd.to_datetime(gross.index).normalize()
    eq = eq[eq.index >= pd.Timestamp(SPAN_START)]
    gross = gross.reindex(eq.index).ffill().fillna(0.0)

    r_raw = eq.pct_change().fillna(0.0)
    idle = (1.0 - gross.shift(1).fillna(gross.iloc[0])).clip(0.0, 1.0)
    r_cf = r_raw + idle * CASH_YIELD_DAILY
    r_n = _nifty(eq.index)

    safe = f"{mod_name.replace('.', '_')}_{int(CASH)}"
    RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "equity": eq, "gross": gross, "r_raw": r_raw, "r_cf": r_cf,
        "r_nifty50": r_n,
    }).to_csv(RESULTS / f"extended_{safe}_curve.csv")

    print(f"days={len(eq)}  avg gross={gross.mean()*100:.1f}%  "
          f"trades={score.get('trade_count', '?')}", flush=True)

    print(f"\n{'FY':6} {'regime':16} {'Nifty':>8} {'raw':>8} {'+cf':>8} "
          f"{'rawDD':>7} {'avgGr':>6}")
    for label, a, b, hint in FYS:
        rr, rc, rn = _sl(r_raw, a, b), _sl(r_cf, a, b), _sl(r_n, a, b)
        g = float(_sl(gross, a, b).mean()) if len(_sl(gross, a, b)) else 0.0
        print(f"{label:6} {hint:16} {(1+rn).prod()-1:>+8.1%} "
              f"{(1+rr).prod()-1:>+8.1%} {(1+rc).prod()-1:>+8.1%} "
              f"{_maxdd(rr):>7.1%} {g:>6.0%}")

    print(f"\n{'bucket':18} {'Sortino(cf)':>11} {'ret(cf)':>9} {'NiftyRet':>9}")
    subs = []
    for label, a, b in BUCKETS:
        rc, rn = _sl(r_cf, a, b), _sl(r_n, a, b)
        s = _sortino(rc)
        subs.append(s)
        print(f"{label:18} {s:>11.2f} {(1+rc).prod()-1:>+9.1%} "
              f"{(1+rn).prod()-1:>+9.1%}")
    finite = [s for s in subs if np.isfinite(s)]
    stat = (min(finite) / max(finite)) if finite and max(finite) > 0 else float("nan")
    print(f"sub-period min/max ratio (stationarity-style, cf): {stat:+.3f}  "
          f"min={min(finite):+.2f}")

    crash = _sl(r_raw, date(2020, 2, 1), date(2020, 4, 30))
    recov = _sl(r_cf, date(2020, 4, 1), date(2021, 3, 31))
    recov_n = _sl(r_n, date(2020, 4, 1), date(2021, 3, 31))
    full_cf, full_n = r_cf, r_n
    out = {
        "_module": mod_name, "cash": CASH,
        "span": [str(SPAN_START), str(SPAN_END)],
        "avg_gross": float(gross.mean()),
        "cagr_raw": _cagr(r_raw), "cagr_cf": _cagr(r_cf),
        "cagr_nifty": _cagr(r_n),
        "maxdd_raw": _maxdd(r_raw), "maxdd_cf": _maxdd(r_cf),
        "maxdd_nifty": _maxdd(r_n),
        "sortino_cf": _sortino(r_cf),
        "covid_crash_dd_raw": _maxdd(crash),
        "fy21_recovery_cf": float((1 + recov).prod() - 1),
        "fy21_recovery_nifty": float((1 + recov_n).prod() - 1),
        "sub_period_sortinos_cf": subs,
        "sub_period_ratio": stat,
    }
    (RESULTS / f"extended_{safe}.json").write_text(
        json.dumps(out, default=str, indent=2)
    )

    print(f"\nFULL SPAN  : CAGR raw {out['cagr_raw']:+.1%}  cf "
          f"{out['cagr_cf']:+.1%}  Nifty {out['cagr_nifty']:+.1%}")
    print(f"           : maxDD raw {out['maxdd_raw']:.1%}  cf "
          f"{out['maxdd_cf']:.1%}  Nifty {out['maxdd_nifty']:.1%}  "
          f"Sortino(cf) {out['sortino_cf']:.2f}")
    print(f"COVID crash DD (raw, 2020-02..04): {out['covid_crash_dd_raw']:.1%}  "
          f"| FY21 recovery: cf {out['fy21_recovery_cf']:+.1%} vs Nifty "
          f"{out['fy21_recovery_nifty']:+.1%}")
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
