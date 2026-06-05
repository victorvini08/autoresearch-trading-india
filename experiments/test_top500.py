'''LAST EXPERIMENT — run the EXACT locked momentum book on a TOP-500 universe
(mid/small-cap expansion) vs the locked top-200, at Rs5L:
  PART 1 — sub-period STATIONARITY (does the bigger universe stay robust?)
  PART 2 — RETURNS (is the momentum premium bigger down-cap, after costs?)

The strategy is UNCHANGED (IndiaMomentumQualityCarry); only the injected PIT
universe (and the sector-enrichment DB) is swapped to top-500. Caveat: the cost
model uses ~flat slippage, so mid-cap impact is likely UNDER-stated -> any
top-500 edge here is an optimistic upper bound.

Run:  uv run python -m experiments.test_top500
'''
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

import prepare
from prepare import (
    BACKTEST_START, TEST_BOUNDARY, WARMUP_CALENDAR_DAYS, MIN_FOLD_UNIVERSE,
    _load_feeds, _min_active_universe, _pit_universe, _score_window,
    _sub_period_sortinos, _walk_forward_folds,
)
from data.universe import get_universe_at, snapshot_dates
from backtest.metrics import sortino
from backtest.engine import run_backtest
from strategy import IndiaMomentumQualityCarry

CASH = 500_000.0
CASH_D = (1.065) ** (1 / 252) - 1
MACRO_DB = 'storage/macro.duckdb'
TOP500 = Path('storage/universe_top500.duckdb')
RUN_START = date(2019, 7, 1)
RUN_END = date(2026, 5, 14)
TRADE_START = date(2022, 7, 1)
FYS = [('FY23', date(2022, 4, 1), date(2023, 3, 31)),
       ('FY24', date(2023, 4, 1), date(2024, 3, 31)),
       ('FY25', date(2024, 4, 1), date(2025, 3, 31)),
       ('FY26p', date(2025, 4, 1), date(2026, 5, 14))]


class Mom500(IndiaMomentumQualityCarry):
    params = (('universe_db_path', str(TOP500)),)   # sectors from top-500 DB
class Mom500Cont(Mom500):
    def prenext(self): self.next()
class Mom200Cont(IndiaMomentumQualityCarry):
    def prenext(self): self.next()


def _pit500(window_end):
    sd = [d for d in snapshot_dates(TOP500) if d <= window_end]
    ubd = {d: frozenset(get_universe_at(d, TOP500)) for d in sd}
    union = sorted(set().union(*ubd.values())) if ubd else []
    return union, ubd


def _ratio(s):
    if len(s) < 2: return None
    f = 1e-3; sg = [x if abs(x) >= f else (f if x >= 0 else -f) for x in s]
    lo, hi = min(sg), max(sg)
    return lo / hi if hi > 0 else min(map(abs, sg)) / max(map(abs, sg))


def _cf(score):
    eq = score['equity_curve'].copy()
    if len(eq) < 2: return pd.Series(dtype=float), pd.Series(dtype=float)
    eq.index = pd.to_datetime(eq.index)
    ret = eq.pct_change().fillna(0.0)
    g = score['gross_exposure_daily'].copy()
    if len(g):
        g.index = pd.to_datetime(g.index); g = g.reindex(eq.index).ffill().fillna(0.0)
    else:
        g = pd.Series(0.0, index=eq.index)
    idle = (1 - g.shift(1).fillna(g.iloc[0])).clip(0, 1)
    return ret, ret + idle * CASH_D


def part1():
    prepare.INITIAL_CASH = CASH
    plan = []
    for (_a, _b, vs, ve) in _walk_forward_folds(BACKTEST_START, TEST_BOUNDARY):
        members, ubd = _pit500(ve)
        if not members or _min_active_universe(ubd, vs, ve) < MIN_FOLD_UNIVERSE:
            continue
        plan.append({'vs': vs, 've': ve, 'members': members, 'ubd': ubd})
    raw, cf, starts, grosses = [], [], [], []
    for i, p in enumerate(plan):
        feeds = _load_feeds(p['vs'] - timedelta(days=WARMUP_CALENDAR_DAYS), p['ve'], p['members'])
        sc = _score_window(Mom500, feeds, p['ubd'], score_start=p['vs'])
        r_raw, r_cf = _cf(sc)
        g = sc['gross_exposure_daily']
        grosses.append(float(g.mean()) if len(g) else 0.0)
        starts.append(p['vs'])
        raw.append(round(float(sortino(r_raw)), 4) if len(r_raw) > 1 and np.isfinite(sortino(r_raw)) else None)
        cf.append(round(float(sortino(r_cf)), 4) if len(r_cf) > 1 and np.isfinite(sortino(r_cf)) else None)
        print(f'  fold {i+1}/{len(plan)} done (gross {grosses[-1]*100:.0f}%)', flush=True)
    print(f'\n=== PART 1: TOP-500 MOMENTUM sub-period STATIONARITY @Rs5L ===', flush=True)
    print(f'  avg realized gross across folds: {np.mean(grosses)*100:.0f}% '
          f'(if ~25% the OTHER-sector cap is throttling -> result invalid)', flush=True)
    for label, per in [('raw (canonical)', raw), ('cash-floored', cf)]:
        subs = _sub_period_sortinos(starts, per); r = _ratio(subs)
        fin = [x for x in per if x is not None]
        print(f'  {label}: val Sortino mean={np.mean(fin):.3f}  '
              f'sub-periods={[round(x,3) for x in subs]}  '
              f'stationarity={r:.4f} -> {"PASS" if (r and r>=0.20) else "FAIL"}', flush=True)
    print('  [reference] TOP-200 momentum: stationarity +0.49 PASS', flush=True)


def _nifty():
    con = duckdb.connect(MACRO_DB, read_only=True)
    df = con.execute("SELECT dt,value FROM macro_daily WHERE series_id='index_nifty_50' ORDER BY dt").fetch_df()
    con.close()
    return df.set_index(pd.DatetimeIndex(df['dt']))['value'].astype(float)


def _maxdd(r):
    eq = (1 + r).cumprod().to_numpy(); return float((eq / np.maximum.accumulate(eq) - 1).min())


def _cont(cls, feeds, ubd):
    res = run_backtest(cls, feeds, initial_cash=CASH, strategy_kwargs={'universe_by_date': ubd})
    eq = res['equity_curve'].copy(); eq.index = pd.to_datetime(eq.index)
    g = res['gross_exposure_daily'].copy(); g.index = pd.to_datetime(g.index); g = g.reindex(eq.index).ffill().fillna(0.0)
    ret = eq.pct_change().fillna(0.0)
    idle = (1 - g.shift(1).fillna(g.iloc[0])).clip(0, 1)
    return ret + idle * CASH_D, g


def part2():
    prepare.INITIAL_CASH = CASH
    nifty = _nifty()
    m5, ubd5 = _pit500(RUN_END)
    feeds5 = _load_feeds(RUN_START, RUN_END, m5)
    r500, g500 = _cont(Mom500Cont, feeds5, ubd5)
    m2, ubd2 = _pit_universe(RUN_END)
    feeds2 = _load_feeds(RUN_START, RUN_END, m2)
    r200, g200 = _cont(Mom200Cont, feeds2, ubd2)
    nyrs = (RUN_END - TRADE_START).days / 365.25
    print('\n=== PART 2: RETURNS @Rs5L (continuous, +cashfloor, FY23-FY26p) ===', flush=True)
    def cum(r, a=TRADE_START, b=RUN_END):
        x = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]; return float((1 + x).prod() - 1)
    def nret(a, b):
        s = nifty[(nifty.index >= pd.Timestamp(a)) & (nifty.index <= pd.Timestamp(b))]
        return float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 1 else 0.0
    print(f'{"":22}' + ''.join(f'{fy:>9}' for fy, *_ in FYS) + f'{"CUM":>9}{"CAGR":>8}{"maxDD":>8}{"avgGr":>7}', flush=True)
    print(f'{"Nifty50":22}' + ''.join(f'{nret(a,b)*100:>+8.1f}%' for _, a, b in FYS) +
          f'{nret(TRADE_START,RUN_END)*100:>+8.1f}%{((1+nret(TRADE_START,RUN_END))**(1/nyrs)-1)*100:>+7.1f}%'
          f'{_maxdd(nifty[nifty.index>=pd.Timestamp(TRADE_START)].pct_change().fillna(0))*100:>7.1f}%{"":>7}', flush=True)
    for name, r, g in [('MOMENTUM top-200', r200, g200), ('MOMENTUM top-500', r500, g500)]:
        c = cum(r); cagr = (1 + c) ** (1 / nyrs) - 1
        tr = r[r.index >= pd.Timestamp(TRADE_START)]
        print(f'{name:22}' + ''.join(f'{cum(r,a,b)*100:>+8.1f}%' for _, a, b in FYS) +
              f'{c*100:>+8.1f}%{cagr*100:>+7.1f}%{_maxdd(tr)*100:>7.1f}%'
              f'{g[g.index>=pd.Timestamp(TRADE_START)].mean()*100:>6.0f}%', flush=True)


def main():
    part1()
    part2()
    print('\nDONE', flush=True)


if __name__ == '__main__':
    main()
